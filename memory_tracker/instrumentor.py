import ast
import sys
import os
import traceback

from .injector import DecoratorInjector
from .importer import SourceTransformImporter


# ============================================================
# Internal utilities
# ============================================================


def find_insertion_index_for_imports(module_node: ast.Module) -> int:
    """Returns the correct index for inserting imports at the top of a module.

    The insertion index is computed as follows:
    - Skip the initial module docstring, if present.
    - Skip any "from __future__ import ..." statements.

    Args:
        module_node: The parsed AST module node.

    Returns:
        The index (int) where new imports should be inserted.
    """
    idx = 0

    # skip initial docstring
    if module_node.body:
        first = module_node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            idx = 1

    # skip "from __future__ import ..." statements
    while (
        idx < len(module_node.body)
        and isinstance(module_node.body[idx], ast.ImportFrom)
        and getattr(module_node.body[idx], 'module', '') == '__future__'
    ):
        idx += 1

    return idx


def ensure_module_import(
    tree: ast.Module, module_name: str, alias_name: str, asname: str
) -> ast.Module:
    """Ensures a specific instrumentation import exists in the module.

    If the import already exists, it will not be inserted again. Otherwise,
    a properly placed `from <module_name> import <alias_name> as <asname>`
    node is added at the correct position.

    Args:
        tree: The AST module representing the source code.
        module_name: Name of the module to import from.
        alias_name: Name of the imported function or symbol.
        asname: Alias used in the import.

    Returns:
        The updated AST module node.
    """
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            for alias in node.names:
                if alias.name == alias_name:
                    return tree

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module_name:
                    return tree

    insert_idx = find_insertion_index_for_imports(tree)
    import_node = ast.ImportFrom(
        module=module_name,
        names=[ast.alias(name=alias_name, asname=asname)],
        level=0,
    )
    tree.body.insert(insert_idx, import_node)
    return tree


# ============================================================
# Main instrumentation functions
# ============================================================


def instrument_source(source: str, path: str):
    """Parses, transforms, and compiles Python source code.

    This function:
    - Parses the source into an AST.
    - Ensures the instrumentation decorator is imported.
    - Injects decorators into functions using `DecoratorInjector`.
    - Compiles the modified AST into a code object.

    Args:
        source: The original Python source code.
        path: The filesystem path of the file (used for compile metadata).

    Returns:
        A tuple `(code_obj, tree)` where:
            code_obj: The compiled Python code object.
            tree: The modified AST object (useful for debugging).
    """
    tree = ast.parse(source, filename=path)

    # ensure import for instrumentation decorator
    tree = ensure_module_import(
        tree, 'memory_tracker.profiler', 'tracked_profile', 'm__mp_profile'
    )

    # inject decorators
    injector = DecoratorInjector(
        [
            'm__mp_profile',
            'tracked_profile',
            'property',
            'setter',
            'getter',
            'delete',
            'staticmethod',
        ],
        'm__mp_profile',
    )
    tree = injector.visit(tree)
    ast.fix_missing_locations(tree)

    return compile(tree, filename=path, mode='exec'), tree


# ============================================================
# Instrumented execution
# ============================================================


def prepare_instrumented_code(path_to_script: str):
    """Reads and instruments a Python script, returning its executable components.

    The function:
    - Loads the file from disk.
    - Injects instrumentation decorators via AST transformation.
    - Prepares a `__main__`-like globals dictionary.
    - Adjusts the working directory and `sys.path` for execution.

    It does **not** execute the code. Instead, it returns values required
    for later execution.

    Args:
        path_to_script: Path to the Python file to instrument.

    Returns:
        A tuple `(code_obj, module_globals, cleanup_callback)` where:
            code_obj: The compiled instrumented code.
            module_globals: A dict representing the execution namespace.
            cleanup_callback: A function that restores environment changes.

    Raises:
        SystemExit: If the file cannot be read or contains syntax errors.
    """
    abspath = os.path.abspath(path_to_script)
    target_dir = os.path.dirname(abspath) or '.'

    # adjust environment
    sys.path.insert(0, target_dir)
    old_cwd = os.getcwd()
    os.chdir(target_dir)

    def cleanup():
        """Restores the previous working directory and sys.path."""
        os.chdir(old_cwd)
        try:
            sys.path.remove(target_dir)
        except ValueError:
            pass

    # read script
    try:
        with open(abspath, 'r', encoding='utf-8') as f:
            src = f.read()
    except OSError as e:
        print(f'Failed to read file {abspath}: {e}', file=sys.stderr)
        cleanup()
        sys.exit(1)

    # instrument source
    try:
        code_obj, _ = instrument_source(src, abspath)
    except SyntaxError as e:
        print('Syntax error while parsing script:', e, file=sys.stderr)
        cleanup()
        sys.exit(1)

    module_globals = {
        '__name__': '__main__',
        '__file__': abspath,
        '__package__': None,
        '__cached__': None,
    }

    return code_obj, module_globals, cleanup


def execute_instrumented_code(code_obj, module_globals, extra_argv=None):
    """Executes a previously instrumented code object.

    This function:
    - Replaces ``sys.argv`` to simulate normal script execution.
    - Installs a custom import hook (`SourceTransformImporter`) so that
      future imports are also instrumented.
    - Executes the provided code object inside the prepared namespace.

    Args:
        code_obj: The compiled instrumented code object.
        module_globals: The namespace in which the code will execute.
        extra_argv: Optional list of additional command-line arguments.

    Raises:
        SystemExit: Propagated if the executed script calls sys.exit().
    """
    abspath = module_globals['__file__']

    # adjust sys.argv
    sys_argv_saved = sys.argv
    sys.argv = [abspath] + (extra_argv or [])

    target_dir = os.path.dirname(abspath)
    importer = SourceTransformImporter(target_dir, instrument_source)
    sys.meta_path.insert(0, importer)

    try:
        exec(code_obj, module_globals)

    except SystemExit:
        raise

    except Exception:
        traceback.print_exc()
        sys.exit(1)

    finally:
        sys.argv = sys_argv_saved
        try:
            sys.meta_path.remove(importer)
        except ValueError:
            pass


def run_instrumented(path_to_script: str, extra_argv=None):
    """Convenience function that prepares and executes an instrumented script.

    This wraps both:
    - `prepare_instrumented_code()`
    - `execute_instrumented_code()`

    And guarantees environment cleanup afterwards.

    Args:
        path_to_script: Path to the Python file to instrument and execute.
        extra_argv: Additional command-line arguments to pass to the script.
    """
    code_obj, module_globals, cleanup = prepare_instrumented_code(
        path_to_script
    )

    try:
        execute_instrumented_code(
            code_obj, module_globals, extra_argv=extra_argv
        )
    finally:
        cleanup()
