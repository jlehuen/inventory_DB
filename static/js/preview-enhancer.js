// preview-enhancer.js - Gère la prévisualisation "Quick Look" au survol

document.addEventListener('DOMContentLoaded', function() {
    initQuickPreview();
});

function initQuickPreview() {
    // Créer le conteneur de prévisualisation s'il n'existe pas
    let previewContainer = document.querySelector('.quick-preview-container');
    if (!previewContainer) {
        previewContainer = document.createElement('div');
        previewContainer.className = 'quick-preview-container';
        document.body.appendChild(previewContainer);
    }

    const previewTriggers = document.querySelectorAll('.objet-card, .clickable-row, .timeline-card');
    let previewTimeout;
    let currentId = null;

    previewTriggers.forEach(trigger => {
        trigger.addEventListener('mouseenter', function(e) {
            const objectId = this.getAttribute('data-object-id');
            if (!objectId) return;

            // Annuler tout timeout de fermeture
            clearTimeout(previewTimeout);

            // Ne pas recharger si c'est déjà le même objet
            if (currentId === objectId && previewContainer.classList.contains('active')) return;

            currentId = objectId;

            // Positionner temporairement pour éviter les sauts
            updatePreviewPosition(e, previewContainer);

            // Charger le contenu
            previewContainer.innerHTML = '<div class="preview-loading"><i class="fas fa-spinner fa-spin"></i> Chargement...</div>';
            previewContainer.classList.add('active');

            fetch(`/api/objet_preview/${objectId}`)
                .then(response => {
                    if (!response.ok) throw new Error('Erreur de chargement');
                    return response.text();
                })
                .then(html => {
                    // Vérifier si on est toujours sur le même objet
                    if (currentId === objectId) {
                        previewContainer.innerHTML = html;
                    }
                })
                .catch(err => {
                    console.error(err);
                    previewContainer.innerHTML = '<div class="preview-loading">Impossible de charger l\'aperçu</div>';
                });
        });

        trigger.addEventListener('mousemove', function(e) {
            updatePreviewPosition(e, previewContainer);
        });

        trigger.addEventListener('mouseleave', function() {
            previewTimeout = setTimeout(() => {
                previewContainer.classList.remove('active');
                currentId = null;
            }, 300);
        });
    });
}

function updatePreviewPosition(e, container) {
    const padding = 20;
    let x = e.clientX + padding;
    let y = e.clientY + padding;

    // Ajuster si ça dépasse à droite
    if (x + container.offsetWidth > window.innerWidth) {
        x = e.clientX - container.offsetWidth - padding;
    }

    // Ajuster si ça dépasse en bas
    if (y + container.offsetHeight > window.innerHeight) {
        y = e.clientY - container.offsetHeight - padding;
    }

    container.style.left = x + 'px';
    container.style.top = y + 'px';
}
