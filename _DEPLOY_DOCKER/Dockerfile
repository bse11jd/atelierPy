# === Dockerfile atelierPy ===
# Image de base légère, compatible amd64 et arm64 (Pi) via buildx
FROM python:3.12-slim

# Pas de fichiers .pyc, logs non bufferisés (utile pour voir les logs docker en direct)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /app

# Installation des dépendances d'abord (profite du cache Docker si le code change
# mais pas requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source de l'application
COPY . .

# Dossier où vivra la base SQLite (sera monté en volume, voir docker-compose.yml)
RUN mkdir -p /app/instance

# Port d'écoute de waitress à l'intérieur du conteneur
EXPOSE 8080

# --- À ADAPTER ---
# Remplacer par le vrai point d'entrée de l'application (celui qui appelle
# create_app() et lance waitress.serve(...)).
# Exemple si vous avez un fichier run.py avec :
#   from APP import create_app
#   from waitress import serve
#   serve(create_app(), host="0.0.0.0", port=8080)
CMD ["python", "app.py"]
