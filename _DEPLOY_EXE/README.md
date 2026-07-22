# Flask Desktop App (Flask + SQLAlchemy + pywebview)

Transformer un projet Flask/SQLite/SQLAlchemy en application de bureau (Linux et Windows).

## Structure

```

La base SQLite reste stockée sous instance/dtabase.db



Installer : pywebview et pyinstaller (Verifier requirement.txt / pip install -r requirements.txt)

## 

## 1\. Tester en mode web classique

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

→ http://127.0.0.1:5000

## 2\. Tester en mode "fenêtre native" (sans packaging)

```bash
python desktop.py
```

Une fenêtre s'ouvre directement (pas de navigateur), le serveur Flask tourne
en arrière-plan dans un thread.

* **Linux** : pywebview utilise WebKitGTK. Si besoin :

```bash
  sudo apt install python3-gi gir1.2-webkit2-4.0 libgtk-3-dev
  ```

* **Windows** : pywebview utilise Edge WebView2 (déjà présent sur Windows 10/11
à jour). Sinon, installer le runtime WebView2 (gratuit, chez Microsoft).

## 3\. Packager en exécutable (PyInstaller)

**Sur Linux** (génère un binaire Linux) :

```bash
pyinstaller --onefile --windowed --add-data "templates:templates" --add-data "static:static" --name "Atelier Cafe Racer" desktop.py
```

**Sur Windows** (génère un .exe Windows — doit être lancé DEPUIS Windows,
PyInstaller ne fait pas de cross-compilation) :

```powershell
pyinstaller --onefile --windowed --add-data "templates;templates" --add-data "static;static" --name "Atelier Cafe Racer" desktop.py
```

⚠️ Sur Windows le séparateur `--add-data` est `;` et pas `:` comme sur Linux.

Le résultat se trouve dans `dist/` :

* Linux : `dist/MesTaches`
* Windows : `dist/MesTaches.exe`

### Remarques importantes

* **Un exécutable par OS** : il faut lancer PyInstaller séparément sur une
machine Linux pour le binaire Linux, et sur une machine Windows pour le
`.exe`. Pas de cross-compilation fiable.
* `--windowed` : évite qu'une console noire s'ouvre derrière la fenêtre.
* `--onefile` : un seul exécutable autonome (plus lent à démarrer, mais plus
simple à distribuer). Alternative : `--onedir` (démarrage plus rapide, mais
dossier avec plusieurs fichiers).
* Si tu ajoutes une icône : `--icon=mon\_icone.ico` (Windows) ou
`--icon=mon\_icone.png` (Linux, support variable selon l'environnement de bureau).

## 4\. Aller plus loin

* Ajouter une icône dans la barre des tâches / le dock.
* Créer un raccourci `.desktop` (Linux) ou un raccourci `.lnk` (Windows) qui
pointe vers l'exécutable généré.
* Si le projet grossit, envisager `PyOxidizer` ou `briefcase` comme
alternatives à PyInstaller.

