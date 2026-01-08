// form-enhancer.js - Améliore l'expérience des formulaires avec validation visuelle

document.addEventListener('DOMContentLoaded', function() {
    enhanceInputFields();
    setupFormValidation();
    enhanceFileUploads();
});

// Améliore l'apparence et l'interaction des champs de formulaire
function enhanceInputFields() {
    const inputFields = document.querySelectorAll('input[type="text"], input[type="url"], input[type="password"], textarea, select');
    
    inputFields.forEach(field => {
        // Ajouter des classes de focus pour améliorer le retour visuel
        field.addEventListener('focus', function() {
            this.parentNode.classList.add('field-focused');
            this.classList.add('input-focused');
            
            // Animer le label associé si présent
            const label = this.parentNode.querySelector('label');
            if (label) {
                label.style.color = '#2e86de';
                label.style.transition = 'color 0.3s';
            }
        });
        
        field.addEventListener('blur', function() {
            this.parentNode.classList.remove('field-focused');
            this.classList.remove('input-focused');
            
            // Réinitialiser le label
            const label = this.parentNode.querySelector('label');
            if (label) {
                label.style.color = '';
            }
        });
        
        // Ajouter une classe lorsque le champ contient une valeur
        field.addEventListener('input', function() {
            if (this.value.trim() !== '') {
                this.classList.add('has-value');
            } else {
                this.classList.remove('has-value');
            }
        });
        
        // Déclencher l'événement input pour initialiser l'état
        const event = new Event('input');
        field.dispatchEvent(event);
    });
}

// Configure la validation visuelle des formulaires
// Affiche un message d'erreur global pour le formulaire
function showFormError(form, message) {
    // Supprimer les anciens messages
    const oldError = form.querySelector('.form-global-error');
    if (oldError) {
        oldError.remove();
    }
    
    // Créer le nouveau message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-global-error';
    errorDiv.textContent = message;
    errorDiv.style.backgroundColor = '#f8d7da';
    errorDiv.style.color = '#721c24';
    errorDiv.style.padding = '0.75rem 1.25rem';
    errorDiv.style.marginBottom = '1rem';
    errorDiv.style.borderRadius = '6px';
    errorDiv.style.animation = 'slideDown 0.3s ease';
    
    // Ajouter au début du formulaire
    form.insertBefore(errorDiv, form.firstChild);
    
    // Scroll vers le message
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setupFormValidation() {
    const forms = document.querySelectorAll('form:not(.search-form):not(.inline-form)');
    
    forms.forEach(form => {
        const requiredFields = form.querySelectorAll('[required]');
        const submitButton = form.querySelector('button[type="submit"]');
        
        if (requiredFields.length > 0 && submitButton) {
            // Ajouter des indicateurs visuels aux champs obligatoires
            requiredFields.forEach(field => {
                const label = field.parentNode.querySelector('label');
                if (label && !label.innerHTML.includes('*')) {
                    label.innerHTML += ' <span class="required-indicator">*</span>';
                }
                
                // Valider à la sortie du champ
                field.addEventListener('blur', function() {
                    validateField(this);
                });
                
                // Valider en temps réel pour les champs déjà visités
                field.addEventListener('input', function() {
                    if (this.dataset.visited === 'true') {
                        validateField(this);
                    }
                });
                
                field.addEventListener('focus', function() {
                    this.dataset.visited = 'true';
                });
            });
            
            // Valider à la soumission
            form.addEventListener('submit', function(e) {
                let isValid = true;
                
                requiredFields.forEach(field => {
                    if (!validateField(field)) {
                        isValid = false;
                        field.focus();
                    }
                });
                
                if (!isValid) {
                    e.preventDefault();
                    // Afficher un message d'erreur global
                    showFormError(form, "Veuillez corriger les erreurs dans le formulaire.");
                }
            });
        }
    });
}

// Valide un champ individuel
function validateField(field) {
    const errorMessage = field.parentNode.querySelector('.field-error');
    let isValid = true;
    let message = '';
    
    // Supprimer l'erreur existante
    if (errorMessage) {
        errorMessage.remove();
    }
    
    // Réinitialiser l'état visuel
    field.classList.remove('field-invalid', 'field-valid');
    
    // Validation de base pour les champs requis
    if (field.required && field.value.trim() === '') {
        isValid = false;
        message = 'Ce champ est obligatoire';
    }
    
    // Validation pour les champs URL
    if (field.type === 'url' && field.value.trim() !== '') {
        try {
            new URL(field.value);
        } catch (e) {
            isValid = false;
            message = 'Veuillez entrer une URL valide (ex: https://exemple.com)';
        }
    }
    
    // Ajouter une classe en fonction de l'état
    if (isValid) {
        field.classList.add('field-valid');
    } else {
        field.classList.add('field-invalid');
        
        // Créer et afficher le message d'erreur
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        errorDiv.style.color = '#e74c3c';
        errorDiv.style.fontSize = '0.85rem';
        errorDiv.style.marginTop = '0.25rem';
        errorDiv.style.animation = 'fadeIn 0.3s';
        field.parentNode.appendChild(errorDiv);
    }
    
    return isValid;
}