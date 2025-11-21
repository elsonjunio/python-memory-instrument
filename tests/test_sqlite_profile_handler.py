import sqlite3
import pytest
from pathlib import Path

from memory_tracker.sqlite_profile_handler import SQLiteProfileHandler


@pytest.fixture
def temp_db(tmp_path):
    """Cria um banco temporário e retorna uma instância limpa do handler."""
    db_path = tmp_path / 'test_profile.db'

    # Forçar reset da instância singleton para testes
    SQLiteProfileHandler._instance = None
    handler = SQLiteProfileHandler.instance(db_path=str(db_path))

    yield handler

    handler.close()
    SQLiteProfileHandler._instance = None


@pytest.fixture
def example_entry():
    return {
        'func': 'test_function',
        'mem_before': 10.5,
        'mem_after': 15.25,
        'mem_diff': 4.75,
        'timestamp': 1234567890.0,
        'log': 'LINE A\nLINE B\n',
    }


def test_tables_exist(temp_db):
    """Garante que as tabelas foram criadas corretamente."""
    cur = temp_db.conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}

    assert 'logs' in tables
    assert 'entries' in tables


def test_insert_log_and_entry(temp_db, example_entry):
    """Testa a inserção de log + entry."""
    temp_db.handle(example_entry)

    cur = temp_db.conn.cursor()

    # Verificar se o log foi inserido
    cur.execute('SELECT * FROM logs')
    logs = cur.fetchall()
    assert len(logs) == 1

    # Verificar se entry foi inserida
    cur.execute('SELECT * FROM entries')
    entries = cur.fetchall()
    assert len(entries) == 1


def test_log_deduplication(temp_db, example_entry):
    """Mesmo log_text deve gerar apenas uma entrada na tabela logs."""
    temp_db.handle(example_entry)
    temp_db.handle(example_entry)  # Repetido

    cur = temp_db.conn.cursor()

    # logs deve ter só 1 registro
    cur.execute('SELECT COUNT(*) FROM logs')
    count_logs = cur.fetchone()[0]
    assert count_logs == 1

    # entries deve ter 2 (duas chamadas ao handler)
    cur.execute('SELECT COUNT(*) FROM entries')
    count_entries = cur.fetchone()[0]
    assert count_entries == 2


def test_entry_references_log_hash(temp_db, example_entry):
    temp_db.handle(example_entry)

    cur = temp_db.conn.cursor()

    # pega o log_hash da tabela logs
    cur.execute('SELECT hash FROM logs LIMIT 1')
    inserted_hash = cur.fetchone()[0]

    # verificar que entry aponta para esse hash
    cur.execute('SELECT log_hash FROM entries LIMIT 1')
    entry_hash = cur.fetchone()[0]

    assert entry_hash == inserted_hash


def test_values_inserted_correctly(temp_db, example_entry):
    temp_db.handle(example_entry)

    cur = temp_db.conn.cursor()
    cur.execute(
        'SELECT func, mem_before, mem_after, mem_diff, timestamp FROM entries LIMIT 1'
    )
    row = cur.fetchone()

    assert row[0] == example_entry['func']
    assert row[1] == example_entry['mem_before']
    assert row[2] == example_entry['mem_after']
    assert row[3] == example_entry['mem_diff']
    assert row[4] == example_entry['timestamp']
