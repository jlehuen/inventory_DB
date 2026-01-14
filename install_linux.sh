#!/bin/bash

# Script d'installation automatique pour Inventaire CCNM sur une distribution Linux (Ubuntu)

# Configuration
APP_DIR="/var/www/inventaire_ccnm"
REPO_URL="https://github.com/jlehuen/inventory_DB"
DOMAIN_NAME="localhost" # Valeur par défaut
USER_WWW="www-data"

# Couleurs pour les logs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO] $1${NC}"; }
log_warn() { echo -e "${YELLOW}[WARN] $1${NC}"; }
log_error() { echo -e "${RED}[ERROR] $1${NC}"; }

# Vérification des droits root
if [ "$EUID" -ne 0 ]; then
  log_error "Ce script doit être lancé avec les privilèges root (sudo)."
  exit 1
fi

# 1. Collecte d'informations
echo "=================================================="
echo "   Installation Inventaire CCNM - Linux (Ubuntu)"
echo "=================================================="
read -p "Entrez votre nom de domaine (ex: inventaire.ccnm.fr) [localhost]: " input_domain
if [ ! -z "$input_domain" ]; then
    DOMAIN_NAME="$input_domain"
fi

# 2. Préparation du système
log_info "Mise à jour du système et installation des dépendances..."
apt update && apt upgrade -y
apt install python3-pip python3-venv python3-dev build-essential libssl-dev libffi-dev nginx git -y

# 3. Installation de l'application
log_info "Installation de l'application dans $APP_DIR..."

if [ -d "$APP_DIR" ]; then
    log_warn "Le dossier $APP_DIR existe déjà."
    read -p "Voulez-vous supprimer le dossier existant et réinstaller ? (o/N) " confirm
    if [[ "$confirm" =~ ^[oO]$ ]]; then
        rm -rf "$APP_DIR"
        git clone "$REPO_URL" "$APP_DIR"
    else
        log_info "Mise à jour du dépôt existant..."
        cd "$APP_DIR"
        git pull origin main
    fi
else
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

# 4. Environnement virtuel
log_info "Configuration de l'environnement virtuel Python..."
# On s'assure d'avoir les droits pour écrire
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 5. Configuration .env
log_info "Configuration des variables d'environnement..."
if [ ! -f ".env" ]; then
    log_info "Génération d'un nouveau fichier .env..."
    SECRET_KEY=$(python3 -c 'import os; print(os.urandom(24).hex())')
    
    echo -n "Définissez un mot de passe pour l'administrateur par défaut : "
    read -s ADMIN_PWD
    echo ""
    
    cat <<EOF > .env
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$ADMIN_PWD
EOF
    log_info "Fichier .env créé avec succès."
else
    log_info "Fichier .env existant détecté et conservé."
fi

# 6. Permissions
log_info "Application des permissions critiques..."
mkdir -p database/uploads
mkdir -p logs

# Changement de propriétaire vers www-data
chown -R $USER_WWW:$USER_WWW "$APP_DIR"
# Permissions d'écriture spécifiques
chmod -R 775 "$APP_DIR/database"
chmod -R 775 "$APP_DIR/logs"

# 7. Service Systemd (Gunicorn)
log_info "Configuration du service Systemd (Gunicorn)..."
SERVICE_FILE="/etc/systemd/system/inventaire.service"
cat <<EOF > $SERVICE_FILE
[Unit]
Description=Gunicorn instance to serve Inventaire CCNM
After=network.target

[Service]
User=$USER_WWW
Group=$USER_WWW
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind unix:inventaire.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start inventaire
systemctl enable inventaire
systemctl status inventaire --no-pager | head -n 5

# 8. Configuration Nginx
log_info "Configuration de Nginx..."
NGINX_CONF="/etc/nginx/sites-available/inventaire"
cat <<EOF > $NGINX_CONF
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;

    # Augmenter la taille maximale d'upload
    client_max_body_size 16M;

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/inventaire.sock;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }

    # Sécurisation des uploads
    location /static/database/uploads {
        alias $APP_DIR/database/uploads;
        expires 30d;
    }
}
EOF

# Activation du site
ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
# Suppression du site par défaut si présent pour éviter les conflits
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    rm /etc/nginx/sites-enabled/default
fi

# Test et redémarrage
nginx -t
if [ $? -eq 0 ]; then
    systemctl restart nginx
    log_info "Nginx redémarré avec succès."
else
    log_error "Erreur dans la configuration Nginx. Vérifiez $NGINX_CONF"
fi

# 9. Firewall
if command -v ufw >/dev/null; then
    log_info "Configuration du pare-feu UFW..."
    ufw allow 'Nginx Full'
fi

echo "=================================================="
log_info "Installation terminée !"
echo -e "L'application est accessible sur : ${GREEN}http://$DOMAIN_NAME${NC}"
echo ""
echo "Pour activer HTTPS (recommandé), lancez :"
echo "sudo apt install certbot python3-certbot-nginx"
echo "sudo certbot --nginx -d $DOMAIN_NAME"
echo "=================================================="
