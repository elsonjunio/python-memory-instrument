import atexit
import io
import json
import time
from memory_profiler import memory_usage, profile

_profile_data = []


def tracked_profile(func):
    """Wrapper para capturar uso de memória e log detalhado."""

    def wrapper(*args, **kwargs):
        start = time.time()
        mem_before = memory_usage(-1, interval=0.1, timeout=1)[0]

        # Cria stream para capturar o log do memory_profiler
        stream = io.StringIO()
        profiled_func = profile(stream=stream)(func)

        result = profiled_func(*args, **kwargs)

        mem_after = memory_usage(-1, interval=0.1, timeout=1)[0]

        # Captura o log detalhado do profile
        stream.seek(0)
        profile_log = stream.read()
        stream.close()

        _profile_data.append(
            {
                'func': func.__qualname__,
                'mem_before': mem_before,
                'mem_after': mem_after,
                'mem_diff': mem_after - mem_before,
                'timestamp': start,
                'log': profile_log,
            }
        )

        return result

    return wrapper


@atexit.register
def save_profile_data():
    """Salva dados agregados em JSON ao terminar a execução."""
    with open('profile_report.json', 'w', encoding='utf-8') as f:
        json.dump(_profile_data, f, indent=2, ensure_ascii=False)
