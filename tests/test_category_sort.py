"""
Test du tri des objets par catégorie.
"""
import pytest
from app import get_db_connection

def test_categorie_sort_order(client, app_fixture):
    """
    Test que les objets d'une catégorie sont triés par date de fabrication croissante.
    """
    # 1. Insérer des données de test
    # On utilise le contexte de l'application pour être sûr d'avoir la bonne config DB
    with app_fixture.app_context():
        conn = get_db_connection()
        
        # Insertion dans le désordre
        objets = [
            # (nom, categorie, date_fabrication, numero_inventaire)
            ('Objet 1990', 'TestCategory', '1990', 'INV_TEST_002'),
            ('Objet 1980', 'TestCategory', '1980', 'INV_TEST_001'),
            ('Objet 2000', 'TestCategory', '2000', 'INV_TEST_003'),
            ('Objet SansDate', 'TestCategory', '', 'INV_TEST_004'),
        ]
        
        for nom, cat, date, num in objets:
            conn.execute(
                'INSERT INTO objets (nom, categorie, date_fabrication, numero_inventaire) VALUES (?, ?, ?, ?)',
                (nom, cat, date, num)
            )
        conn.commit()
        conn.close()

    # 2. Requête sur la page de catégorie
    response = client.get('/categorie/TestCategory')
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    # 3. Vérification de l'ordre
    # On cherche les positions des noms dans le HTML
    pos_1980 = html.find('Objet 1980')
    pos_1990 = html.find('Objet 1990')
    pos_2000 = html.find('Objet 2000')
    pos_sans_date = html.find('Objet SansDate')

    # Vérification que tous les objets sont présents
    assert pos_1980 != -1
    assert pos_1990 != -1
    assert pos_2000 != -1
    assert pos_sans_date != -1

    # Vérification de l'ordre chronologique
    # L'ordre attendu est : SansDate (string vide), 1980, 1990, 2000
    # car en SQL '1980' > '' (chaine vide)
    
    # Note: L'ordre exact des chaines vides vs non-vides dépend de l'implémentation SQL,
    # mais ASC met généralement les chaines vides au début.
    
    assert pos_sans_date < pos_1980
    assert pos_1980 < pos_1990
    assert pos_1990 < pos_2000
