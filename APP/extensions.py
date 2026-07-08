# -*- coding: utf-8 -*-
"""
APP/extensions.py
------------------
Instanciation des extensions Flask, séparées de l'application
pour éviter les imports circulaires entre APP et ROUTES.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Merci de vous connecter pour accéder à cet écran."
login_manager.login_message_category = "warning"
