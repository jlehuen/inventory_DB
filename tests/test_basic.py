"""
Module de tests basiques.

Ce module vérifie le bon fonctionnement des routes publiques principales
(page d'accueil) et la gestion des erreurs (404).
"""

def test_index(client):
    """Test que la page d'accueil s'affiche correctement."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Inventaire CCNM" in response.data or b"CCNM" in response.data

def test_404(client):
    """Test qu'une page inexistante renvoie 404."""
    response = client.get('/page-inexistante')
    assert response.status_code == 404
