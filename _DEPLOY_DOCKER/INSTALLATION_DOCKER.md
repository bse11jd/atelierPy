# Installation de Docker — Guide par plateforme

Ce guide couvre l'installation de Docker sur les trois types de machines cibles
pour atelierPy : **Windows**, **Linux (Ubuntu/Lubuntu)** et **Raspberry Pi (DietPi)**.

---

## 1. Windows (PC)

Windows utilise **Docker Desktop**, qui s'appuie sur WSL2.

### 1.1 Prérequis : WSL2

1. Ouvrir PowerShell **en administrateur**
2. Installer WSL2 :
   ```powershell
   wsl --install
   ```
3. Redémarrer la machine si demandé
4. Vérifier la version installée :
   ```powershell
   wsl --status
   ```
   Doit indiquer "Version par défaut : 2"

### 1.2 Vérifier la virtualisation matérielle

1. Ouvrir le **Gestionnaire des tâches** → onglet **Performance** → **CPU**
2. Regarder la ligne **Virtualisation**
   - Si **Activée** → rien à faire, passer à l'étape 1.3
   - Si **Désactivée** → redémarrer, entrer dans le BIOS/UEFI (touche `Suppr`,
     `F2`, `F10` ou `F12` selon la carte mère), activer **Intel VT-x** /
     **AMD-V** (souvent dans l'onglet "Advanced" ou "CPU Configuration"),
     sauvegarder et redémarrer

### 1.3 Installer Docker Desktop

1. Télécharger l'installeur depuis [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Lancer l'installeur, cocher **"Use WSL 2 instead of Hyper-V"** (option par défaut)
3. Redémarrer si demandé
4. Lancer Docker Desktop, patienter le premier démarrage (initialisation du moteur)

### 1.4 Configuration recommandée

- **Settings → General** : cocher "Start Docker Desktop when you log in"
  (pour que le conteneur redémarre automatiquement avec la machine)
- **Settings → Resources** : ajuster la RAM/CPU allouée à WSL2 si la machine
  est limitée en ressources

### 1.5 Vérification

Ouvrir PowerShell (utilisateur normal cette fois) :
```powershell
docker --version
docker compose version
docker run hello-world
```
Si le message de bienvenue Docker s'affiche, l'installation est fonctionnelle.

### 1.6 Pare-feu

Si atelierPy doit être accessible depuis d'autres postes du réseau :
1. **Panneau de configuration → Pare-feu Windows Defender → Paramètres avancés**
2. Nouvelle règle entrante → Port → TCP → port choisi (ex: `8080`) → Autoriser

---

## 2. Linux (Ubuntu / Lubuntu)

Sur PC Linux, on installe **Docker Engine** directement (pas Docker Desktop,
inutile hors environnement de bureau lourd).

### 2.1 Installation via le script officiel (le plus simple)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### 2.2 Installation manuelle via les dépôts APT (alternative recommandée en production)

```bash
# Dépendances
sudo apt update
sudo apt install ca-certificates curl gnupg

# Clé GPG officielle Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Dépôt Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installation
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 2.3 Autoriser l'utilisateur courant à utiliser Docker sans `sudo`

```bash
sudo usermod -aG docker $USER
```
> Nécessite une **déconnexion/reconnexion** (ou `newgrp docker`) pour prendre effet.

### 2.4 Démarrage de Docker

qq commandes :

```bash
sudo systemctl enable docker  --pour faire un Démarrage automatique au boot
sudo systemctl disable docker --pour Désactiver un Démarrage automatique au boot
sudo systemctl start docker   --Démarrage
systemctl status docker --status....
```

### 2.5 Vérification

```bash
docker --version
docker compose version
docker run hello-world
```

### 2.6 Pare-feu (si `ufw` actif, à tester avec sudo ufw status)

```bash
sudo ufw allow 8080/tcp
```

---

## 3. Raspberry Pi (DietPi, ARM)

DietPi étant une distribution allégée basée sur Debian, la méthode la plus
fiable est le script officiel Docker (compatible ARM).

### 3.1 Mise à jour du système

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Installation de Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

> Alternative : DietPi propose aussi Docker directement dans son outil de
> configuration (`dietpi-software` → chercher "Docker"), ce qui peut être
> plus simple si vous préférez rester dans l'écosystème DietPi.

### 3.3 Installer le plugin Compose (si non inclus)

```bash
sudo apt install docker-compose-plugin
```

### 3.4 Autoriser l'utilisateur courant

```bash
sudo usermod -aG docker $USER
```
Déconnexion/reconnexion nécessaire.

### 3.5 Démarrage automatique au boot

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

### 3.6 Vérification

```bash
docker --version
docker compose version
docker run hello-world
```
Qq commandes 

```bash
docker images          # liste les images construites
docker ps -a           # liste les conteneurs (actifs et arrêtés)
docker system df -v              # détail de l'espace utilisé par image/conteneur/volume
docker inspect atelierpy:latest  # métadonnées complètes d'une image précise
```

### 3.7 Point d'attention ressources

Le Raspberry Pi ayant peu de RAM, vérifier la charge après démarrage du
conteneur :
```bash
docker stats
free -h
```
Pour une application légère comme atelierPy (Flask + SQLite), ça devrait
rester largement dans les capacités d'un Pi standard (1 Go+ de RAM).

---

## 4. Récapitulatif des commandes de vérification (toutes plateformes)

| Commande                  | Vérifie                                      |
|----------------------------|-----------------------------------------------|
| `docker --version`         | Docker Engine installé                        |
| `docker compose version`   | Plugin Compose disponible                     |
| `docker run hello-world`    | Le moteur fonctionne de bout en bout          |
| `docker info`              | Détails complets (architecture, stockage...)  |

---

## 5. Étape suivante

Une fois Docker installé et vérifié sur la machine cible, reprendre la
procédure de dockerisation d'atelierPy (build de l'image, lancement via
`docker compose up -d`) décrite dans le README principal du projet.
