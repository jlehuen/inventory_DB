import os

def nettoyer_fichiers(app, get_db_connection, allowed_extensions):
    """
    Fonction de nettoyage simplifiée qui retourne des informations claires et cohérentes.
    """
    logger = app.logger
    dossier_uploads = app.config['UPLOAD_FOLDER']

    # Résultat à retourner
    resultat = {
        'fichiers_supprimes': [],
        'espace_libere': 0,
        'erreurs': []
    }

    logger.info("=== DÉBUT DU NETTOYAGE ===")

    # Vérifier que le dossier existe
    if not os.path.exists(dossier_uploads):
        msg = f"Le dossier {dossier_uploads} n'existe pas."
        logger.error(msg)
        resultat['erreurs'].append(msg)
        return resultat

    try:
        # Étape 1: Récupérer tous les fichiers du dossier uploads
        fichiers_dossier = []
        for fichier in os.listdir(dossier_uploads):
            ext = fichier.split('.')[-1].lower() if '.' in fichier else ''
            if ext in allowed_extensions:
                fichiers_dossier.append(fichier)

        logger.info(f"Trouvé {len(fichiers_dossier)} fichiers dans le dossier uploads")

        # Étape 2: Récupérer les références de la base de données
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

        logger.info(f"Trouvé {len(fichiers_references)} fichiers référencés en base de données")

        # Étape 3: Identifier et supprimer les fichiers orphelins
        for fichier in fichiers_dossier:
            if fichier not in fichiers_references:
                logger.info(f"Fichier orphelin trouvé: {fichier}")

                # Supprimer le fichier
                chemin_complet = os.path.join(dossier_uploads, fichier)
                try:
                    if os.path.exists(chemin_complet):
                        # Obtenir la taille avant suppression
                        taille = os.path.getsize(chemin_complet)

                        # Supprimer le fichier
                        os.remove(chemin_complet)

                        # Enregistrer l'information
                        resultat['fichiers_supprimes'].append(fichier)
                        resultat['espace_libere'] += taille

                        logger.info(f"  => Supprimé: {fichier} ({formater_taille_fichier(taille)})")
                    else:
                        msg = f"Le fichier {chemin_complet} n'existe pas mais est listé comme orphelin"
                        logger.warning(msg)
                        resultat['erreurs'].append(msg)
                except Exception as e:
                    msg = f"Erreur lors de la suppression de {chemin_complet}: {str(e)}"
                    logger.error(msg)
                    resultat['erreurs'].append(msg)

        # Résumé du nettoyage
        nb_fichiers = len(resultat['fichiers_supprimes'])
        espace_libere = formater_taille_fichier(resultat['espace_libere'])
        logger.info(f"=== FIN DU NETTOYAGE: {nb_fichiers} fichiers supprimés, {espace_libere} libérés ===")

        return resultat

    except Exception as e:
        msg = f"Erreur générale lors du nettoyage: {str(e)}"
        logger.error(msg, exc_info=True)
        resultat['erreurs'].append(msg)
        return resultat


def formater_taille_fichier(octets):
    """
    Convertit une taille en octets en format lisible (KB, MB, etc.)
    """
    if octets < 1024:
        return f"{octets} octets"
    elif octets < 1024 * 1024:
        return f"{octets / 1024:.2f} KB"
    else:
        return f"{octets / (1024 * 1024):.2f} MB"
