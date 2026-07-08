# -*- coding: utf-8 -*-
"""
APP/models.py
-------------
Modèles de données SQLAlchemy.
Structure de base prévue pour évoluer (CAISSE, CATALOGUE, FACTURES...).
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from APP.extensions import db


class User(UserMixin, db.Model):
    """Comptes des super-utilisateurs et administrateurs (authentification requise)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="super_utilisateur")
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Category(db.Model):
    """Catégories de prestations : bar, atelier, adhésion, autres... (liste modifiable)."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), unique=True, nullable=False)
    # Couleur d'affichage des boutons de prestations de cette catégorie en CAISSE
    couleur = db.Column(db.String(9), nullable=False, default="#4a5568")

    prestations = db.relationship(
        "CatalogueItem", backref="categorie", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category {self.nom}>"


class CatalogueItem(db.Model):
    """Prestations facturables, rattachées à une catégorie."""

    __tablename__ = "catalogue_items"

    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(150), nullable=False)
    prix = db.Column(db.Float, nullable=False, default=0.0)
    categorie_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    def __repr__(self):
        return f"<CatalogueItem {self.libelle} - {self.prix}€>"


class PaymentMethod(db.Model):
    """Moyens de paiement : cash, CB, virement, chèque (liste modifiable)."""

    __tablename__ = "payment_methods"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), unique=True, nullable=False)
    # Coché pour le(s) moyen(s) de paiement à comptabiliser dans le fond de caisse
    # (espèces). Sert au calcul automatique de la somme disponible en caisse.
    est_especes = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<PaymentMethod {self.nom}>"


class Invoice(db.Model):
    """Factures issues de la CAISSE, consultables depuis le TABLEAU DE BORD."""

    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False)
    date_facture = db.Column(db.DateTime, default=datetime.utcnow)
    montant = db.Column(db.Float, nullable=False, default=0.0)
    moyen_paiement_id = db.Column(db.Integer, db.ForeignKey("payment_methods.id"), nullable=True)
    panier_id = db.Column(db.Integer, db.ForeignKey("paniers.id"), nullable=True)
    permanence_id = db.Column(db.Integer, db.ForeignKey("permanences.id"), nullable=True)

    moyen_paiement = db.relationship("PaymentMethod")
    permanence = db.relationship("Permanence")

    def __repr__(self):
        return f"<Invoice {self.numero} - {self.montant}€>"


class Permanence(db.Model):
    """
    Suivi des permanences (ouverture/fermeture) et du fond de caisse associé.
    Une seule permanence peut être 'ouverte' à la fois. L'accès à l'écran
    CAISSE est conditionné à l'existence d'une permanence ouverte.
    """

    __tablename__ = "permanences"

    id = db.Column(db.Integer, primary_key=True)
    statut = db.Column(db.String(10), nullable=False, default="ouverte")  # 'ouverte' / 'fermee'

    nom_ouverture = db.Column(db.String(80), nullable=False)
    date_ouverture = db.Column(db.DateTime, default=datetime.utcnow)
    fond_ouverture = db.Column(db.Float, nullable=False, default=0.0)

    nom_fermeture = db.Column(db.String(80), nullable=True)
    date_fermeture = db.Column(db.DateTime, nullable=True)
    fond_fermeture = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<Permanence {self.id} ({self.statut}) - {self.nom_ouverture}>"


class RetraitCaisse(db.Model):
    """
    Retrait d'argent dans la caisse espèces (ex: achat de consommables,
    dépôt en banque...). Réservé aux super-utilisateurs et admins.

    Le retrait est possible que la permanence soit ouverte ou fermée :
    - si une permanence est ouverte au moment du retrait, il y est rattaché
      (permanence_id renseigné) et vient en déduction du calcul automatique
      du fond de caisse disponible pour cette permanence ;
    - sinon, il est enregistré sans permanence associée (permanence_id NULL),
      simplement à titre d'historique.

    - nom_personne : nom de la personne qui effectue physiquement le retrait
      (saisi dans le formulaire, peut différer du compte connecté).
    - auteur : nom d'utilisateur du compte connecté ayant enregistré l'opération.
    """

    __tablename__ = "retraits_caisse"

    id = db.Column(db.Integer, primary_key=True)
    permanence_id = db.Column(db.Integer, db.ForeignKey("permanences.id"), nullable=True)
    montant = db.Column(db.Float, nullable=False)
    motif = db.Column(db.String(200), nullable=False)
    nom_personne = db.Column(db.String(120), nullable=False, default="")
    auteur = db.Column(db.String(80), nullable=False)
    date_retrait = db.Column(db.DateTime, default=datetime.utcnow)

    permanence = db.relationship(
        "Permanence",
        backref=db.backref("retraits", lazy=True, order_by="RetraitCaisse.date_retrait.desc()"),
    )

    def __repr__(self):
        return f"<RetraitCaisse {self.montant}€ - {self.motif}>"


class Panier(db.Model):
    """
    Panier de facturation (écran CAISSE).

    Statuts possibles :
    - brouillon  : vente en cours de saisie, créée sans nom d'adhérent.
                   Tant qu'il est dans cet état, la navigation ailleurs sur le
                   site est bloquée (côté écran) : il faut le finaliser via
                   « Encaisser » (sans nom obligatoire) ou « Enregistrer »
                   (nom d'adhérent obligatoire, passe alors en 'en_attente').
    - en_attente : panier nommé et sauvegardé pour plus tard, en attente
                   d'encaissement (ou de complément), consultable depuis la
                   liste des paniers en attente / le Tableau de bord.
    - encaisse   : facturé. Reste modifiable (lignes, nom) ; le montant de
                   la facture liée est automatiquement recalculé si les
                   lignes changent après coup.
    - annule     : abandonné, non facturé, non modifiable.
    """

    __tablename__ = "paniers"

    id = db.Column(db.Integer, primary_key=True)
    nom_adherent = db.Column(db.String(120), nullable=True)
    statut = db.Column(db.String(15), nullable=False, default="brouillon")
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_encaissement = db.Column(db.DateTime, nullable=True)
    permanence_id = db.Column(db.Integer, db.ForeignKey("permanences.id"), nullable=True)

    lignes = db.relationship(
        "PanierLigne", backref="panier", lazy=True, cascade="all, delete-orphan",
        order_by="PanierLigne.id",
    )
    facture = db.relationship("Invoice", backref="panier", uselist=False)
    permanence = db.relationship("Permanence")

    @property
    def total(self):
        return sum(ligne.sous_total for ligne in self.lignes)

    @property
    def nb_lignes(self):
        return len(self.lignes)

    def __repr__(self):
        return f"<Panier {self.id} - {self.nom_adherent} ({self.statut})>"


class PanierLigne(db.Model):
    """
    Ligne d'un panier : une prestation du catalogue, avec quantité.
    Le libellé et le prix unitaire sont dupliqués au moment de l'ajout
    (pour ne pas être affectés par une modification ultérieure du catalogue).
    """

    __tablename__ = "panier_lignes"

    id = db.Column(db.Integer, primary_key=True)
    panier_id = db.Column(db.Integer, db.ForeignKey("paniers.id"), nullable=False)
    catalogue_item_id = db.Column(db.Integer, db.ForeignKey("catalogue_items.id"), nullable=True)

    libelle = db.Column(db.String(150), nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False, default=0.0)
    quantite = db.Column(db.Integer, nullable=False, default=1)

    @property
    def sous_total(self):
        return self.prix_unitaire * self.quantite

    def __repr__(self):
        return f"<PanierLigne {self.libelle} x{self.quantite}>"
