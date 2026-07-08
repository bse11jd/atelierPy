# -*- coding: utf-8 -*-
"""
ROUTES/tableau_de_bord.py
---------------------------
Écran TABLEAU DE BORD - réservé aux super-utilisateurs et admins.
- Liste des factures avec filtre, tri, pagination (50 par page) et export CSV.
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

tableau_de_bord_bp = Blueprint("tableau_de_bord", __name__)

FACTURES_PAR_PAGE = 50


def _query_factures():
    """Construit la requête des factures selon les filtres/tri passés en paramètres GET."""
    query = Invoice.query

    moyen_paiement_id = request.args.get("moyen_paiement_id", type=int)
    date_debut = request.args.get("date_debut")
    date_fin = request.args.get("date_fin")
    tri = request.args.get("tri", "date_desc")

    if moyen_paiement_id:
        query = query.filter(Invoice.moyen_paiement_id == moyen_paiement_id)
    if date_debut:
        query = query.filter(Invoice.date_facture >= date_debut)
    if date_fin:
        query = query.filter(Invoice.date_facture <= date_fin)

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
    date_debut = request.args.get("date_debut")
    date_fin = request.args.get("date_fin")

    conditions = [Invoice.moyen_paiement_id == PaymentMethod.id]
    if date_debut:
        conditions.append(Invoice.date_facture >= date_debut)
    if date_fin:
        conditions.append(Invoice.date_facture <= date_fin)

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
    pagination = db.paginate(
        _query_factures(), page=page, per_page=FACTURES_PAR_PAGE, error_out=False
    )

    moyens_paiement = PaymentMethod.query.order_by(PaymentMethod.nom).all()

    paniers_non_payes = _query_paniers_non_payes().all()
    retraits = _query_retraits().all()

    repartition_moyens = _query_repartition_moyens().all()
    total_general = sum(r.total for r in repartition_moyens)

    return render_template(
        "tableau_de_bord.html",
        factures=pagination.items,
        pagination=pagination,
        moyens_paiement=moyens_paiement,
        paniers_non_payes=paniers_non_payes,
        retraits=retraits,
        repartition_moyens=repartition_moyens,
        total_general=total_general,
        args=request.args,
        page_url=lambda n: url_for(
            "tableau_de_bord.tableau_de_bord",
            **{**request.args.to_dict(), "page": n},
        ),
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
            f.date_facture.strftime("%Y-%m-%d %H:%M") if f.date_facture else "",
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
            p.date_creation.strftime("%Y-%m-%d %H:%M") if p.date_creation else "",
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
            r.date_retrait.strftime("%Y-%m-%d %H:%M") if r.date_retrait else "",
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
        return redirect(url_for("tableau_de_bord.tableau_de_bord"))

    try:
        montant_val = float(montant.replace(",", "."))
    except ValueError:
        montant_val = 0.0

    if montant_val <= 0:
        flash("Le montant du retrait doit être supérieur à 0.", "danger")
        return redirect(url_for("tableau_de_bord.tableau_de_bord"))

    retrait.nom_personne = nom_personne
    retrait.motif = motif
    retrait.montant = montant_val
    db.session.commit()
    flash("Retrait mis à jour.", "success")
    return redirect(url_for("tableau_de_bord.tableau_de_bord"))


@tableau_de_bord_bp.route("/tableau-de-bord/retrait/<int:retrait_id>/supprimer", methods=["POST"])
@role_required("super_utilisateur")
def tableau_de_bord_retrait_supprimer(retrait_id):
    retrait = RetraitCaisse.query.get_or_404(retrait_id)
    db.session.delete(retrait)
    db.session.commit()
    flash("Retrait supprimé.", "info")
    return redirect(url_for("tableau_de_bord.tableau_de_bord"))
