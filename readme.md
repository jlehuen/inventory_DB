# Inventaire CCNM & Musée Martial Vivet

Ce projet est une application web de gestion d'inventaire destinée à cataloguer, préserver et valoriser le patrimoine numérique (micro-ordinateurs, périphériques, documentation) du **Centre Culturel sur le Numérique du Mans (CCNM)** et du **Musée Martial Vivet**.

Développée en **Python (Flask)**, l'application s'inspire de la rigueur des outils de conservation muséale (type [patstec.fr](https://www.patstec.fr)) tout en offrant une interface moderne et dynamique.

---

## 🚀 Fonctionnalités Clés

### Gestion de Collection
*   **Fiches détaillées** : Gestion complète des objets (Nom, Fabricant, Année, Description, État, Provenance).
*   **Numérotation Automatique Intelligente** : Génération de numéros d'inventaire uniques (ex: `INV_IC2_0001`) avec gestion automatique des collisions en cas d'ajouts simultanés.
*   **Champs Dynamiques par Catégorie** : Les attributs spécifiques (ex: "Focale" pour un appareil photo, "RAM" pour un ordinateur) sont configurables sans toucher au code (via JSON).
*   **Galerie Média** :
    *   Support du **Glisser-Déposer (Drag & Drop)** pour l'upload d'images.
    *   Réorganisation des images et ajout de légendes.
    *   Génération automatique de miniatures optimisées.

### Ressources Documentaires
*   **Liens Contextuels** : Association de liens web spécifiques à chaque objet (manuels, vidéos de démonstration).
*   **Bibliothèque de Liens** : Gestion centralisée de liens utiles globaux, classés par catégories.
*   **Export PDF** : Génération à la volée de fiches d'inventaire imprimables et standardisées.

### Expérience Utilisateur & Recherche
*   **Moteur de Recherche Global** : Recherche plein texte incluant nom, description, fabricant, année, attributs spécifiques et contenu des liens.
*   **Découverte Aléatoire** : Module AJAX permettant d'afficher 3 objets au hasard sans recharger la page.
*   **Responsive Design** : Interface adaptée aux tablettes et mobiles pour une consultation en réserve ou en salle d'exposition.

### Administration Sécurisée
*   **Sécurité Renforcée** : Protection contre les attaques par force brute (bannissement temporaire d'IP).
*   **Travail Collaboratif Sûr (Verrouillage Optimiste)** : Système empêchant l'écrasement accidentel de données si deux administrateurs modifient la même fiche simultanément.

---

## 🏗 Architecture Technique

L'application repose sur des choix techniques robustes pour garantir l'intégrité des données :

1.  **Backend** : Python / Flask.
2.  **Base de Données** : SQLite avec schéma relationnel strict (`static/schema.sql`).
3.  **Gestion de la Concurrence** : Utilisation d'une colonne `version` dans la base de données. Lors d'une mise à jour, l'application vérifie que la version en base correspond à celle chargée par l'utilisateur. Si elles diffèrent, la modification est rejetée pour protéger le travail de l'autre administrateur.
4.  **Ressources Hybrides** :
    *   Les données structurées sont en **Base de Données**.
    *   La configuration flexible (catégories, attributs) et les ressources globales sont en **JSON**.

---

## 🛠 Installation (Local)

### Prérequis
*   Python 3.8 ou supérieur.
*   Git.

### Étapes

1.  **Cloner le dépôt :**
    ```bash
    git clone <url_du_depot>
    cd inventaire_CCNM
    ```

2.  **Créer et activer un environnement virtuel (Recommandé) :**
    *   *MacOS / Linux :*
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   *Windows :*
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```

3.  **Installer les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration (Optionnel) :**
    Créez un fichier `.env` à la racine pour sécuriser vos accès :
    ```ini
    SECRET_KEY=votre_cle_secrete_aleatoire
    ADMIN_USERNAME=admin
    ADMIN_PASSWORD=votre_mot_de_passe
    ```
    *Note : Une fois le premier compte admin créé via l'interface ou le lancement initial, la variable `ADMIN_PASSWORD` peut être retirée.*

5.  **Lancer l'application :**
    *   *Via le script (MacOS/Linux) :*
        ```bash
        ./run_server.command
        ```
    *   *Via Python :*
        ```bash
        python app.py
        ```
    Accédez à l'application sur `http://127.0.0.1:5000`.

---

## ⚙️ Manuel de Configuration

L'application est conçue pour être évolutive sans modification du code source Python.

### Gestion des Catégories (`static/categories.json`)
Ce fichier définit la structure de votre inventaire. Vous pouvez ajouter des catégories ou modifier les champs requis pour chacune.

**Exemple d'ajout d'une catégorie :**
```json
"Consoles": {
  "icon": "fa-gamepad",
  "description": "Consoles de jeux vidéo de salon et portables.",
  "attributes": [
    { "id": "generation", "label": "Génération", "type": "text", "ordre": 1 },
    { "id": "region", "label": "Région (PAL/NTSC)", "type": "text", "ordre": 2 }
  ]
}
```
*Si vous modifiez des attributs existants, utilisez le script de synchronisation (voir section Maintenance).*

---

## 🧹 Maintenance et Utilitaires

Le dossier `scripts/` et `utils/` contient des outils essentiels pour la vie du projet :

| Script | Description | Commande |
| :--- | :--- | :--- |
| **backup.command** | Crée une archive complète (Base de données + Images) dans le dossier `backups/`. | `./backup.command` |
| **sync_categories.py** | À lancer après avoir modifié `categories.json`. Met à jour les objets existants en base pour refléter la nouvelle structure JSON. | `python utils/sync_categories.py` |
| **clean_images.py** | Analyse le dossier d'upload et supprime les images qui ne sont plus liées à aucun objet (nettoyage orphelins). | `python scripts/clean_images.py` |
| **resize_existing...** | Redimensionne et optimise les images qui auraient été uploadées manuellement sans passer par l'interface. | `python scripts/resize_existing_images.py` |

---

## 🧪 Tests Automatisés

Une suite de tests **pytest** garantit la non-régression des fonctionnalités critiques (Authentification, Ajout, Sécurité, Conflits).

Les tests utilisent une base de données temporaire et **ne touchent jamais** à vos données de production.

```bash
# Lancer tous les tests
pytest

# Lancer avec détails
pytest -v
```

---

## 📂 Structure du Projet

```
inventaire_CCNM/
├── app.py                      # Cœur de l'application Flask (Routes, Logique)
├── requirements.txt            # Dépendances Python
├── static/
│   ├── categories.json         # CONFIGURATION MAJEURE : Structure des objets
│   ├── liens.json              # Base de données des liens globaux
│   ├── schema.sql              # Structure SQL de la base de données
│   ├── css/                    # Styles (Modern UI)
│   └── js/                     # Scripts front (Drag&Drop, Éditeurs)
├── templates/                  # Vues HTML (Jinja2)
│   └── admin/                  # Interfaces d'administration
├── database/
│   ├── database.db             # Fichier de données SQLite
│   └── uploads/                # Stockage des images des objets
├── scripts/                    # Scripts de maintenance backend
└── utils/                      # Utilitaires système
```

## Déploiement

Pour passer en production (Serveur Linux, Nginx, Gunicorn), consultez le guide dédié : [**DEPLOY.md**](DEPLOY.md).

---
**Licence & Crédits**
Projet développé pour le CCNM.
Iconographie : FontAwesome.
Police : Effra Std.