# Guide de Déploiement en Production - Inventaire CCNM

Ce guide décrit les étapes pour déployer l'application d'inventaire CCNM sur un serveur Linux (Ubuntu 22.04/24.04 recommandé).

## Références

- [https://flask-fr.readthedocs.io/tutorial/deploy/] (https://flask-fr.readthedocs.io/tutorial/deploy/)
- [https://sysadmin.cyklodev.com/deployer-une-application-flask/](https://sysadmin.cyklodev.com/deployer-une-application-flask/)

## 1. Prérequis

*   Un serveur VPS ou dédié sous Ubuntu/Debian.
*   Accès root ou sudo.
*   Un nom de domaine pointant vers l'adresse IP du serveur (ex: `inventaire.ccnm.fr`).

## 2. Préparation du système

Mettez à jour le système et installez les paquets nécessaires (Python, pip, venv, Nginx, git) :

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv python3-dev build-essential libssl-dev libffi-dev nginx git -y
```

## 3. Installation de l'application

Nous allons installer l'application dans `/var/www/inventaire_ccnm`.

### 3.1 Cloner le dépôt

```bash
cd /var/www
sudo git clone https://github.com/jlehuen/inventory_DB inventaire_ccnm
cd inventaire_ccnm
```
*Note : Si vous n'utilisez pas Git sur le serveur, vous pouvez transférer les fichiers via SCP ou SFTP.*

### 3.2 Créer l'environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn  # Serveur d'application pour la production
```

### 3.3 Configuration des variables d'environnement

Créez un fichier `.env` de production :

```bash
cp .env .env.production
nano .env
```

Modifiez les valeurs suivantes :
*   `SECRET_KEY` : Générez une chaîne aléatoire longue et complexe.
*   `FLASK_ENV` : Mettez `production`.
*   `ADMIN_PASSWORD` : Définissez un mot de passe fort pour le compte admin par défaut.

## 4. Permissions et Dossiers

C'est une étape **critique**. L'application utilise SQLite (fichier `.db`) et permet l'upload d'images. L'utilisateur web (`www-data`) doit avoir les droits d'écriture.

```bash
# Créer les dossiers nécessaires s'ils n'existent pas
mkdir -p database/uploads
mkdir -p logs

# Donner la propriété à www-data
sudo chown -R www-data:www-data /var/www/inventaire_ccnm
sudo chmod -R 775 /var/www/inventaire_ccnm/database
sudo chmod -R 775 /var/www/inventaire_ccnm/logs
```

## 5. Configuration de Gunicorn (Service Systemd)

Nous allons créer un service pour que l'application démarre automatiquement et redémarre en cas de crash.

Créez le fichier `/etc/systemd/system/inventaire.service` :

```bash
sudo nano /etc/systemd/system/inventaire.service
```

Collez le contenu suivant :

```ini
[Unit]
Description=Gunicorn instance to serve Inventaire CCNM
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/inventaire_ccnm
Environment="PATH=/var/www/inventaire_ccnm/venv/bin"
# Workers = (2 * CPU) + 1. Pour un petit serveur, 3 est généralement bon.
ExecStart=/var/www/inventaire_ccnm/venv/bin/gunicorn --workers 3 --bind unix:inventaire.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
```

Démarrez et activez le service :

```bash
sudo systemctl start inventaire
sudo systemctl enable inventaire
sudo systemctl status inventaire
```
*(Vérifiez que le statut est "active (running)")*

## 6. Configuration de Nginx

Nginx va servir de proxy inverse (pour rediriger le trafic web vers Gunicorn) et gérer les fichiers statiques ainsi que la limite de taille d'upload.

Créez le fichier de configuration :

```bash
sudo nano /etc/nginx/sites-available/inventaire
```

Collez le contenu suivant (remplacez `votre_domaine.com` par le vrai domaine) :

```nginx
server {
    listen 80;
    server_name votre_domaine.com www.votre_domaine.com;

    # Augmenter la taille maximale d'upload (ici 16Mo pour correspondre à Flask)
    client_max_body_size 16M;

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/inventaire_ccnm/inventaire.sock;
    }

    location /static {
        alias /var/www/inventaire_ccnm/static;
        expires 30d;
    }

    # Sécurisation des uploads (empêcher l'exécution de scripts)
    location /static/database/uploads {
        alias /var/www/inventaire_ccnm/database/uploads;
        expires 30d;
        add_header Content-Disposition "attachment";
    }
}
```

Activez le site et testez la configuration :

```bash
sudo ln -s /etc/nginx/sites-available/inventaire /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 7. Sécurisation (HTTPS)

Il est fortement recommandé d'activer HTTPS avec Certbot (Let's Encrypt).

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d votre_domaine.com
```

Suivez les instructions à l'écran. Certbot modifiera automatiquement la configuration Nginx pour rediriger le trafic HTTP vers HTTPS.

## 8. Maintenance et Mises à jour

### Mettre à jour l'application
Pour mettre à jour le code :

```bash
cd /var/www/inventaire_ccnm
sudo git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart inventaire
```

### Sauvegardes
Les données importantes sont :
1.  Le fichier de base de données : `database/database.db`
2.  Les images uploadées : `database/uploads/`

Pensez à mettre en place une tâche cron pour sauvegarder ces éléments régulièrement vers un emplacement externe.

Exemple de script de backup simple :

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
tar -czf /backups/inventaire_backup_$DATE.tar.gz /var/www/inventaire_ccnm/database
```
