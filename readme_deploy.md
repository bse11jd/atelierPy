# Déploiement automatique Flask → Raspberry Pi via Git push
Ce package met en place un workflow simple : tu fais `git push pi main` sur ta
machine Windows, et l'app se met à jour et redémarre automatiquement sur le
Raspberry Pi.
## Principe
1. Un **dépôt Git "bare"** (sans dossier de travail) est créé sur le Pi.
2. Un **hook `post-receive`** se déclenche à chaque push reçu : il récupère
   le code, installe les dépendances Python, et redémarre le service.
3. L'app tourne en **service systemd** (via `waitress`), donc elle démarre
   aussi automatiquement au boot du Pi — bonus gratuit.
## Prérequis sur le Pi
- Python 3 + `python3-venv` installés (`sudo apt install python3-venv`)
- Accès SSH depuis ta machine Windows vers le Pi
- Un utilisateur avec droits `sudo` (souvent `pi` ou `dietpi`)
## Installation (une seule fois, sur le Pi)
1. Copie ces 3 fichiers sur le Pi (par SCP, clé USB, etc.) :
   - `setup-pi.sh`
   - `post-receive`
   - `monapp.service`
2. Ouvre `setup-pi.sh` et adapte les variables en haut du fichier :
   - `APP_NAME` : nom de ton app (ex: `mestaches`)
   - `PORT` : port d'écoute (ex: `8000`)
   - `FLASK_ENTRYPOINT` : le point d'entrée Flask, format `module:variable`.
     Si ton fichier principal est `app.py` avec `app = Flask(__name__)`,
     laisse `app:app`. Si ton objet Flask s'appelle autrement, adapte.
3. Lance le script :
   ```bash
   chmod +x setup-pi.sh
   ./setup-pi.sh
   ```
Le script va créer le dépôt bare, le venv, le service systemd, et configurer
les permissions nécessaires. Il affiche à la fin la commande exacte à utiliser
pour ajouter le remote Git.
## Configuration côté Windows (ta machine de dev)
Dans ton projet Flask (celui qui a `app.py`, `requirements.txt`, etc.) :
```bash
# Ajoute .gitignore (voir exemple-gitignore.txt fourni)
git init                     # si ce n'est pas déjà un dépôt git
git add .
git commit -m "Version initiale"
# Ajoute le Pi comme remote (adapte IP et chemin selon la sortie de setup-pi.sh)
# git remote remove pi 
git remote add pi ssh://root@192.168.1.194/home/root/repos/atelierPy.git
# Déploie !
git push pi main
```
À partir de là, **chaque `git push pi main`** :
- met à jour le code sur le Pi,
- réinstalle les dépendances si `requirements.txt` a changé,
- redémarre le service automatiquement.
## Vérifier que tout fonctionne
Sur le Pi :
```bash
sudo systemctl status atelierPy.service      # état du service
sudo journalctl -u atelierPy.service -f      # logs en direct
```
L'app est accessible sur `http://<IP_DU_PI>:8000` (ou le port choisi).
## Important : requirements.txt
Assure-toi que `waitress` est bien dans ton `requirements.txt` :
```
Flask
Flask-SQLAlchemy
waitress
```
## Points d'attention
- **Base de données** : le `.gitignore` fourni exclut `instance/` et les
  fichiers `.db`/`.sqlite3` pour que le déploiement ne les écrase jamais.
  Stocke ta base dans `instance/` (comportement par défaut de Flask) ou
  adapte le `.gitignore` à l'emplacement réel de ta DB.
- **Changements de schéma SQLAlchemy** : ce workflow ne gère pas les
  migrations automatiques. Si tu changes tes modèles, prévois une étape
  manuelle (ou ajoute Flask-Migrate/Alembic si le projet grossit).
- **Première fois** : le premier push peut prendre un peu de temps (création
  du venv déjà faite par le script, mais installation des paquets pip au
  premier déploiement).
- **Architecture ARM** : comme le venv est créé *directement sur le Pi*, pas
  de souci de compatibilité x86/ARM — chaque paquet est installé pour la
  bonne architecture.
