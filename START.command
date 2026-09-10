#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "============================================"
echo " VMware Assessment Visualizer"
echo "============================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo ""
  echo "Python 3 n'est pas installé."
  echo "Installez Python depuis https://www.python.org/downloads/macos/"
  echo "puis relancez ce fichier."
  read -n 1 -s -r -p "Appuyez sur une touche pour fermer..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "[1/3] Création de l'environnement Python..."
  python3 -m venv .venv
fi

source .venv/bin/activate

if [ ! -f ".venv/.deps_installed" ]; then
  echo "[2/3] Installation des dépendances (premier lancement uniquement)..."
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  touch .venv/.deps_installed
else
  echo "[2/3] Dépendances déjà installées."
fi

echo "[3/3] Démarrage du dashboard..."
echo "URL locale : http://localhost:8501"
echo "Pour arrêter : Ctrl+C"
echo ""

streamlit run app.py --server.address=localhost --server.port=8501 --browser.gatherUsageStats=false
