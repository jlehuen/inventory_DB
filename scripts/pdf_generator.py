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

def generate_object_pdf(objet, images, liens, base_url, lang='fr'):
    """
    Génère un fichier PDF pour un objet du catalogue avec ses détails et images

    Args:
        objet: Dictionnaire contenant les détails de l'objet
        images: Liste des images associées à l'objet
        liens: Liste des liens (informations) associés à l'objet
        base_url: URL de base pour construire les chemins complets des images
        lang: Langue du PDF ('fr' ou 'en')

    Returns:
        Objet BytesIO contenant le PDF généré
    """
    # Traductions statiques
    trans = {
        'fr': {
            'header': "Inventaire CCNM - Fiche descriptive",
            'title_prefix': "CCNM - Centre Culturel sur le Numérique du Mans",
            'subtitle': "Collection de micro-ordinateurs et de dispositifs numériques",
            'desc_title': "Description",
            'general_data': "Données générales",
            'cat': "Catégorie",
            'model': "Modèle",
            'title': "Titre",
            'mfr': "Fabricant",
            'pub': "Éditeur",
            'year': "Année de sortie",
            'year_pub': "Année d'édition",
            'infos': "Informations",
            'state': "État de l'objet",
            'number': "Numéro",
            'biblio': "Informations bibliographiques",
            'tech': "Caractéristiques techniques",
            'images': "Images supplémentaires",
            'created': "Fiche créée le",
            'updated': "Mise à jour le",
            'generated': "Document généré le",
            'no_spec': "Non spécifiée"
        },
        'en': {
            'header': "CCNM Inventory - Descriptive Sheet",
            'title_prefix': "CCNM - Cultural Center for Digital Heritage of Le Mans",
            'subtitle': "Collection of microcomputers and digital devices",
            'desc_title': "Description",
            'general_data': "General Data",
            'cat': "Category",
            'model': "Model",
            'title': "Title",
            'mfr': "Manufacturer",
            'pub': "Publisher",
            'year': "Release Year",
            'year_pub': "Edition Year",
            'infos': "Information",
            'state': "Object Condition",
            'number': "Inventory Number",
            'biblio': "Bibliographic Information",
            'tech': "Technical Specifications",
            'images': "Additional Images",
            'created': "Created on",
            'updated': "Updated on",
            'generated': "Document generated on",
            'no_spec': "Not specified"
        }
    }
    
    t = trans.get(lang, trans['fr'])
    
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

    # Fonction callback pour dessiner le QR Code et le copyright
    def draw_footer_and_header(canvas, doc, is_first_page=True):
        canvas.saveState()
        
        # Titre header (uniquement sur la première page)
        if is_first_page:
            canvas.setFont('Helvetica-Oblique', 9)
            canvas.setFillColor(colors.grey)
            canvas.drawString(2*cm, A4[1] - 1.5*cm, t['header'])
            
            if qr_buffer:
                # Positionnement en haut à droite
                qr_size = 3*cm
                x_pos = A4[0] - qr_size - 1*cm
                y_pos = A4[1] - qr_size - 1*cm
                
                canvas.drawImage(ImageReader(qr_buffer), x_pos, y_pos, width=qr_size, height=qr_size)
                
                # Ajouter l'URL en texte sous le QR code
                canvas.setFont('Helvetica', 8)
                canvas.drawCentredString(x_pos + qr_size/2, y_pos - 10, f"ID: {objet['id']}")
        
        # Mention de copyright en bas à droite (sur toutes les pages)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 2*cm, 1*cm, "© Musée Martial Vivet, Le Mans Université")
            
        canvas.restoreState()

    def on_first_page(canvas, doc):
        draw_footer_and_header(canvas, doc, is_first_page=True)

    def on_later_pages(canvas, doc):
        draw_footer_and_header(canvas, doc, is_first_page=False)

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
    elements.append(Paragraph(t['title_prefix'], styles['Heading3']))
    elements.append(Paragraph(t['subtitle'], styles['Italic']))
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

    # Description (choix de la langue)
    description = objet['description']
    if lang == 'en' and 'description_en' in objet.keys() and objet['description_en']:
        description = objet['description_en']

    if description:
        elements.append(Paragraph(t['desc_title'], heading2_style))
        elements.append(create_paragraph(description, normal_style))
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
    elements.append(Paragraph(t['general_data'], heading2_style))

    # Adapter les libellés selon la catégorie (comme sur la vue HTML)
    is_book_or_soft = objet['categorie'] in ['Livres', 'Logiciels']
    label_nom = (t['title'] if objet['categorie'] == 'Livres' else "Nom du logiciel") if is_book_or_soft else t['model']
    label_fabricant = t['pub'] if is_book_or_soft else t['mfr']
    label_annee = (t['year_pub'] if objet['categorie'] == 'Livres' else "Année de sortie / copyright") if is_book_or_soft else t['year']

    # Utiliser des paragraphes pour toutes les cellules de données
    data = [
        [t['cat'], create_paragraph(objet['categorie'] or t['no_spec'], table_cell_style)],
        [label_nom, create_paragraph(objet['nom'], table_cell_style)],
        [label_fabricant, create_paragraph(objet['fabricant'] or t['no_spec'], table_cell_style)],
        [label_annee, create_paragraph(objet['date_fabrication'] or t['no_spec'], table_cell_style)],
        [t['infos'], links_cell_content],
        [t['state'], create_paragraph(objet['etat'] or t['no_spec'], table_cell_style)],
        [t['number'], create_paragraph(objet['numero_inventaire'] or t['no_spec'], table_cell_style)]
    ]

    t_table = Table(data, colWidths=[4*cm, 10*cm])
    t_table.setStyle(TableStyle([
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

    elements.append(t_table)
    elements.append(Spacer(1, 0.5*cm))

    # Ajouter les attributs spécifiques s'ils existent
    if objet['attributs_specifiques']:
        try:
            attributs = json.loads(objet['attributs_specifiques'])

            if attributs:
                # Titre de section adapté à la catégorie
                section_title = t['biblio'] if objet['categorie'] == 'Livres' else (t['tech'] if objet['categorie'] != 'Logiciels' else "Informations détaillées")
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
                t_table_spec = Table(data, colWidths=[4*cm, 10*cm])
                t_table_spec.setStyle(TableStyle([
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

                elements.append(t_table_spec)
                elements.append(Spacer(1, 0.5*cm))
        except Exception as e:
            # En cas d'erreur de parsing JSON, simplement ignorer cette section
            print(f"Erreur lors du traitement des attributs spécifiques: {e}")
            pass

    # Images supplémentaires
    if images:
        elements.append(Paragraph(t['images'], heading2_style))

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

    if objet['date_ajout']:
        elements.append(Paragraph(f"{t['created']} {objet['date_ajout'][:10]}", footer_style))
    
    if objet['date_modification']:
        elements.append(Paragraph(f"{t['updated']} {objet['date_modification'][:10]}", footer_style))
    
    elements.append(Paragraph(f"{t['generated']} {datetime.now().strftime('%Y-%m-%d')}", footer_style))

    # Construire le document
    doc.build(elements, onFirstPage=on_first_page, onLaterPages=on_later_pages)

    # Réinitialiser la position du curseur au début du buffer
    buffer.seek(0)
    return buffer


def generate_cartel_pdf(objet, base_url, lang='fr'):
    """
    Génère une étiquette (cartel) au format 15x10 cm pour un objet.
    
    Args:
        objet: Dictionnaire contenant les détails de l'objet
        base_url: URL de base pour le QR code
        lang: Langue du cartel ('fr' ou 'en')
        
    Returns:
        Objet BytesIO contenant le PDF généré
    """
    # Traductions statiques
    trans = {
        'fr': {
            'unknown_mfr': "Fabricant inconnu",
            'unknown_year': "Année inconnue"
        },
        'en': {
            'unknown_mfr': "Unknown Manufacturer",
            'unknown_year': "Unknown Year"
        }
    }
    t_lang = trans.get(lang, trans['fr'])

    buffer = io.BytesIO()
    
    # Génération du QR Code
    qr_buffer = io.BytesIO()
    try:
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
        print(f"Erreur génération QR Code cartel: {e}")
        qr_buffer = None

    # Dimensions du cartel : 15cm x 10cm
    cartel_size = (15*cm, 10*cm)
    
    # Callback pour dessiner le QR Code
    def on_cartel_page(canvas, doc):
        canvas.saveState()
        if qr_buffer:
            # Positionnement en haut à droite
            qr_size = 2.2*cm
            # Marges doc = 0.5cm. On le place dans le coin en haut à droite de la zone contenu
            # x = largeur page - marge droite - taille QR
            x_pos = 15*cm - 0.5*cm - qr_size
            # y = hauteur page - marge haut - taille QR
            y_pos = 10*cm - 0.5*cm - qr_size + 0.2*cm # Un petit ajustement vers le haut pour aligner avec le titre
            
            canvas.drawImage(ImageReader(qr_buffer), x_pos, y_pos, width=qr_size, height=qr_size)
            
        # Mention de copyright en bas à droite
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(15*cm - 0.5*cm, 0.3*cm, "© Musée Martial Vivet, Le Mans Université")
        
        # Traits de coupe (Corners) et bordure de découpe
        canvas.setStrokeColor(colors.lightgrey)
        canvas.setLineWidth(0.2)
        # Bordure complète très discrète
        canvas.rect(0, 0, 15*cm, 10*cm)
        
        # Traits de coupe plus marqués aux angles
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.5)
        d = 0.5*cm # Longueur du trait
        
        # Bas-Gauche
        canvas.line(0, 0, d, 0)
        canvas.line(0, 0, 0, d)
        # Bas-Droite
        canvas.line(15*cm, 0, 15*cm - d, 0)
        canvas.line(15*cm, 0, 15*cm, d)
        # Haut-Gauche
        canvas.line(0, 10*cm, d, 10*cm)
        canvas.line(0, 10*cm, 0, 10*cm - d)
        # Haut-Droite
        canvas.line(15*cm, 10*cm, 15*cm - d, 10*cm)
        canvas.line(15*cm, 10*cm, 15*cm, 10*cm - d)
        
        canvas.restoreState()

    # Marges réduites pour maximiser l'espace
    doc = SimpleDocTemplate(
        buffer,
        pagesize=cartel_size,
        leftMargin=0.5*cm,
        rightMargin=0.5*cm,
        topMargin=0.5*cm,
        bottomMargin=0.5*cm
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
        alignment=0, # Gauche
        rightIndent=2.5*cm # Laisser de la place pour le QR code
    )
    
    subtitle_style = ParagraphStyle(
        'CartelSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        spaceAfter=10,
        textColor=colors.darkgrey,
        rightIndent=2.5*cm # Laisser de la place pour le QR code aussi ici si besoin
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
    fabricant = objet['fabricant'] or t_lang['unknown_mfr']
    annee = objet['date_fabrication'] or t_lang['unknown_year']
    elements.append(Paragraph(f"<b>{fabricant}</b> ({annee})", subtitle_style))
    
    # 3. Description (Complète) - Choix de la langue
    description = objet['description']
    if lang == 'en' and 'description_en' in objet.keys() and objet['description_en']:
        description = objet['description_en']

    if description:
        elements.append(Paragraph(description, body_style))
    
    # 4. Caractéristiques techniques (Attributs spécifiques)
    if objet['attributs_specifiques']:
        try:
            attributs = json.loads(objet['attributs_specifiques'])
            
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
            
            # Construction du tableau de caractéristiques
            table_data = []
            
            # Construction des lignes du tableau (Max 6 pour ne pas déborder du cartel 10cm)
            for label, val, _ in ordered_attrs[:6]:
                table_data.append([
                    Paragraph(f"<b>{label}</b>", specs_style),
                    Paragraph(str(val), specs_style)
                ])
                
            if table_data:
                elements.append(Spacer(1, 0.3*cm))
                
                # Largeur totale disponible = 15cm (page) - 1cm (marges G+D) = 14cm
                # Répartition : 4.5cm pour le libellé, 9.5cm pour la valeur
                col_widths = [4.5*cm, 9.5*cm]
                
                t_table = Table(table_data, colWidths=col_widths)
                t_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 1),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke), # Optionnel : léger gris pour la colonne titre pour plus de lisibilité
                ]))
                elements.append(t_table)
                
        except Exception as e:
            print(f"Erreur rendu caractéristiques cartel : {e}")
            pass # Ignorer les erreurs de parsing ici
            
    doc.build(elements, onFirstPage=on_cartel_page)
    buffer.seek(0)
    return buffer


def generate_qr_only_pdf(objet, base_url):
    """
    Génère une étiquette carrée (5x5 cm) contenant uniquement le QR code de l'objet.
    
    Args:
        objet: Dictionnaire contenant les détails de l'objet
        base_url: URL de base pour le QR code
        
    Returns:
        Objet BytesIO contenant le PDF généré
    """
    buffer = io.BytesIO()
    
    # Génération du QR Code
    qr_buffer = io.BytesIO()
    try:
        clean_base_url = base_url.rstrip('/')
        object_url = f"{clean_base_url}/objet/{objet['id']}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M, # Correction moyenne pour plus de robustesse
            box_size=10,
            border=2, # Bordure réduite pour maximiser la taille du QR
        )
        qr.add_data(object_url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
    except Exception as e:
        print(f"Erreur génération QR Code seul: {e}")
        qr_buffer = None

    # Dimensions de l'étiquette : 5cm x 5cm
    label_size = (5*cm, 5*cm)
    
    # Créer le document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=label_size,
        leftMargin=0.2*cm,
        rightMargin=0.2*cm,
        topMargin=0.2*cm,
        bottomMargin=0.2*cm
    )
    
    def on_qr_page(canvas, doc):
        canvas.saveState()
        if qr_buffer:
            # QR code prend presque toute la place
            qr_size = 4.4*cm
            x_pos = (5*cm - qr_size) / 2
            y_pos = (5*cm - qr_size) / 2 + 0.2*cm # Un peu plus haut pour laisser de la place au texte en bas
            
            canvas.drawImage(ImageReader(qr_buffer), x_pos, y_pos, width=qr_size, height=qr_size)
            
            # ID de l'objet en bas
            canvas.setFont('Helvetica-Bold', 7)
            canvas.drawCentredString(2.5*cm, 0.3*cm, f"INV: {objet['numero_inventaire']}")
        
        # Bordure de découpe discrète
        canvas.setStrokeColor(colors.lightgrey)
        canvas.setLineWidth(0.1)
        canvas.rect(0, 0, 5*cm, 5*cm)
        
        canvas.restoreState()

    # Le document est vide de "Platypus elements", on dessine tout dans le callback
    doc.build([Spacer(1, 1)], onFirstPage=on_qr_page)
    buffer.seek(0)
    return buffer
