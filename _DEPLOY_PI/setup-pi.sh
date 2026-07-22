#!/bin/bash
set -e

# ============================================================
#  CONFIGURATION — à adapter avant de lancer le script
# ============================================================
APP_NAME="atelierPy"                          # nom de l'app / du service
APP_USER="$(whoami)"                       # utilisateur qui fera tourner l'app (souvent "pi" ou "dietpi")
REPO_DIR="/home/${APP_USER}/repos/${APP_NAME}.git"    # dépôt bare (reçoit les push)
WORK_DIR="/home/${APP_USER}/apps/${APP_NAME}"         # dossier de travail (code déployé)
BRANCH="main"                               # branche à déployer
PORT="49080"                                 # port d'écoute de l'app
FLASK_ENTRYPOINT="app:app"                  # module:variable Flask (adapter si besoin)
# ============================================================

echo "==> Création du dépôt bare : ${REPO_DIR}"
mkdir -p "${REPO_DIR}"
git init --bare "${REPO_DIR}"

echo "==> Création du dossier de travail : ${WORK_DIR}"
mkdir -p "${WORK_DIR}"

echo "==> Installation du hook post-receive"
cp "$(dirname "$0")/post-receive" "${REPO_DIR}/hooks/post-receive"
sed -i "s|__WORK_DIR__|${WORK_DIR}|g; s|__REPO_DIR__|${REPO_DIR}|g; s|__BRANCH__|${BRANCH}|g; s|__APP_NAME__|${APP_NAME}|g" "${REPO_DIR}/hooks/post-receive"
chmod +x "${REPO_DIR}/hooks/post-receive"

echo "==> Premier checkout (dépôt vide pour l'instant, sera rempli au premier push)"

echo "==> Création du venv dans ${WORK_DIR}"
python3 -m venv "${WORK_DIR}/venv"

echo "==> Installation du service systemd"
cp "$(dirname "$0")/monapp.service" "/tmp/${APP_NAME}.service"
sed -i "s|__WORK_DIR__|${WORK_DIR}|g; s|__APP_USER__|${APP_USER}|g; s|__PORT__|${PORT}|g; s|__FLASK_ENTRYPOINT__|${FLASK_ENTRYPOINT}|g; s|__APP_NAME__|${APP_NAME}|g" "/tmp/${APP_NAME}.service"
sudo mv "/tmp/${APP_NAME}.service" "/etc/systemd/system/${APP_NAME}.service"
sudo systemctl daemon-reload
sudo systemctl enable "${APP_NAME}.service"

echo "==> Autorisation de redémarrage du service sans mot de passe (utilisé par le hook)"
echo "${APP_USER} ALL=(ALL) NOPASSWD: /bin/systemctl restart ${APP_NAME}.service" | sudo tee "/etc/sudoers.d/${APP_NAME}-deploy" > /dev/null
sudo chmod 440 "/etc/sudoers.d/${APP_NAME}-deploy"

echo ""
echo "============================================================"
echo " Configuration terminée !"
echo ""
echo " Sur ta machine de dev, ajoute le remote Git :"
echo ""
echo "   git remote add pi ssh://${APP_USER}@<IP_DU_PI>${REPO_DIR}"
echo ""
echo " Puis pour déployer :"
echo ""
echo "   git push pi ${BRANCH}"
echo ""
echo " L'app sera automatiquement installée/mise à jour et redémarrée."
echo " Elle écoutera sur : http://<IP_DU_PI>:${PORT}"
echo "============================================================"
