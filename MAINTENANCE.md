# Maintenance et Déploiement - Inventaire CCNM

Ce guide regroupe les informations essentielles pour la gestion, la mise à jour et la maintenance du serveur.

## 🔗 Accès Rapides

- **URL du site** : [http://musee-ic2-demo/](http://musee-ic2-demo/)
- **Administration** :
  - **Identifiant** : `admin`
  - **Mot de passe** : `[VOIR_MEMOIRE_PRIVEE]`

  ## 🖥️ Accès Serveur (SSH)

  ```bash
  ssh collection@musee-ic2-demo
  # Mot de passe : [VOIR_MEMOIRE_PRIVEE]
  ```
---

## 🚀 Procédures de Déploiement

### 1. Mise à jour du code (Routine)
À exécuter depuis votre machine locale après avoir modifié des fichiers :

1. **Synchroniser les fichiers** :
   ```bash
   ./update_remote.sh
   ```
2. **Mettre à jour les dépendances** (si `requirements.txt` a été modifié) :
   ```bash
   ssh collection@musee-ic2-demo "sudo /www/inventaire_ccnm/venv/bin/pip install -r /www/inventaire_ccnm/requirements.txt"
   ```
3. **Appliquer les permissions et redémarrer** :
   ```bash
   ssh collection@musee-ic2-demo "sudo chown -R www-data:www-data /www/inventaire_ccnm && sudo systemctl restart inventaire"
   ```

### 2. Synchronisation des Données (DB & Images)
Pour envoyer votre base de données locale et vos images vers le serveur :

```bash
# Transfert via rsync
rsync -avz ./database/ root@musee-ic2-demo:/www/inventaire_ccnm/database/

# Rétablissement des droits et redémarrage
ssh root@musee-ic2-demo "chown -R www-data:www-data /www/inventaire_ccnm/database && chmod -R 775 /www/inventaire_ccnm/database && systemctl restart inventaire"
```

---

## 🛠️ Maintenance et Diagnostic

### Commandes Système (sur le serveur)
- **Vérifier le statut** : `sudo systemctl status inventaire`
- **Logs en temps réel** : `sudo journalctl -u inventaire.service -f`
- **Logs détaillés (50 dernières lignes)** : `sudo journalctl -u inventaire.service -n 50 --no-pager`
- **Redémarrage propre** :
  ```bash
  sudo systemctl stop inventaire
  sudo systemctl start inventaire
  ```
- **Vérification Nginx** : `sudo nginx -t`

### Réinitialisation du compte Admin
Si le mot de passe admin du site ne fonctionne plus, forcez la mise à jour depuis le `.env` :
```bash
ssh root@musee-ic2-demo "cd /www/inventaire_ccnm && source venv/bin/activate && python3 -c 'from app import create_admin_user; create_admin_user()'"
```

### Console Python (venv)
```bash
cd /www/inventaire_ccnm
source venv/bin/activate
python
```

---

## 📦 Archivage Git
Pour sauvegarder vos changements locaux sur GitHub :
```bash
git add .
git commit -m "Description de vos modifications"
git push origin main
```
