# -*- coding: utf-8 -*-
"""
ROUTES/catalogue.py
---------------------
Écran CATALOGUE - réservé aux super-utilisateurs et admins.
Liste des prestations facturables, classées par catégorie.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils import role_required
from APP.extensions import db
from APP.models import CatalogueItem, Category

catalogue_bp = Blueprint("catalogue", __name__)


@catalogue_bp.route("/catalogue")
@role_required("super_utilisateur")
def catalogue():
    items = CatalogueItem.query.join(Category).order_by(Category.nom, CatalogueItem.libelle).all()
    categories = Category.query.order_by(Category.nom).all()
    return render_template("catalogue.html", items=items, categories=categories)


@catalogue_bp.route("/catalogue/ajouter", methods=["POST"])
@role_required("super_utilisateur")
def catalogue_ajouter():
    libelle = request.form.get("libelle", "").strip()
    prix = request.form.get("prix", "0").strip()
    categorie_id = request.form.get("categorie_id")

    if not libelle or not categorie_id:
        flash("Libellé et catégorie sont obligatoires.", "warning")
        return redirect(url_for("catalogue.catalogue"))

    try:
        prix_val = float(prix.replace(",", "."))
    except ValueError:
        prix_val = 0.0

    item = CatalogueItem(libelle=libelle, prix=prix_val, categorie_id=int(categorie_id))
    db.session.add(item)
    db.session.commit()
    flash(f"Prestation « {libelle} » ajoutée.", "success")
    return redirect(url_for("catalogue.catalogue"))


@catalogue_bp.route("/catalogue/modifier/<int:item_id>", methods=["POST"])
@role_required("super_utilisateur")
def catalogue_modifier(item_id):
    item = CatalogueItem.query.get_or_404(item_id)

    libelle = request.form.get("libelle", "").strip()
    prix = request.form.get("prix", "0").strip()
    categorie_id = request.form.get("categorie_id")

    if not libelle or not categorie_id:
        flash("Libellé et catégorie sont obligatoires.", "warning")
        return redirect(url_for("catalogue.catalogue"))

    try:
        prix_val = float(prix.replace(",", "."))
    except ValueError:
        prix_val = 0.0

    item.libelle = libelle
    item.prix = prix_val
    item.categorie_id = int(categorie_id)
    db.session.commit()
    flash(f"Prestation « {libelle} » mise à jour.", "success")
    return redirect(url_for("catalogue.catalogue"))


@catalogue_bp.route("/catalogue/supprimer/<int:item_id>", methods=["POST"])
@role_required("super_utilisateur")
def catalogue_supprimer(item_id):
    item = CatalogueItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f"Prestation « {item.libelle} » supprimée.", "info")
    return redirect(url_for("catalogue.catalogue"))
