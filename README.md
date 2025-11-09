# 🧠 memory-tracker

memory-tracker é uma ferramenta de instrumentação automática para monitorar o uso de memória em scripts Python.
Ele adiciona automaticamente decoradores de medição em todas as funções de um projeto, executa o código instrumentado e gera relatórios estruturados de consumo de memória.

## 🚀 Principais Recursos

- Instrumentação automática de funções via AST (Abstract Syntax Tree)

- Captura de uso de memória antes e depois da execução de cada função

- Geração de logs detalhados em JSON

- Relatório HTML com linha do tempo e métricas agregadas

- Suporte a múltiplos módulos e importações internas

- Compatível com Python ≥3.8

### 📦 Instalação
**1️⃣ Clone o repositório**
```bash
git clone https://github.com/<seu-usuario>/python-memory-instrument.git
cd python-memory-instrument
```

**2️⃣ Instale as dependências com Poetry**
```bash
poetry install
```

Se preferir usar pip:

```bash
pip install .
```

### ▶️ Execução

Para executar um script instrumentado e monitorar o uso de memória:
```bash
poetry run python -m memory_tracker.cli caminho/para/seu_script.py
```

ou, se estiver fora do ambiente Poetry:
```bash
python -m memory_tracker.cli caminho/para/seu_script.py
```

Exemplo:
```bash
python -m memory_tracker.cli old/src/main.py
```

### 📊 Relatório

Durante a execução, o memory-tracker cria um arquivo profile_report.json contendo o log detalhado do consumo de memória.

Você pode gerar um relatório visual (HTML) executando:
```bash
python -m memory_tracker.report_builder profile_report.json
```

Isso cria um arquivo profile_report.html com:

- Gráfico de linha do tempo do uso de memória

- Métricas agregadas (média, total, variação)

- Detalhes por função instrumentada

### 🧩 Estrutura do Projeto

```bash
memory_tracker/
│
├── cli.py              # Ponto de entrada do CLI
├── importer.py         # Importador que intercepta módulos e aplica instrumentação
├── injector.py         # Injeta decoradores nas funções (AST)
├── instrumentor.py     # Coordena a instrumentação e execução
├── profiler.py         # Define o decorator tracked_profile
├── report_builder.py   # Gera relatório HTML
└── __init__.py
tests/
└── test_injector.py
```
