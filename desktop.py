"""
Lanceur "application de bureau" : démarre le serveur Flask dans un thread
en arrière-plan, puis ouvre une fenêtre native (pywebview) qui affiche l'app.
Fonctionne sur Linux et Windows.
"""
import threading
import webview

from app import app  # importe l'app Flask + SQLAlchemy définie dans app.py

HOST = "127.0.0.1"
PORT = 5000


def lancer_flask():
    # use_reloader=False et debug=False : indispensable en mode packagé/thread
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def main():
    thread_flask = threading.Thread(target=lancer_flask, daemon=True)
    thread_flask.start()

    webview.create_window(
        "Mes Tâches",
        f"http://{HOST}:{PORT}",
        width=560,
        height=720,
        resizable=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
