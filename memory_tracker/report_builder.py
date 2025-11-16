import json
import sys
from datetime import datetime
from pathlib import Path
from html import escape

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Profiling</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body {{
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 2rem;
    background: #f4f4f9;
  }}
  h1 {{
    text-align: center;
    margin-bottom: 2rem;
  }}
  .card {{
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    padding: 1.5rem;
    margin: 1.5rem auto;
    width: 80%;
  }}
  .metrics {{
    display: flex;
    flex-wrap: wrap;
    justify-content: space-around;
    margin-top: 1rem;
  }}
  .metric {{
    background: #eef2f7;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem;
    flex: 1 1 25%;
    text-align: center;
  }}
  pre {{
    background: #1e1e1e;
    color: #dcdcdc;
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
  }}
  .log-box {{
      background: #1e1e1e;
      color: #dcdcdc;
      padding: 1rem;
      margin: 0.5rem;
      border-radius: 8px;
      font-family: monospace;
      white-space: pre;
      overflow-x: auto;
      flex: 1 1 100%;
  }}
</style>
</head>
<body>
  <h1>📊 Relatório de Execução e Memória</h1>
  <div class="card">
    <h2>Resumo Geral</h2>
    <canvas id="memoryChart" height="120"></canvas>
    <div class="metrics">
      <div class="metric"><strong>Total de Funções:</strong><br>{total_funcs}</div>
      <div class="metric"><strong>Média Δ Memória:</strong><br>{avg_mem:.3f} MiB</div>
      <div class="metric"><strong>Total Memória Antes:</strong><br>{total_before:.3f} MiB</div>
      <div class="metric"><strong>Total Memória Depois:</strong><br>{total_after:.3f} MiB</div>
      <div class="metric"><strong>Total Δ Memória:</strong><br>{total_diff:.3f} MiB</div>
    </div>
  </div>
  {entries_html}
<script>
document.addEventListener("DOMContentLoaded", function() {{
    const ctx = document.getElementById('memoryChart');
    const labels = {labels};
    const beforeData = {before_data};
    const afterData = {after_data};

    new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: labels,
            datasets: [
                {{
                    label: 'Memória Antes (MiB)',
                    data: beforeData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    fill: true,
                    tension: 0.3
                }},
                {{
                    label: 'Memória Depois (MiB)',
                    data: afterData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    fill: true,
                    tension: 0.3
                }}
            ]
        }},
        options: {{
            responsive: true,
            plugins: {{
                legend: {{
                    position: 'top',
                }},
                title: {{
                    display: true,
                    text: 'Linha do Tempo do Consumo de Memória'
                }}
            }},
            scales: {{
                x: {{
                    title: {{
                        display: true,
                        text: 'Tempo (ordem de execução)'
                    }}
                }},
                y: {{
                    title: {{
                        display: true,
                        text: 'Memória (MiB)'
                    }}
                }}
            }}
        }}
    }});
}});
</script>
</body>
</html>
"""


def build_html_report(data):

    # Ordenar por timestamp
    data.sort(key=lambda x: x.get('timestamp', 0))

    labels = [d['func'] for d in data]
    before_data = [d['mem_before'] for d in data]
    after_data = [d['mem_after'] for d in data]

    total_funcs = len(data)
    total_before = sum(before_data)
    total_after = sum(after_data)
    total_diff = sum(d['mem_diff'] for d in data)
    avg_mem = total_diff / total_funcs if total_funcs else 0

    entries_html = ''
    for d in data:
        log = escape(d.get('log', '') or 'Sem log capturado')
        entries_html += f"""
        <div class="card">
            <h3>🧩 {d['func']}</h3>
            <div class="metrics">
                <div class="metric"><strong>Memória Antes:</strong><br>{d['mem_before']:.3f} MiB</div>
                <div class="metric"><strong>Memória Depois:</strong><br>{d['mem_after']:.3f} MiB</div>
                <div class="metric"><strong>Δ Memória:</strong><br>{d['mem_diff']:.3f} MiB</div>
                <div class="metric"><strong>Timestamp:</strong><br>{datetime.fromtimestamp(d['timestamp']).strftime('%H:%M:%S')}</div>
                <div class="log-box">{log}</div>
            </div>
        </div>
        """

    html = HTML_TEMPLATE.format(
        total_funcs=total_funcs,
        avg_mem=avg_mem,
        total_before=total_before,
        total_after=total_after,
        total_diff=total_diff,
        labels=json.dumps(labels),
        before_data=json.dumps(before_data),
        after_data=json.dumps(after_data),
        entries_html=entries_html,
    )

    return html


def load_from_json(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data


def save_html_report(html, json_path):
    output_file = Path(json_path).with_suffix('.html')
    output_file.write_text(html, encoding='utf-8')
    print(f'✅ Relatório gerado: {output_file.resolve()}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(
            'Uso: python instrument_build_report.py caminho/do/profile_report.json'
        )
        sys.exit(1)
    json_path = sys.argv[1]
    html = build_html_report(load_from_json(json_path))
    save_html_report(html, json_path)
