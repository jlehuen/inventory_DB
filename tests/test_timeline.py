"""
Tests pour la frise chronologique (timeline).
"""

def test_timeline_display(client):
    """Test que la page timeline s'affiche."""
    response = client.get('/timeline')
    assert response.status_code == 200
    assert "Frise chronologique" in response.get_data(as_text=True)

def test_timeline_multi_filter(client):
    """Test le filtrage par plusieurs catégories sur la timeline."""
    # On teste avec deux catégories
    response = client.get('/timeline?categories=Ordinateurs&categories=Consoles+de+jeu')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # On vérifie que les catégories sont présentes
    assert "Ordinateurs" in html
    assert "Consoles de jeu" in html
    # On vérifie la présence du bouton de réinitialiser (avec accent)
    assert "Réinitialiser" in html
