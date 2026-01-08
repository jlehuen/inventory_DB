# Guide de déploiement sécurisé pour l'application Catalogue CCNM

Ce guide vous explique comment déployer l'application de manière sécurisée avec les fonctionnalités d'authentification.

## 1. Configuration initiale

### Prérequis
- Python 3.7 ou supérieur
- pip (gestionnaire de paquets Python)
- Un serveur web (recommandé: Nginx)

### Installation des dépendances

```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Sur Windows:
venv\Scripts\activate
# Sur macOS/Linux:
source venv/bin/activate

# Installer les dépendances
pip install flask flask-login flask-wtf werkzeug python-dotenv reportlab
```

### Configuration des variables d'environnement

1. Créez un fichier `.env` à la racine du projet en vous basant sur l'exemple fourni
2. Modifiez les valeurs selon votre environnement:

```
# .env
SECRET_KEY=votre_clef_secrete_complexe_et_unique
FLASK_ENV=production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=mot_de_passe_fort_et_unique
```

> **IMPORTANT**: Utilisez des mots de passe forts pour votre compte administrateur!

## 2. Initialisation de la base de données

La base de données sera automatiquement créée au premier démarrage de l'application. Vous pouvez exécuter le script d'initialisation manuellement si nécessaire:

```bash
python -c "from app import init_db, init_auth_db, create_admin_user, get_db_connection; init_db(); init_auth_db(); create_admin_user()"
```

## 3. Structure des dossiers

Assurez-vous que ces répertoires existent et ont les permissions appropriées:

```bash
mkdir -p database/uploads logs
chmod 750 database database/uploads logs
```

## 4. Exécution en développement

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Définir l'environnement
export FLASK_ENV=development

# Lancer l'application
python app.py
```

## 5. Déploiement en production

### Option 1: Utiliser Gunicorn (recommandé)

```bash
# Installer Gunicorn
pip install gunicorn

# Lancer l'application avec Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option 2: Utiliser uWSGI

```bash
# Installer uWSGI
pip install uwsgi

# Créer un fichier de configuration uwsgi.ini:
[uwsgi]
module = app:app
master = true
processes = 4
socket = 0.0.0.0:5000
chmod-socket = 660
vacuum = true
die-on-term = true

# Lancer l'application avec uWSGI
uwsgi --ini uwsgi.ini
```

### Configuration de Nginx en tant que proxy inverse

```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /chemin/vers/votre/app/static;
        expires 30d;
    }
}
```

## 6. Sécurité supplémentaire

### Activer HTTPS

Utilisez [Certbot](https://certbot.eff.org/) pour obtenir un certificat SSL gratuit:

```bash
# Installer Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtenir un certificat et configurer Nginx
sudo certbot --nginx -d votre-domaine.com
```

### Sauvegardes régulières

Configurez des sauvegardes régulières de la base de données:

```bash
# Script de sauvegarde
#!/bin/bash
BACKUP_DIR="/chemin/vers/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
cp /chemin/vers/votre/app/database/database.db "$BACKUP_DIR/database_$DATE.db"
```

Ajoutez ce script à votre crontab pour des sauvegardes automatiques.

### Mises à jour de sécurité

Vérifiez régulièrement les mises à jour des dépendances:

```bash
pip list --outdated
pip install --upgrade flask flask-login werkzeug
```

## 7. Conseils de sécurité supplémentaires

1. **Mots de passe**: Utilisez un gestionnaire de mots de passe pour générer et stocker des mots de passe forts
2. **Pare-feu**: Configurez un pare-feu pour limiter l'accès aux ports non nécessaires
3. **Mises à jour du système**: Gardez votre système d'exploitation et tous les logiciels à jour
4. **Surveillance**: Mettez en place un système de surveillance pour détecter les activités suspectes
5. **Moins de privilèges**: Exécutez l'application avec un utilisateur disposant du minimum de privilèges nécessaires

## Connexion à l'application

Une fois l'application déployée, vous pouvez vous connecter à l'interface d'administration:

1. Accédez à `http://votre-domaine.com/login`
2. Utilisez les identifiants définis dans votre fichier `.env`
3. Vous serez redirigé vers le panneau d'administration
