# -*- coding: utf-8 -*-
"""
ROUTES/retrait_caisse.py
--------------------------
Écran RETRAIT CAISSE - réservé aux super-utilisateurs et admins.

Permet d'enregistrer un retrait d'espèces dans la caisse. Un retrait
nécessite :
- le nom de la personne qui effectue le retrait (obligatoire) ;
- un motif (obligatoire) ;
- un montant strictement positif.

Le retrait est possible que la permanence soit ouverte ou fermée :
- si une permanence est ouverte, le retrait y est automatiquement rattaché
  et son montant est déduit du fond de caisse suggéré en fin de permanence
  (écran Accueil) ;
- sinon, il est simplement enregistré à titre d'historique, sans permanence
  associée.

L'historique complet des retraits (modification, suppression) est
consultable depuis l'écran TABLEAU DE BORD.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from utils import role_required, get_permanence_active, total_retraits_permanence
from APP.extensions import db
from APP.models import RetraitCaisse

retrait_caisse_bp = Blueprint("retrait_caisse", __name__)


@retrait_caisse_bp.route("/retrait-caisse")
@role_required("super_utilisateur")
def retrait_caisse():
    permanence = get_permanence_active()
    total_retraits = total_retraits_permanence(permanence.id) if permanence else 0.0
    return render_template(
        "retrait_caisse.html",
        permanence=permanence,
        total_retraits=total_retraits,
    )


@retrait_caisse_bp.route("/retrait-caisse/ajouter", methods=["POST"])
@role_required("super_utilisateur")
def retrait_caisse_ajouter():
    permanence = get_permanence_active()

    nom_personne = request.form.get("nom_personne", "").strip()
    motif = request.form.get("motif", "").strip()
    montant = request.form.get("montant", "0").strip()

    if not nom_personne:
        flash("Le nom de la personne qui effectue le retrait est obligatoire.", "danger")
        return redirect(url_for("retrait_caisse.retrait_caisse"))

    if not motif:
        flash("Le motif du retrait est obligatoire.", "danger")
        return redirect(url_for("retrait_caisse.retrait_caisse"))

    try:
        montant_val = float(montant.replace(",", "."))
    except ValueError:
        montant_val = 0.0

    if montant_val <= 0:
        flash("Le montant du retrait doit être supérieur à 0.", "danger")
        return redirect(url_for("retrait_caisse.retrait_caisse"))

    retrait = RetraitCaisse(
        permanence_id=permanence.id if permanence else None,
        montant=montant_val,
        motif=motif,
        nom_personne=nom_personne,
        auteur=current_user.username,
    )
    db.session.add(retrait)
    db.session.commit()
    flash(f"Retrait de {montant_val:.2f} € enregistré pour {nom_personne} ({motif}).", "success")
    return redirect(url_for("retrait_caisse.retrait_caisse"))
