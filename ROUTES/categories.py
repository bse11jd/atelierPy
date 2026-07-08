# -*- coding: utf-8 -*-
"""
ROUTES/categories.py
---------------------
Écran CATEGORIES - réservé aux super-utilisateurs et admins.
Liste modifiable des catégories de prestations (bar, atelier, adhésion, autres...).
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils import role_required
from APP.extensions import db
from APP.models import Category

categories_bp = Blueprint("categories", __name__)


@categories_bp.route("/categories")
@role_required("super_utilisateur")
def categories():
    liste = Category.query.order_by(Category.nom).all()
    return render_template("categories.html", categories=liste)


@categories_bp.route("/categories/ajouter", methods=["POST"])
@role_required("super_utilisateur")
def categories_ajouter():
    nom = request.form.get("nom", "").strip()
    couleur = request.form.get("couleur", "#4a5568").strip() or "#4a5568"
    if nom:
        if Category.query.filter_by(nom=nom).first():
            flash(f"La catégorie « {nom} » existe déjà.", "warning")
        else:
            db.session.add(Category(nom=nom, couleur=couleur))
            db.session.commit()
            flash(f"Catégorie « {nom} » ajoutée.", "success")
    return redirect(url_for("categories.categories"))


@categories_bp.route("/categories/modifier/<int:cat_id>", methods=["POST"])
@role_required("super_utilisateur")
def categories_modifier(cat_id):
    cat = Category.query.get_or_404(cat_id)
    nom = request.form.get("nom", "").strip()
    couleur = request.form.get("couleur", "").strip()

    if not nom:
        flash("Le nom de la catégorie est obligatoire.", "warning")
    elif Category.query.filter(Category.nom == nom, Category.id != cat_id).first():
        flash(f"La catégorie « {nom} » existe déjà.", "warning")
    else:
        cat.nom = nom
        if couleur:
            cat.couleur = couleur
        db.session.commit()
        flash(f"Catégorie mise à jour : « {nom} ».", "success")

    return redirect(url_for("categories.categories"))


@categories_bp.route("/categories/supprimer/<int:cat_id>", methods=["POST"])
@role_required("super_utilisateur")
def categories_supprimer(cat_id):
    cat = Category.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    flash(f"Catégorie « {cat.nom} » supprimée.", "info")
    return redirect(url_for("categories.categories"))
