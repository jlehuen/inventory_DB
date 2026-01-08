# PatstecClone - Catalogue du patrimoine scientifique et technique

Ce projet est une application web permettant de cataloguer et de présenter des objets scientifiques et techniques, similaire au site [patstec.fr](https://www.patstec.fr).

## Fonctionnalités

- Affichage d'objets scientifiques avec images et descriptions détaillées
- Catégorisation des objets
- Recherche d'objets par mot-clé
- Interface d'administration pour ajouter, modifier et supprimer des objets
- Base de données SQLite pour le stockage des données

## Prérequis

- Python 3.7+
- [Flask](https://perso.liris.cnrs.fr/pierre-antoine.champin/2019/progweb-python/cours/cm2.html)
- Reportlab

## Installation

1. Clonez le dépôt sur votre machine locale :

```bash
git clone https://github.com/lehuen/ccnm.git
cd ccnm
```

2. Créez et activez un environnement virtuel Python :

```bash
# Sous Windows
python -m venv venv
venv\Scripts\activate

# Sous Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Installez les dépendances requises :

```bash
pip install flask
pip install reportlab
```

## Structure du projet

```
CCNM/
│
├── app.py                 # Application Flask principale
├── schema.sql             # Schéma de base de données SQLite
├── database.db            # Base de données SQLite (créée au premier démarrage)
├── pdf_generator.py       # Script de génération de fiches PDF
├── README.md              # Documentation du projet
│
├── static/                # Fichiers statiques
│   ├── css/               # Feuilles de style CSS
│   │   └── style.css      # Style principal du site
│   │
│   └── uploads/           # Dossier pour les images téléchargées
│
└── templates/             # Templates HTML
    ├── base.html          # Template de base avec header et footer
    ├── index.html         # Page d'accueil
    ├── detail.html        # Page de détail d'un objet
    ├── categories.html    # Liste des catégories
    ├── categorie.html     # Objets d'une catégorie spécifique
    ├── resultats.html     # Résultats de recherche
    │
    └── admin/             # Templates d'administration
        ├── index.html     # Tableau de bord admin
        ├── ajouter.html   # Formulaire d'ajout
        └── modifier.html  # Formulaire de modification
```

## Utilisation

1. Démarrez l'application :

```bash
python app.py
```

2. Accédez à l'application dans votre navigateur à l'adresse `http://127.0.0.1:5000`

3. Pour accéder à l'interface d'administration, naviguez vers `http://127.0.0.1:5000/admin`

## Personnalisation

### Modifier l'apparence

Vous pouvez personnaliser l'apparence du site en modifiant le fichier `static/css/style.css`. Les couleurs principales sont définies comme variables CSS au début du fichier :

```css
:root {
    --primary-color: #2c3e50;
    --secondary-color: #3498db;
    --accent-color: #e74c3c;
    --light-color: #ecf0f1;
    --dark-color: #2c3e50;
    --text-color: #333;
}
```

### Ajouter des catégories personnalisées

Les catégories sont créées dynamiquement lorsque vous ajoutez ou modifiez un objet. Il suffit de spécifier une nouvelle catégorie dans le champ correspondant du formulaire.

## Déploiement en production

Pour un environnement de production, il est recommandé de :

1. Utiliser un serveur WSGI comme Gunicorn ou uWSGI
2. Configurer un serveur web comme Nginx en tant que proxy inverse
3. Désactiver le mode debug (`debug=False` dans app.py)
4. Configurer une clé secrète sécurisée pour Flask
5. Mettre en place HTTPS

Exemple de configuration pour Gunicorn :

```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

---
Les paramètres de sécurité (nombre de tentatives, durée de blocage) sont configurables directement dans le module login_security.py.
---




## Licence

Ce projet est disponible sous licence MIT. Vous êtes libre de l'utiliser, le modifier et le distribuer selon vos besoins.

## Contact

Pour toute question ou suggestion, veuillez créer une issue sur ce dépôt.
