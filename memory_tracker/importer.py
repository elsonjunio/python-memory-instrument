import os
import importlib.abc
import importlib.util
import importlib.machinery
import traceback


class SourceTransformImporter(
    importlib.abc.MetaPathFinder, importlib.abc.Loader
):
    """
    Importador personalizado que intercepta a carga de módulos Python (.py)
    e aplica uma função de transformação de código-fonte (como instrumentação)
    antes da execução.

    É usado para instrumentar dinamicamente módulos importados durante a
    execução de um script principal.
    """

    def __init__(self, base_path: str, instrument_source):
        """
        Args:
            base_path (str): Caminho base do projeto (somente módulos dentro dele serão transformados).
            instrument_source (callable): Função que recebe (source, path)
                                          e retorna (code_object, ast_tree).
        """
        self.base_path = os.path.abspath(base_path)
        self.instrument_source = instrument_source

    # ============================================================
    # Interceptação de imports
    # ============================================================

    def find_spec(self, fullname, path=None, target=None):
        """
        Localiza o módulo e decide se deve ser instrumentado.
        """
        try:
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        except ModuleNotFoundError:
            return None

        if not spec or not spec.origin:
            return None

        mod_path = os.path.abspath(spec.origin)

        # apenas módulos dentro do diretório base
        if not mod_path.startswith(self.base_path):
            return None

        # apenas arquivos Python comuns
        if not mod_path.endswith('.py'):
            return None

        # substitui o loader padrão por este
        spec.loader = self
        spec.origin_path = mod_path
        return spec

    # ============================================================
    # Criação e execução de módulo instrumentado
    # ============================================================

    def create_module(self, spec):
        """
        Usa o mecanismo padrão de criação de módulos.
        """
        return None

    def exec_module(self, module):
        """
        Executa o módulo aplicando a transformação de código-fonte.
        """
        mod_path = getattr(module.__spec__, 'origin_path', None)
        if not mod_path:
            # fallback para carregamento padrão
            return importlib.util.exec_module(module)

        try:
            with open(mod_path, 'r', encoding='utf-8') as f:
                src = f.read()

            code_obj, _ = self.instrument_source(src, mod_path)
            exec(code_obj, module.__dict__)

        except Exception as e:
            print(f'[instrumentor] Falha ao instrumentar {mod_path}: {e}')
            traceback.print_exc()

            # fallback: executa código original sem instrumentar
            importlib.util.exec_module(module)
