# -*- coding: utf-8 -*-
"""
ROUTES/admindb.py
-------------------
Écran ADMINDB - réservé aux admins.
Point d'accès à Adminer (interface d'administration de la base SQLite).
Adminer est un outil externe (PHP) ; ici on prépare simplement l'écran
d'accès/paramétrage, l'intégration technique (URL du service Adminer)
sera précisée à une étape ultérieure du projet.
"""

import os
from flask import Blueprint, render_template, current_app

from utils import role_required

admindb_bp = Blueprint("admindb", __name__)


@admindb_bp.route("/admindb")
@role_required("admin")
def admindb():
    db_path = current_app.config.get("INSTANCE_DB_PATH")
    db_exists = os.path.exists(db_path) if db_path else False
    # URL d'Adminer à configurer lors du déploiement (ex: docker-compose avec adminer)
    adminer_url = current_app.config.get("ADMINER_URL", None)
    return render_template(
        "admindb.html", db_path=db_path, db_exists=db_exists, adminer_url=adminer_url
    )
