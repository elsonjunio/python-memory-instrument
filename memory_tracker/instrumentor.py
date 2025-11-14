import ast
import sys
import os
import traceback

from .injector import DecoratorInjector
from .importer import SourceTransformImporter


# ============================================================
# Utilitários internos
# ============================================================

def find_insertion_index_for_imports(module_node: ast.Module) -> int:
    """
    Retorna o índice adequado (após docstring e 'from __future__' imports)
    para inserir novos imports no início do módulo.
    """
    idx = 0

    # pula docstring inicial
    if module_node.body:
        first = module_node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            idx = 1

    # pula importações do tipo "from __future__ import ..."
    while (
        idx < len(module_node.body)
        and isinstance(module_node.body[idx], ast.ImportFrom)
        and getattr(module_node.body[idx], 'module', '') == '__future__'
    ):
        idx += 1

    return idx


def ensure_module_import(tree: ast.Module, module_name: str, alias_name: str, asname: str) -> ast.Module:
    """
    Garante que o módulo de instrumentação (ex: 'metrics.track') esteja importado.
    Caso já exista, não insere duplicado.
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
# Funções principais de instrumentação
# ============================================================

def instrument_source(source: str, path: str):
    """
    Constrói a AST do código-fonte, injeta decorators e retorna o code object compilado.
    """
    tree = ast.parse(source, filename=path)

    # garante import para o decorator rastreador
    tree = ensure_module_import(tree, 'memory_tracker.profiler', 'tracked_profile', 'm__mp_profile')

    # injeta o decorator nas funções
    injector = DecoratorInjector(['m__mp_profile', 'tracked_profile', 'property', 'setter', 'getter', 'delete', 'staticmethod'], 'm__mp_profile')
    tree = injector.visit(tree)
    ast.fix_missing_locations(tree)

    # retorna o código compilado + AST para depuração
    return compile(tree, filename=path, mode='exec'), tree


# ============================================================
# Função principal: execução instrumentada
# ============================================================

def run_instrumented(path_to_script: str, extra_argv=None):
    """
    Lê um script Python, instrumenta em tempo real e executa como '__main__'.
    Permite também instrumentar módulos importados durante a execução.
    """
    abspath = os.path.abspath(path_to_script)
    target_dir = os.path.dirname(abspath) or '.'

    # Ajusta ambiente de execução
    sys.path.insert(0, target_dir)
    old_cwd = os.getcwd()
    os.chdir(target_dir)

    try:
        with open(abspath, 'r', encoding='utf-8') as f:
            src = f.read()
    except OSError as e:
        print(f'Erro ao ler arquivo {abspath}: {e}', file=sys.stderr)
        sys.exit(1)

    # Compila o código instrumentado
    try:
        code_obj, _ = instrument_source(src, abspath)
    except SyntaxError as e:
        print('Erro de sintaxe ao parsear o arquivo alvo:', e, file=sys.stderr)
        os.chdir(old_cwd)
        sys.exit(1)

    # Prepara ambiente de execução do script
    module_globals = {
        '__name__': '__main__',
        '__file__': abspath,
        '__package__': None,
        '__cached__': None,
    }

    # Ajusta sys.argv para simular execução normal
    sys_argv_saved = sys.argv
    sys.argv = [abspath] + (extra_argv or [])

    # Executa com importação instrumentada
    try:
        importer = SourceTransformImporter(target_dir, instrument_source)
        sys.meta_path.insert(0, importer)

        exec(code_obj, module_globals)

    except SystemExit:
        raise  # respeita sys.exit() do script alvo

    except Exception:
        traceback.print_exc()
        sys.exit(1)

    finally:
        # restaura ambiente
        sys.argv = sys_argv_saved
        os.chdir(old_cwd)
        try:
            sys.path.remove(target_dir)
        except ValueError:
            pass
