// icon-enhancer.js - Améliore les icônes de catégories et ajoute des animations subtiles

document.addEventListener('DOMContentLoaded', function() {
    // Chargement des icônes depuis le fichier JSON
    loadCategoryIcons();

    // Animer les icônes dans les boutons au survol
    const actionButtons = document.querySelectorAll('.btn, .btn-small');
    actionButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            const icon = this.querySelector('i');
            if (icon) {
                icon.style.transition = 'transform 0.3s ease';
                icon.style.transform = 'scale(1.2)';
            }
        });

        button.addEventListener('mouseleave', function() {
            const icon = this.querySelector('i');
            if (icon) {
                icon.style.transform = 'scale(1)';
            }
        });
    });

    // Améliorer le tableau d'administration
    enhanceAdminTable();

    // Améliorer les messages flash
    enhanceFlashMessages();

    // Ajouter des indications de chargement pour les actions importantes
    addLoadingIndicators();
});

// Fonction pour charger les icônes depuis le JSON
function loadCategoryIcons() {
    fetch('/static/categories.json')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Appliquer les icônes personnalisées aux cartes de catégorie
            const categorieCards = document.querySelectorAll('.categorie-card');
            categorieCards.forEach(card => {
                const categoryTitle = card.querySelector('h2')?.textContent.trim();
                const iconElement = card.querySelector('.categorie-icon i');

                if (iconElement && categoryTitle && data[categoryTitle] && data[categoryTitle].icon) {
                    // Remplacer l'icône par défaut par l'icône personnalisée
                    iconElement.className = `fas ${data[categoryTitle].icon}`;
                }
            });
        })
        .catch(error => {
            console.error("Erreur lors du chargement des icônes de catégories:", error);
        });
}

// Améliorer l'apparence et le comportement des tableaux administratifs
function enhanceAdminTable() {
    const adminTables = document.querySelectorAll('.admin-table');

    adminTables.forEach(table => {
        // Ajouter une classe zebra-stripe pour alterner les couleurs des lignes
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach((row, index) => {
            if (index % 2 === 1) {
                row.style.backgroundColor = 'rgba(0, 0, 0, 0.02)';
            }
        });

        // Ajouter une animation au survol des lignes
        rows.forEach(row => {
            row.addEventListener('mouseenter', function() {
                this.style.transition = 'background-color 0.3s';
                this.style.backgroundColor = 'rgba(46, 134, 222, 0.08)';
            });

            row.addEventListener('mouseleave', function() {
                this.style.transition = 'background-color 0.3s';
                this.style.backgroundColor = this.rowIndex % 2 === 1 ? 'rgba(0, 0, 0, 0.02)' : '';
            });
        });
    });
}

// Améliorer l'apparence des messages flash
function enhanceFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash');

    flashMessages.forEach(message => {
        // Ajouter une icône appropriée en fonction du type de message
        const firstChild = message.firstChild;
        let icon = document.createElement('i');

        if (message.classList.contains('flash-success')) {
            icon.className = 'fas fa-check-circle';
            icon.style.marginRight = '10px';
            icon.style.color = '#27ae60';
        } else if (message.classList.contains('flash-error')) {
            icon.className = 'fas fa-exclamation-triangle';
            icon.style.marginRight = '10px';
            icon.style.color = '#e74c3c';
        } else if (message.classList.contains('flash-warning')) {
            icon.className = 'fas fa-exclamation-circle';
            icon.style.marginRight = '10px';
            icon.style.color = '#f39c12';
        } else {
            icon.className = 'fas fa-info-circle';
            icon.style.marginRight = '10px';
            icon.style.color = '#2e86de';
        }

        message.insertBefore(icon, firstChild);

        // Ajouter un bouton de fermeture
        const closeButton = document.createElement('span');
        closeButton.innerHTML = '&times;';
        closeButton.style.float = 'right';
        closeButton.style.fontSize = '1.5rem';
        closeButton.style.fontWeight = 'bold';
        closeButton.style.cursor = 'pointer';
        closeButton.style.marginLeft = '15px';

        closeButton.addEventListener('click', function() {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 300);
        });

        message.appendChild(closeButton);
    });
}

// Ajouter des indicateurs de chargement pour les actions importantes
function addLoadingIndicators() {
    // Ajouter des indicateurs de chargement aux formulaires
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        form.addEventListener('submit', function() {
            // Vérifier si c'est un formulaire qui nécessite un indicateur de chargement
            const submitButton = this.querySelector('button[type="submit"]');

            if (submitButton && !this.classList.contains('search-form') && !this.classList.contains('inline-form')) {
                // Sauvegarder le texte original du bouton
                const originalText = submitButton.innerHTML;

                // Ajouter l'indicateur de chargement
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Traitement...';
                submitButton.disabled = true;

                // Réactiver le bouton après un certain délai au cas où la soumission échoue
                setTimeout(() => {
                    if (submitButton.innerHTML.includes('Traitement')) {
                        submitButton.innerHTML = originalText;
                        submitButton.disabled = false;
                    }
                }, 15000); // 15 secondes
            }
        });
    });
}
