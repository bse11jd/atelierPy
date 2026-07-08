# -*- coding: utf-8 -*-
"""
ROUTES/maintenance.py
------------------------
Écran MAINTENANCE - réservé aux admins.
Export de la base de données (téléchargement / sauvegarde sur clé USB).
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, current_app, send_file

from utils import role_required

maintenance_bp = Blueprint("maintenance", __name__)


@maintenance_bp.route("/maintenance")
@role_required("admin")
def maintenance():
    db_path = current_app.config.get("INSTANCE_DB_PATH")
    db_exists = os.path.exists(db_path) if db_path else False
    db_size_ko = round(os.path.getsize(db_path) / 1024, 1) if db_exists else 0
    return render_template("maintenance.html", db_exists=db_exists, db_size_ko=db_size_ko)


@maintenance_bp.route("/maintenance/export-db")
@role_required("admin")
def maintenance_export_db():
    """
    Télécharge une copie horodatée de la base SQLite.
    Sur un poste avec clé USB montée, le navigateur permet de choisir
    le dossier de destination (y compris la clé USB) lors du téléchargement.
    """
    db_path = current_app.config.get("INSTANCE_DB_PATH")
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_fichier = f"backup_database_{horodatage}.db"
    return send_file(db_path, as_attachment=True, download_name=nom_fichier)
