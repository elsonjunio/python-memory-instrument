import os
import sys
from memory_tracker.instrumentor import instrument_source
from memory_tracker.injector import DecoratorInjector
from memory_tracker.importer import SourceTransformImporter
from memory_tracker.instrumentor import prepare_instrumented_code
from memory_tracker.profiler import ProfileManager
from memory_tracker.sqlite_profile_handler import SQLiteProfileHandler
import sqlite3

from flask import Flask, jsonify
from memory_tracker.report_builder import build_html_report


def execute_query(db_path, query, params=None):
    """
    Executa uma query SQL e retorna todas as linhas.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    rows = cursor.fetchall()
    conn.close()

    return rows

def load_entries(db_path):
    query = """
        SELECT 
            e.func,
            e.mem_before,
            e.mem_after,
            e.mem_diff,
            e.timestamp,
            l.log_text
        FROM entries e
        JOIN logs l ON l.hash = e.log_hash
        ORDER BY e.id ASC;
    """

    rows = execute_query(db_path, query)

    # Converter em objetos Python
    return [
        {
            "func": r[0],
            "mem_before": r[1],
            "mem_after": r[2],
            "mem_diff": r[3],
            "timestamp": r[4],
            "log": r[5],
        }
        for r in rows
    ]



abspath = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'application.py'
)
target_dir = os.path.dirname(abspath) or '.'

DATABASE = os.path.join(target_dir, 'profile_logs.db')

sqlite_handler = SQLiteProfileHandler(DATABASE)
profile_manager = ProfileManager()
profile_manager.set_handler(sqlite_handler)

code_obj, module_globals, cleanup = prepare_instrumented_code(abspath)

try:
    importer = SourceTransformImporter(target_dir, instrument_source)
    sys.meta_path.insert(0, importer)
    exec(code_obj, module_globals)
except SystemExit:
    raise

app = module_globals['app']


@app.route('/report')
def report():
    entries = load_entries(DATABASE)
    html = build_html_report(entries)

    return html


