"""
Application Flask principale pour l'inventaire du CCNM.

Ce module contient la configuration de l'application, les modèles de données,
les routes et la logique métier pour la gestion de l'inventaire.
"""

import os
import json
import uuid
import sqlite3
import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from PIL import Image

from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_file, send_from_directory, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import requests # Ajout de la bibliothèque requests
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from dotenv import load_dotenv

from scripts import pdf_generator
from scripts.clean_images import (
    nettoyer_fichiers,
    formater_taille_fichier
)

from scripts.login_security import (
    check_login_attempts,
    increment_login_attempts,
    reset_login_attempts,
    init_security_db,
    cleanup_old_attempts,
    get_login_attempts_status
)

# Chargement des variables d'environnement
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = 'database/uploads'
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB par défaut

# Initialiser la protection CSRF
csrf = CSRFProtect(app)

# Assurez-vous que les dossiers nécessaires existent
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Configuration de la journalisation
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# Extension de fichiers autorisées
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

class User:
    """Modèle utilisateur pour l'authentification Flask-Login."""

    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        """Retourne l'identifiant unique de l'utilisateur sous forme de chaîne."""
        return str(self.id)

    @staticmethod
    def get(user_id, db_connection):
        """Récupère un utilisateur par son ID"""
        conn = db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()

        if user:
            return User(user['id'], user['username'], user['password_hash'])
        return None

    @staticmethod
    def get_by_username(username, db_connection):
        """Récupère un utilisateur par son nom d'utilisateur"""
        conn = db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user:
            return User(user['id'], user['username'], user['password_hash'])
        return None

    def verify_password(self, password):
        """Vérifie si le mot de passe correspond au hash stocké"""
        return check_password_hash(self.password_hash, password)

class LoginForm(FlaskForm):
    """Formulaire de connexion utilisateur."""

    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Connexion')

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    """Charge un utilisateur à partir de son ID pour Flask-Login."""
    return User.get(int(user_id), get_db_connection)

# Fonction pour charger le fichier des attributs spécifiques
# Charger les définitions au démarrage de l'application
# CATEGORIE_ATTRIBUTS = get_categorie_attributs()

def get_categorie_attributs():
    """Charge les définitions d'attributs spécifiques depuis le fichier JSON"""
    json_path = os.path.join('static', 'categories.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            categories_data = json.load(f)

            # Adapter au nouveau format JSON (extraire uniquement les attributs)
            attributs = {}
            for categorie, data in categories_data.items():
                if 'attributes' in data:
                    attributs[categorie] = data['attributes']

            return attributs
    except Exception as e:
        app.logger.error(f"Erreur lors du chargement des définitions d'attributs: {e}")
        return {}  # Retourner un dictionnaire vide en cas d'erreur

# Fonction pour récupérer les informations des catégories (avec icônes)
def get_categories_info():
    """Charge les informations complètes des catégories depuis le fichier JSON"""
    json_path = os.path.join('static', 'categories.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Erreur lors du chargement des informations de catégories: {e}")
        return {}  # Retourner un dictionnaire vide en cas d'erreur

@app.template_filter('from_json')
def from_json(value):
    """Filtre Jinja pour convertir une chaîne JSON en dictionnaire Python."""
    try:
        if value:
            return json.loads(value)
        return {}
    except:
        return {}

def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Établit et retourne une connexion à la base de données SQLite."""
    db_path = app.config.get('DATABASE', 'database/database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données avec le schéma SQL complet."""
    conn = get_db_connection()
    with open('static/schema.sql') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    app.logger.info(f"Base de données initialisée avec le nouveau schéma (Path: {app.config.get('DATABASE', 'database/database.db')})")

def log_auth_attempt(user_id, action, req):
    """Enregistre une tentative d'authentification dans la base de données."""
    try:
        conn = get_db_connection()
        ip_address = req.remote_addr
        user_agent = req.user_agent.string if req.user_agent else None
        
        conn.execute(
            'INSERT INTO auth_logs (user_id, action, ip_address, user_agent) VALUES (?, ?, ?, ?)',
            (user_id, action, ip_address, user_agent)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f"Erreur lors de l'enregistrement du log d'auth: {e}")

def create_admin_user():
    """Crée ou met à jour l'utilisateur administrateur par défaut."""
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    # On récupère la variable sans valeur par défaut pour distinguer l'absence de la variable
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (admin_username,)).fetchone()
        
        if not user:
            # Création : Si pas de mot de passe dans l'env, on utilise 'admin' par défaut
            password_to_use = admin_password if admin_password else 'admin'
            password_hash = generate_password_hash(password_to_use)
            conn.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (admin_username, password_hash)
            )
            app.logger.info(f'Utilisateur administrateur "{admin_username}" créé.')
        else:
            # Mise à jour : UNIQUEMENT si une variable d'environnement est explicitement définie
            if admin_password:
                current_hash = user['password_hash']
                if not check_password_hash(current_hash, admin_password):
                    new_hash = generate_password_hash(admin_password)
                    conn.execute(
                        'UPDATE users SET password_hash = ? WHERE id = ?',
                        (new_hash, user['id'])
                    )
                    app.logger.info(f'Mot de passe de l\'administrateur "{admin_username}" mis à jour depuis l\'environnement.')
            
        conn.commit()
    except Exception as e:
        app.logger.error(f"Erreur lors de la création/mise à jour de l'admin: {e}")
    finally:
        conn.close()

def secure_file_path(base_dir, user_input):
    """
    Vérifie que le chemin fourni ne sort pas du répertoire de base
    """
    from pathlib import Path

    # Normaliser le chemin pour supprimer les ../../ etc.
    base_path = Path(base_dir).resolve()

    # Joindre les chemins et résoudre les symboles
    try:
        user_path = (base_path / user_input).resolve()

        # Vérifier que le chemin est bien à l'intérieur du répertoire de base
        if base_path in user_path.parents or base_path == user_path:
            return str(user_path)
        else:
            return None  # Chemin en dehors du répertoire autorisé
    except (ValueError, FileNotFoundError):
        return None

def save_uploaded_file(file):
    """Enregistre un fichier téléchargé et retourne le chemin relatif"""
    if file and allowed_file(file.filename):
        # Générer un nom unique pour éviter les conflits
        filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Optimisation automatique de l'image
        try:
            with Image.open(filepath) as img:
                max_size = (1600, 1600)
                
                # On redimensionne si l'image est plus grande que la cible
                # Ou on ré-enregistre simplement pour appliquer la compression JPEG
                if img.width > max_size[0] or img.height > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Conversion en RGB si nécessaire (pour éviter les erreurs avec les JPEG)
                if img.mode in ('RGBA', 'P') and filepath.lower().endswith(('.jpg', '.jpeg')):
                    img = img.convert('RGB')

                # Sauvegarde avec optimisation et qualité réduite (85%)
                img.save(filepath, optimize=True, quality=85)
                app.logger.info(f"Image optimisée automatiquement : {filename}")

        except Exception as e:
            app.logger.error(f"Erreur lors de l'optimisation de l'image {filename}: {e}")
            # On ne bloque pas l'upload si l'optimisation échoue, l'image originale est déjà là

        return 'database/uploads/' + filename
    return None

def generer_numero_inventaire(db_connection):
    """
    Génère le prochain numéro d'inventaire disponible au format INV_IC2_xxxx.
    Cherche le premier nombre disponible en partant de 0.
    """
    conn = db_connection()
    rows = conn.execute('SELECT numero_inventaire FROM objets').fetchall()
    conn.close()

    existing_numbers = set()
    pattern = re.compile(r'^INV_IC2_(\d{4})$')

    for row in rows:
        inv_num = row['numero_inventaire']
        if inv_num:
            match = pattern.match(inv_num)
            if match:
                existing_numbers.add(int(match.group(1)))

    next_num = 0
    while next_num in existing_numbers:
        next_num += 1

    return f'INV_IC2_{next_num:04d}'

def numero_inventaire_existe(numero, exclude_id=None):
    """
    Vérifie si un numéro d'inventaire existe déjà dans la base de données.

    Args:
        numero: Le numéro d'inventaire à vérifier
        exclude_id: ID de l'objet à exclure de la vérification (utile lors des modifications)

    Returns:
        bool: True si le numéro existe déjà, False sinon
    """
    if not numero:  # Si le numéro est vide, il n'y a pas de conflit
        return False

    conn = get_db_connection()

    if exclude_id:
        # Lors d'une modification, exclure l'objet actuel
        result = conn.execute(
            'SELECT COUNT(*) FROM objets WHERE numero_inventaire = ? AND id != ?',
            (numero, exclude_id)
        ).fetchone()
    else:
        # Lors d'un ajout, vérifier tous les objets
        result = conn.execute(
            'SELECT COUNT(*) FROM objets WHERE numero_inventaire = ?',
            (numero,)
        ).fetchone()

    conn.close()

    # Si le compte est supérieur à 0, le numéro existe déjà
    return result[0] > 0

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Gère la connexion des utilisateurs."""
    # Rediriger si l'utilisateur est déjà connecté
    if current_user.is_authenticated:
        return redirect(url_for('admin'))

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Vérifier si l'utilisateur n'est pas bloqué
        allowed, message = check_login_attempts(username, request, get_db_connection, logger=app.logger)
        if not allowed:
            flash(message, 'error')
            return render_template('login.html', form=form)

        user = User.get_by_username(username, get_db_connection)

        if user and user.verify_password(password):
            # Connexion réussie
            login_user(user)
            reset_login_attempts(username, request, get_db_connection, logger=app.logger)  # Réinitialiser les tentatives

            # Journaliser la connexion réussie
            log_auth_attempt(user.id, 'login', request)
            app.logger.info(f'Connexion réussie pour {username}')

            # Redirection vers la page demandée ou la page admin
            next_page = request.args.get('next')
            flash('Connexion réussie', 'success')
            return redirect(next_page or url_for('admin'))
        else:
            # Connexion échouée
            if user:
                log_auth_attempt(user.id, 'failed_attempt', request)
            else:
                log_auth_attempt(None, 'failed_attempt', request)

            app.logger.warning(f'Tentative de connexion échouée pour {username}')

            # Incrémenter le compteur de tentatives
            is_locked, message = increment_login_attempts(username, request, get_db_connection, logger=app.logger)
            flash(message, 'error')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Gère la déconnexion des utilisateurs."""
    # Journaliser la déconnexion
    if current_user.is_authenticated:
        log_auth_attempt(current_user.id, 'logout', request)
        app.logger.info(f'Déconnexion pour {current_user.username}')

    logout_user()
    flash('Vous avez été déconnecté avec succès', 'success')
    return redirect(url_for('index'))

# Routes de l'application
@app.route('/random_object_fragment')
def random_object_fragment():
    """Retourne le fragment HTML de trois objets au hasard."""
    conn = get_db_connection()
    objets = conn.execute('SELECT * FROM objets ORDER BY RANDOM() LIMIT 3').fetchall()
    conn.close()

    if not objets:
        return '<p>Aucun objet dans la collection.</p>'

    html_parts = []
    for objet in objets:
        image_style = ''
        if objet['image_principale']:
            image_url = url_for('static', filename=objet['image_principale'])
            image_style = f'style="background-image: url(\'{image_url}\')"'
        
        html_parts.append(f'''
        <div class="objet-card">
            <a href="{url_for('detail_objet', id=objet['id'])}">
                <div class="objet-image {'default-image' if not objet['image_principale'] else ''}" {image_style}></div>
                <div class="objet-info">
                    <h3>{objet['nom']}</h3>
                    <p class="objet-categorie">{objet['categorie']}</p>
                    <p class="objet-fabricant">{objet['fabricant']}</p>
                </div>
            </a>
        </div>
        ''')
    
    return "".join(html_parts)

@app.route('/')
def index():
    """Affiche la page d'accueil avec les derniers objets ajoutés."""
    conn = get_db_connection()
    objets = conn.execute('SELECT * FROM objets ORDER BY date_ajout DESC LIMIT 8').fetchall()
    conn.close()
    return render_template('index.html', objets=objets)

@app.route('/contribuer')
def contribuer():
    """Affiche la page d'appel aux contributions."""
    return render_template('contribuer.html')

@app.route('/martial_vivet')
def martial_vivet():
    """Affiche la biographie de Martial Vivet."""
    return render_template('martial_vivet.html')

# Route pour servir les fichiers depuis database/uploads
@app.route('/static/database/uploads/<path:filename>')
def serve_upload(filename):
    """Sert les fichiers uploadés (images) depuis le dossier sécurisé."""
    return send_from_directory('database/uploads', filename)

@app.route('/objet/<int:id>')
def detail_objet(id):
    """Affiche la page de détail d'un objet spécifique."""
    conn = get_db_connection()

    # Récupérer les informations de l'objet
    objet = conn.execute('SELECT * FROM objets WHERE id = ?', (id,)).fetchone()
    if objet is None:
        abort(404)

    # Convertir l'objet en dictionnaire modifiable
    objet_modifiable = dict(objet)

    # Charger les labels à jour depuis categories.json
    categories_info = get_categories_info()
    categorie_objet = objet_modifiable.get('categorie')
    attributs_specifiques_json = objet_modifiable.get('attributs_specifiques')

    if categorie_objet and attributs_specifiques_json and categorie_objet in categories_info:
        try:
            # Créer une map des labels actuels pour la catégorie de l'objet
            label_map = {
                attr['id']: attr['label']
                for attr in categories_info[categorie_objet].get('attributes', [])
            }

            # Parser les attributs stockés dans la base de données
            attributs_stockes = json.loads(attributs_specifiques_json)

            # Mettre à jour les labels dans les attributs stockés
            for attr_id, details in attributs_stockes.items():
                if isinstance(details, dict) and attr_id in label_map:
                    details['label'] = label_map[attr_id]

            # Remplacer les anciens attributs par les nouveaux
            objet_modifiable['attributs_specifiques'] = json.dumps(attributs_stockes)
        except (json.JSONDecodeError, KeyError) as e:
            app.logger.warning(f"Impossible de mettre à jour les labels pour l'objet {id}: {e}")


    # Récupérer toutes les images associées à cet objet
    images = conn.execute(
        'SELECT * FROM images WHERE objet_id = ? ORDER BY ordre',
        (id,)
    ).fetchall()

    # Récupérer tous les liens associés à cet objet
    liens = conn.execute(
        'SELECT * FROM liens WHERE objet_id = ? ORDER BY ordre',
        (id,)
    ).fetchall()

    conn.close()
    return render_template('detail.html', objet=objet_modifiable, images=images, liens=liens)

@app.route('/recherche')
def recherche():
    """Effectue une recherche textuelle sur les objets et leurs attributs."""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Première étape : recherche dans les champs standard, maintenant avec date_fabrication et etat
    objets_standard = conn.execute(
        'SELECT * FROM objets WHERE nom LIKE ? OR description LIKE ? OR fabricant LIKE ? OR numero_inventaire LIKE ? OR date_fabrication LIKE ? OR etat LIKE ?',
        (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')
    ).fetchall()
    
    # Recherche dans les liens (nouvelle table)
    objets_liens = conn.execute(
        'SELECT DISTINCT o.* FROM objets o JOIN liens l ON o.id = l.objet_id WHERE l.url LIKE ? OR l.titre LIKE ?',
        (f'%{query}%', f'%{query}%')
    ).fetchall()

    # Deuxième étape : recherche dans tous les objets pour vérifier les attributs spécifiques
    all_objets = conn.execute('SELECT * FROM objets').fetchall()

    # Convertir les objets en dictionnaires pour faciliter la manipulation
    # On combine les résultats standard et ceux des liens
    objets_standard_dict = {obj['id']: dict(obj) for obj in objets_standard}
    
    for obj in objets_liens:
        objets_standard_dict[obj['id']] = dict(obj)

    # Parcourir tous les objets et vérifier les attributs spécifiques
    for obj in all_objets:
        # Si l'objet est déjà dans les résultats, on passe
        if obj['id'] in objets_standard_dict:
            continue

        # Vérifier les attributs spécifiques
        if obj['attributs_specifiques']:
            try:
                attributs = json.loads(obj['attributs_specifiques'])

                # Rechercher dans toutes les valeurs des attributs
                for attr_key, attr_value in attributs.items():
                    # On ignore les clés techniques (commençant par ordre_ ou label_)
                    if attr_key.startswith('ordre_') or attr_key.startswith('label_'):
                        continue

                    # Extraire la valeur saisie selon le format
                    if isinstance(attr_value, dict) and 'valeur' in attr_value:
                        # Nouveau format avec objet {valeur, ordre, label}
                        value_to_check = str(attr_value['valeur']).lower()
                    else:
                        # Ancien format : la valeur est directe
                        value_to_check = str(attr_value).lower()

                    # Si la requête est dans la valeur de l'attribut, ajouter l'objet aux résultats
                    if query.lower() in value_to_check:
                        objets_standard_dict[obj['id']] = dict(obj)
                        break

            except (json.JSONDecodeError, TypeError):
                # En cas d'erreur de décodage JSON, on ignore simplement cet objet
                app.logger.warning(f"Erreur décodage JSON pour l'objet ID {obj['id']}")
                pass

    conn.close()

    # Convertir les résultats en liste pour le template
    objets = list(objets_standard_dict.values())

    return render_template('resultats.html', objets=objets, query=query)

@app.route('/categories')
def categories():
    """Affiche la liste de toutes les catégories disponibles."""
    # Obtenir les informations de catégories depuis le fichier JSON
    json_categories_info = get_categories_info()
    json_categories = list(json_categories_info.keys())

    # Récupérer aussi les catégories personnalisées de la base de données
    conn = get_db_connection()
    db_categories = []

    if json_categories:
        placeholders = ','.join(['?'] * len(json_categories))
        db_categories = [row['categorie'] for row in conn.execute(
            f'SELECT DISTINCT categorie FROM objets WHERE categorie NOT IN ({placeholders})',
            json_categories
        ).fetchall()]
    else:
        db_categories = [row['categorie'] for row in conn.execute(
            'SELECT DISTINCT categorie FROM objets'
        ).fetchall()]

    # Récupérer le nombre d'objets par catégorie
    counts = {row['categorie']: row['count'] for row in conn.execute(
        'SELECT categorie, COUNT(*) as count FROM objets GROUP BY categorie'
    ).fetchall()}

    conn.close()

    # Combiner les deux sources
    all_categories = sorted(json_categories + db_categories)

    # Formater pour le template
    categories_list = []
    for cat in all_categories:
        # Récupérer le nombre d'objets
        count = counts.get(cat, 0)
        
        # Vérifier si la catégorie est dans le JSON pour récupérer l'icône
        if cat in json_categories_info:
            icon = json_categories_info[cat].get('icon', 'fa-microscope')  # Icône par défaut si non spécifiée
            categories_list.append({'categorie': cat, 'icon': icon, 'count': count})
        else:
            # Catégorie personnalisée sans icône dans le JSON
            categories_list.append({'categorie': cat, 'icon': 'fa-microscope', 'count': count})

    return render_template('categories.html', categories=categories_list)

@app.route('/categorie/<categorie>')
def objets_par_categorie(categorie):
    """Affiche les objets appartenant à une catégorie spécifique."""
    conn = get_db_connection()
    objets = conn.execute('SELECT * FROM objets WHERE categorie = ? ORDER BY date_fabrication ASC', (categorie,)).fetchall()

    # Stats par année pour cette catégorie (Répartition temporelle)
    stats_annees = conn.execute('''
        SELECT SUBSTR(date_fabrication, 1, 4) as annee, COUNT(*) as count
        FROM objets
        WHERE categorie = ? AND date_fabrication IS NOT NULL AND date_fabrication != ''
        GROUP BY annee
        ORDER BY annee ASC
    ''', (categorie,)).fetchall()

    conn.close()

    # Récupérer la description de la catégorie depuis le JSON
    description = None
    categories_info = get_categories_info()
    if categorie in categories_info and 'description' in categories_info[categorie]:
        description = categories_info[categorie]['description']

    return render_template('categorie.html', objets=objets, categorie=categorie, description=description, stats_annees=stats_annees)

@app.route('/collection')
def collection():
    """Affiche toute la collection sous forme de tableau triable"""
    conn = get_db_connection()
    objets = conn.execute('''
        SELECT id, nom, categorie, fabricant, date_fabrication, numero_inventaire
        FROM objets
        ORDER BY nom ASC
    ''').fetchall()
    conn.close()
    return render_template('collection.html', objets=objets)


@app.route('/liens')
def liens():
    """Affiche la page des liens utiles."""
    try:
        with open('static/liens.json', 'r', encoding='utf-8') as f:
            liens_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        liens_data = []
    return render_template('liens.html', categories_liens=liens_data)

@app.route('/admin/liens/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_liens():
    """Permet à l'administrateur d'éditer le fichier JSON des liens utiles."""
    json_path = os.path.join('static', 'liens.json')
    
    if request.method == 'POST':
        json_content = request.form.get('json_content')
        try:
            # Vérifier que c'est du JSON valide
            parsed_json = json.loads(json_content)
            
            # Sauvegarder avec une jolie mise en forme
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_json, f, indent=4, ensure_ascii=False)
                
            flash('La liste des liens a été mise à jour avec succès.', 'success')
            return redirect(url_for('liens'))
        except json.JSONDecodeError as e:
            flash(f'Erreur de syntaxe JSON : {e}', 'error')
            # On renvoie le contenu erroné pour que l'utilisateur puisse corriger sans tout perdre
            return render_template('admin/edit_liens.html', json_content=json_content)
        except Exception as e:
            app.logger.error(f"Erreur lors de la sauvegarde des liens: {e}")
            flash(f'Une erreur est survenue lors de l\'enregistrement : {e}', 'error')
            return render_template('admin/edit_liens.html', json_content=json_content)

    # Chargement initial (GET)
    liens_data = []
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                liens_data = json.load(f)
        else:
            # Modèle par défaut si le fichier n'existe pas
            liens_data = [
                {
                    "categorie": "Exemple de catégorie",
                    "liens": [
                        {
                            "nom": "Nom du site",
                            "url": "https://exemple.com",
                            "description": "Description du site"
                        }
                    ]
                }
            ]
    except Exception as e:
        app.logger.error(f"Erreur lecture liens.json: {e}")
        liens_data = [] # En cas d'erreur, on envoie un tableau vide

    return render_template('admin/edit_liens.html', liens_data=liens_data)


def get_global_liens_urls():
    """Charge les URLs du fichier static/liens.json et les retourne sous forme de set."""
    json_path = os.path.join('static', 'liens.json')
    global_urls = set()
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                global_liens_data = json.load(f)
                for category in global_liens_data:
                    for lien in category.get('liens', []):
                        if 'url' in lien and lien['url']:
                            global_urls.add(lien['url'])
    except Exception as e:
        app.logger.error(f"Erreur lors de la lecture de static/liens.json: {e}")
    return global_urls

def get_collection_liens_urls():
    """Charge toutes les URLs uniques de la table 'liens' de la base de données."""
    conn = get_db_connection()
    db_liens = conn.execute('SELECT url FROM liens WHERE url IS NOT NULL AND url != ""').fetchall()
    conn.close()
    collection_urls = set(row['url'] for row in db_liens)
    return collection_urls

@app.route('/api/collection_urls')
@login_required
def api_collection_urls():
    """Retourne toutes les URLs de la table 'liens' de la base de données au format JSON."""
    urls = list(get_collection_liens_urls())
    return jsonify(urls)

@app.route('/api/global_liens_urls')
@login_required
def api_global_liens_urls():
    """Retourne toutes les URLs du fichier static/liens.json au format JSON."""
    urls = list(get_global_liens_urls())
    return jsonify(urls)

@app.route('/admin/test_links_ajax')
@login_required
def test_links_ajax():
    """
    Teste une liste d'URLs fournie en streamant les résultats.
    Les URLs à vérifier et à exclure sont déterminées côté serveur
    en fonction du paramètre 'origin'.
    """
    origin = request.args.get('origin')
    urls_to_check = set()
    excluded_urls = set() # URLs qui ne seront pas vérifiées

    if origin == 'collection':
        urls_to_check = get_collection_liens_urls()
        excluded_urls = get_global_liens_urls() # Les liens globaux sont exclus de la vérification de la collection
    elif origin == 'liens':
        urls_to_check = get_global_liens_urls()
        # Pas d'exclusion spécifique pour les liens globaux quand on les vérifie depuis leur propre page
    else:
        app.logger.error(f"Appel à test_links_ajax sans 'origin' valide: {origin}")
        return Response("Erreur: Paramètre 'origin' manquant ou invalide.", status=400)

    # Filtrer les URLs à vérifier en retirant celles à exclure
    final_urls_to_check = sorted(list(urls_to_check - excluded_urls))

    def generate_results():
        total_urls = len(final_urls_to_check)
        checked_count = 0

        # Envoie le nombre total d'URLs à vérifier
        yield f"event: total\ndata: {total_urls}\n\n"

        for url in final_urls_to_check:
            status_code = None
            error_message = None
            try:
                # Ajouter un User-Agent et des en-têtes de navigateur pour éviter les blocages
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
                # Utiliser une requête GET avec un timeout court et des en-têtes complets
                response = requests.get(url, timeout=7, allow_redirects=True, headers=headers)
                status_code = response.status_code
                if status_code >= 400:
                    error_message = f"Erreur HTTP {status_code}"
            except requests.exceptions.Timeout:
                error_message = "Délai d'attente dépassé (Timeout)"
                status_code = 408
            except requests.exceptions.RequestException:
                error_message = "Erreur de connexion"
                status_code = 500 # Simule une erreur serveur pour le frontend
            except Exception as e:
                error_message = f"Erreur inattendue: {e}"
                status_code = 500

            checked_count += 1
            progress = (checked_count / total_urls) * 100 if total_urls > 0 else 0

            result_data = {
                'url': url,
                'status_code': status_code,
                'error_message': error_message,
                'progress': round(progress)
            }
            # Envoie un événement "message"
            yield f"data: {json.dumps(result_data)}\n\n"
        
        # Envoie un événement de fin
        yield "event: done\ndata: Vérification terminée\n\n"

    return Response(stream_with_context(generate_results()), mimetype='text/event-stream')


@app.route('/admin')
@login_required
def admin():
    """Affiche le tableau de bord d'administration."""
    conn = get_db_connection()
    
    # 1. Chiffres clés globaux
    total_objets = conn.execute('SELECT COUNT(*) FROM objets').fetchone()[0]
    
    # 2. Stats par catégorie (pour le graphique)
    stats_categories = conn.execute('''
        SELECT categorie, COUNT(*) as count 
        FROM objets 
        GROUP BY categorie 
        ORDER BY count DESC
    ''').fetchall()
    
    # 3. Stats par état (pour le suivi sanitaire)
    stats_etats = conn.execute('''
        SELECT etat, COUNT(*) as count 
        FROM objets 
        WHERE etat IS NOT NULL AND etat != ''
        GROUP BY etat 
        ORDER BY count DESC
    ''').fetchall()
    
    # 4. Derniers objets ajoutés (pour l'activité récente)
    derniers_objets = conn.execute('''
        SELECT id, nom, categorie, numero_inventaire, date_ajout, image_principale 
        FROM objets 
        ORDER BY date_ajout DESC 
        LIMIT 5
    ''').fetchall()

    # 5. Stats par année (Répartition temporelle)
    stats_annees = conn.execute('''
        SELECT SUBSTR(date_fabrication, 1, 4) as annee, COUNT(*) as count
        FROM objets
        WHERE date_fabrication IS NOT NULL AND date_fabrication != ''
        GROUP BY annee
        ORDER BY annee ASC
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/dashboard.html',
                           total_objets=total_objets,
                           stats_categories=stats_categories,
                           stats_etats=stats_etats,
                           derniers_objets=derniers_objets,
                           stats_annees=stats_annees)

@app.route('/admin/ajouter', methods=('GET', 'POST'))
@login_required
def ajouter_objet():
    """Gère l'ajout d'un nouvel objet dans l'inventaire."""
    if request.method == 'POST':
        nom = request.form['nom']
        description = request.form['description']

        # Gestion de la catégorie personnalisée
        if 'categorie_personnalisee' in request.form and request.form['categorie_personnalisee'].strip():
            categorie = request.form['categorie_personnalisee'].strip()
        else:
            categorie = request.form['categorie']

        fabricant = request.form['fabricant']
        date_fabrication = request.form['date_fabrication']
        # url = request.form['donnees_complementaires']  <-- Ancienne gestion
        numero_inventaire = request.form['numero_inventaire']
        origine = request.form.get('origine', '') # Nouveau champ Origine / Donateur

        # Collecte des attributs spécifiques
        attributs_specifiques = {}
        for key, value in request.form.items():
            if key.startswith('attr_') and not key.startswith('attr_ordre_') and not key.startswith('attr_label_') and value.strip():
                attr_key = key[5:]  # Enlever le préfixe 'attr_'

                # Récupérer le label et l'ordre depuis les champs cachés
                label = request.form.get(f'attr_label_{attr_key}', attr_key.replace('_', ' ').title())
                ordre = request.form.get(f'attr_ordre_{attr_key}', 999)

                attributs_specifiques[attr_key] = {
                    'valeur': value.strip(),
                    'label': label,
                    'ordre': ordre
                }

        # Convertir en JSON
        attributs_json = json.dumps(attributs_specifiques) if attributs_specifiques else None

        # Validation
        error = None

        if not nom:
            error = 'Le nom est obligatoire!'
        elif not categorie:
            error = 'La catégorie est obligatoire!'
        elif not numero_inventaire:
            error = 'Le numéro d\'inventaire est obligatoire!'
        elif numero_inventaire_existe(numero_inventaire):
            # Collision détectée : on génère le prochain numéro libre
            nouveau_numero = generer_numero_inventaire(get_db_connection)
            error = f'Le numéro d\'inventaire "{numero_inventaire}" vient d\'être utilisé par un autre utilisateur. Le nouveau numéro "{nouveau_numero}" vous a été attribué. Veuillez cliquer à nouveau sur Ajouter pour confirmer.'
            # On met à jour le numéro pour le réaffichage du formulaire
            numero_inventaire = nouveau_numero

        if error:
            flash(error, 'warning' if 'vient d\'être utilisé' in error else 'error')
            # Renvoyer le formulaire avec les données déjà saisies
            return render_template('admin/ajouter.html',
                                                                        objet={
                                                                        'nom': nom,
                                                                        'description': description,
                                                                        'categorie': categorie,
                                                                        'fabricant': fabricant,
                                                                        'date_fabrication': date_fabrication,
                                                                        # 'url': url,  <-- Plus utilisé
                                                                        'numero_inventaire': numero_inventaire,
                                                                        'origine': origine,
                                                                        'attributs_specifiques': attributs_json
                                                                    })
        else:
            conn = get_db_connection()

            # Gestion de l'image principale
            image_principale_path = ''
            if 'image_principale' in request.files:
                file = request.files['image_principale']
                image_path = save_uploaded_file(file)
                if image_path:
                    image_principale_path = image_path

            try:
                # Insérer les informations de l'objet (sans l'URL dans la table principale)
                cursor = conn.execute(
                    'INSERT INTO objets (nom, description, categorie, fabricant, date_fabrication, numero_inventaire, image_principale, date_ajout, attributs_specifiques, origine) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (nom, description, categorie, fabricant, date_fabrication, numero_inventaire, image_principale_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attributs_json, origine)
                )

                objet_id = cursor.lastrowid
                
                # Traitement des liens (Informations)
                liens = request.form.getlist('liens')
                for i, lien in enumerate(liens):
                    if lien.strip():
                        conn.execute(
                            'INSERT INTO liens (objet_id, url, ordre) VALUES (?, ?, ?)',
                            (objet_id, lien.strip(), i)
                        )

                # Traitement des images supplémentaires
                if 'images_supplementaires' in request.files:
                    files = request.files.getlist('images_supplementaires')
                    for i, file in enumerate(files):
                        image_path = save_uploaded_file(file)
                        if image_path:
                            legende = request.form.get(f'legende_{i}', '')
                            # Utiliser l'index comme ordre
                            conn.execute(
                                'INSERT INTO images (objet_id, chemin, legende, ordre) VALUES (?, ?, ?, ?)',
                                (objet_id, image_path, legende, i)
                            )

                conn.commit()
                conn.close()
                app.logger.info(f'Objet "{nom}" ajouté par {current_user.username}')
                flash('Objet ajouté avec succès !', 'success')
                return redirect(url_for('detail_objet', id=objet_id))
            
            except sqlite3.IntegrityError:
                # En cas de concurrence critique où le check Python est passé mais la base a bloqué
                conn.close()
                nouveau_numero = generer_numero_inventaire(get_db_connection)
                flash(f'Conflit détecté au dernier moment : Le numéro "{numero_inventaire}" a été pris. Nouveau numéro "{nouveau_numero}" attribué. Veuillez valider à nouveau.', 'warning')
                
                return render_template('admin/ajouter.html',
                                      objet={
                                          'nom': nom,
                                          'description': description,
                                          'categorie': categorie,
                                          'fabricant': fabricant,
                                          'date_fabrication': date_fabrication,
                                          'numero_inventaire': nouveau_numero,
                                          'origine': origine,
                                          'attributs_specifiques': attributs_json
                                      })
            except Exception as e:
                conn.close()
                app.logger.error(f"Erreur lors de l'ajout: {e}")
                flash(f"Une erreur est survenue lors de l'enregistrement : {e}", 'error')
                return render_template('admin/ajouter.html',
                                      objet={
                                          'nom': nom,
                                          'description': description,
                                          'categorie': categorie,
                                          'fabricant': fabricant,
                                          'date_fabrication': date_fabrication,
                                          'numero_inventaire': numero_inventaire,
                                          'origine': origine,
                                          'attributs_specifiques': attributs_json
                                      })

    # Générer le prochain numéro d'inventaire disponible pour le formulaire vide
    prochain_numero = generer_numero_inventaire(get_db_connection)
    return render_template('admin/ajouter.html', objet={'numero_inventaire': prochain_numero})

@app.route('/admin/modifier/<int:id>', methods=('GET', 'POST'))
@login_required
def modifier_objet(id):
    """Gère la modification d'un objet existant."""
    conn = get_db_connection()
    objet = conn.execute('SELECT * FROM objets WHERE id = ?', (id,)).fetchone()

    if objet is None:
        abort(404)

    # Récupérer les images existantes
    images = conn.execute('SELECT * FROM images WHERE objet_id = ? ORDER BY ordre', (id,)).fetchall()
    
    # Récupérer les liens existants
    liens = conn.execute('SELECT * FROM liens WHERE objet_id = ? ORDER BY ordre', (id,)).fetchall()

    if request.method == 'POST':
        nom = request.form['nom']
        description = request.form['description']

        # Gestion de la catégorie personnalisée
        if 'categorie_personnalisee' in request.form and request.form['categorie_personnalisee'].strip():
            categorie = request.form['categorie_personnalisee'].strip()
        else:
            categorie = request.form['categorie']

        fabricant = request.form['fabricant']
        date_fabrication = request.form['date_fabrication']
        # url = request.form['donnees_complementaires'] <-- Ancienne gestion
        numero_inventaire = request.form['numero_inventaire']
        etat = request.form.get('etat', '')  # Récupération de l'état de l'objet
        origine = request.form.get('origine', '') # Nouveau champ Origine / Donateur
        version_soumise = int(request.form.get('version', 0))

        # Collecte des attributs spécifiques
        attributs_specifiques = {}
        for key, value in request.form.items():
            if key.startswith('attr_') and not key.startswith('attr_ordre_') and not key.startswith('attr_label_') and value.strip():
                attr_key = key[5:]  # Enlever le préfixe 'attr_'

                # Récupérer le label et l'ordre depuis les champs cachés
                label = request.form.get(f'attr_label_{attr_key}', attr_key.replace('_', ' ').title())
                ordre = request.form.get(f'attr_ordre_{attr_key}', 999)

                attributs_specifiques[attr_key] = {
                    'valeur': value.strip(),
                    'label': label,
                    'ordre': ordre
                }

        # Convertir en JSON
        attributs_json = json.dumps(attributs_specifiques) if attributs_specifiques else None

        # Validation
        error = None

        if not nom:
            error = 'Le nom est obligatoire!'
        elif not categorie:
            error = 'La catégorie est obligatoire!'
        elif numero_inventaire and numero_inventaire_existe(numero_inventaire, exclude_id=id):
            error = f'Le numéro d\'inventaire "{numero_inventaire}" existe déjà!'
        elif version_soumise != objet['version']:
            error = 'Cette fiche a été modifiée par un autre utilisateur entre-temps. Veuillez copier vos modifications, recharger la page et recommencer.'

        if error:
            flash(error, 'error')
            # Récupérer à nouveau les images pour le formulaire
            images = conn.execute('SELECT * FROM images WHERE objet_id = ? ORDER BY ordre', (id,)).fetchall()
            liens = conn.execute('SELECT * FROM liens WHERE objet_id = ? ORDER BY ordre', (id,)).fetchall()
            # On recharge l'objet actuel de la base pour avoir la version la plus récente si nécessaire
            objet_actuel = conn.execute('SELECT * FROM objets WHERE id = ?', (id,)).fetchone()
            conn.close()

            # Renvoyer le formulaire avec les données modifiées (mais on garde la version de la base pour permettre de retenter après rechargement)
            modified_objet = dict(objet_actuel)
            modified_objet.update({
                'nom': nom,
                'description': description,
                'categorie': categorie,
                'fabricant': fabricant,
                'date_fabrication': date_fabrication,
                # 'url': url,
                'numero_inventaire': numero_inventaire,
                'etat': etat,  # Inclure l'état dans les données modifiées
                'origine': origine,
                'attributs_specifiques': attributs_json
            })

            return render_template('admin/modifier.html', objet=modified_objet, images=images, liens=liens)
        else:
            # Gestion de l'image principale
            image_principale_path = objet['image_principale']
            if 'image_principale' in request.files:
                file = request.files['image_principale']
                image_path = save_uploaded_file(file)
                if image_path:
                    image_principale_path = image_path

            # Mettre à jour les informations de l'objet (sans l'URL)
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor = conn.execute(
                'UPDATE objets SET nom = ?, description = ?, categorie = ?, fabricant = ?, date_fabrication = ?, numero_inventaire = ?, image_principale = ?, attributs_specifiques = ?, etat = ?, origine = ?, date_modification = ?, version = version + 1 WHERE id = ? AND version = ?',
                (nom, description, categorie, fabricant, date_fabrication, numero_inventaire, image_principale_path, attributs_json, etat, origine, current_datetime, id, version_soumise)
            )
            
            if cursor.rowcount == 0:
                conn.rollback()
                conn.close()
                flash('Conflit de modification critique : Cette fiche a été modifiée par un autre utilisateur au moment même où vous validiez. Vos modifications ont été annulées pour protéger les données. Veuillez recharger la page.', 'error')
                return redirect(url_for('modifier_objet', id=id))
            
            # Mise à jour des liens : on supprime tout et on recrée (plus simple)
            conn.execute('DELETE FROM liens WHERE objet_id = ?', (id,))
            
            liens_form = request.form.getlist('liens')
            for i, lien in enumerate(liens_form):
                if lien.strip():
                    conn.execute(
                        'INSERT INTO liens (objet_id, url, ordre) VALUES (?, ?, ?)',
                        (id, lien.strip(), i)
                    )

            # Traitement des images à conserver
            images_to_keep = request.form.getlist('garder_image')

            # Supprimer les images qui ne sont pas dans la liste à conserver
            images_to_delete = []
            if images_to_keep:
                placeholders = ','.join(['?'] * len(images_to_keep))
                images_to_delete = conn.execute(
                    f'SELECT id, chemin FROM images WHERE objet_id = ? AND id NOT IN ({placeholders})',
                    [id] + images_to_keep
                ).fetchall()
            else:
                images_to_delete = conn.execute(
                    'SELECT id, chemin FROM images WHERE objet_id = ?',
                    (id,)
                ).fetchall()

            # Supprimer les fichiers physiques des images
            for image in images_to_delete:
                try:
                    file_path = os.path.join('static', image['chemin'])
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    app.logger.error(f"Erreur lors de la suppression du fichier {image['chemin']}: {e}")

            # Supprimer les entrées dans la base de données
            if not images_to_keep:
                conn.execute('DELETE FROM images WHERE objet_id = ?', (id,))
            else:
                placeholders = ','.join(['?'] * len(images_to_keep))
                conn.execute(
                    f'DELETE FROM images WHERE objet_id = ? AND id NOT IN ({placeholders})',
                    [id] + images_to_keep
                )

            # Mettre à jour les légendes et l'ordre des images existantes
            for index, image_id in enumerate(images_to_keep):
                legende = request.form.get(f'legende_{image_id}', '')
                conn.execute('UPDATE images SET legende = ?, ordre = ? WHERE id = ?', (legende, index, image_id))

            # Traitement des nouvelles images
            if 'nouvelles_images' in request.files:
                files = request.files.getlist('nouvelles_images')
                # Obtenir l'ordre maximum actuel
                max_ordre = conn.execute('SELECT MAX(ordre) FROM images WHERE objet_id = ?', (id,)).fetchone()[0] or 0

                for i, file in enumerate(files):
                    image_path = save_uploaded_file(file)
                    if image_path:
                        legende = request.form.get(f'nouvelle_legende_{i}', '')
                        conn.execute(
                            'INSERT INTO images (objet_id, chemin, legende, ordre) VALUES (?, ?, ?, ?)',
                            (id, image_path, legende, max_ordre + i + 1)
                        )

            conn.commit()
            conn.close()
            app.logger.info(f'Objet "{nom}" (ID: {id}) modifié par {current_user.username}')
            flash('Objet modifié avec succès !', 'success')
            return redirect(url_for('detail_objet', id=id))

    conn.close()
    return render_template('admin/modifier.html', objet=objet, images=images, liens=liens)

@app.route('/admin/supprimer/<int:id>', methods=('POST',))
@login_required
def supprimer_objet(id):
    """Gère la suppression d'un objet et de ses ressources associées."""
    conn = get_db_connection()
    # Récupérer l'objet avant suppression pour la journalisation
    objet = conn.execute('SELECT nom FROM objets WHERE id = ?', (id,)).fetchone()

    # Récupérer les chemins des images pour pouvoir les supprimer du système de fichiers
    images = conn.execute('SELECT chemin FROM images WHERE objet_id = ?', (id,)).fetchall()
    image_principale = conn.execute('SELECT image_principale FROM objets WHERE id = ?', (id,)).fetchone()

    # Supprimer l'objet (la contrainte CASCADE supprimera aussi les images dans la base)
    conn.execute('DELETE FROM objets WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    # Supprimer les fichiers d'images du système de fichiers
    for image in images:
        if image['chemin']:
            try:
                file_path = os.path.join('static', image['chemin'])
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                app.logger.error(f"Erreur lors de la suppression du fichier {image['chemin']}: {e}")

    # Supprimer l'image principale
    if image_principale and image_principale['image_principale']:
        try:
            file_path = os.path.join('static', image_principale['image_principale'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            app.logger.error(f"Erreur lors de la suppression de l'image principale: {e}")

    if objet:
        app.logger.info(f'Objet "{objet["nom"]}" (ID: {id}) supprimé par {current_user.username}')
    flash('Objet supprimé avec succès !', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/security', methods=['GET'])
@login_required
def admin_security():
    """Page d'administration pour visualiser l'état des tentatives de connexion"""
    # Nettoyer les anciennes tentatives à chaque visite de la page
    cleanup_old_attempts(get_db_connection, days=30, logger=app.logger)

    # Récupérer l'état actuel
    login_status = get_login_attempts_status(get_db_connection)

    return render_template('admin/security.html', login_status=login_status)

@app.route('/admin/export/csv')
@login_required
def export_csv():
    """Génère et télécharge un export CSV complet de l'inventaire."""
    import csv
    import io
    from flask import Response

    conn = get_db_connection()
    # Récupérer tous les objets
    objets = conn.execute('SELECT * FROM objets ORDER BY id').fetchall()
    conn.close()

    # Créer un flux en mémoire pour le fichier CSV
    output = io.StringIO()
    # Définir le writer CSV (séparateur point-virgule pour Excel fr)
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # En-têtes des colonnes
    headers = ['ID', 'Nom / Titre', 'Catégorie', 'Fabricant / Éditeur', 'Année', 'N° Inventaire', 'État', 'Donateur', 'Date d\'ajout']
    writer.writerow(headers)

    # Écrire les données
    for obj in objets:
        writer.writerow([
            obj['id'],
            obj['nom'],
            obj['categorie'],
            obj['fabricant'],
            obj['date_fabrication'],
            obj['numero_inventaire'],
            obj['etat'],
            obj['origine'],
            obj['date_ajout']
        ])

    # Revenir au début du flux
    output.seek(0)
    
    # Créer la réponse avec les bons en-têtes pour le téléchargement
    return Response(
        output.getvalue().encode('utf-8-sig'), # utf-8-sig pour qu'Excel reconnaisse les accents
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=inventaire_ccnm_{datetime.now().strftime('%Y-%m-%d')}.csv"}
    )

@app.route('/objet/<int:id>/pdf')
def generate_pdf(id):
    """Génère et sert le fichier PDF de la fiche de l'objet."""
    conn = get_db_connection()

    # Récupérer les informations de l'objet
    objet = conn.execute('SELECT * FROM objets WHERE id = ?', (id,)).fetchone()
    if objet is None:
        abort(404)

    # Récupérer toutes les images associées à cet objet
    images = conn.execute(
        'SELECT * FROM images WHERE objet_id = ? ORDER BY ordre',
        (id,)
    ).fetchall()

    # Récupérer tous les liens associés à cet objet
    liens = conn.execute(
        'SELECT * FROM liens WHERE objet_id = ? ORDER BY ordre',
        (id,)
    ).fetchall()

    conn.close()

    # Générer le PDF
    base_url = request.url_root
    pdf_buffer = pdf_generator.generate_object_pdf(objet, images, liens, base_url)

    # Renvoyer le PDF comme fichier téléchargeable
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{objet['nom']}-fiche.pdf",
        mimetype='application/pdf'
    )

@app.route('/objet/<int:id>/cartel')
@login_required
def generate_cartel(id):
    """Génère et sert le cartel (étiquette) de l'objet au format PDF."""
    conn = get_db_connection()
    objet = conn.execute('SELECT * FROM objets WHERE id = ?', (id,)).fetchone()
    conn.close()

    if objet is None:
        abort(404)

    # Générer le PDF du cartel
    base_url = request.url_root
    pdf_buffer = pdf_generator.generate_cartel_pdf(objet, base_url)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Cartel-{objet['nom']}.pdf",
        mimetype='application/pdf'
    )

# Séparation des fonctions GET et POST pour le nettoyage
@app.route('/admin/nettoyage', methods=['GET'])
@login_required
def nettoyer_fichiers():
    """Affiche la page de simulation du nettoyage des fichiers"""
    try:
        # Exécuter la détection des orphelins sans suppression (simulation)
        # Code spécifique pour l'aperçu, ne supprime rien
        dossier_uploads = app.config['UPLOAD_FOLDER']
        orphelins = []
        erreurs = []

        # Vérifier que le dossier existe
        if not os.path.exists(dossier_uploads):
            flash(f"Le dossier {dossier_uploads} n'existe pas.", "error")
            return redirect(url_for('admin'))

        # Récupérer tous les fichiers du dossier
        fichiers_dossier = []
        for fichier in os.listdir(dossier_uploads):
            ext = fichier.split('.')[-1].lower() if '.' in fichier else ''
            if ext in ALLOWED_EXTENSIONS:
                fichiers_dossier.append(fichier)

        # Récupérer les références de la base de données
        fichiers_references = []
        conn = get_db_connection()

        # Images principales
        images_principales = conn.execute(
            "SELECT image_principale FROM objets WHERE image_principale IS NOT NULL AND image_principale != ''"
        ).fetchall()

        for img in images_principales:
            nom_fichier = os.path.basename(img['image_principale'])
            fichiers_references.append(nom_fichier)

        # Images supplémentaires
        images_supplementaires = conn.execute(
            "SELECT chemin FROM images WHERE chemin IS NOT NULL AND chemin != ''"
        ).fetchall()

        for img in images_supplementaires:
            nom_fichier = os.path.basename(img['chemin'])
            fichiers_references.append(nom_fichier)

        conn.close()

        # Identifier les orphelins
        for fichier in fichiers_dossier:
            if fichier not in fichiers_references:
                orphelins.append(fichier)

        # Préparer les résultats pour l'affichage
        resultats = {
            "fichiers_dans_dossier": fichiers_dossier,
            "images_referencees_db": fichiers_references,
            "orphelins_detectes": orphelins,
            "fichiers_supprimes": [],
            "erreurs": erreurs
        }

        # Message d'information
        if orphelins:
            flash(f"Simulation: {len(orphelins)} fichier(s) orphelin(s) détecté(s).", 'info')
        else:
            flash("Simulation: Aucun fichier orphelin détecté.", 'info')

    except Exception as e:
        app.logger.error(f"Erreur lors de la simulation: {str(e)}", exc_info=True)
        flash(f"Une erreur s'est produite lors de la simulation: {str(e)}", 'error')
        return redirect(url_for('admin'))

    return render_template('admin/nettoyage.html', resultats=resultats)

@app.route('/admin/nettoyage/execute', methods=['POST'])
@login_required
def admin_post_nettoyage():
    """Exécute le nettoyage des fichiers et redirige vers la page d'administration"""
    from scripts.clean_images import nettoyer_fichiers, formater_taille_fichier

    try:
        # Exécuter le nettoyage réel avec la nouvelle fonction
        resultat = nettoyer_fichiers(app, get_db_connection, ALLOWED_EXTENSIONS)

        # Nombre de fichiers supprimés et espace libéré
        nb_fichiers = len(resultat['fichiers_supprimes'])
        espace_texte = formater_taille_fichier(resultat['espace_libere'])

        # Logs pour le débogage
        app.logger.info(f"Résultats du nettoyage:")
        app.logger.info(f"- Fichiers supprimés: {nb_fichiers}")
        app.logger.info(f"- Liste des fichiers: {resultat['fichiers_supprimes']}")
        app.logger.info(f"- Espace libéré: {espace_texte}")
        app.logger.info(f"- Erreurs: {len(resultat['erreurs'])}")

        # Message à afficher
        if nb_fichiers > 0:
            flash(f"Nettoyage terminé : {nb_fichiers} fichiers supprimés, {espace_texte} d'espace libéré.", 'success')
        else:
            flash("Aucun fichier à supprimer n'a été trouvé.", 'info')

        # Journaliser le résultat
        app.logger.info(f'Nettoyage effectué par {current_user.username}: {nb_fichiers} images supprimées, {espace_texte} libérés')

    except Exception as e:
        app.logger.error(f"Erreur lors du nettoyage des fichiers: {str(e)}", exc_info=True)
        flash(f"Une erreur s'est produite lors du nettoyage: {str(e)}", 'error')

    # Rediriger vers la page d'administration
    return redirect(url_for('admin'))

# Ajout d'entêtes de sécurité
@app.after_request
def add_security_headers(response):
    """Ajoute les en-têtes de sécurité HTTP à la réponse."""
    # Protection contre le clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # Protection XSS avancée
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Empêche le navigateur de deviner le type MIME
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Politique de sécurité du contenu (CSP) - version plus permissive pour le développement
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; img-src 'self' data: https:; font-src 'self' https://cdnjs.cloudflare.com data:;"
    # Référant
    response.headers['Referrer-Policy'] = 'same-origin'
    return response

# Gestionnaire d'erreur 404
@app.errorhandler(404)
def page_not_found(e):
    """Gère les erreurs 404 (Page non trouvée)."""
    return render_template('404.html'), 404

# Gestionnaire d'erreur 500
@app.errorhandler(500)
def internal_error(e):
    """Gère les erreurs 500 (Erreur interne du serveur)."""
    app.logger.error(f'Erreur 500: {str(e)}')
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Créer la base de données si elle n'existe pas
    if not os.path.exists('database/database.db'):
        os.makedirs('database', exist_ok=True)
        init_db()
        create_admin_user() # On crée l'admin juste après l'initialisation complète
    
    # On s'assure toujours que l'admin est à jour (au cas où le .env change)
    create_admin_user()

    app.logger.info('Application démarrée')

    # Exécuter l'application en fonction de l'environnement
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(debug=True)
    else:
        app.run(host='0.0.0.0', port=5000)
