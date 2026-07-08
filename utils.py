# -*- coding: utf-8 -*-
"""
utils.py
--------
Fonctions communes réutilisables dans tout le projet :
- hiérarchie des rôles
- décorateurs de contrôle d'accès (role_required)
- fonctions utilitaires diverses (ex: export CSV)
"""

from functools import wraps
from flask import abort, redirect, url_for, request, flash
from flask_login import current_user

from APP.extensions import db

# ---------------------------------------------------------------------------
# Hiérarchie des niveaux de droits
# ---------------------------------------------------------------------------
# utilisateur       -> niveau 1 : accès libre, pas d'authentification requise
# super_utilisateur -> niveau 2 : authentification requise
# admin             -> niveau 3 : authentification requise
ROLE_LEVELS = {
    "utilisateur": 1,
    "super_utilisateur": 2,
    "admin": 3,
}


def role_level(role_name):
    """Retourne le niveau numérique associé à un rôle."""
    return ROLE_LEVELS.get(role_name, 0)


def current_role():
    """
    Retourne le rôle de l'utilisateur courant.
    Un visiteur non authentifié est considéré comme 'utilisateur'.
    """
    if current_user.is_authenticated:
        return current_user.role
    return "utilisateur"


def has_access(required_role):
    """Vrai si le rôle courant a un niveau >= au rôle requis."""
    return role_level(current_role()) >= role_level(required_role)


def role_required(required_role):
    """
    Décorateur à poser sur une route pour exiger un niveau de droit minimum.
    Exemple : @role_required("admin")
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not has_access(required_role):
                if not current_user.is_authenticated and required_role != "utilisateur":
                    flash("Merci de vous connecter pour accéder à cet écran.", "warning")
                    return redirect(url_for("auth.login", next=request.path))
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


# ---------------------------------------------------------------------------
# Gestion de la permanence (ouverture/fermeture, fond de caisse)
# ---------------------------------------------------------------------------
def get_permanence_active():
    """Retourne la permanence actuellement ouverte, ou None si aucune n'est ouverte."""
    from APP.models import Permanence

    return Permanence.query.filter_by(statut="ouverte").order_by(Permanence.date_ouverture.desc()).first()


def get_derniere_permanence_fermee():
    """Retourne la dernière permanence fermée (pour préremplir le fond d'ouverture suivant)."""
    from APP.models import Permanence

    return (
        Permanence.query.filter_by(statut="fermee")
        .order_by(Permanence.date_fermeture.desc())
        .first()
    )


def montant_especes_depuis(date_debut):
    """
    Calcule la somme des factures encaissées en espèces depuis une date donnée.
    Utilisé pour suggérer le montant de fond de caisse en fin de permanence.
    """
    from APP.models import Invoice, PaymentMethod

    total = (
        db.session.query(db.func.coalesce(db.func.sum(Invoice.montant), 0.0))
        .join(PaymentMethod, Invoice.moyen_paiement_id == PaymentMethod.id)
        .filter(PaymentMethod.est_especes.is_(True))
        .filter(Invoice.date_facture >= date_debut)
        .scalar()
    )
    return total or 0.0


def total_retraits_permanence(permanence_id):
    """
    Calcule la somme des retraits d'espèces enregistrés pour une permanence donnée.
    Utilisé pour déduire ces retraits du fond de caisse suggéré en fin de permanence.
    """
    from APP.models import RetraitCaisse

    if not permanence_id:
        return 0.0

    total = (
        db.session.query(db.func.coalesce(db.func.sum(RetraitCaisse.montant), 0.0))
        .filter(RetraitCaisse.permanence_id == permanence_id)
        .scalar()
    )
    return total or 0.0


def permanence_requise(view_func):
    """
    Décorateur : bloque l'accès à une route si aucune permanence n'est ouverte.
    À utiliser en complément de role_required sur l'écran CAISSE.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if get_permanence_active() is None:
            flash("Veuillez d'abord ouvrir la permanence depuis l'écran Accueil.", "warning")
            return redirect(url_for("accueil.accueil"))
        return view_func(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Facturation (CAISSE)
# ---------------------------------------------------------------------------
def generer_numero_facture():
    """Génère un numéro de facture unique du jour : F-AAAAMMJJ-0001, 0002, ..."""
    from datetime import datetime
    from APP.models import Invoice

    prefixe = f"F-{datetime.utcnow():%Y%m%d}-"
    nb_du_jour = Invoice.query.filter(Invoice.numero.like(f"{prefixe}%")).count()
    return f"{prefixe}{nb_du_jour + 1:04d}"


# ---------------------------------------------------------------------------
# Export CSV générique
# ---------------------------------------------------------------------------
import csv
import io


def export_to_csv(rows, headers, filename="export.csv"):
    """
    Construit une réponse Flask téléchargeable au format CSV.
    - rows : liste de listes/tuples (les lignes de données)
    - headers : liste des en-têtes de colonnes
    """
    from flask import Response

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)

    output = buffer.getvalue()
    buffer.close()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
