# -*- coding: utf-8 -*-
"""
APP/__init__.py
----------------
Factory Flask : crée et configure l'application.
"""

import os
from flask import Flask

from APP.extensions import db, login_manager
from APP.models import User


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
    )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    instance_dir = os.path.join(basedir, "instance")
    os.makedirs(instance_dir, exist_ok=True)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cle-secrete-a-changer-en-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(instance_dir, "database.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["INSTANCE_DB_PATH"] = os.path.join(instance_dir, "database.db")

    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Rend `current_role` disponible dans tous les templates (masquage des menus)
    from utils import current_role

    @app.context_processor
    def inject_current_role():
        return {"current_role": current_role()}

    # ------------------------------------------------------------------
    # Enregistrement des blueprints (routes)
    # ------------------------------------------------------------------
    from ROUTES.accueil import accueil_bp
    from ROUTES.caisse import caisse_bp
    from ROUTES.categories import categories_bp
    from ROUTES.catalogue import catalogue_bp
    from ROUTES.paiement import paiement_bp
    from ROUTES.tableau_de_bord import tableau_de_bord_bp
    from ROUTES.retrait_caisse import retrait_caisse_bp
    from ROUTES.admindb import admindb_bp
    from ROUTES.maintenance import maintenance_bp
    from ROUTES.auth import auth_bp

    app.register_blueprint(accueil_bp)
    app.register_blueprint(caisse_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(catalogue_bp)
    app.register_blueprint(paiement_bp)
    app.register_blueprint(tableau_de_bord_bp)
    app.register_blueprint(retrait_caisse_bp)
    app.register_blueprint(admindb_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(auth_bp)

    # ------------------------------------------------------------------
    # Commande CLI d'initialisation de la base
    # ------------------------------------------------------------------
    @app.cli.command("init-db")
    def init_db():
        """Crée/met à niveau les tables et un compte admin par défaut (flask init-db)."""
        from APP.migrations import appliquer_migrations

        appliquer_migrations()
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", role="admin")
            admin.set_password("admin")
            db.session.add(admin)
            db.session.commit()
            print("Base initialisée. Compte créé : admin / admin (à changer !)")
        else:
            print("Base déjà initialisée / mise à niveau.")

    # ------------------------------------------------------------------
    # Mise à niveau automatique au démarrage :
    # 1) on ajoute les colonnes manquantes sur les tables déjà existantes
    #    (jamais de suppression ni de recréation de la base) ;
    # 2) on crée les tables entièrement nouvelles qui n'existent pas encore ;
    # 3) on garantit la présence du compte admin par défaut.
    # ------------------------------------------------------------------
    with app.app_context():
        from APP.migrations import appliquer_migrations

        appliquer_migrations()
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", role="admin")
            admin.set_password("admin")
            db.session.add(admin)
            db.session.commit()

    # ------------------------------------------------------------------
    # Gestion des erreurs
    # ------------------------------------------------------------------
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    return app
