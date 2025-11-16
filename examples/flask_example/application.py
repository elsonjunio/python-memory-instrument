from flask import Flask, jsonify
import time
import random
from modules.fn import other_func

# ------------------------------------------------
# Aplicação Flask
# ------------------------------------------------
app = Flask(__name__)


@app.route('/')
def index():
    return jsonify({'message': 'Servidor Flask com memory_tracker ativo!'})


@app.route('/random')
def random_calc():
    """Função de exemplo que será medida."""
    data = [random.random() for _ in range(50000)]
    time.sleep(0.1)
    return jsonify({'sum': sum(data)})


@app.route('/fn')
def fn():
    a = other_func()
    return jsonify(a)


