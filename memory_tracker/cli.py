import sys
import os
import argparse

from .instrumentor import run_instrumented


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Instrumenta um script Python adicionando decorators de monitoramento '
            '(@profile, @tracked_profile, etc.) e executa o código instrumentado em memória.'
        )
    )

    parser.add_argument(
        'script',
        help='Caminho para o script alvo (.py)',
    )

    parser.add_argument(
        'args',
        nargs=argparse.REMAINDER,
        help='Argumentos que serão passados ao script alvo (opcionais)',
    )

    args = parser.parse_args()

    # Validação de caminho
    if not os.path.isfile(args.script):
        print(f'Erro: arquivo não encontrado: {args.script}', file=sys.stderr)
        sys.exit(2)

    # Verifica se o memory_profiler está disponível
    try:
        import memory_profiler  # noqa: F401
    except ImportError:
        print(
            'Pacote "memory_profiler" não encontrado.\n'
            'Instale com: pip install memory-profiler',
            file=sys.stderr,
        )
        sys.exit(3)

    try:
        run_instrumented(args.script, extra_argv=args.args)
    except KeyboardInterrupt:
        print('\nExecução interrompida pelo usuário.')
        sys.exit(130)
    except Exception as e:
        print(f'Erro durante a execução do script instrumentado: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
