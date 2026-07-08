# -*- coding: utf-8 -*-
"""
ROUTES/accueil.py
------------------
Écran ACCUEIL - accessible sans authentification (niveau utilisateur).
Gère aussi l'ouverture / fermeture de la permanence et le fond de caisse.
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils import (
    role_required,
    get_permanence_active,
    get_derniere_permanence_fermee,
    montant_especes_depuis,
    total_retraits_permanence,
)
from APP.extensions import db
from APP.models import Permanence, Panier

accueil_bp = Blueprint("accueil", __name__)


@accueil_bp.route("/")
@accueil_bp.route("/accueil")
@role_required("utilisateur")
def accueil():
    permanence = get_permanence_active()

    if permanence:
        # Suggestion de fond de fermeture = fond d'ouverture + espèces encaissées
        # depuis l'ouverture - retraits d'espèces effectués pendant la permanence
        montant_suggere = (
            permanence.fond_ouverture
            + montant_especes_depuis(permanence.date_ouverture)
            - total_retraits_permanence(permanence.id)
        )
        # Paniers encaissés depuis l'ouverture de la permanence en cours
        paniers_encaisses = (
            Panier.query.filter_by(statut="encaisse", permanence_id=permanence.id)
            .order_by(Panier.date_encaissement.desc())
            .all()
        )
    else:
        derniere = get_derniere_permanence_fermee()
        montant_suggere = derniere.fond_fermeture if derniere and derniere.fond_fermeture is not None else 0.0
        # Aucune permanence ouverte : derniers paniers encaissés, tous confondus
        paniers_encaisses = (
            Panier.query.filter_by(statut="encaisse")
            .order_by(Panier.date_encaissement.desc())
            .limit(20)
            .all()
        )

    return render_template(
        "accueil.html",
        permanence=permanence,
        montant_suggere=montant_suggere,
        paniers_encaisses=paniers_encaisses,
    )


@accueil_bp.route("/permanence/ouvrir", methods=["POST"])
@role_required("utilisateur")
def permanence_ouvrir():
    if get_permanence_active() is not None:
        flash("Une permanence est déjà ouverte.", "warning")
        return redirect(url_for("accueil.accueil"))

    nom = request.form.get("nom_permanent", "").strip()
    fond = request.form.get("fond_ouverture", "0").strip()

    if not nom:
        flash("Le nom du permanent est obligatoire pour ouvrir la permanence.", "danger")
        return redirect(url_for("accueil.accueil"))

    try:
        fond_val = float(fond.replace(",", "."))
    except ValueError:
        fond_val = 0.0

    permanence = Permanence(
        statut="ouverte",
        nom_ouverture=nom,
        date_ouverture=datetime.utcnow(),
        fond_ouverture=fond_val,
    )
    db.session.add(permanence)
    db.session.commit()
    flash(f"Permanence ouverte par {nom}.", "success")
    return redirect(url_for("accueil.accueil"))


@accueil_bp.route("/permanence/fermer", methods=["POST"])
@role_required("utilisateur")
def permanence_fermer():
    permanence = get_permanence_active()
    if permanence is None:
        flash("Aucune permanence n'est actuellement ouverte.", "warning")
        return redirect(url_for("accueil.accueil"))

    nom = request.form.get("nom_permanent", "").strip()
    fond = request.form.get("fond_fermeture", "0").strip()

    if not nom:
        flash("Le nom du permanent est obligatoire pour fermer la permanence.", "danger")
        return redirect(url_for("accueil.accueil"))

    try:
        fond_val = float(fond.replace(",", "."))
    except ValueError:
        fond_val = 0.0

    permanence.statut = "fermee"
    permanence.nom_fermeture = nom
    permanence.date_fermeture = datetime.utcnow()
    permanence.fond_fermeture = fond_val
    db.session.commit()
    flash(f"Permanence fermée par {nom}.", "success")
    return redirect(url_for("accueil.accueil"))
