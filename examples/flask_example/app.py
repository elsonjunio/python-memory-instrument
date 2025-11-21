import os
import sys
from memory_tracker.instrumentor import instrument_source
from memory_tracker.injector import DecoratorInjector
from memory_tracker.importer import SourceTransformImporter
from memory_tracker.instrumentor import prepare_instrumented_code
from memory_tracker.profiler import ProfileManager, tracked_profile
from memory_tracker.sqlite_profile_handler import SQLiteProfileHandler
import sqlite3

from flask import Flask
from memory_tracker.report_builder import build_html_report

_original_add_url_rule = Flask.add_url_rule


def _patched_add_url_rule(
    self,
    rule,
    endpoint=None,
    view_func=None,
    provide_automatic_options=None,
    **options
):
    """
    Monkey patch para interceptar toda rota antes de ser registrada.
    """
    # Ignore rotas internas
    if endpoint == 'static':
        return _original_add_url_rule(
            self,
            rule,
            endpoint,
            view_func,
            provide_automatic_options,
            **options
        )

    # Só aplica o wrapper se houver função
    if view_func is not None:

        # evita dupla instrumentação
        if not getattr(view_func, '_is_profiled', False):
            wrapped = tracked_profile(view_func)
            wrapped._is_profiled = True
            view_func = wrapped

    # Evita erros ter a mesma função ativa em endpoints diferentes por não ter endpoint definido
    endpoint = endpoint or rule

    # Chama o método original
    return _original_add_url_rule(self, rule, endpoint, view_func, **options)


Flask.add_url_rule = _patched_add_url_rule


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
            'func': r[0],
            'mem_before': r[1],
            'mem_after': r[2],
            'mem_diff': r[3],
            'timestamp': r[4],
            'log': r[5],
        }
        for r in rows
    ]


def apply_profile_to_routes(app):
    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint

        # segurança: skip endpoints do próprio Flask
        if endpoint in ('static',):
            continue

        original_view = app.view_functions[endpoint]

        # evita dupla aplicação do decorator (muito importante!)
        if getattr(original_view, '_is_profiled', False):
            continue

        wrapped = tracked_profile(original_view)
        wrapped._is_profiled = True

        app.view_functions[endpoint] = wrapped


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
#apply_profile_to_routes(app) # Para usar monkey patch: _patched_add_url_rule


@app.route('/report')
def report():
    entries = load_entries(DATABASE)
    html = build_html_report(entries)

    return html
