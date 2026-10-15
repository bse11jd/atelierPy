# -*- coding: utf-8 -*-
"""
ROUTES/tableau_de_bord.py
---------------------------
Écran TABLEAUX DE BORD - réservé aux super-utilisateurs et admins.
Un seul onglet dans le bandeau haut ; les 3 tableaux sont des pages distinctes
reliées par une sous-navigation en page (_tableau_de_bord_sousnav.html) :
  /tableau-de-bord                      -> Factures (+ répartition par moyen de paiement)
  /tableau-de-bord/paniers-non-payes    -> Paniers non payés
  /tableau-de-bord/retraits             -> Retraits de caisse
- Liste des factures avec filtre, tri, pagination (50 par page) et export CSV.
  Filtre de période : « Mois en cours » (par défaut) ou « Toutes périodes » ; les
  dates Du / Au ne s'appliquent que pour « Toutes périodes ».
  Affiche le permanent (celui qui a ouvert la permanence) et l'adhérent facturé.
- Répartition des encaissements par moyen de paiement (mêmes filtres de dates
  que les factures), exportable en CSV.
- Liste des paniers non payés (en attente d'encaissement), exportable en CSV.
- Historique des retraits d'espèces de caisse (modification, suppression),
  exportable en CSV.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import and_

from utils import role_required, export_to_csv
from APP.extensions import db
from APP.models import Invoice, PaymentMethod, Panier, RetraitCaisse
from APP.temps import (
    aujourdhui_local, bornes_jour_local_utc, bornes_mois_local_utc,
    formater_local, libelle_mois, parse_date_locale,
)

tableau_de_bord_bp = Blueprint("tableau_de_bord", __name__)

FACTURES_PAR_PAGE = 50


PERIODE_MOIS = "mois"      # valeur par défaut : mois en cours (heure locale)
PERIODE_TOUTES = "toutes"  # toutes périodes : les dates Du / Au s'appliquent


def _periode():
    """Période choisie : « mois » (défaut, aussi pour toute valeur inconnue) ou « toutes »."""
    if request.args.get("periode") == PERIODE_TOUTES:
        return PERIODE_TOUTES
    return PERIODE_MOIS


def _bornes_dates():
    """
    Retourne (debut_utc, fin_exclue_utc) selon le filtre de période (None = pas de borne) :

    - période « mois » (par défaut) : le mois en cours, en heure locale ; les
      champs Du / Au éventuellement présents dans l'URL sont conservés à l'écran
      mais IGNORÉS ici ;
    - période « toutes » : filtres date_debut / date_fin (jours au format
      AAAA-MM-JJ, en heure locale), None si le champ est vide ou invalide. Le jour
      de fin est INCLUS en entier : on filtre sur « date < minuit local du lendemain ».
    """
    if _periode() == PERIODE_MOIS:
        return bornes_mois_local_utc(aujourdhui_local())

    debut = parse_date_locale(request.args.get("date_debut"))
    fin = parse_date_locale(request.args.get("date_fin"))
    debut_utc = bornes_jour_local_utc(debut)[0] if debut else None
    fin_exclue_utc = bornes_jour_local_utc(fin)[1] if fin else None
    return debut_utc, fin_exclue_utc


def _query_factures():
    """Construit la requête des factures selon les filtres/tri passés en paramètres GET."""
    query = Invoice.query

    moyen_paiement_id = request.args.get("moyen_paiement_id", type=int)
    debut_utc, fin_exclue_utc = _bornes_dates()
    tri = request.args.get("tri", "date_desc")

    if moyen_paiement_id:
        query = query.filter(Invoice.moyen_paiement_id == moyen_paiement_id)
    if debut_utc:
        query = query.filter(Invoice.date_facture >= debut_utc)
    if fin_exclue_utc:
        query = query.filter(Invoice.date_facture < fin_exclue_utc)

    tri_options = {
        "date_desc": Invoice.date_facture.desc(),
        "date_asc": Invoice.date_facture.asc(),
        "montant_desc": Invoice.montant.desc(),
        "montant_asc": Invoice.montant.asc(),
        "numero": Invoice.numero.asc(),
    }
    query = query.order_by(tri_options.get(tri, Invoice.date_facture.desc()))

    return query


def _query_repartition_moyens():
    """
    Construit la requête de répartition des encaissements par moyen de
    paiement (nombre de factures + montant total), filtrée sur la même
    plage de dates que la liste des factures (date_debut / date_fin),
    mais sans tenir compte du filtre par moyen de paiement (puisque le but
    est justement de comparer les différents moyens entre eux).
    Un moyen de paiement sans encaissement sur la période apparaît quand
    même, avec un total de 0 (jointure externe).
    """
    debut_utc, fin_exclue_utc = _bornes_dates()

    conditions = [Invoice.moyen_paiement_id == PaymentMethod.id]
    if debut_utc:
        conditions.append(Invoice.date_facture >= debut_utc)
    if fin_exclue_utc:
        conditions.append(Invoice.date_facture < fin_exclue_utc)

    query = (
        db.session.query(
            PaymentMethod.nom.label("moyen"),
            db.func.count(Invoice.id).label("nb_factures"),
            db.func.coalesce(db.func.sum(Invoice.montant), 0.0).label("total"),
        )
        .outerjoin(Invoice, and_(*conditions))
        .group_by(PaymentMethod.id)
        .order_by(PaymentMethod.nom)
    )
    return query


def _query_paniers_non_payes():
    return Panier.query.filter_by(statut="en_attente").order_by(Panier.date_creation.desc())


def _query_retraits():
    return RetraitCaisse.query.order_by(RetraitCaisse.date_retrait.desc())


@tableau_de_bord_bp.route("/tableau-de-bord")
@role_required("super_utilisateur")
def tableau_de_bord():
    page = request.args.get("page", 1, type=int)
    # Query.paginate (et non db.paginate) : db.paginate n'accepte plus d'objet Query
    # avec SQLAlchemy 2.1.
    pagination = _query_factures().paginate(
        page=page, per_page=FACTURES_PAR_PAGE, error_out=False
    )

    moyens_paiement = PaymentMethod.query.order_by(PaymentMethod.nom).all()

    repartition_moyens = _query_repartition_moyens().all()
    total_general = sum(r.total for r in repartition_moyens)

    return render_template(
        "tableau_de_bord.html",
        factures=pagination.items,
        pagination=pagination,
        moyens_paiement=moyens_paiement,
        repartition_moyens=repartition_moyens,
        total_general=total_general,
        periode=_periode(),
        mois_en_cours=libelle_mois(aujourdhui_local()),
        args=request.args,
        page_url=lambda n: url_for(
            "tableau_de_bord.tableau_de_bord",
            **{**request.args.to_dict(), "page": n},
        ),
    )


@tableau_de_bord_bp.route("/tableau-de-bord/paniers-non-payes")
@role_required("super_utilisateur")
def tableau_de_bord_paniers():
    return render_template(
        "tableau_de_bord_paniers.html",
        paniers_non_payes=_query_paniers_non_payes().all(),
    )


@tableau_de_bord_bp.route("/tableau-de-bord/retraits")
@role_required("super_utilisateur")
def tableau_de_bord_retraits():
    return render_template(
        "tableau_de_bord_retraits.html",
        retraits=_query_retraits().all(),
    )


# ---------------------------------------------------------------------------
# Exports CSV (un par tableau)
# ---------------------------------------------------------------------------
@tableau_de_bord_bp.route("/tableau-de-bord/export.csv")
@role_required("super_utilisateur")
def tableau_de_bord_export():
    factures = _query_factures().all()
    rows = [
        [
            f.numero,
            formater_local(f.date_facture, "%Y-%m-%d %H:%M"),
            f.permanence.nom_ouverture if f.permanence else "",
            f.panier.nom_adherent if f.panier else "",
            f"{f.montant:.2f}",
            f.moyen_paiement.nom if f.moyen_paiement else "",
        ]
        for f in factures
    ]
    return export_to_csv(
        rows,
        ["Numéro", "Date", "Permanent", "Adhérent", "Montant", "Moyen de paiement"],
        "factures.csv",
    )


@tableau_de_bord_bp.route("/tableau-de-bord/repartition/export.csv")
@role_required("super_utilisateur")
def tableau_de_bord_repartition_export():
    repartition = _query_repartition_moyens().all()
    rows = [[r.moyen, r.nb_factures, f"{r.total:.2f}"] for r in repartition]
    return export_to_csv(
        rows,
        ["Moyen de paiement", "Nombre de factures", "Total"],
        "repartition_moyens_paiement.csv",
    )


@tableau_de_bord_bp.route("/tableau-de-bord/paniers-non-payes/export.csv")
@role_required("super_utilisateur")
def tableau_de_bord_paniers_non_payes_export():
    paniers = _query_paniers_non_payes().all()
    rows = [
        [
            p.nom_adherent,
            p.permanence.nom_ouverture if p.permanence else "",
            formater_local(p.date_creation, "%Y-%m-%d %H:%M"),
            p.nb_lignes,
            f"{p.total:.2f}",
        ]
        for p in paniers
    ]
    return export_to_csv(
        rows,
        ["Adhérent", "Permanent", "Créé le", "Lignes", "Total"],
        "paniers_non_payes.csv",
    )


@tableau_de_bord_bp.route("/tableau-de-bord/retraits/export.csv")
@role_required("super_utilisateur")
def tableau_de_bord_retraits_export():
    retraits = _query_retraits().all()
    rows = [
        [
            formater_local(r.date_retrait, "%Y-%m-%d %H:%M"),
            r.permanence.nom_ouverture if r.permanence else "",
            r.nom_personne,
            r.motif,
            f"{r.montant:.2f}",
        ]
        for r in retraits
    ]
    return export_to_csv(
        rows,
        ["Date", "Permanent", "Nom", "Motif", "Montant"],
        "retraits_caisse.csv",
    )


# ---------------------------------------------------------------------------
# Retraits de caisse : modification / suppression (correction d'erreur de saisie)
# ---------------------------------------------------------------------------
@tableau_de_bord_bp.route("/tableau-de-bord/retrait/<int:retrait_id>/modifier", methods=["POST"])
@role_required("super_utilisateur")
def tableau_de_bord_retrait_modifier(retrait_id):
    retrait = RetraitCaisse.query.get_or_404(retrait_id)

    nom_personne = request.form.get("nom_personne", "").strip()
    motif = request.form.get("motif", "").strip()
    montant = request.form.get("montant", "0").strip()

    if not nom_personne or not motif:
        flash("Le nom de la personne et le motif sont obligatoires.", "danger")
        return redirect(url_for("tableau_de_bord.tableau_de_bord_retraits"))

    try:
        montant_val = float(montant.replace(",", "."))
    except ValueError:
        montant_val = 0.0

    if montant_val <= 0:
        flash("Le montant du retrait doit être supérieur à 0.", "danger")
        return redirect(url_for("tableau_de_bord.tableau_de_bord_retraits"))

    retrait.nom_personne = nom_personne
    retrait.motif = motif
    retrait.montant = montant_val
    db.session.commit()
    flash("Retrait mis à jour.", "success")
    return redirect(url_for("tableau_de_bord.tableau_de_bord_retraits"))


@tableau_de_bord_bp.route("/tableau-de-bord/retrait/<int:retrait_id>/supprimer", methods=["POST"])
@role_required("super_utilisateur")
def tableau_de_bord_retrait_supprimer(retrait_id):
    retrait = RetraitCaisse.query.get_or_404(retrait_id)
    db.session.delete(retrait)
    db.session.commit()
    flash("Retrait supprimé.", "info")
    return redirect(url_for("tableau_de_bord.tableau_de_bord_retraits"))
