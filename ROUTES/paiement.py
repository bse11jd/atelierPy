# -*- coding: utf-8 -*-
"""
ROUTES/paiement.py
--------------------
Écran PAIEMENT - réservé aux super-utilisateurs et admins.
Liste modifiable des moyens de paiement (cash, CB, virement, chèque).
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils import role_required
from APP.extensions import db
from APP.models import PaymentMethod

paiement_bp = Blueprint("paiement", __name__)


@paiement_bp.route("/paiement")
@role_required("super_utilisateur")
def paiement():
    moyens = PaymentMethod.query.order_by(PaymentMethod.nom).all()
    return render_template("paiement.html", moyens=moyens)


@paiement_bp.route("/paiement/ajouter", methods=["POST"])
@role_required("super_utilisateur")
def paiement_ajouter():
    nom = request.form.get("nom", "").strip()
    est_especes = request.form.get("est_especes") == "on"
    if nom:
        if PaymentMethod.query.filter_by(nom=nom).first():
            flash(f"Le moyen de paiement « {nom} » existe déjà.", "warning")
        else:
            db.session.add(PaymentMethod(nom=nom, est_especes=est_especes))
            db.session.commit()
            flash(f"Moyen de paiement « {nom} » ajouté.", "success")
    return redirect(url_for("paiement.paiement"))


@paiement_bp.route("/paiement/modifier/<int:pm_id>", methods=["POST"])
@role_required("super_utilisateur")
def paiement_modifier(pm_id):
    pm = PaymentMethod.query.get_or_404(pm_id)
    nom = request.form.get("nom", "").strip()
    est_especes = request.form.get("est_especes") == "on"

    if not nom:
        flash("Le nom du moyen de paiement est obligatoire.", "warning")
    elif PaymentMethod.query.filter(PaymentMethod.nom == nom, PaymentMethod.id != pm_id).first():
        flash(f"Le moyen de paiement « {nom} » existe déjà.", "warning")
    else:
        pm.nom = nom
        pm.est_especes = est_especes
        db.session.commit()
        flash(f"Moyen de paiement mis à jour : « {nom} ».", "success")

    return redirect(url_for("paiement.paiement"))


@paiement_bp.route("/paiement/supprimer/<int:pm_id>", methods=["POST"])
@role_required("super_utilisateur")
def paiement_supprimer(pm_id):
    pm = PaymentMethod.query.get_or_404(pm_id)
    db.session.delete(pm)
    db.session.commit()
    flash(f"Moyen de paiement « {pm.nom} » supprimé.", "info")
    return redirect(url_for("paiement.paiement"))
