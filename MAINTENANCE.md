# 📘 Guide de Maintenance & Déploiement - Inventaire CCNM

Ce guide est un tutoriel pas-à-pas pour gérer l'application, du développement local jusqu'à la mise en ligne sur le serveur de l'Université.

## 🔐 1. Informations d'Accès (Privé)

| Service | Accès / URL | Identifiants |
| :--- | :--- | :--- |
| **Site Web** | [http://musee-ic2-demo/](http://musee-ic2-demo/) | `admin` / `[VOIR_MEMOIRE_PRIVEE]` |
| **Serveur (SSH)** | `ssh collection@musee-ic2-demo` | Mot de passe : `[VOIR_MEMOIRE_PRIVEE]` |
| **Dépôt Git** | `github.com:jlehuen/inventory_DB.git` | Via clé SSH |

## 💻 2. Cycle de Développement (Local)

Avant de déployer, assurez-vous que vos modifications sont sauvegardées sur GitHub.

### Sauvegarder sur GitHub
```bash
git add .
git commit -m "Description de vos changements"
git push origin main
```

---

## 🚀 3. Procédure de Déploiement

### A. Installation Initiale (Nouveau Serveur)
À ne faire qu'une seule fois si vous installez l'application sur un nouveau serveur :


```bash
scp install_ic2.sh collection@musee-ic2-demo:~/  # Copier le script d'installation
ssh collection@musee-ic2-demo                    # Se connecter au serveur
sudo bash install_ic2.sh                         # Lancer le script
```
*Note : Le script vous demandera de définir le mot de passe de l'administrateur.*

### B. Mise à jour du code (Routine)

C'est la procédure standard pour mettre en ligne vos modifications de code régulières.


```bash
# Envoyer les fichiers vers le serveur
./update_remote.sh  

# Mettre à jour les dépendances si le fichier requirements.txt a été modifié
ssh collection@musee-ic2-demo "sudo /www/inventaire_ccnm/venv/bin/pip install -r /www/inventaire_ccnm/requirements.txt" 

# Appliquer les permissions et redémarrer le service (indispensable)
ssh collection@musee-ic2-demo "sudo chown -R www-data:www-data /www/inventaire_ccnm && sudo systemctl restart inventaire"
```

---

## 📂 4. Synchronisation des Données (Base de données & Images)

Si vous avez ajouté des objets ou des photos **localement** et que vous souhaitez les envoyer sur le serveur de production.

```bash
# Envoyer les dossiers vers le serveur
rsync -avz ./database/ root@musee-ic2-demo:/www/inventaire_ccnm/database/

# Rétablir les droits et redémarrer le service sur le serveur
ssh root@musee-ic2-demo "chown -R www-data:www-data /www/inventaire_ccnm/database && chmod -R 775 /www/inventaire_ccnm/database && systemctl restart inventaire"
```

---

## 🛠️ 5. Résolution de Problèmes (FAQ)

### Le service de traduction ne fonctionne pas ?
L'application doit passer par le proxy de l'université. Vérifiez que le fichier `.env` sur le serveur contient les lignes suivantes :

```bash
HTTP_PROXY=http://proxy.univ-lemans.fr:3128/
HTTPS_PROXY=http://proxy.univ-lemans.fr:3128/
```

### Mot de passe Admin oublié ou incorrect ?
Vous pouvez forcer la réinitialisation du compte `admin` avec les identifiants définis dans votre fichier `.env` sur le serveur :

```bash
ssh root@musee-ic2-demo "cd /www/inventaire_ccnm && source venv/bin/activate && python3 -c 'from app import create_admin_user; create_admin_user()'"
```

### Le site affiche "502 Bad Gateway" ?
Cela signifie que le serveur Gunicorn ne répond plus. Tentez un redémarrage forcé :

```bash
ssh collection@musee-ic2-demo "sudo systemctl stop inventaire && sudo systemctl start inventaire"
```

## 🔍 6. Commandes de Diagnostic (Sur le serveur)

### Vérifier l'état du service
```bash
sudo systemctl status inventaire
```

### Consulter les logs en temps réel
```bash
sudo journalctl -u inventaire.service -f
```

### Tester la configuration du serveur Web (Nginx)
```bash
sudo nginx -t
```

### Ouvrir une console Python dans l'environnement du projet
```bash
cd /www/inventaire_ccnm
source venv/bin/activate
python
```
