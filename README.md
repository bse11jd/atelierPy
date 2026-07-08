# Atelier Café Racer — Application de gestion (Flask + SQLite)

## Installation

```bash
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
python app.py
```

L'application est accessible sur http://localhost:5000

Au premier lancement, la base SQLite est créée automatiquement dans `instance/database.db`
avec un compte administrateur par défaut :

- **Identifiant :** admin
- **Mot de passe :** admin

⚠️ À changer immédiatement depuis l'écran **Droits** (`/auth`).

Vous pouvez aussi ré-initialiser la base manuellement :

```bash
flask --app app.py init-db
```

## Niveaux de droits

| Niveau              | Authentification | Écrans accessibles |
|----------------------|:---:|---|
| `utilisateur`        | non | Accueil, Caisse |
| `super_utilisateur`  | oui | + Catégories, Catalogue, Paiement, Tableau de bord |
| `admin`              | oui | + AdminDB, Maintenance, Droits (AUTH) |

Un visiteur non connecté est automatiquement considéré comme `utilisateur`.
Le bandeau affiche le niveau de droit courant, ainsi que les boutons
**Connexion** / **Déconnexion**. Les menus non accessibles selon le rôle
sont masqués (voir `templates/base.html` et `utils.py`).

## Organisation du projet

```
.
├── app.py                  # Point d'entrée (lance le serveur Flask)
├── utils.py                # Fonctions communes : décorateur role_required, export CSV...
├── requirements.txt
├── APP/                    # Code Python principal
│   ├── __init__.py         # Factory Flask (create_app), enregistrement des blueprints
│   ├── extensions.py       # Instances partagées : db (SQLAlchemy), login_manager
│   └── models.py           # Modèles : User, Category, CatalogueItem, PaymentMethod, Invoice
├── ROUTES/                 # Un fichier de routes par écran (blueprints Flask)
│   ├── accueil.py          # écran ACCUEIL       (utilisateur)
│   ├── caisse.py           # écran CAISSE        (utilisateur)
│   ├── categories.py       # écran CATEGORIES    (super_utilisateur)
│   ├── catalogue.py        # écran CATALOGUE     (super_utilisateur)
│   ├── paiement.py         # écran PAIEMENT      (super_utilisateur)
│   ├── tableau_de_bord.py  # écran TABLEAU DE BORD (super_utilisateur)
│   ├── admindb.py          # écran ADMINDB       (admin)
│   ├── maintenance.py      # écran MAINTENANCE   (admin)
│   └── auth.py             # écran AUTH : login/logout + gestion des droits (admin)
├── templates/              # Un template HTML par écran, même nom que la route
│   ├── base.html           # bandeau, menu conditionnel, login/logout
│   ├── accueil.html / caisse.html / categories.html / catalogue.html
│   ├── paiement.html / tableau_de_bord.html / admindb.html / maintenance.html
│   ├── auth.html           # formulaire login + gestion des comptes
│   └── 403.html            # page d'erreur "accès refusé"
├── static/
│   └── css/style.css
└── instance/
    └── database.db         # généré automatiquement (SQLite)
```

## Gestion de la permanence (écran Accueil)

- Pour ouvrir une permanence : le permanent saisit obligatoirement son **nom** et le
  **fond de caisse de début** (préRempli avec le montant de fin de la permanence
  précédente, mais modifiable).
- Le champ nom est toujours vide à l'affichage (il n'est jamais réutilisé automatiquement) :
  il doit être ressaisi à chaque ouverture et à chaque fermeture.
- Tant qu'une permanence est ouverte, l'écran affiche un bouton **Fermer la permanence** :
  le permanent (ré)indique son nom et confirme/corrige la **somme disponible en caisse**
  (calculée automatiquement = fond de début + total des encaissements « espèces » depuis
  l'ouverture, mais ce champ reste modifiable pour un comptage réel).
- **L'accès à l'écran CAISSE est bloqué** si aucune permanence n'est ouverte
  (redirection automatique vers l'Accueil avec message).
- Le moyen de paiement à comptabiliser comme "espèces" se coche dans l'écran **Paiement**
  (case « Espèces »), ce qui permet au calcul du fond de caisse de rester correct même
  si le libellé exact du moyen de paiement change.

## Écran CAISSE — facturation des adhérents

- **Nouvelle vente** : un clic sur « + Nouvelle vente » crée immédiatement un panier vide
  (statut « brouillon », **sans nom d'adhérent**) et ouvre son détail : on peut tout de
  suite ajouter des prestations, sans étape de saisie de nom au préalable.
- **Tant qu'une vente est en « brouillon »**, elle doit être finalisée avant de pouvoir
  naviguer ailleurs sur le site : le menu, le logo et le bouton Déconnexion sont bloqués
  (message d'alerte), et une confirmation du navigateur est demandée en cas de fermeture
  d'onglet ou d'actualisation. Les actions de la page elle-même (ajouter une prestation,
  modifier une quantité, Encaisser, Enregistrer, Annuler) restent, elles, pleinement actives.
- **Deux façons de finaliser une vente** :
  - *Encaisser immédiatement* : nécessite de choisir un moyen de paiement ; **impossible si
    le panier est vide** (contrôle serveur + bouton désactivé côté écran). **Le nom de
    l'adhérent n'est pas requis.** Génère une facture numérotée (`F-AAAAMMJJ-0001`, etc.),
    liée au panier et à la permanence en cours. Le panier passe en statut « encaissé ».
  - *Enregistrer* pour plus tard : **le nom de l'adhérent est obligatoire** dans ce cas.
    Le panier passe en statut « en attente » et apparaît dans la liste des paniers en
    attente (Caisse et Tableau de bord), modifiable à tout moment.
  - *Annuler* : possible tant que le panier n'est pas encaissé ; passe le panier au statut
    « annulé », non facturé, non modifiable.
- **Ajouter des prestations** : les prestations du catalogue sont affichées sous forme de
  boutons, groupés par catégorie, colorés selon la couleur définie dans l'écran Catégories.
  Un clic ajoute la prestation (ou incrémente sa quantité si déjà présente).
- **La facture reste modifiable après encaissement** : les lignes du panier (ajout,
  quantité, suppression) et le nom de l'adhérent restent modifiables même une fois le
  panier encaissé ; le montant de la facture liée est recalculé automatiquement à chaque
  modification.
- **Écran Accueil** : affiche la liste des paniers encaissés depuis l'ouverture de la
  permanence en cours (ou les 20 derniers si aucune permanence n'est ouverte).

## Écran RETRAIT CAISSE

- Nouvel écran dédié, réservé aux **super-utilisateurs et admins** (menu et tuile
  Accueil visibles uniquement pour ces niveaux).
- Un retrait nécessite le **nom de la personne** qui effectue le retrait (obligatoire),
  un **motif** (obligatoire) et un **montant > 0**. Le compte connecté qui saisit
  l'opération est aussi enregistré en base (non affiché sur l'écran Tableau de bord).
- **Accessible même si aucune permanence n'est ouverte** : si une permanence est
  ouverte, le retrait y est automatiquement rattaché et déduit du fond de caisse
  suggéré en fin de permanence (écran Accueil) ; sinon il est simplement conservé
  à titre d'historique, sans permanence associée.
- L'**historique complet des retraits**, toutes permanences confondues, ainsi que leur
  **modification** et leur **suppression** (correction d'erreur de saisie, accessibles
  aux super-utilisateurs et admins), se trouvent sur l'écran **Tableau de bord**.

## Écran TABLEAU DE BORD

Organisé en 3 blocs, dans cet ordre : **Factures** (avec son sous-tableau
**Répartition par moyen de paiement**), **Paniers non payés**, **Retraits de caisse**.
Chaque tableau a son propre **bouton Exporter CSV**, placé juste au-dessus de la ligne
d'en-têtes de colonnes.

1. **Factures** : colonnes **Permanent** (celui qui a ouvert la permanence pendant laquelle
   la facture a été émise) et **Adhérent** (nom renseigné dans le panier). **Pagination** :
   50 factures par page, navigation Précédent/Suivant, filtres et tri conservés d'une page
   à l'autre. L'export CSV porte sur l'intégralité du résultat filtré (pas seulement la page
   affichée). Un sous-tableau **Répartition des encaissements par moyen de paiement**
   (nombre de factures + montant total par moyen) applique **les mêmes filtres de dates**
   que la liste des factures ci-dessus (mais pas le filtre par moyen de paiement, puisque le
   but est justement de les comparer entre eux) ; il est **exportable en CSV** séparément.
2. **Paniers non payés** : liste des paniers en attente d'encaissement (adhérent, permanent,
   date de création, nombre de lignes, total), avec un lien direct pour rouvrir le panier
   dans l'écran Caisse, et export CSV.
3. **Retraits de caisse** : historique complet des retraits d'espèces (toutes permanences
   confondues), avec **modification** et **suppression** possibles sur chaque ligne
   (correction d'une erreur de saisie), et export CSV.

## Écran CAISSE — comportement permanence fermée

- L'écran Caisse reste **accessible** même si aucune permanence n'est ouverte.
- Le démarrage d'une **nouvelle vente est bloqué** dans ce cas (message explicite + lien
  vers l'Accueil pour ouvrir une permanence).
- La liste des **paniers en attente** reste affichée et modifiable, pour ne pas bloquer
  la finalisation d'un panier déjà commencé pendant que la permanence était encore ouverte.

## Points prévus pour la suite

- **ADMINDB** : intégration effective d'Adminer (URL de service à configurer via
  `app.config["ADMINER_URL"]`).
- **TABLEAU DE BORD** : les filtres/tri/export CSV sont fonctionnels dès maintenant,
  ils s'enrichiront automatiquement avec les factures créées en caisse.
