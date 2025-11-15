import ast
from typing import Iterable


class DecoratorInjector(ast.NodeTransformer):
    """
    Injeta automaticamente um decorator específico em todas as funções de um módulo
    (incluindo funções assíncronas), caso ele ainda não esteja presente.

    É usada para instrumentar código automaticamente antes da execução,
    adicionando o decorator configurado (ex: `@tracked_profile`).
    """

    def __init__(self, known_decorators: Iterable[str], decorator_name: str):
        """
        Args:
            known_decorators (Iterable[str]): Lista de nomes de decorators que já
                indicam instrumentação. Exemplo: ['m__mp_profile', 'tracked_profile'].
            decorator_name (str): Nome do decorator que deve ser adicionado
                (ex: 'm__mp_profile').
        """
        self.known_decorators = set(known_decorators)
        self.decorator_name = decorator_name

    # ============================================================
    # Utilitários internos
    # ============================================================

    def _has_decorator(self, node: ast.AST) -> bool:
        """
        Verifica se o nó (função) já possui algum dos decorators conhecidos.
        """
        for d in getattr(node, 'decorator_list', []):
            # Exemplo: @tracked_profile → ast.Name(id="tracked_profile")
            if isinstance(d, ast.Name) and d.id in self.known_decorators:
                return True
            # Exemplo: @module.tracked_profile → ast.Attribute(attr="tracked_profile")
            if (
                isinstance(d, ast.Attribute)
                and getattr(d, 'attr', None) in self.known_decorators
            ):
                return True
        return False

    # ============================================================
    # Transformações AST
    # ============================================================

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """
        Adiciona o decorator à função, se ainda não estiver presente.
        """
        self.generic_visit(node)
        if not self._has_decorator(node):
            node.decorator_list.insert(
                0, ast.Name(id=self.decorator_name, ctx=ast.Load())
            )
        return node

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        """
        Adiciona o decorator à função assíncrona, se ainda não estiver presente.
        """
        self.generic_visit(node)
        if not self._has_decorator(node):
            node.decorator_list.insert(
                0, ast.Name(id=self.decorator_name, ctx=ast.Load())
            )
        return node
