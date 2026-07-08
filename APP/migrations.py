# -*- coding: utf-8 -*-
"""
APP/migrations.py
-------------------
Mini-système de mise à niveau de la base de données SQLite.

Objectif : quand le modèle de données évolue (nouvelle colonne, nouvelle table,
contrainte assouplie), la base existante doit être mise à niveau EN PLACE,
sans jamais perdre de données.

Fonctionnement :
- Les nouvelles TABLES sont créées automatiquement par `db.create_all()`
  (SQLAlchemy ne touche jamais aux tables déjà existantes avec create_all).
- Les nouvelles COLONNES sur des tables déjà existantes sont ajoutées via
  `ALTER TABLE ... ADD COLUMN`, à partir de la liste `MIGRATIONS` ci-dessous.
- Le passage d'une colonne existante de NOT NULL à nullable (contrainte
  assouplie) n'est PAS possible avec un simple ALTER TABLE sous SQLite : il
  faut reconstruire la table. C'est le rôle de `MIGRATIONS_NULLABLE` /
  `_rendre_colonne_nullable()`, qui recrée la table à l'identique (schéma
  actuel de APP.models, où la colonne est déjà nullable) et recopie toutes
  les données existantes, sans aucune perte.

Pour ajouter une évolution future :
- nouvelle colonne obligatoire/optionnelle sur une table existante :
  ajouter une ligne dans MIGRATIONS (table, colonne, définition SQL) ;
- colonne existante qui devient optionnelle : ajouter une ligne dans
  MIGRATIONS_NULLABLE (table, colonne).
Rien d'autre à faire, la mise à niveau est appliquée automatiquement au
démarrage de l'application.
"""

from sqlalchemy import text, inspect
from sqlalchemy.schema import CreateTable

from APP.extensions import db

# ---------------------------------------------------------------------------
# Historique des évolutions de schéma (colonnes ajoutées à des tables
# déjà existantes). Format : (nom_table, nom_colonne, définition_sql)
# ---------------------------------------------------------------------------
MIGRATIONS = [
    ("payment_methods", "est_especes", "BOOLEAN NOT NULL DEFAULT 0"),
    ("categories", "couleur", "VARCHAR(9) NOT NULL DEFAULT '#4a5568'"),
    ("invoices", "panier_id", "INTEGER"),
    ("invoices", "permanence_id", "INTEGER"),
    ("retraits_caisse", "nom_personne", "VARCHAR(120) NOT NULL DEFAULT ''"),
]

# ---------------------------------------------------------------------------
# Historique des colonnes devenues optionnelles (contrainte NOT NULL retirée
# sur une colonne déjà existante). Format : (nom_table, nom_colonne)
# ---------------------------------------------------------------------------
MIGRATIONS_NULLABLE = [
    ("paniers", "nom_adherent"),
    ("retraits_caisse", "permanence_id"),
]


def _rendre_colonne_nullable(connexion, inspector, table_name, colonne):
    """
    Reconstruit `table_name` pour retirer la contrainte NOT NULL de `colonne`,
    en conservant toutes les données existantes. Ne fait rien si la colonne
    est déjà nullable (ou si la table/colonne n'existe pas encore).
    """
    if table_name not in inspector.get_table_names():
        return False

    colonnes_info = {c["name"]: c for c in inspector.get_columns(table_name)}
    if colonne not in colonnes_info:
        return False
    if colonnes_info[colonne]["nullable"]:
        return False  # déjà à niveau, rien à faire

    table = db.metadata.tables[table_name]
    colonnes_communes = [c.name for c in table.columns if c.name in colonnes_info]
    colonnes_sql = ", ".join(colonnes_communes)
    table_temporaire = f"{table_name}__ancien"

    connexion.execute(text(f"ALTER TABLE {table_name} RENAME TO {table_temporaire}"))
    connexion.execute(CreateTable(table))
    connexion.execute(text(
        f"INSERT INTO {table_name} ({colonnes_sql}) "
        f"SELECT {colonnes_sql} FROM {table_temporaire}"
    ))
    connexion.execute(text(f"DROP TABLE {table_temporaire}"))
    return True


def appliquer_migrations():
    """
    Met à niveau la base existante (colonnes manquantes ajoutées, contraintes
    NOT NULL assouplies), sans jamais supprimer ni perdre les données présentes.
    Doit être appelée dans un contexte applicatif (app.app_context()),
    APRÈS db.init_app() et AVANT db.create_all().
    """
    tables_existantes = inspect(db.engine).get_table_names()

    if not tables_existantes:
        # Base vide ou inexistante : rien à mettre à niveau, create_all()
        # créera directement le schéma complet et à jour.
        return

    colonnes_ajoutees = []
    tables_reconstruites = []

    with db.engine.begin() as connexion:
        # Inspector lié à LA MÊME connexion/transaction que les modifications
        # de schéma, pour être toujours à jour (une nouvelle connexion pourrait
        # ne pas voir les changements pas encore validés).
        inspector = inspect(connexion)

        for table, colonne, definition in MIGRATIONS:
            if table not in inspector.get_table_names():
                continue  # la table sera créée par create_all() avec la colonne dès le départ

            colonnes_existantes = [c["name"] for c in inspector.get_columns(table)]
            if colonne in colonnes_existantes:
                continue  # déjà à niveau

            connexion.execute(text(f"ALTER TABLE {table} ADD COLUMN {colonne} {definition}"))
            colonnes_ajoutees.append(f"{table}.{colonne}")
            inspector = inspect(connexion)  # rafraîchir après modification du schéma

        for table, colonne in MIGRATIONS_NULLABLE:
            if _rendre_colonne_nullable(connexion, inspector, table, colonne):
                tables_reconstruites.append(f"{table}.{colonne}")
                inspector = inspect(connexion)  # rafraîchir après reconstruction de la table

    if colonnes_ajoutees:
        print(f"[migration] Base mise à niveau : colonnes ajoutées -> {', '.join(colonnes_ajoutees)}")
    if tables_reconstruites:
        print(f"[migration] Contrainte NOT NULL retirée -> {', '.join(tables_reconstruites)}")
