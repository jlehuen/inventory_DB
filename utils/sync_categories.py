#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de synchronisation entre categories.json et la base de données SQLite
Ce script permet de maintenir la cohérence des données après des modifications
dans la structure des catégories ou des attributs spécifiques.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('sync_categories.log'),
		logging.StreamHandler()
	]
)
logger = logging.getLogger('sync_categories')

# Constantes et configuration
DB_PATH = 'database/database.db'
JSON_PATH = 'static/categories.json'

def get_db_connection():
	"""Établit une connexion à la base de données SQLite"""
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	return conn

def load_categories_json():
	"""Charge les définitions de catégories depuis le fichier JSON"""
	try:
		with open(JSON_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)
	except Exception as e:
		logger.error(f"Erreur lors du chargement du fichier JSON: {e}")
		return {}

def get_all_objects():
	"""Récupère tous les objets de la base de données"""
	conn = get_db_connection()
	try:
		objets = conn.execute('SELECT id, nom, categorie, attributs_specifiques FROM objets').fetchall()
		return [dict(obj) for obj in objets]
	except Exception as e:
		logger.error(f"Erreur lors de la récupération des objets: {e}")
		return []
	finally:
		conn.close()

def update_object(obj_id, attributs_json, modification_date=None):
	"""Met à jour les attributs spécifiques d'un objet"""
	conn = get_db_connection()
	try:
		if modification_date is None:
			modification_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		
		conn.execute(
			'UPDATE objets SET attributs_specifiques = ?, date_modification = ? WHERE id = ?',
			(attributs_json, modification_date, obj_id)
		)
		conn.commit()
		return True
	except Exception as e:
		logger.error(f"Erreur lors de la mise à jour de l'objet {obj_id}: {e}")
		return False
	finally:
		conn.close()

def synchronize_category_names(categories_data, simulate=True):
	"""
	Synchronise les noms de catégories entre le JSON et la base de données
	
	Args:
		categories_data: Données des catégories depuis le JSON
		simulate: Si True, simule les changements sans les appliquer
	
	Returns:
		dict: Statistiques sur les opérations effectuées
	"""
	stats = {"renames": 0, "processed": 0, "errors": 0}
	objects = get_all_objects()
	
	# Dictionnaire des anciennes et nouvelles catégories
	# À personnaliser selon vos besoins de renommage
	category_mapping = {
		# 'Ancien nom': 'Nouveau nom',
		# Par exemple:
		# 'Appareil photo': 'Photographie',
	}
	
	if not category_mapping:
		logger.info("Aucun mappage de catégories défini, étape ignorée.")
		return stats
	
	for obj in objects:
		stats["processed"] += 1
		old_category = obj['categorie']
		
		if old_category in category_mapping:
			new_category = category_mapping[old_category]
			logger.info(f"Objet {obj['id']} ({obj['nom']}): Catégorie '{old_category}' → '{new_category}'")
			
			if not simulate:
				conn = get_db_connection()
				try:
					conn.execute(
						'UPDATE objets SET categorie = ?, date_modification = ? WHERE id = ?',
						(new_category, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), obj['id'])
					)
					conn.commit()
					stats["renames"] += 1
				except Exception as e:
					logger.error(f"Erreur lors de la mise à jour de la catégorie de l'objet {obj['id']}: {e}")
					stats["errors"] += 1
				finally:
					conn.close()
			else:
				stats["renames"] += 1
	
	return stats

def synchronize_attributes(categories_data, simulate=True):
	"""
	Synchronise les attributs spécifiques entre le JSON et la base de données
	et corrige les attributs mal formatés
	"""
	stats = {"updated": 0, "processed": 0, "errors": 0, "unchanged": 0, "fixed_format": 0}
	objects = get_all_objects()
	
	for obj in objects:
		stats["processed"] += 1
		
		# Ignorer si la catégorie n'existe pas dans le JSON ou si elle n'a pas d'attributs définis
		if obj['categorie'] not in categories_data or 'attributes' not in categories_data[obj['categorie']]:
			continue
		
		# Récupérer les attributs définis pour cette catégorie
		category_attributes = {attr['id']: attr for attr in categories_data[obj['categorie']]['attributes']}
		
		# Charger les attributs existants de l'objet
		current_attributes = {}
		if obj['attributs_specifiques']:
			try:
				current_attributes = json.loads(obj['attributs_specifiques'])
			except json.JSONDecodeError:
				logger.error(f"Erreur de décodage JSON pour l'objet {obj['id']}")
				stats["errors"] += 1
				continue
		
		# Initialiser les attributs mis à jour avec les valeurs actuelles
		updated_attributes = {}
		changes_made = False
		
		# Parcourir les attributs existants et les adapter au nouveau format si nécessaire
		for key, value in current_attributes.items():
			# Ignorer les clés techniques
			if key.startswith('ordre_') or key.startswith('label_'):
				continue
				
			# SOLUTION GÉNÉRIQUE : Vérifier si l'attribut a un format incorrect
			# Cela inclut les objets qui se convertissent en "[object Object]"
			if isinstance(value, dict) and not 'valeur' in value:
				logger.info(f"Format incorrect détecté pour l'attribut '{key}' de l'objet {obj['id']} ({obj['nom']})")
				
				# Récupérer ordre et label depuis la définition si disponible
				attr_ordre = 999
				attr_label = key.replace('_', ' ').capitalize()
				
				if key in category_attributes:
					attr_def = category_attributes[key]
					attr_ordre = attr_def.get('ordre', 999)
					attr_label = attr_def.get('label', attr_label)
				
				# Corriger le format avec une valeur vide
				updated_attributes[key] = {
					'valeur': '',
					'ordre': attr_ordre,
					'label': attr_label
				}
				changes_made = True
				stats["fixed_format"] += 1
				continue
			
			# Traitement normal pour les attributs avec un format correct
			if key in category_attributes:
				attr_def = category_attributes[key]
				
				if isinstance(value, dict) and 'valeur' in value:
					# Mettre à jour l'ordre et le label si nécessaire
					if value.get('ordre') != attr_def.get('ordre') or value.get('label') != attr_def.get('label'):
						updated_value = value.copy()
						updated_value['ordre'] = attr_def.get('ordre', 999)
						updated_value['label'] = attr_def.get('label', key.replace('_', ' ').capitalize())
						updated_attributes[key] = updated_value
						changes_made = True
					else:
						# Conserver tel quel
						updated_attributes[key] = value
				else:
					# Convertir l'ancien format au nouveau format
					updated_attributes[key] = {
						'valeur': value,
						'ordre': attr_def.get('ordre', 999),
						'label': attr_def.get('label', key.replace('_', ' ').capitalize())
					}
					changes_made = True
			else:
				# L'attribut n'existe plus dans la définition mais on préserve sa valeur
				if isinstance(value, dict) and 'valeur' in value:
					updated_attributes[key] = value
				else:
					updated_attributes[key] = {
						'valeur': value,
						'ordre': 999,
						'label': key.replace('_', ' ').capitalize()
					}
					changes_made = True
		
		# Décommentons cette partie pour ajouter automatiquement des champs vides 
		# pour les nouveaux attributs définis dans le JSON
		for attr_id, attr_def in category_attributes.items():
			if attr_id not in updated_attributes:
				updated_attributes[attr_id] = {
					'valeur': '',
					'ordre': attr_def.get('ordre', 999),
					'label': attr_def.get('label', attr_id.replace('_', ' ').capitalize())
				}
				changes_made = True
				logger.info(f"Ajout du nouvel attribut '{attr_id}' avec le format correct")
		
		# Enregistrer les modifications si nécessaire
		if changes_made:
			logger.info(f"Mise à jour des attributs pour l'objet {obj['id']} ({obj['nom']})")
			
			if not simulate:
				attributs_json = json.dumps(updated_attributes)
				success = update_object(obj['id'], attributs_json)
				if success:
					stats["updated"] += 1
				else:
					stats["errors"] += 1
			else:
				stats["updated"] += 1
		else:
			stats["unchanged"] += 1
	
	return stats

def main():
	"""Fonction principale du script"""
	logger.info("Démarrage de la synchronisation categories.json → base de données")
	
	# Vérifier l'existence des fichiers
	if not os.path.exists(DB_PATH):
		logger.error(f"Base de données introuvable: {DB_PATH}")
		return
	
	if not os.path.exists(JSON_PATH):
		logger.error(f"Fichier JSON introuvable: {JSON_PATH}")
		return
	
	# Charger les données
	categories_data = load_categories_json()
	if not categories_data:
		logger.error("Impossible de charger les données des catégories")
		return
	
	# Mode simulation par défaut (changer à False pour appliquer les modifications)
	SIMULATION = True
	mode = "SIMULATION" if SIMULATION else "PRODUCTION"
	logger.info(f"Mode: {mode}")
	
	# Synchroniser les noms de catégories si nécessaire
	# (décommenter pour activer)
	# cat_stats = synchronize_category_names(categories_data, simulate=SIMULATION)
	# logger.info(f"Synchronisation des catégories: {cat_stats['renames']}/{cat_stats['processed']} renommées, {cat_stats['errors']} erreurs")
	
	# Synchroniser les attributs
	attr_stats = synchronize_attributes(categories_data, simulate=SIMULATION)
	logger.info(f"Synchronisation des attributs: {attr_stats['updated']}/{attr_stats['processed']} mis à jour, {attr_stats['unchanged']} inchangés, {attr_stats['errors']} erreurs")
	logger.info(f"Attributs avec format incorrect corrigés: {attr_stats['fixed_format']}")
	
	logger.info(f"Synchronisation terminée ({mode})")
	
	if SIMULATION:
		logger.info("Pour appliquer les modifications, modifiez la variable SIMULATION à False")

if __name__ == "__main__":
	main()