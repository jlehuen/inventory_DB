# scripts/login_security.py
# Module de sécurité pour la gestion des tentatives de connexion (version BD)

from datetime import datetime, timedelta
import logging
import sqlite3

# Configuration de la limite de tentatives de connexion
MAX_LOGIN_ATTEMPTS = 5  # Nombre maximum de tentatives
LOCKOUT_TIME = 15  # Durée de blocage en minutes

def init_security_db(get_db_connection):
    """
    Initialise la table des tentatives de connexion dans la base de données

    Args:
        get_db_connection: Fonction pour obtenir une connexion à la base de données
    """
    conn = get_db_connection()

    # Créer la table login_attempts si elle n'existe pas
    conn.execute('''
    CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        attempts INTEGER DEFAULT 1,
        locked_until TIMESTAMP,
        last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(username, ip_address)
    )
    ''')

    conn.commit()
    conn.close()

def get_login_attempt_key(username, request):
    """
    Crée une clé unique pour suivre les tentatives de connexion

    Args:
        username: Le nom d'utilisateur utilisé pour la tentative de connexion
        request: L'objet request Flask contenant l'adresse IP

    Returns:
        tuple: (username, ip_address)
    """
    ip = request.remote_addr
    return (username, ip)

def check_login_attempts(username, request, get_db_connection, logger=None):
    """
    Vérifie si l'utilisateur est autorisé à se connecter ou s'il est bloqué

    Args:
        username: Le nom d'utilisateur à vérifier
        request: L'objet request Flask
        get_db_connection: Fonction pour obtenir une connexion à la base de données
        logger: Instance de logger (optionnel)

    Returns:
        tuple: (autorisé, message d'erreur)
    """
    key = get_login_attempt_key(username, request)
    now = datetime.now()

    conn = get_db_connection()

    # Rechercher l'entrée pour cet utilisateur et cette IP
    query = """
    SELECT attempts, locked_until FROM login_attempts
    WHERE username = ? AND ip_address = ?
    """
    result = conn.execute(query, key).fetchone()
    conn.close()

    # Si aucune entrée trouvée, l'utilisateur est autorisé
    if not result:
        return True, None

    # Vérifier si l'utilisateur est bloqué
    if result['locked_until'] and datetime.fromisoformat(result['locked_until']) > now:
        locked_until = datetime.fromisoformat(result['locked_until'])
        remaining = (locked_until - now).total_seconds() // 60
        message = f"Compte temporairement bloqué. Réessayez dans {int(remaining)} minutes."

        if logger:
            logger.warning(f"Tentative de connexion bloquée pour {username}: {message}")

        return False, message

    # Si la période de blocage est terminée, on laisse passer (le compteur sera réinitialisé plus tard)
    return True, None

def increment_login_attempts(username, request, get_db_connection, logger=None):
    """
    Incrémente le compteur de tentatives de connexion pour un utilisateur
    Bloque l'utilisateur si le nombre maximum de tentatives est atteint

    Args:
        username: Le nom d'utilisateur à incrémenter
        request: L'objet request Flask
        get_db_connection: Fonction pour obtenir une connexion à la base de données
        logger: Instance de logger (optionnel)

    Returns:
        tuple: (est_bloqué, message)
    """
    key = get_login_attempt_key(username, request)
    now = datetime.now()

    conn = get_db_connection()

    # Vérifier si une entrée existe déjà pour cet utilisateur et cette IP
    query = """
    SELECT id, attempts, locked_until FROM login_attempts
    WHERE username = ? AND ip_address = ?
    """
    result = conn.execute(query, key).fetchone()

    if result:
        # Si une entrée existe et que le blocage est terminé, réinitialiser le compteur
        if result['locked_until'] and datetime.fromisoformat(result['locked_until']) <= now:
            update_query = """
            UPDATE login_attempts
            SET attempts = 1, locked_until = NULL, last_attempt = ?
            WHERE id = ?
            """
            conn.execute(update_query, (now.isoformat(), result['id']))
            attempts = 1
        else:
            # Sinon, incrémenter le compteur
            update_query = """
            UPDATE login_attempts
            SET attempts = attempts + 1, last_attempt = ?
            WHERE id = ?
            """
            conn.execute(update_query, (now.isoformat(), result['id']))
            attempts = result['attempts'] + 1
    else:
        # Si aucune entrée n'existe, en créer une nouvelle
        insert_query = """
        INSERT INTO login_attempts (username, ip_address, attempts, last_attempt)
        VALUES (?, ?, 1, ?)
        """
        conn.execute(insert_query, (username, key[1], now.isoformat()))
        attempts = 1

    if logger:
        logger.info(f"Tentative de connexion échouée pour {username} - Tentative #{attempts}")

    # Vérifier si l'utilisateur doit être bloqué
    if attempts >= MAX_LOGIN_ATTEMPTS:
        # Bloquer l'utilisateur pour la durée configurée
        locked_until = now + timedelta(minutes=LOCKOUT_TIME)

        update_query = """
        UPDATE login_attempts
        SET locked_until = ?
        WHERE username = ? AND ip_address = ?
        """
        conn.execute(update_query, (locked_until.isoformat(), username, key[1]))

        message = f"Trop de tentatives de connexion échouées. Compte bloqué pour {LOCKOUT_TIME} minutes."

        if logger:
            logger.warning(f"Compte {username} bloqué jusqu'à {locked_until}")

        conn.commit()
        conn.close()
        return True, message

    conn.commit()
    conn.close()

    remaining = MAX_LOGIN_ATTEMPTS - attempts
    return False, f"Mot de passe incorrect. Il vous reste {remaining} tentative(s)."

def reset_login_attempts(username, request, get_db_connection, logger=None):
    """
    Réinitialise le compteur de tentatives pour un utilisateur après connexion réussie

    Args:
        username: Le nom d'utilisateur à réinitialiser
        request: L'objet request Flask
        get_db_connection: Fonction pour obtenir une connexion à la base de données
        logger: Instance de logger (optionnel)
    """
    key = get_login_attempt_key(username, request)

    conn = get_db_connection()

    # Supprimer l'entrée pour cet utilisateur et cette IP
    delete_query = """
    DELETE FROM login_attempts
    WHERE username = ? AND ip_address = ?
    """
    conn.execute(delete_query, key)

    conn.commit()
    conn.close()

    if logger:
        logger.info(f"Compteur de tentatives réinitialisé pour {username} après connexion réussie")

def cleanup_old_attempts(get_db_connection, days=30, logger=None):
    """
    Nettoie les anciennes tentatives de connexion non bloquées

    Args:
        get_db_connection: Fonction pour obtenir une connexion à la base de données
        days: Nombre de jours après lesquels supprimer les tentatives (défaut: 30)
        logger: Instance de logger (optionnel)

    Returns:
        int: Nombre d'entrées supprimées
    """
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    conn = get_db_connection()

    # Supprimer les tentatives plus anciennes que la date limite et non bloquées
    delete_query = """
    DELETE FROM login_attempts
    WHERE last_attempt < ? AND (locked_until IS NULL OR locked_until < ?)
    """

    cursor = conn.execute(delete_query, (cutoff_date, datetime.now().isoformat()))
    deleted_count = cursor.rowcount

    conn.commit()
    conn.close()

    if logger and deleted_count > 0:
        logger.info(f"Nettoyage: {deleted_count} anciennes tentatives de connexion supprimées")

    return deleted_count

def get_login_attempts_status(get_db_connection):
    """
    Retourne l'état actuel des tentatives de connexion pour le débogage ou la surveillance

    Args:
        get_db_connection: Fonction pour obtenir une connexion à la base de données

    Returns:
        list: Liste des tentatives de connexion actuelles
    """
    conn = get_db_connection()
    now = datetime.now()

    query = """
    SELECT id, username, ip_address, attempts, locked_until, last_attempt
    FROM login_attempts
    ORDER BY last_attempt DESC
    """

    results = conn.execute(query).fetchall()
    conn.close()

    status = []
    for row in results:
        is_locked = False
        remaining_minutes = 0

        if row['locked_until']:
            locked_until = datetime.fromisoformat(row['locked_until'])
            is_locked = locked_until > now

            if is_locked:
                remaining_minutes = int((locked_until - now).total_seconds() // 60)

        status.append({
            'id': row['id'],
            'username': row['username'],
            'ip_address': row['ip_address'],
            'attempts': row['attempts'],
            'is_locked': is_locked,
            'remaining_minutes': remaining_minutes,
            'last_attempt': row['last_attempt']
        })

    return status
