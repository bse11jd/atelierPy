#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd ~/storage/shared/DOCUMENTS/AtelierPy-main
source ~/venv/bin/activate
waitress-serve --listen=127.0.0.1:5000 app:app
