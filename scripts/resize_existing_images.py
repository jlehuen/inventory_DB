"""
Script de redimensionnement et d'optimisation des images existantes.

Ce script parcourt le dossier des uploads et optimise les images qui n'ont pas
été traitées lors de leur téléchargement initial.
"""

import os
import logging
from PIL import Image

# Configuration
UPLOAD_FOLDER = 'database/uploads'
MAX_SIZE = (1600, 1600)  # Taille maximale (largeur, hauteur)
JPEG_QUALITY = 85        # Qualité JPEG (0-100)

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def resize_and_optimize(filepath):
    """
    Redimensionne et optimise une image donnée.
    """
    try:
        with Image.open(filepath) as img:
            # Vérifier si l'image a besoin d'être redimensionnée
            if img.width > MAX_SIZE[0] or img.height > MAX_SIZE[1]:
                logger.info(f"Redimensionnement de {os.path.basename(filepath)} ({img.width}x{img.height})")
                img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
            else:
                # Même si la taille est bonne, on veut peut-être ré-enregistrer pour la compression
                pass

            # Conversion en RGB si nécessaire (pour éviter les erreurs avec les JPEG)
            if img.mode in ('RGBA', 'P') and filepath.lower().endswith(('.jpg', '.jpeg')):
                img = img.convert('RGB')

            # Sauvegarde avec optimisation
            # On conserve le format original sauf si on force autre chose
            img.save(filepath, optimize=True, quality=JPEG_QUALITY)
            logger.info(f"Optimisé : {os.path.basename(filepath)}")
            return True

    except Exception as e:
        logger.error(f"Erreur sur {filepath}: {e}")
        return False

def main():
    """Fonction principale exécutant l'optimisation des images."""
    if not os.path.exists(UPLOAD_FOLDER):
        logger.error(f"Le dossier {UPLOAD_FOLDER} n'existe pas.")
        return

    count = 0
    total_space_saved = 0

    logger.info("Démarrage de l'optimisation des images...")

    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Ignorer les fichiers cachés et non-images
        if filename.startswith('.') or not os.path.isfile(filepath):
            continue
            
        ext = filename.lower().split('.')[-1]
        if ext not in ['jpg', 'jpeg', 'png']:
            continue

        original_size = os.path.getsize(filepath)
        
        if resize_and_optimize(filepath):
            new_size = os.path.getsize(filepath)
            saved = original_size - new_size
            total_space_saved += saved
            count += 1
            if saved > 0:
                logger.info(f"Gain: {saved / 1024:.2f} KB")

    logger.info(f"Terminé. {count} images traitées.")
    logger.info(f"Espace total libéré : {total_space_saved / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
