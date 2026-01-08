# Inventaire CCNM

Ce projet est une application web permettant de cataloguer et de présenter la collection de micro-ordinateurs et de dispositifs numériques du **Centre Culturel sur le Numérique du Mans (CCNM)** et du **Musée Martial Vivet**.

Il est similaire dans l'esprit au site [patstec.fr](https://www.patstec.fr).

## Fonctionnalités

*   **Catalogue en ligne** : Affichage des objets avec images, descriptions détaillées, état, et liens d'informations multiples.
*   **Recherche avancée** : Recherche par mot-clé incluant le nom, la description, le fabricant, le numéro d'inventaire, l'année, et même les attributs spécifiques.
*   **Numéros d'inventaire automatiques** : Génération automatique de numéros uniques (ex: `INV_IC2_0001`).
*   **Champs dynamiques** :
    *   Attributs spécifiques selon la catégorie (définis dans `categories.json`).
    *   Gestion de multiples liens d'informations (URL) pour chaque objet.
    *   Galerie d'images avec gestion de l'ordre et des légendes.
*   **Administration** : Interface sécurisée pour ajouter, modifier et supprimer des objets (nécessite une authentification).
*   **Export PDF** : Génération automatique de fiches PDF pour chaque objet, incluant toutes les données et images.
*   **Sécurité** : Protection contre les attaques par force brute sur la page de connexion.
*   **Responsive Design** : Interface moderne adaptée aux mobiles et aux grands écrans (mode "wide" pour les détails).

## Prérequis

*   Python 3.7+
*   Pip (gestionnaire de paquets Python)

## Installation Rapide (Développement)

1.  **Cloner le dépôt :**
    ```bash
    git clone https://github.com/jlehuen/inventory_DB.git
    cd inventory_DB
    ```

2.  **Créer un environnement virtuel :**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Sur Windows: venv\Scripts\activate
    ```

3.  **Installer les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurer l'environnement :**
    Copiez le fichier `.env.example` (s'il existe) ou créez un fichier `.env` à la racine :
    ```ini
    SECRET_KEY=votre_cle_secrete_tres_longue
    ADMIN_USERNAME=admin
    ADMIN_PASSWORD=votre_mot_de_passe
    FLASK_ENV=development
    ```

5.  **Lancer l'application :**
    ```bash
    ./run.command  # Ou: python app.py
    ```
    Accédez à `http://127.0.0.1:5000`.

## Structure du Projet

```
inventory_DB/
├── app.py                 # Application Flask principale (routes, modèles)
├── requirements.txt       # Liste des dépendances Python
├── DEPLOY.md              # Guide de déploiement en production
├── run.command            # Script de lancement rapide
├── static/
│   ├── css/               # Styles (modernui.css, style.css)
│   ├── categories.json    # Configuration des attributs par catégorie
│   └── schema.sql         # Schéma de la base de données
├── templates/             # Templates HTML (Jinja2)
│   ├── base.html          # Layout principal
│   ├── admin/             # Templates d'administration
│   └── ...
├── scripts/               # Scripts utilitaires
│   ├── pdf_generator.py   # Génération PDF
│   ├── clean_images.py    # Nettoyage des images orphelines
│   └── login_security.py  # Sécurité de l'authentification
└── database/
    └── uploads/           # Stockage des images uploadées
```

## Déploiement en Production

Un guide complet pour le déploiement sur un serveur Linux (Ubuntu/Debian) avec Nginx et Gunicorn est disponible dans le fichier [DEPLOY.md](DEPLOY.md).

## Licence

Ce projet est développé pour le CCNM.