
import pytest
import io
from app import get_db_connection

def test_generate_cartel_pdf(client, auth, app_fixture):
    """Test la génération du cartel PDF pour un objet."""
    # 1. Créer un objet de test en base
    with app_fixture.app_context():
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO objets (nom, categorie, numero_inventaire) VALUES (?, ?, ?)',
            ('Objet Test PDF', 'Informatique', 'PDF_TEST_001')
        )
        conn.commit()
        objet_id = conn.execute('SELECT id FROM objets WHERE numero_inventaire = ?', ('PDF_TEST_001',)).fetchone()['id']

    # 2. Se connecter et accéder à la route du cartel
    auth.login()
    response = client.get(f'/objet/{objet_id}/cartel')
    
    # 3. Vérifications
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert b'%PDF' in response.data  # Signature PDF

def test_generate_fiche_pdf(client, auth, app_fixture):
    """Test la génération de la fiche A4 PDF pour un objet."""
    # 1. Réutiliser l'objet créé ou en créer un nouveau
    with app_fixture.app_context():
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO objets (nom, categorie, numero_inventaire) VALUES (?, ?, ?)',
            ('Objet Test Fiche A4', 'Informatique', 'PDF_TEST_002')
        )
        conn.commit()
        objet_id = conn.execute('SELECT id FROM objets WHERE numero_inventaire = ?', ('PDF_TEST_002',)).fetchone()['id']

    # 2. Se connecter et accéder à la route de la fiche
    auth.login()
    response = client.get(f'/objet/{objet_id}/pdf')
    
    # 3. Vérifications
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert b'%PDF' in response.data  # Signature PDF

