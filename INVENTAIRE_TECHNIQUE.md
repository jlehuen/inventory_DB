# Inventaire Technique & Infrastructure

Ce document récapitule les choix technologiques et les prérequis pour le déploiement en production de l'application de catalogage du patrimoine scientifique.

## 1. Inventaire des Technologies

### **Backend (Logique Métier & Serveur)**
*   **Langage** : Python 3.x
*   **Framework Web** : Flask (Micro-framework flexible et léger).
*   **Base de Données** : SQLite 3.
    *   *Gestion de la structure* : Fichier souverain `static/schema.sql`.
    *   *Intégrité* : Contraintes `UNIQUE` sur les numéros d'inventaire.
*   **Sécurité Applicative** :
    *   **Verrouillage Optimiste** : Système de `version` dans la table `objets` pour empêcher l'écrasement de données lors d'éditions concurrentes.
    *   **Protection Brute-force** : Script `scripts/login_security.py` pour le blocage temporaire d'IP après échecs répétés.
*   **Génération de Documents** : `scripts/pdf_generator.py` pour l'export de fiches d'objets.

### **Frontend (Interface & Expérience Utilisateur)**
*   **Moteur de Template** : Jinja2 (intégré à Flask).
*   **Interface (UI)** :
    *   HTML5 / CSS3 (Design "Modern UI" avec ombres portées multi-couches et textures subtiles).
    *   **Typographie** : Polices locales (Effra Std) pour une autonomie totale sans dépendances externes (Google Fonts).
*   **Interactivité (JS)** :
    *   **Vanilla JS** : Pas de frameworks lourds (type React/Vue) pour maximiser la vitesse de chargement.
    *   **AJAX (Fetch API)** : Chargement dynamique de fragments HTML pour les fonctionnalités "Objet au hasard".
    *   **SPA (Single Page Application)** : L'éditeur de liens utiles (`edit_liens.html`) fonctionne comme une application autonome pilotée par un état JavaScript (`appState`).
    *   **UX** : Drag & Drop natif pour les images (`form-enhancer.js`).

### **Configuration & Données Dynamiques**
*   **Fichiers JSON** : Utilisation de `static/categories.json` et `static/liens.json` comme sources de vérité pour les labels d'attributs et les ressources externes, permettant une mise à jour sans toucher à la base de données.

---

## 2. Infrastructure de Production

Pour garantir la stabilité, la sécurité et la performance en production, l'architecture suivante est recommandée :

### **Serveur d'Application (WSGI)**
Ne pas utiliser le serveur de développement Flask.
*   **Gunicorn** (recommandé sur Linux) ou **Waitress** (sur Windows) : Gère les processus de l'application de manière robuste.

### **Serveur Web & Reverse Proxy (Nginx)**
*   **Rôle** : Reçoit les requêtes HTTP/HTTPS.
*   **SSL/TLS** : Gestion du HTTPS (via Certbot/Let's Encrypt).
*   **Fichiers Statiques** : Nginx sert directement le dossier `static/` et `database/uploads/`, déchargeant ainsi Python de cette tâche.
*   **Sécurité** : Limitation du débit et masquage des versions serveur.

### **Conteneurisation (Docker)**
*   Utilisation de l'image officielle Python Slim.
*   Isolation complète de l'environnement (dépendances isolées de l'OS hôte).
*   Voir `TUTO_DOCKER.md` pour les instructions de build.

### **Maintenance & Sauvegardes**
*   **Stockage** : Espace disque dédié pour `database/uploads/`.
*   **Tâches Cron** :
    *   Exécution quotidienne de `backup.command` pour sauvegarder le fichier `.db` et les images.
    *   Nettoyage périodique via `scripts/clean_images.py` pour supprimer les fichiers orphelins.

---

## 3. Dépendances Principales (`requirements.txt`)
*   `Flask` : Cœur de l'application.
*   `python-dotenv` : Gestion des variables d'environnement.
*   `Pillow` : Traitement et redimensionnement des images.
*   *(Optionnel)* `Pytest` : Pour la validation du code via les tests unitaires.
