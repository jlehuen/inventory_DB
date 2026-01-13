"""
Module de génération de PDF.

Ce module fournit les fonctionnalités nécessaires pour générer des fiches d'objets
au format PDF en utilisant la bibliothèque ReportLab.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import os
import io
from flask import url_for
import json
from datetime import datetime
import qrcode

def generate_object_pdf(objet, images, liens, base_url):
    """
    Génère un fichier PDF pour un objet du catalogue avec ses détails et images

    Args:
        objet: Dictionnaire contenant les détails de l'objet
        images: Liste des images associées à l'objet
        liens: Liste des liens (informations) associés à l'objet
        base_url: URL de base pour construire les chemins complets des images

    Returns:
        Objet BytesIO contenant le PDF généré
    """
    # Créer un buffer pour stocker le PDF
    buffer = io.BytesIO()

    # Génération du QR Code
    qr_buffer = io.BytesIO()
    try:
        # Construire l'URL complète vers la fiche objet
        # On s'assure que l'URL ne finit pas par un double slash si base_url en a déjà un
        clean_base_url = base_url.rstrip('/')
        object_url = f"{clean_base_url}/objet/{objet['id']}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(object_url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
    except Exception as e:
        print(f"Erreur génération QR Code: {e}")
        qr_buffer = None

    # Fonction callback pour dessiner le QR Code sur la première page
    def on_first_page(canvas, doc):
        canvas.saveState()
        # Titre header
        canvas.setFont('Helvetica-Oblique', 9)
        canvas.setFillColor(colors.grey)
        canvas.drawString(2*cm, A4[1] - 1.5*cm, "Inventaire CCNM - Fiche descriptive")
        
        if qr_buffer:
            # Positionnement en haut à droite
            # A4 width = 595.27, height = 841.89
            qr_size = 3*cm
            x_pos = A4[0] - qr_size - 1*cm
            y_pos = A4[1] - qr_size - 1*cm
            
            canvas.drawImage(ImageReader(qr_buffer), x_pos, y_pos, width=qr_size, height=qr_size)
            
            # Ajouter l'URL en texte sous le QR code
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(x_pos + qr_size/2, y_pos - 10, f"ID: {objet['id']}")
            
        canvas.restoreState()

    # Créer le document avec marges appropriées
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # Obtenir les styles de base
    styles = getSampleStyleSheet()

    # Créer des styles personnalisés
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor('#2c3e50')
    )

    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#3498db')
    )

    normal_style = styles['Normal']

    # Créer un style pour les cellules de tableau contenant du texte
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,  # Espacement des lignes
        wordWrap='CJK'  # Permettre le retour à la ligne automatique
    )

    # Créer un style pour les URLs
    url_style = ParagraphStyle(
        'URLStyle',
        parent=styles['Normal'],
        wordWrap='CJK'
    )

    # Fonction pour formater l'URL en conservant le lien mais en tronquant le texte affiché
    def format_clickable_url(url, max_length=45):
        """
        Formate une URL pour qu'elle soit tronquée visuellement mais reste un lien cliquable.
        Utilise la syntaxe de ReportLab pour les liens.
        """
        if not url:
            return "-"

        # Si l'URL est déjà assez courte, la retourner telle quelle
        if len(url) <= max_length:
            return f'<a href="{url}">{url}</a>'

        # Diviser l'URL en parties pour une troncature plus intelligente
        parts = url.split('/')

        if len(parts) >= 3:  # A au moins 'http:', '', 'domain.com', ...
            domain_part = '/'.join(parts[:3])  # Prend "http://domaine.com"

            # Si le domaine est déjà trop long
            if len(domain_part) > max_length - 3:
                display_text = domain_part[:max_length-3] + "..."
                return f'<a href="{url}">{display_text}</a>'

            # Calculer combien de caractères nous pouvons utiliser pour le reste
            remaining_chars = max_length - len(domain_part) - 3

            if remaining_chars > 0:
                path_part = '/'.join(parts[3:])
                if path_part:
                    display_text = domain_part + "/" + path_part[:remaining_chars] + "..."
                    return f'<a href="{url}">{display_text}</a>'
                return f'<a href="{url}">{domain_part}</a>'
            display_text = domain_part + "..."
            return f'<a href="{url}">{display_text}</a>'

        # Fallback pour les URL non standard
        display_text = url[:max_length-3] + "..."
        return f'<a href="{url}">{display_text}</a>'

    # Fonction pour convertir un texte en paragraphe avec style
    def create_paragraph(text, style=normal_style):
        """
        Crée un objet Paragraph à partir d'un texte, pour permettre les retours à la ligne automatiques.
        Renvoie un tiret si le texte est vide.
        """
        if not text or text.strip() == "":
            return Paragraph("-", style)
        return Paragraph(text, style)

    # Éléments du document
    elements = []

    # Logo et en-tête (facultatif)
    elements.append(Paragraph("CCNM - Centre Culturel sur le Numérique du Mans", styles['Heading3']))
    elements.append(Paragraph("Collection de micro-ordinateurs et de dispositifs numériques", styles['Italic']))
    elements.append(Spacer(1, 1*cm))

    # Titre
    elements.append(Paragraph(objet['nom'], title_style))
    elements.append(Spacer(1, 0.5*cm))

    # Si l'objet a une image principale, l'ajouter
    if objet['image_principale']:
        # Chemin physique pour l'image
        img_path = objet['image_principale'] # Le chemin est déjà complet
        if os.path.exists(img_path):
            img = Image(img_path, width=300, height=200, kind='proportional')
            elements.append(img)
            elements.append(Spacer(1, 0.5*cm))

    # Description
    if objet['description']:
        elements.append(Paragraph("Description", heading2_style))
        elements.append(create_paragraph(objet['description'], normal_style))
        elements.append(Spacer(1, 0.5*cm))

    # Formater les URLs cliquables
    links_cell_content = []
    if liens:
        for lien in liens:
            if lien['url']:
                url_html = format_clickable_url(lien['url'])
                # Ajouter une puce avant chaque lien
                links_cell_content.append(Paragraph(f"• {url_html}", url_style))
    
    if not links_cell_content:
        links_cell_content = create_paragraph("-", normal_style)

    # Informations techniques sous forme de tableau
    elements.append(Paragraph("Données générales", heading2_style))

    # Adapter les libellés selon la catégorie (comme sur la vue HTML)
    is_book = objet['categorie'] == 'Livres'
    label_nom = "Titre" if is_book else "Modèle"
    label_fabricant = "Éditeur" if is_book else "Fabricant"
    label_annee = "Année d'édition" if is_book else "Année de sortie"

    # Utiliser des paragraphes pour toutes les cellules de données
    data = [
        ["Catégorie", create_paragraph(objet['categorie'] or "Non spécifiée", table_cell_style)],
        [label_nom, create_paragraph(objet['nom'], table_cell_style)],
        [label_fabricant, create_paragraph(objet['fabricant'] or "Non spécifié", table_cell_style)],
        [label_annee, create_paragraph(objet['date_fabrication'] or "Non spécifiée", table_cell_style)],
        ["Informations", links_cell_content],
        ["État de l'objet", create_paragraph(objet['etat'] or "Non spécifié", table_cell_style)],
        ["Numéro", create_paragraph(objet['numero_inventaire'] or "Non spécifié", table_cell_style)]
    ]

    t = Table(data, colWidths=[4*cm, 10*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))

    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))

    # Ajouter les attributs spécifiques s'ils existent
    if objet['attributs_specifiques']:
        try:
            attributs = json.loads(objet['attributs_specifiques'])

            if attributs:
                # Titre de section adapté à la catégorie
                section_title = "Informations bibliographiques" if objet['categorie'] == 'Livres' else "Caractéristiques techniques"
                elements.append(Paragraph(section_title, heading2_style))

                # Préparer les données pour le tableau
                data = []
                ordered_attrs = []

                # Préparer les attributs avec leur ordre
                for key, value in attributs.items():
                    # Ignorer les clés commençant par "ordre_"
                    if not key.startswith('ordre_') and not key.startswith('label_'):
                        # Vérifier si la valeur est un dictionnaire avec une structure {valeur, ordre, label}
                        if isinstance(value, dict) and 'valeur' in value:
                            display_value = value['valeur']
                            order = value.get('ordre', 999)  # Utiliser 999 comme valeur par défaut
                            # Utiliser le label fourni dans le dictionnaire si disponible
                            display_key = value.get('label', key.replace('_', ' ').capitalize())
                            ordered_attrs.append((display_key, display_value, order))
                        else:
                            # Pour les anciens formats sans ordre ni label
                            display_key = key.replace('_', ' ').capitalize()
                            ordered_attrs.append((display_key, value, 999))

                # Trier les attributs par ordre
                ordered_attrs.sort(key=lambda x: x[2])

                # Créer les lignes du tableau en utilisant des paragraphes
                for display_key, value, _ in ordered_attrs:
                    # Utiliser create_paragraph pour permettre les retours à la ligne
                    data.append([display_key, create_paragraph(str(value), table_cell_style)])

                # Créer et styliser le tableau
                t = Table(data, colWidths=[4*cm, 10*cm])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]))

                elements.append(t)
                elements.append(Spacer(1, 0.5*cm))
        except Exception as e:
            # En cas d'erreur de parsing JSON, simplement ignorer cette section
            print(f"Erreur lors du traitement des attributs spécifiques: {e}")
            pass

    # Images supplémentaires
    if images:
        elements.append(Paragraph("Images supplémentaires", heading2_style))

        # Ajouter jusqu'à 3 images supplémentaires
        for i, image in enumerate(images[:3]):
            img_path = image['chemin']  # Le chemin est déjà complet
            if os.path.exists(img_path):
                img = Image(img_path, width=250, height=180, kind='proportional')
                elements.append(img)
                if image['legende']:
                    elements.append(Paragraph(f"<i>{image['legende']}</i>", normal_style))
                elements.append(Spacer(1, 0.5*cm))

    # Pied de page
    elements.append(Spacer(1, 1*cm))

    # Créer un style centré pour le pied de page
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Italic'],
        alignment=1  # 1 = centre, 0 = gauche, 2 = droite
    )

    elements.append(Paragraph(f"Fiche créée le {objet['date_ajout'][:10]}", footer_style))
    if objet['date_modification']:
        elements.append(Paragraph(f"Mise à jour le {objet['date_modification'][:10]}", footer_style))
    elements.append(Paragraph(f"Document généré le {datetime.now().strftime('%Y-%m-%d')}", footer_style))

    # Construire le document
    doc.build(elements, onFirstPage=on_first_page)

    # Réinitialiser la position du curseur au début du buffer
    buffer.seek(0)
    return buffer

def generate_cartel_pdf(objet):
    """
    Génère une étiquette (cartel) au format 15x10 cm pour un objet.
    
    Args:
        objet: Dictionnaire contenant les détails de l'objet
        
    Returns:
        Objet BytesIO contenant le PDF généré
    """
    buffer = io.BytesIO()
    
    # Dimensions du cartel : 15cm x 10cm
    cartel_size = (15*cm, 10*cm)
    
    # Marges réduites pour maximiser l'espace
    doc = SimpleDocTemplate(
        buffer,
        pagesize=cartel_size,
        leftMargin=1*cm,
        rightMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Styles personnalisés pour le cartel
    title_style = ParagraphStyle(
        'CartelTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=18,
        spaceAfter=6,
        textColor=colors.black,
        alignment=0 # Gauche
    )
    
    subtitle_style = ParagraphStyle(
        'CartelSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        spaceAfter=10,
        textColor=colors.darkgrey
    )
    
    body_style = ParagraphStyle(
        'CartelBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=8,
        alignment=4 # Justifié
    )
    
    specs_style = ParagraphStyle(
        'CartelSpecs',
        parent=styles['Normal'],
        fontSize=9,
        leading=10,
        textColor=colors.HexColor('#444444')
    )

    elements = []
    
    # 1. Nom de l'objet
    elements.append(Paragraph(objet['nom'], title_style))
    
    # 2. Fabricant et Année
    fabricant = objet['fabricant'] or "Fabricant inconnu"
    annee = objet['date_fabrication'] or "Année inconnue"
    elements.append(Paragraph(f"<b>{fabricant}</b> - {annee}", subtitle_style))
    
    # 3. Description (Complète)
    if objet['description']:
        elements.append(Paragraph(objet['description'], body_style))
    
    # 4. Caractéristiques techniques (Attributs spécifiques)
    if objet['attributs_specifiques']:
        try:
            attributs = json.loads(objet['attributs_specifiques'])
            specs_text = []
            
            # Récupération et tri des attributs comme dans la fiche principale
            ordered_attrs = []
            for key, value in attributs.items():
                if not key.startswith('ordre_') and not key.startswith('label_'):
                    if isinstance(value, dict) and 'valeur' in value:
                        display_value = value['valeur']
                        order = value.get('ordre', 999)
                        display_key = value.get('label', key.replace('_', ' ').capitalize())
                        ordered_attrs.append((display_key, display_value, order))
                    else:
                        display_key = key.replace('_', ' ').capitalize()
                        ordered_attrs.append((display_key, value, 999))
            
            ordered_attrs.sort(key=lambda x: x[2])
            
            # Construction de la chaîne de caractéristiques
            # On en prend quelques unes pour ne pas déborder
            for label, val, _ in ordered_attrs[:5]: # Max 5 caractéristiques
                specs_text.append(f"<b>{label}:</b> {val}")
                
            if specs_text:
                elements.append(Spacer(1, 0.2*cm))
                elements.append(Paragraph(" | ".join(specs_text), specs_style))
                
        except Exception:
            pass # Ignorer les erreurs de parsing ici
            
    doc.build(elements)
    buffer.seek(0)
    return buffer
