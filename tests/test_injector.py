import ast
from memory_tracker.injector import DecoratorInjector


def test_injector_adds_decorator():
    source = """
def foo():
    return 42
"""
    tree = ast.parse(source)
    injector = DecoratorInjector(["__mp_profile"], "__mp_profile")
    tree = injector.visit(tree)
    ast.fix_missing_locations(tree)

    # Extrai a função decorada
    func_node = tree.body[0]
    assert isinstance(func_node.decorator_list[0], ast.Name)
    assert func_node.decorator_list[0].id == "__mp_profile"
