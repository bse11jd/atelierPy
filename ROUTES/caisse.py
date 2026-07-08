# -*- coding: utf-8 -*-
"""
ROUTES/caisse.py
------------------
Écran CAISSE - facturation des prestations aux adhérents.

Nouveau fonctionnement (saisie directe, sans panier nommé au préalable) :
- Cliquer sur « Nouvelle vente » crée immédiatement un panier vide, statut
  'brouillon', SANS nom d'adhérent, et ouvre son détail : on peut tout de
  suite ajouter des prestations.
- Tant qu'un panier est en 'brouillon', il doit être finalisé avant de
  pouvoir naviguer ailleurs sur le site (blocage géré côté template/JS) :
  - soit *Encaisser* immédiatement (le nom de l'adhérent n'est PAS requis) ;
  - soit *Enregistrer* pour plus tard (le nom de l'adhérent est OBLIGATOIRE
    dans ce cas ; le panier passe alors en statut 'en_attente').
- *Annuler* reste possible à tout moment tant que le panier n'est pas encaissé.
- Une fois encaissé, le panier reste modifiable (lignes, nom) : le montant
  de la facture liée est recalculé automatiquement si les lignes changent.
- Si aucune permanence n'est ouverte : l'écran CAISSE reste consultable
  (liste des paniers en attente visible et modifiable), mais la création
  d'une NOUVELLE VENTE est bloquée.
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils import role_required, permanence_requise, get_permanence_active, generer_numero_facture
from APP.extensions import db
from APP.models import Panier, PanierLigne, Category, CatalogueItem, PaymentMethod, Invoice

caisse_bp = Blueprint("caisse", __name__)

# Statuts sur lesquels les lignes du panier restent modifiables (tout sauf annulé)
STATUTS_MODIFIABLES = ("brouillon", "en_attente", "encaisse")


# ---------------------------------------------------------------------------
# Écran principal : nouvelle vente + liste des paniers en attente
# (accessible même si aucune permanence n'est ouverte)
# ---------------------------------------------------------------------------
@caisse_bp.route("/caisse")
@role_required("utilisateur")
def caisse():
    paniers_en_attente = (
        Panier.query.filter_by(statut="en_attente").order_by(Panier.date_creation.desc()).all()
    )
    return render_template(
        "caisse.html",
        paniers_en_attente=paniers_en_attente,
        permanence=get_permanence_active(),
    )


@caisse_bp.route("/caisse/nouveau", methods=["POST"])
@role_required("utilisateur")
@permanence_requise
def caisse_nouveau_panier():
    permanence = get_permanence_active()
    panier = Panier(
        nom_adherent=None,
        statut="brouillon",
        date_creation=datetime.utcnow(),
        permanence_id=permanence.id if permanence else None,
    )
    db.session.add(panier)
    db.session.commit()
    return redirect(url_for("caisse.caisse_panier", panier_id=panier.id))


# ---------------------------------------------------------------------------
# Détail / édition d'un panier
# ---------------------------------------------------------------------------
def _synchroniser_facture(panier):
    """Si le panier est déjà encaissé, met à jour le montant de la facture liée."""
    if panier.statut == "encaisse" and panier.facture:
        panier.facture.montant = panier.total
        db.session.commit()


@caisse_bp.route("/caisse/panier/<int:panier_id>")
@role_required("utilisateur")
def caisse_panier(panier_id):
    panier = Panier.query.get_or_404(panier_id)
    categories = (
        Category.query.join(CatalogueItem).order_by(Category.nom).distinct().all()
    )
    moyens_paiement = PaymentMethod.query.order_by(PaymentMethod.nom).all()
    return render_template(
        "caisse.html",
        panier=panier,
        categories=categories,
        moyens_paiement=moyens_paiement,
    )


@caisse_bp.route("/caisse/panier/<int:panier_id>/renommer", methods=["POST"])
@role_required("utilisateur")
def caisse_panier_renommer(panier_id):
    panier = Panier.query.get_or_404(panier_id)
    if panier.statut == "annule":
        flash("Ce panier n'est plus modifiable.", "warning")
        return redirect(url_for("caisse.caisse"))

    nom_adherent = request.form.get("nom_adherent", "").strip()
    if not nom_adherent:
        flash("Le nom de l'adhérent est obligatoire pour enregistrer le panier.", "danger")
        return redirect(url_for("caisse.caisse_panier", panier_id=panier.id))

    panier.nom_adherent = nom_adherent
    if panier.statut == "brouillon":
        panier.statut = "en_attente"
    db.session.commit()
    flash("Panier enregistré.", "success")
    return redirect(url_for("caisse.caisse"))


@caisse_bp.route("/caisse/panier/<int:panier_id>/ajouter", methods=["POST"])
@role_required("utilisateur")
def caisse_panier_ajouter(panier_id):
    panier = Panier.query.get_or_404(panier_id)
    if panier.statut not in STATUTS_MODIFIABLES:
        flash("Ce panier n'est plus modifiable.", "warning")
        return redirect(url_for("caisse.caisse"))

    item = CatalogueItem.query.get_or_404(request.form.get("item_id", type=int))

    # Si la prestation est déjà présente dans le panier, on incrémente la quantité.
    ligne = PanierLigne.query.filter_by(panier_id=panier.id, catalogue_item_id=item.id).first()
    if ligne:
        ligne.quantite += 1
    else:
        ligne = PanierLigne(
            panier_id=panier.id,
            catalogue_item_id=item.id,
            libelle=item.libelle,
            prix_unitaire=item.prix,
            quantite=1,
        )
        db.session.add(ligne)

    db.session.commit()
    _synchroniser_facture(panier)
    return redirect(url_for("caisse.caisse_panier", panier_id=panier.id))


@caisse_bp.route("/caisse/panier/<int:panier_id>/ligne/<int:ligne_id>/quantite", methods=["POST"])
@role_required("utilisateur")
def caisse_ligne_quantite(panier_id, ligne_id):
    panier = Panier.query.get_or_404(panier_id)
    ligne = PanierLigne.query.filter_by(id=ligne_id, panier_id=panier.id).first_or_404()

    if panier.statut not in STATUTS_MODIFIABLES:
        flash("Ce panier n'est plus modifiable.", "warning")
        return redirect(url_for("caisse.caisse"))

    nouvelle_quantite = request.form.get("quantite", type=int, default=1)
    if nouvelle_quantite is None or nouvelle_quantite < 1:
        db.session.delete(ligne)
    else:
        ligne.quantite = nouvelle_quantite
    db.session.commit()
    _synchroniser_facture(panier)
    return redirect(url_for("caisse.caisse_panier", panier_id=panier.id))


@caisse_bp.route("/caisse/panier/<int:panier_id>/ligne/<int:ligne_id>/supprimer", methods=["POST"])
@role_required("utilisateur")
def caisse_ligne_supprimer(panier_id, ligne_id):
    panier = Panier.query.get_or_404(panier_id)
    ligne = PanierLigne.query.filter_by(id=ligne_id, panier_id=panier.id).first_or_404()

    if panier.statut not in STATUTS_MODIFIABLES:
        flash("Ce panier n'est plus modifiable.", "warning")
        return redirect(url_for("caisse.caisse"))

    db.session.delete(ligne)
    db.session.commit()
    _synchroniser_facture(panier)
    return redirect(url_for("caisse.caisse_panier", panier_id=panier.id))


# ---------------------------------------------------------------------------
# Actions globales sur le panier : Encaisser / Annuler
# ---------------------------------------------------------------------------
@caisse_bp.route("/caisse/panier/<int:panier_id>/encaisser", methods=["POST"])
@role_required("utilisateur")
def caisse_panier_encaisser(panier_id):
    panier = Panier.query.get_or_404(panier_id)

    if panier.statut not in ("brouillon", "en_attente"):
        flash("Ce panier ne peut plus être encaissé.", "warning")
        return redirect(url_for("caisse.caisse"))

    if panier.nb_lignes == 0:
        flash("Impossible d'encaisser un panier sans prestation.", "danger")
        return redirect(url_for("caisse.caisse_panier", panier_id=panier.id))

    moyen_paiement_id = request.form.get("moyen_paiement_id", type=int)
    moyen = PaymentMethod.query.get(moyen_paiement_id) if moyen_paiement_id else None
    if not moyen:
        flash("Merci de choisir un moyen de paiement.", "danger")
        return redirect(url_for("caisse.caisse_panier", panier_id=panier.id))

    permanence = get_permanence_active()

    facture = Invoice(
        numero=generer_numero_facture(),
        date_facture=datetime.utcnow(),
        montant=panier.total,
        moyen_paiement_id=moyen.id,
        panier_id=panier.id,
        permanence_id=permanence.id if permanence else panier.permanence_id,
    )
    db.session.add(facture)

    panier.statut = "encaisse"
    panier.date_encaissement = datetime.utcnow()
    db.session.commit()

    nom_affiche = panier.nom_adherent or "client anonyme"
    flash(
        f"Panier de {nom_affiche} encaissé : {panier.total:.2f} € "
        f"({moyen.nom}) - facture {facture.numero}.",
        "success",
    )
    return redirect(url_for("caisse.caisse"))


@caisse_bp.route("/caisse/panier/<int:panier_id>/annuler", methods=["POST"])
@role_required("utilisateur")
def caisse_panier_annuler(panier_id):
    panier = Panier.query.get_or_404(panier_id)
    if panier.statut not in ("brouillon", "en_attente"):
        flash("Ce panier n'est plus modifiable.", "warning")
        return redirect(url_for("caisse.caisse"))

    panier.statut = "annule"
    db.session.commit()
    nom_affiche = panier.nom_adherent or "client anonyme"
    flash(f"Panier de {nom_affiche} annulé.", "info")
    return redirect(url_for("caisse.caisse"))
