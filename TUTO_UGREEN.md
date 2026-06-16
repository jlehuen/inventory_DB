# Tutoriel : Déployer l'application Inventaire sur un NAS UGREEN avec Docker

Ce guide vous explique comment empaqueter votre application web Python/Flask dans une image Docker et la déployer sur un NAS UGREEN (ou tout autre système supportant Docker).

Nous utiliserons **Docker Compose**, qui simplifie grandement la gestion des conteneurs.

## Prérequis

*   Un NAS UGREEN avec l'application Docker installée.
*   Un accès SSH à votre NAS (recommandé) ou un accès à l'interface graphique de Docker sur le NAS.
*   Les fichiers de votre projet transférés sur votre NAS.

---

## Étape 1 : Préparer l'application pour la production

Le serveur web fourni avec Flask (`flask run`) est conçu pour le développement et n'est pas assez robuste pour la production. Nous allons utiliser **Gunicorn**, un serveur WSGI (Web Server Gateway Interface) standard pour les applications Python.

### 1.1. Ajouter Gunicorn aux dépendances

Modifiez votre fichier `requirements.txt` pour y inclure `gunicorn`.

**Fichier : `requirements.txt`**

```
blinker==1.9.0
charset-normalizer==3.4.4
click==8.3.1
Flask==3.1.2
Flask-Login==0.6.3
Flask-WTF==1.2.2
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
pillow==12.1.0
python-dotenv==1.2.1
reportlab==4.4.7
Werkzeug==3.1.4
WTForms==3.2.1
pytest
pytest-flask
qrcode
requests
gunicorn
```

---

## Étape 2 : Créer le `Dockerfile`

Le `Dockerfile` est une "recette" qui indique à Docker comment construire l'image de votre application. Créez un nouveau fichier nommé `Dockerfile` (sans extension) à la racine de votre projet.

**Fichier : `Dockerfile`**

```dockerfile
# Étape 1: Choisir l'image de base
# On part d'une image Python 3.9 légère et optimisée.
FROM python:3.9-slim

# Étape 2: Définir le répertoire de travail dans le conteneur
# Toutes les commandes suivantes seront exécutées depuis /app
WORKDIR /app

# Étape 3: Copier et installer les dépendances
# On copie d'abord uniquement le fichier des dépendances pour profiter du cache Docker.
# Si ce fichier ne change pas, Docker n'exécutera pas à nouveau l'installation.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Étape 4: Copier le reste de l'application
COPY . .

# Étape 5: Exposer le port
# On indique que l'application écoute sur le port 5000 à l'intérieur du conteneur.
EXPOSE 5000

# Étape 6: Commande de lancement
# C'est la commande qui sera exécutée au démarrage du conteneur.
# On lance Gunicorn en le liant à l'adresse 0.0.0.0 (toutes les interfaces réseau)
# sur le port 5000, avec 4 workers pour gérer les requêtes.
# 'app:app' signifie : dans le fichier 'app.py', lance l'objet 'app' (votre instance Flask).
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "app:app"]
```

---

## Étape 3 : Créer le fichier `.dockerignore`

Pour éviter d'inclure des fichiers inutiles (comme l'environnement virtuel, les caches, etc.) dans notre image Docker et la garder la plus légère possible, créez un fichier `.dockerignore` à la racine.

**Fichier : `.dockerignore`**

```
# Dossiers de cache et d'environnement virtuel
venv
__pycache__
.pytest_cache
.git
.idea

# Fichiers de configuration locaux
.env
*.pyc

# Fichiers de documentation ou temporaires
backups/
*.md
```

---

## Étape 4 : Créer le fichier `docker-compose.yml`

C'est le chef d'orchestre. Ce fichier va décrire le service de votre application, comment le construire et comment le lancer. Il est extrêmement pratique.

**Fichier : `docker-compose.yml`**

```yaml
# Version de la syntaxe Docker Compose
version: '3.8'

# Définition des services
services:
  # Nom de notre service
  web:
    # Indique à Compose de construire l'image en utilisant le Dockerfile
    # présent dans le répertoire courant ('.')
    build: .
    
    # Redémarre le conteneur automatiquement sauf s'il est explicitement arrêté.
    restart: unless-stopped
    
    # Mappage des ports :
    # On lie le port 8080 de votre NAS (l'hôte) au port 5000 du conteneur (exposé dans le Dockerfile).
    # Vous accéderez donc à l'app via http://<IP_DU_NAS>:8080
    ports:
      - "8080:5000"
      
    # Mappage des volumes : C'EST L'ÉTAPE LA PLUS IMPORTANTE !
    # Cela permet de rendre vos données persistantes. Les données seront stockées
    # sur votre NAS et non à l'intérieur du conteneur.
    # Syntaxe: <dossier_sur_le_NAS>:<dossier_dans_le_conteneur>
    volumes:
      # On mappe le dossier 'database' de votre projet sur le NAS
      # vers le dossier '/app/database' dans le conteneur.
      # Ainsi, la base de données SQLite et les images uploadées survivront
      # aux redémarrages et mises à jour du conteneur.
      - ./database:/app/database
      
      # On peut aussi mapper les logs
      - ./logs:/app/logs

    # Variables d'environnement (optionnel, mais bonne pratique)
    environment:
      - FLASK_ENV=production
```

---

## Étape 5 : Déploiement et Lancement

Vous avez maintenant 4 nouveaux fichiers (`gunicorn` dans `requirements.txt`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`). Transférez votre projet complet sur votre NAS.

### Méthode A : Via SSH (Recommandée)

1.  Connectez-vous en SSH à votre NAS.
2.  Naviguez jusqu'au répertoire de votre projet : `cd /chemin/vers/votre/projet`
3.  Lancez la construction de l'image et le démarrage du conteneur avec une seule commande :

    ```bash
    docker-compose up -d --build
    ```

    *   `up` : Crée et démarre les conteneurs.
    *   `-d` : (detached) Lance les conteneurs en arrière-plan.
    *   `--build` : Force la reconstruction de l'image (utile si vous avez modifié le `Dockerfile` ou le code).

### Méthode B : Via l'interface graphique Docker du NAS

1.  Ouvrez l'application Docker sur votre NAS UGREEN.
2.  Cherchez une section "Compose", "Stacks" ou "Déploiement d'application".
3.  Choisissez de créer une nouvelle stack/application.
4.  Copiez **l'intégralité du contenu de votre fichier `docker-compose.yml`** dans l'éditeur en ligne.
5.  Donnez un nom à votre stack (ex: `inventaire`) et validez. L'interface se chargera d'exécuter l'équivalent de la commande `docker-compose up`.

---

## Étape 6 : Accéder à votre application

Votre application est maintenant en cours d'exécution ! Vous pouvez y accéder depuis n'importe quel appareil sur votre réseau local via l'adresse de votre NAS, en utilisant le port que nous avons défini dans `docker-compose.yml` :

**http://<IP_DE_VOTRE_NAS>:8080**

Pour arrêter l'application (via SSH) :

```bash
docker-compose down
```
