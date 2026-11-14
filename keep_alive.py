from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "¡El Asistente CTX de Zarek está vivo 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

def keep_alive():
    # A daemon thread cannot keep a controlled bot shutdown hanging.
    t = Thread(target=run, daemon=True, name="ctx-health-server")
    t.start()
