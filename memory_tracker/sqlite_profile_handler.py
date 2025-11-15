import sqlite3
import hashlib
from threading import Lock


class SQLiteProfileHandler:
    _instance = None
    _lock = Lock()

    def __init__(self, db_path='profile_logs.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL;')
        self._cursor = self.conn.cursor()
        self._create_tables()

    @classmethod
    def instance(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(*args, **kwargs)
        return cls._instance

    def _create_tables(self):
        # Tabela com logs
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                hash TEXT PRIMARY KEY,
                log_text TEXT NOT NULL
            );
        """
        )

        # Tabela com entradas (corrigido: mem_* agora s�o REAL)
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                func TEXT NOT NULL,
                mem_before REAL NOT NULL,
                mem_after REAL NOT NULL,
                mem_diff REAL NOT NULL,
                timestamp REAL NOT NULL,
                log_hash TEXT NOT NULL,
                FOREIGN KEY (log_hash) REFERENCES logs(hash)
            );
        """
        )

        self.conn.commit()

    def _hash_log(self, log_text):
        return hashlib.sha256(log_text.encode('utf-8')).hexdigest()

    def handle(self, entry: dict):
        log_text = entry['log']
        log_hash = self._hash_log(log_text)

        # 1 \u2014 Inserir log somente se n�o existir
        self._cursor.execute(
            'INSERT OR IGNORE INTO logs (hash, log_text) VALUES (?, ?)',
            (log_hash, log_text),
        )

        # 2 \u2014 Inserir entry com tipos corretos
        self._cursor.execute(
            """
            INSERT INTO entries (
                func, mem_before, mem_after, mem_diff, timestamp, log_hash
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                entry['func'],
                float(entry['mem_before']),
                float(entry['mem_after']),
                float(entry['mem_diff']),
                float(entry['timestamp']),
                log_hash,
            ),
        )

        self.conn.commit()

    def close(self):
        self.conn.close()
