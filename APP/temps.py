# -*- coding: utf-8 -*-
"""
APP/temps.py
-------------
Gestion centralisée des dates et heures.

Principe :
- En BASE, toutes les dates sont stockées en UTC (naïf, sans fuseau), comme
  c'était déjà le cas : les données existantes restent donc valides.
- À l'AFFICHAGE, à l'EXPORT CSV, dans les FILTRES par date et pour le NUMÉRO
  DE FACTURE (date du jour), on raisonne en heure locale (Europe/Paris par
  défaut, modifiable via la variable d'environnement APP_TIMEZONE).

Si la base de fuseaux horaires n'est pas disponible (ex. Windows sans le
paquet `tzdata`), on retombe sur le fuseau du système.
"""

import os
from datetime import datetime, time, timedelta, timezone

try:
    from zoneinfo import ZoneInfo

    FUSEAU = ZoneInfo(os.environ.get("APP_TIMEZONE", "Europe/Paris"))
except Exception:  # zoneinfo/tzdata indisponible : repli sur le fuseau système
    FUSEAU = None


def maintenant_utc():
    """Date/heure courante en UTC, sans info de fuseau (valeur stockée en base)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _utc_vers_local(dt_utc_naif):
    aware = dt_utc_naif.replace(tzinfo=timezone.utc)
    return aware.astimezone(FUSEAU) if FUSEAU else aware.astimezone()


def formater_local(dt, fmt="%d/%m/%Y %H:%M"):
    """Formate une date UTC stockée en base en heure locale ('' si None)."""
    if dt is None:
        return ""
    return _utc_vers_local(dt).strftime(fmt)


def aujourdhui_local():
    """Date du jour en heure locale."""
    return _utc_vers_local(maintenant_utc()).date()


def _local_vers_utc_naif(dt_local_naif):
    if FUSEAU:
        aware = dt_local_naif.replace(tzinfo=FUSEAU)
    else:
        aware = dt_local_naif.astimezone()  # naïf => interprété en heure système
    return aware.astimezone(timezone.utc).replace(tzinfo=None)


def parse_date_locale(texte):
    """Convertit 'AAAA-MM-JJ' (champ <input type=date>) en date, ou None si invalide/vide."""
    try:
        return datetime.strptime(texte, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def bornes_jour_local_utc(date_locale):
    """
    Pour un jour local donné, retourne (debut, fin_exclue) exprimés en UTC :
    minuit local de ce jour -> minuit local du lendemain.
    À utiliser ainsi : date >= debut ET date < fin_exclue.
    """
    debut = datetime.combine(date_locale, time.min)
    fin = datetime.combine(date_locale + timedelta(days=1), time.min)
    return _local_vers_utc_naif(debut), _local_vers_utc_naif(fin)
