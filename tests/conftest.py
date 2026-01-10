"""
Configuration des tests Pytest.

Ce fichier définit les fixtures partagées (client de test, authentification,
base de données temporaire) pour l'ensemble des tests.
"""

import os
import tempfile
import pytest
from app import app, init_db, User, get_db_connection
from werkzeug.security import generate_password_hash

# Classe utilitaire pour gérer l'authentification dans les tests
class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, username='admin', password='password'):
        return self._client.post(
            '/login',
            data={'username': username, 'password': password}
        )

    def logout(self):
        return self._client.get('/logout')

@pytest.fixture
def app_fixture():
    # Configuration de l'application pour les tests
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app

@pytest.fixture
def client(app_fixture):
    # Création d'un fichier temporaire pour la base de données
    db_fd, db_path = tempfile.mkstemp()
    
    app_fixture.config['DATABASE'] = db_path
    
    # Création du contexte d'application
    with app_fixture.app_context():
        # Initialisation de la base de données
        init_db()
        # Création d'un utilisateur admin de test
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            ('admin', generate_password_hash('password'))
        )
        conn.commit()
        conn.close()
        
    # Création du client de test
    with app_fixture.test_client() as client:
        yield client

    # Nettoyage : fermeture et suppression du fichier temporaire
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def auth(client):
    return AuthActions(client)