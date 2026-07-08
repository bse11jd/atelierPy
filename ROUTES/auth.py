# -*- coding: utf-8 -*-
"""
ROUTES/auth.py
----------------
Écran AUTH :
- /login  et /logout : accessibles à tous (formulaire d'authentification)
- /auth   : gestion des comptes et niveaux de droits, réservé aux admins
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from utils import role_required
from APP.extensions import db
from APP.models import User

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Connexion / déconnexion (super-utilisateurs et admins)
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("accueil.accueil"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.actif and user.check_password(password):
            login_user(user)
            flash(f"Bienvenue {user.username} ({user.role}).", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("accueil.accueil"))

        flash("Identifiants invalides ou compte désactivé.", "danger")

    return render_template("auth.html", mode="login")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("accueil.accueil"))


# ---------------------------------------------------------------------------
# Gestion des niveaux de droits (admin uniquement)
# ---------------------------------------------------------------------------
@auth_bp.route("/auth")
@role_required("admin")
def auth_gestion():
    utilisateurs = User.query.order_by(User.username).all()
    return render_template("auth.html", mode="gestion", utilisateurs=utilisateurs)


@auth_bp.route("/auth/ajouter", methods=["POST"])
@role_required("admin")
def auth_ajouter():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "super_utilisateur")

    if role not in ("super_utilisateur", "admin"):
        role = "super_utilisateur"

    if not username or not password:
        flash("Identifiant et mot de passe sont obligatoires.", "warning")
    elif User.query.filter_by(username=username).first():
        flash(f"Le compte « {username} » existe déjà.", "warning")
    else:
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f"Compte « {username} » créé avec le rôle {role}.", "success")

    return redirect(url_for("auth.auth_gestion"))


@auth_bp.route("/auth/modifier/<int:user_id>", methods=["POST"])
@role_required("admin")
def auth_modifier(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form.get("role")
    actif = request.form.get("actif") == "on"

    if role in ("super_utilisateur", "admin"):
        user.role = role
    user.actif = actif

    nouveau_mdp = request.form.get("password", "").strip()
    if nouveau_mdp:
        user.set_password(nouveau_mdp)

    db.session.commit()
    flash(f"Compte « {user.username} » mis à jour.", "success")
    return redirect(url_for("auth.auth_gestion"))


@auth_bp.route("/auth/supprimer/<int:user_id>", methods=["POST"])
@role_required("admin")
def auth_supprimer(user_id):
    if user_id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte.", "danger")
        return redirect(url_for("auth.auth_gestion"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"Compte « {user.username} » supprimé.", "info")
    return redirect(url_for("auth.auth_gestion"))
