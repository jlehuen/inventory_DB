#!/bin/bash

# ==============================================================================
# Script de préparation et déploiement de mise-à-jour (rsync)
# Projet : Inventaire CCNM
# ==============================================================================

# Configuration
REMOTE_USER="root"
REMOTE_HOST="musee-ic2-demo"
REMOTE_DIR="/www/inventaire_ccnm"

# Couleurs pour la sortie
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Vérifier qu'on est au bon endroit
if [ ! -f "app.py" ]; then
    echo -e "\033[0;31m❌ Erreur : Lancez ce script depuis la racine du projet (là où se trouve app.py)\033[0m"
    exit 1
fi

echo -e "${BLUE}--- 1. Nettoyage des caches Python ---${NC}"
find . -type d \( -name "__pycache__" -o -name ".pytest_cache" \) -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
echo -e "${GREEN}Caches nettoyés.${NC}"

echo -e "\n${BLUE}--- 2. Synchronisation vers ${REMOTE_USER}@${REMOTE_HOST} ---${NC}"

# Note : l'option -i permet de voir exactement ce qui est modifié
# >f+++++++ : nouveau fichier
# .f....... : fichier inchangé
# >f.st.... : fichier mis à jour (taille/temps)

rsync -avzi --delete \
    --exclude='venv/' \
    --exclude='.git/' \
    --exclude='.env' \
    --exclude='.pytest_cache/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='tests/' \
    --exclude='backups/' \
    --exclude='database/*.db' \
    --exclude='database/uploads/*' \
    --exclude='logs/*.log' \
    --exclude='*.command' \
    --exclude='*.webloc' \
    --exclude='pytest.ini' \
    --exclude='gemini.sh' \
    ./ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Mise à jour synchronisée avec succès !${NC}"
    echo -e "\n${BLUE}Vérification du dossier scripts sur le serveur :${NC}"
    ssh ${REMOTE_USER}@${REMOTE_HOST} "ls -la ${REMOTE_DIR}/scripts"
    
    echo -e "\n${BLUE}Prochaines étapes recommandées (nécessite sudo) :${NC}"
    echo "Redémarrer le service : ssh -t ${REMOTE_USER}@${REMOTE_HOST} 'sudo systemctl restart inventaire'"
else
    echo -e "\n\033[0;31m❌ Erreur lors de la synchronisation rsync.${NC}"
    exit 1
fi
