#!/bin/bash

# Script pour automatiser le push vers GitHub
# Usage: ./push.sh "Votre message de commit"

# Vérifier si un message est fourni, sinon en demander un
if [ -z "$1" ]; then
    read -p "Message de commit : " MESSAGE
    if [ -z "$MESSAGE" ]; then
        MESSAGE="Mise à jour automatique le $(date +'%d/%m/%Y %H:%M')"
    fi
else
    MESSAGE="$1"
fi

echo "🚀 Préparation du push..."
git add .

echo "📝 Création du commit : $MESSAGE"
git commit -m "$MESSAGE"

echo "📤 Envoi vers GitHub (branche main)..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Terminé avec succès !"
else
    echo "❌ Une erreur est survenue lors du push."
fi
