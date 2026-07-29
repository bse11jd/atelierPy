# Dockerisation d'atelierPy — Procédure

Ce document décrit comment containeriser l'application **atelierPy** (Flask/SQLite)
et la builder pour un déploiement sur **Windows**, **Linux (Ubuntu/Lubuntu)** et
**Raspberry Pi (DietPi, ARM)**.

> ⚠️ Ce document ne couvre **pas** la configuration des machines cibles
> (Docker Desktop, Docker Engine, virtualisation BIOS, etc.) — uniquement la
> partie "construire et faire tourner le conteneur".

---

## 1. Fichiers fournis

| Fichier              | Rôle                                                            |
|-----------------------|------------------------------------------------------------------|
| `Dockerfile`          | Construit l'image Python + dépendances + code de l'app          |
| `docker-compose.yml`  | Lance le conteneur avec le bon port, volume et fichier `.env`    |
| `.dockerignore`       | Exclut les fichiers inutiles/sensibles du build (venv, .git, db) |
| `.env.example`        | Modèle de variables d'environnement (à copier en `.env`)         |

Ces fichiers sont à placer **à la racine du projet atelierPy** (au même niveau
que `requirements.txt`).

---

## 2. Points à adapter avant le premier build

1. **Point d'entrée de l'application** (`CMD` dans le `Dockerfile`)
   Actuellement placeholder : `python app.py`.
   À remplacer par la commande réelle qui lance `create_app()` + waitress
   (ex: `waitress-serve --host=0.0.0.0 --port=8080 --call APP:create_app`).

2. **Chemin de la base SQLite / dossier `instance/`**
   Le volume `./data/instance:/app/instance` suppose que Flask écrit la base
   dans `instance/` relatif à la racine de l'app. À ajuster si le chemin réel
   diffère (`SQLALCHEMY_DATABASE_URI` dans la config).

3. **`requirements.txt`**
   Doit être à jour et inclure `waitress` (déjà fait d'après votre projet).

4. **`SECRET_KEY`**
   À définir dans `.env` (jamais en dur dans le code ni committé).

---

## 3. Build de l'image

### 3.1 Build simple (architecture locale uniquement, necessite docker)

```bash
docker compose build
```

Utile pour tester rapidement sur la machine où vous développez.

### 3.2 Build multi-architecture (Windows/Linux PC **et** Raspberry Pi)

Le Raspberry Pi tourne en `arm64`, les PC en `amd64`. Pour produire une seule
image compatible avec les deux, utiliser `buildx` :

```bash
# Une seule fois : créer un builder multi-arch
docker buildx create --use --name atelierpy-builder

# Build + push vers un registre (Docker Hub, ou registre privé)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t <votre-registre>/atelierpy:latest \
  --push .
```

> `buildx` a besoin de pousser vers un registre pour produire une image
> multi-arch exploitable (impossible de charger deux architectures en local
> avec `--load`). Si vous ne voulez pas de registre public, un registre privé
> local (ex: `registry:2` en conteneur) fait l'affaire.

Sur chaque machine cible, `docker compose pull` puis `docker compose up -d`
récupérera automatiquement la bonne architecture.

---

## 4. Lancement du conteneur

```bash
# Copier le modèle d'environnement et l'adapter
cp .env.example .env

# Démarrer
docker compose up -d

# Vérifier les logs
docker compose logs -f atelierpy
```

L'application sera accessible sur `http://<ip-machine>:8080`.

---

## 5. Mise à jour du code

À chaque nouvelle version du code :

```bash
git pull                     # récupérer le code à jour
docker compose build         # reconstruire l'image
docker compose up -d         # relancer avec la nouvelle image
docker compose ps            # verif 
```

La base SQLite dans `./data/instance` n'est **pas** affectée par ces
commandes puisqu'elle vit dans un volume externe à l'image.

---

## 6. Différences avec le déploiement actuel (Pi via Git bare repo)

| Aspect                  | Déploiement actuel (Pi)                     | Déploiement Docker                          |
|--------------------------|----------------------------------------------|----------------------------------------------|
| Récupération du code    | `git push` → hook `post-receive`             | `git pull` manuel ou via image poussée sur registre |
| Lancement de l'app      | `systemd` → `waitress` directement           | `systemd`/Docker → conteneur → `waitress`    |
| Dépendances             | venv Python installé sur la machine          | Installées dans l'image, isolées de l'hôte   |
| Redémarrage auto        | Géré par `systemd`                           | Géré par `restart: always` (+ Docker au boot) |

Le hook `post-receive` existant peut être conservé pour récupérer le code, et
étendu pour déclencher `docker compose up -d --build` à la fin — ce point sera
à détailler dans une prochaine étape si vous le souhaitez.

---

## 7. Prochaines étapes possibles

- Configuration des machines cibles (Docker Desktop/Engine, démarrage auto)
- Adaptation du hook `post-receive` du Pi pour déclencher un rebuild Docker
- Mise en place d'un registre privé pour la distribution multi-arch
- Ajout d'un reverse proxy (nginx) si accès HTTPS ou plusieurs services
