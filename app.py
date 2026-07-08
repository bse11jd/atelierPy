# -*- coding: utf-8 -*-
"""
app.py
------
Point d'entrée de l'application. Lance le serveur de développement Flask.
Usage : python app.py
"""

from APP import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
