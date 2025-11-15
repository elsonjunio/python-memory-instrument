# profiler.py
import io
import json
import time
from memory_profiler import memory_usage, profile
from threading import Thread, Lock, Event
from queue import Queue, Empty
import atexit
from typing import Optional


class JsonFileProfileHandler:
    """Handler padrão: grava logs JSON incrementais em um arquivo aberto."""

    def __init__(
        self, filename: str = 'profile_report.json', indent: Optional[int] = 2
    ):
        self.filename = filename
        self._file = open(filename, 'w', encoding='utf-8')
        self._first = True
        self._lock = Lock()
        self._indent = indent
        self._file.write('[\n')

    def handle(self, entry: dict):
        """Grava o item no arquivo JSON incrementalmente (thread-safe)."""
        with self._lock:
            if not self._first:
                self._file.write(',\n')
            else:
                self._first = False
            json.dump(
                entry, self._file, ensure_ascii=False, indent=self._indent
            )
            self._file.flush()

    def close(self):
        with self._lock:
            # fechar o array JSON corretamente
            self._file.write('\n]\n')
            try:
                self._file.close()
            except Exception:
                pass


class ProfileManager:
    """
    Gerencia o recebimento de logs de profiling e os envia para um handler,
    processando-os em um worker thread para não bloquear a execução das funções.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_once()
        return cls._instance

    def _init_once(self):
        self._queue: 'Queue[Optional[dict]]' = Queue()
        self._handler = JsonFileProfileHandler()
        self._thread = Thread(
            target=self._worker, daemon=True, name='ProfileManagerWorker'
        )
        self._stop_event = Event()
        self._thread.start()

    def _worker(self):
        """Loop do worker que consome a fila e chama handler.handle()."""
        while not self._stop_event.is_set():
            try:
                entry = self._queue.get(timeout=0.5)
            except Empty:
                continue
            if entry is None:
                # sinal de término
                break
            try:
                self._handler.handle(entry)
            except Exception as e:
                # não deixar o worker morrer por uma exceção de handler
                print(f'[ProfileManager] erro ao processar entrada: {e}')

        # esvaziar a fila antes de fechar
        while True:
            try:
                entry = self._queue.get_nowait()
            except Empty:
                break
            if entry is not None:
                try:
                    self._handler.handle(entry)
                except Exception:
                    pass

    def set_handler(self, handler):
        """
        Substitui o handler atual. O handler precisa ter:
          - handle(entry: dict)
          - close()
        """
        # fechar handler antigo de forma segura
        old = getattr(self, '_handler', None)
        if old:
            try:
                old.close()
            except Exception:
                pass
        self._handler = handler

    def emit(self, entry: dict):
        """Enfila um evento. É rápido e thread-safe."""
        if not hasattr(self, '_queue'):
            # em casos estranhos, garantir inicialização
            self._init_once()
        self._queue.put(entry)

    def shutdown(self, timeout: float = 5.0):
        """
        Solicita parada do worker e fecha o handler.
        Chamar no final da aplicação para garantir flush.
        """
        if not hasattr(self, '_stop_event'):
            return
        self._stop_event.set()
        # colocar sentinel para que o thread saia imediatamente
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        self._thread.join(timeout=timeout)
        # fechar handler
        try:
            if hasattr(self, '_handler') and self._handler:
                self._handler.close()
        except Exception:
            pass


# registra um shutdown automático via atexit (ainda útil em encerramento normal)
_mgr = ProfileManager()
atexit.register(lambda: _mgr.shutdown(timeout=2.0))


def tracked_profile(func):
    """Decorator que mede o uso de memória e envia para o ProfileManager."""

    def wrapper(*args, **kwargs):
        start = time.time()
        mem_before = memory_usage(-1, interval=0.1, timeout=1)[0]

        # capturar log detalhado do memory_profiler
        stream = io.StringIO()
        profiled_func = profile(stream=stream)(func)
        result = profiled_func(*args, **kwargs)
        mem_after = memory_usage(-1, interval=0.1, timeout=1)[0]

        stream.seek(0)
        profile_log = stream.read()
        stream.close()

        entry = {
            'func': func.__qualname__,
            'mem_before': mem_before,
            'mem_after': mem_after,
            'mem_diff': mem_after - mem_before,
            'timestamp': start,
            'log': profile_log,
        }

        # envia ao manager de forma não bloqueante
        ProfileManager().emit(entry)
        return result

    return wrapper
