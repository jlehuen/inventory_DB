import pytest
from app import get_db_connection

def test_login(client, auth):
    """Test de la connexion administrateur."""
    # Test d'accès à la page de login
    assert client.get('/login').status_code == 200
    
    # Test de connexion réussie
    response = auth.login()
    assert response.headers["Location"] == "/admin" # Redirection après succès
    
    # Test avec logout
    auth.logout()
    
    # Test de connexion échouée
    response = auth.login(username='admin', password='mauvais_password')
    assert b'Connexion' in response.data # On reste sur la page de login (ou message d'erreur)

def test_home_link_redirection(client, auth):
    """Vérifie que le lien Accueil pointe vers admin si connecté, sinon index."""
    # Cas 1: Non connecté
    response = client.get('/')
    assert response.status_code == 200
    # On cherche le lien dans la nav ou le logo. 
    # Le href doit être "/" (index)
    # Note: Flask url_for('index') retourne '/'
    assert b'href="/"' in response.data

    # Cas 2: Connecté
    auth.login()
    response = client.get('/')
    assert response.status_code == 200
    # Le href doit être "/admin"
    assert b'href="/admin"' in response.data

def test_admin_access_required(client):
    """Vérifie que les pages admin sont protégées."""
    # Essayer d'accéder sans être connecté
    response = client.get('/admin/ajouter')
    assert response.status_code == 302 # Redirection vers login
    assert '/login' in response.headers["Location"]

def test_ajouter_objet(client, auth, app_fixture):
    """Test du processus complet d'ajout d'un objet."""
    # 1. Connexion
    auth.login()
    
    # 2. Vérifier qu'on accède à la page d'ajout
    assert client.get('/admin/ajouter').status_code == 200
    
    # 3. Soumettre le formulaire d'ajout
    data = {
        'nom': 'Microscope Test',
        'description': 'Description de test',
        'categorie': 'Microscopie',
        'fabricant': 'Zeiss',
        'date_fabrication': '1950',
        'numero_inventaire': 'INV_TEST_001',
        # Simulation d'un attribut spécifique dynamique
        'attr_Grossissement': '100x',
        'attr_label_Grossissement': 'Grossissement',
        'attr_ordre_Grossissement': '1'
    }
    
    response = client.post('/admin/ajouter', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Objet ajout\xc3\xa9 avec succ\xc3\xa8s' in response.data # "ajouté avec succès" encodé
    
    # 4. Vérifier en base de données
    with app_fixture.app_context():
        conn = get_db_connection()
        objet = conn.execute('SELECT * FROM objets WHERE numero_inventaire = ?', ('INV_TEST_001',)).fetchone()
        assert objet is not None
        assert objet['nom'] == 'Microscope Test'
        assert 'Grossissement' in objet['attributs_specifiques']
        assert '100x' in objet['attributs_specifiques']
