# Inventaire CCNM

Ce projet est une application web permettant de cataloguer et de présenter la collection de micro-ordinateurs et de dispositifs numériques du **Centre Culturel sur le Numérique du Mans (CCNM)** et du **Musée Martial Vivet**.

Il s'inspire de l'esprit du site [patstec.fr](https://www.patstec.fr) pour la préservation du patrimoine scientifique et technique.

## Fonctionnalités

*   **Catalogue en ligne** : Affichage des objets avec images, descriptions détaillées, état, et liens d'informations multiples.
*   **Recherche avancée** : Recherche par mot-clé incluant le nom, la description, le fabricant, le numéro d'inventaire, l'année, et même les attributs spécifiques.
*   **Numéros d'inventaire automatiques** : Génération automatique de numéros uniques (ex: `INV_IC2_0001`) avec gestion intelligente des conflits (réattribution automatique si le numéro est pris au dernier moment).
*   **Champs dynamiques** :
    *   Attributs spécifiques selon la catégorie (entièrement configurables via `static/categories.json`).
    *   Gestion de multiples liens d'informations (URL) pour chaque objet.
    *   Galerie d'images avec gestion de l'ordre et des légendes.
    *   **Chargement facilité** : Support du glisser-déposer (Drag & Drop) pour toutes les images.
*   **Administration** : 
    *   Interface sécurisée pour ajouter, modifier et supprimer des objets (nécessite une authentification).
    *   **Verrouillage optimiste** : Prévention des conflits de modification (si deux admins éditent la même fiche en même temps).
*   **Export PDF** : Génération automatique de fiches PDF complètes pour chaque objet.
*   **Sécurité** : Protection contre les attaques par force brute sur la page de connexion.
*   **Responsive Design** : Interface moderne adaptée aux mobiles et aux grands écrans.
*   **Maintenance facile** : Outils intégrés pour la sauvegarde, le nettoyage des images et la mise à jour du schéma de données.

## Gestion des Catégories

L'application est entièrement dynamique. Pour ajouter ou modifier une catégorie d'objets (ex: "Consoles de jeu", "Appareils photo"), vous n'avez pas besoin de modifier le code Python. Tout se configure dans le fichier `static/categories.json`.

### Ajouter une catégorie

1.  Ouvrez `static/categories.json`.
2.  Ajoutez un nouvel objet avec le nom de la catégorie au pluriel :
    ```json
    "Appareils photo": {
      "icon": "fa-camera",
      "description": "Appareils de prise de vue historiques.",
      "attributes": [
        { "id": "focale", "label": "Focale", "type": "text", "ordre": 1 },
        { "id": "format", "label": "Format", "type": "text", "ordre": 2 }
      ]
    }
    ```
3.  Enregistrez. La catégorie apparaîtra immédiatement dans l'interface d'ajout et de modification.

### Modifier une catégorie

*   **Changer l'icône ou la description** : Modifiez simplement les valeurs dans le JSON.
*   **Ajouter des champs spécifiques** : Ajoutez une entrée dans la liste `attributes`.
*   **Renommer une catégorie** : Si vous renommez une catégorie dans le JSON, vous devrez également mettre à jour les objets existants en base de données pour qu'ils pointent vers le nouveau nom.

## Prérequis

*   Python 3.8+
*   Pip (gestionnaire de paquets Python)

## Installation et Lancement (Local)

1.  **Installation des dépendances :**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration (Optionnel mais recommandé) :**
    Créez un fichier `.env` à la racine si vous souhaitez personnaliser les accès :
    
    ```ini
    SECRET_KEY=votre_cle_secrete
    ADMIN_USERNAME=admin
    ADMIN_PASSWORD=votre_mot_de_passe_initial
    ```
    > **Note de sécurité :** 
    > 1. Lancez l'application une première fois pour créer le compte administrateur.
    > 2. Une fois le compte créé, vous pouvez **supprimer la ligne `ADMIN_PASSWORD`** du fichier `.env`.
    > 3. Le mot de passe restera actif (stocké de manière hachée en base) et ne sera plus lisible en clair.
    > 4. Si vous laissez la variable `ADMIN_PASSWORD`, le mot de passe sera réinitialisé à cette valeur à chaque redémarrage.

3.  **Lancer le serveur :**

    ```bash
    ./run_server.command
    # Ou via python : python app.py
    ```
    Le serveur démarrera à l'adresse `http://127.0.0.1:5000`.

4.  **Accéder à l'application :**
    Vous pouvez utiliser le script suivant pour ouvrir directement votre navigateur :
    
    ```bash
    ./run_client.command
    ```

## Structure du Projet

```
inventaire_CCNM/
├── app.py                      # Application Flask principale
├── requirements.txt            # Liste des dépendances
├── DEPLOY.md                   # Guide de déploiement production
├── run_server.command          # Lancement du serveur
├── run_client.command          # Ouverture du navigateur
├── backup.command              # Script de sauvegarde (base de données)
├── upgrade.command             # Script de mise à jour des dépendances
├── static/
│   ├── css/                    # Feuilles de style
│   ├── categories.json         # Configuration des attributs par catégorie
│   └── schema.sql              # Schéma de la base de données
├── templates/                  # Templates HTML (Jinja2)
├── scripts/                    # Scripts backend
│   ├── pdf_generator.py        # Moteur PDF
│   ├── clean_images.py         # Nettoyage fichiers orphelins
│   ├── login_security.py       # Sécurité auth
│   └── resize_existing_images.py # Optimisation des images uploadées
├── utils/
│   └── sync_categories.py      # Outil de synchronisation JSON <-> BDD
└── database/
    ├── database.db             # Base de données SQLite (créée au lancement)
    └── uploads/                # Stockage des images
```

## Maintenance

Le projet inclut plusieurs utilitaires pour faciliter la maintenance au quotidien :

*   **Sauvegardes** : `./backup.command` crée une archive datée de la base de données et des images dans le dossier `backups/`.
*   **Évolution du modèle** : Si vous modifiez `static/categories.json` (ajout/suppression d'attributs), utilisez `python utils/sync_categories.py` pour mettre à jour les données existantes en base.
*   **Optimisation** : `python scripts/resize_existing_images.py` permet de redimensionner et compresser les images qui auraient été uploadées sans traitement.

## Tests Automatisés

Pour garantir la stabilité du projet lors des modifications, une suite de tests automatisés est disponible. Elle utilise **pytest** et vérifie les fonctionnalités critiques (connexion, ajout d'objet, sécurité) sans affecter votre base de données réelle (utilisation d'une base temporaire).

### Lancer les tests pas à pas

Ouvrez un terminal dans le dossier du projet et exécutez les commandes suivantes :

```bash
# 1. Activer l'environnement virtuel (indispensable)
source venv/bin/activate

# 2. Lancer tous les tests
pytest

# Optionnel : Voir le détail de chaque test
pytest -v

# Optionnel : S'arrêter dès la première erreur rencontrée
pytest -x
```

> **Note importante** : Les tests créent automatiquement une base de données temporaire. Vos données réelles (dans `database/database.db`) ne sont **jamais touchées** par les tests.

### Que testons-nous ?
*   **Intégrité** : L'application démarre correctement.
*   **Routing** : Les pages principales (Accueil, Login) répondent (Code 200).
*   **Sécurité** : Les pages d'administration sont bien inaccessibles sans authentification.
*   **Fonctionnalités** : Le cycle complet d'ajout d'un objet (Formulaire -> Base de données) est validé, y compris la gestion des champs dynamiques JSON.

## Déploiement

Un guide détaillé pour le déploiement sur un serveur Linux (avec Nginx/Gunicorn) est disponible dans [DEPLOY.md](DEPLOY.md).

## Licence

Projet développé pour le Centre Culturel sur le Numérique du Mans.
