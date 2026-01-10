import json
import sqlite3
import shutil
import os

# Configuration
DB_PATH = 'database/database.db'
JSON_PATH = 'static/categories.json'
BACKUP_JSON_PATH = 'static/categories.json.bak'

# Mapping singulier -> pluriel
MAPPING = {
    "Ordinateur": "Ordinateurs",
    "Console de jeu": "Consoles de jeu",
    "Périphérique": "Périphériques",
    "Calculatrice": "Calculatrices",
    "Stockage": "Stockages",
    "Livre": "Livres"
}

def migrate():
    print("--- Démarrage de la migration vers le pluriel ---")

    # 1. Sauvegarde du JSON
    if os.path.exists(JSON_PATH):
        shutil.copy(JSON_PATH, BACKUP_JSON_PATH)
        print(f"Sauvegarde créée : {BACKUP_JSON_PATH}")

    # 2. Lecture et transformation du JSON
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        new_data = {}
        for old_key, content in data.items():
            if old_key in MAPPING:
                new_key = MAPPING[old_key]
                print(f"JSON : Renommage '{old_key}' -> '{new_key}'")
                new_data[new_key] = content
            else:
                print(f"Attention : Pas de mapping pour '{old_key}', conservé tel quel.")
                new_data[old_key] = content
        
        # Écriture du nouveau JSON
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        print("Fichier static/categories.json mis à jour.")

    except Exception as e:
        print(f"Erreur lors du traitement JSON : {e}")
        return

    # 3. Mise à jour de la Base de Données
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for old_cat, new_cat in MAPPING.items():
            cursor.execute("SELECT count(*) FROM objets WHERE categorie = ?", (old_cat,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                cursor.execute("UPDATE objets SET categorie = ? WHERE categorie = ?", (new_cat, old_cat))
                print(f"DB : {count} objets mis à jour de '{old_cat}' vers '{new_cat}'")
            else:
                print(f"DB : Aucun objet trouvé pour '{old_cat}'")
        
        conn.commit()
        conn.close()
        print("Base de données mise à jour avec succès.")
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la base de données : {e}")
        # Restauration du JSON en cas d'erreur DB pour garder la cohérence
        shutil.copy(BACKUP_JSON_PATH, JSON_PATH)
        print("Restauration du fichier JSON effectuée suite à l'erreur.")

if __name__ == "__main__":
    migrate()
