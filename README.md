# VMware Assessment Visualizer — macOS

Cette application affiche localement les données collectées par le VMware Assessment Collector.

## Prérequis
- macOS Tahoe
- Python 3.10 ou plus récent
- Environ 300 Mo d'espace libre pour l'environnement Python

## Méthode rapide

1. Décompressez `VMware_Assessment_Visualizer_Mac.zip`.
2. Ouvrez le dossier.
3. Double-cliquez sur `START.command`.
4. macOS peut demander une autorisation la première fois. Si le fichier est bloqué :
   - clic droit > Ouvrir, ou
   - Terminal : `chmod +x START.command && ./START.command`
5. Le navigateur s'ouvre normalement sur :
   `http://localhost:8501`

Le premier lancement crée automatiquement un environnement Python `.venv` et installe les dépendances.

## Méthode Terminal

```bash
cd /chemin/vers/VMware_Assessment_Visualizer_Mac
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Données
Le ZIP de l'assessment est déjà inclus et extrait sous `assessment_data/`.
L'application fonctionne entièrement en local pour l'analyse des CSV.

## Arrêt
Dans la fenêtre Terminal qui exécute Streamlit : `Ctrl+C`.

## Mise à jour avec un futur assessment
Remplacez le contenu de `assessment_data/` par un nouveau dossier généré par le collector, en conservant les dossiers par vCenter et les CSV standards (`03-ESXi-Hosts.csv`, `04-VMs.csv`, etc.).
