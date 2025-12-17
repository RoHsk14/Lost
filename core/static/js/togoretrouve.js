// Fonctions JavaScript communes pour TogoRetrouvé

// Configuration des URLs d'API (à adapter selon les URLs Django)
const API_URLS = {
    valider_declaration: '/agent/api/declarations/{id}/valider/',
    rejeter_declaration: '/agent/api/declarations/{id}/rejeter/',
    publier_declaration: '/agent/api/declarations/{id}/publier/',
    approuver_reclamation: '/agent/api/reclamations/{id}/approuver/',
    rejeter_reclamation: '/agent/api/reclamations/{id}/rejeter/',
    mark_notification_read: '/agent/api/notifications/{id}/mark-read/',
    delete_notification: '/agent/api/notifications/{id}/delete/',
};

// Helper pour obtenir le token CSRF
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
           document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
}

// Helper pour afficher des alertes
function showAlert(message, type = 'info', duration = 5000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'error' ? 'times' : type === 'success' ? 'check' : 'info'}-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const content = document.querySelector('.admin-content, .agent-content') || document.body;
    content.insertBefore(alertDiv, content.firstChild);
    
    // Auto-dismiss
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    }
}

// Helper pour les requêtes AJAX
async function makeRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || `HTTP ${response.status}`);
        }
        
        return result;
    } catch (error) {
        console.error('Request failed:', error);
        throw error;
    }
}

// État de chargement pour les boutons
function setLoading(element, loading = true) {
    if (!element) return;
    
    if (loading) {
        element.disabled = true;
        element.dataset.originalHtml = element.innerHTML;
        element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Traitement...';
        element.classList.add('loading');
    } else {
        element.disabled = false;
        element.innerHTML = element.dataset.originalHtml || element.innerHTML;
        element.classList.remove('loading');
        delete element.dataset.originalHtml;
    }
}

// === FONCTIONS POUR LES DÉCLARATIONS ===

// Valider une déclaration
async function validerDeclaration(declarationId) {
    const btn = document.querySelector(`[onclick*="validerDeclaration(${declarationId})"]`);
    
    if (!confirm('Confirmer la validation de cette déclaration ?')) {
        return;
    }
    
    setLoading(btn);
    
    try {
        const url = API_URLS.valider_declaration.replace('{id}', declarationId);
        const result = await makeRequest(url, 'POST');
        
        if (result.success) {
            showAlert('Déclaration validée avec succès !', 'success');
            
            // Mettre à jour l'interface
            updateDeclarationStatus(declarationId, 'valide');
            
            // Optionnel: recharger la page après un délai
            setTimeout(() => {
                if (window.location.pathname.includes('detail')) {
                    location.reload();
                }
            }, 1500);
        } else {
            showAlert(result.message || 'Erreur lors de la validation', 'error');
        }
    } catch (error) {
        showAlert('Erreur de connexion', 'error');
    } finally {
        setLoading(btn, false);
    }
}

// Rejeter une déclaration
async function rejeterDeclaration(declarationId, motif) {
    if (!motif || !motif.trim()) {
        showAlert('Le motif de rejet est obligatoire', 'warning');
        return;
    }
    
    const btn = document.querySelector(`[onclick*="rejeterDeclaration(${declarationId})"]`);
    setLoading(btn);
    
    try {
        const url = API_URLS.rejeter_declaration.replace('{id}', declarationId);
        const result = await makeRequest(url, 'POST', { motif: motif });
        
        if (result.success) {
            showAlert('Déclaration rejetée avec succès !', 'success');
            updateDeclarationStatus(declarationId, 'rejete');
            
            setTimeout(() => {
                if (window.location.pathname.includes('detail')) {
                    location.reload();
                }
            }, 1500);
        } else {
            showAlert(result.message || 'Erreur lors du rejet', 'error');
        }
    } catch (error) {
        showAlert('Erreur de connexion', 'error');
    } finally {
        setLoading(btn, false);
    }
}

// Publier une déclaration
async function publierDeclaration(declarationId) {
    const btn = document.querySelector(`[onclick*="publierDeclaration(${declarationId})"]`);
    
    if (!confirm('Publier cette déclaration ?')) {
        return;
    }
    
    setLoading(btn);
    
    try {
        const url = API_URLS.publier_declaration.replace('{id}', declarationId);
        const result = await makeRequest(url, 'POST');
        
        if (result.success) {
            showAlert('Déclaration publiée avec succès !', 'success');
            updateDeclarationStatus(declarationId, 'publie');
            
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert(result.message || 'Erreur lors de la publication', 'error');
        }
    } catch (error) {
        showAlert('Erreur de connexion', 'error');
    } finally {
        setLoading(btn, false);
    }
}

// Mettre à jour le statut visuel d'une déclaration
function updateDeclarationStatus(declarationId, newStatus) {
    const row = document.querySelector(`[data-declaration-id="${declarationId}"]`);
    if (!row) return;
    
    const statusBadge = row.querySelector('.badge-status');
    if (statusBadge) {
        // Supprimer les anciennes classes de statut
        statusBadge.className = statusBadge.className.replace(/badge-\w+/g, '');
        statusBadge.classList.add('badge-status', `badge-${newStatus}`);
        
        // Mettre à jour le texte
        const statusTexts = {
            'valide': 'Validé',
            'rejete': 'Rejeté',
            'publie': 'Publié'
        };
        statusBadge.textContent = statusTexts[newStatus] || newStatus;
    }
    
    // Masquer/mettre à jour les boutons d'action
    const actionButtons = row.querySelectorAll('.action-btn');
    actionButtons.forEach(btn => {
        if (newStatus === 'valide' && btn.textContent.includes('Valider')) {
            btn.style.display = 'none';
        } else if (newStatus === 'rejete' || newStatus === 'publie') {
            btn.style.display = 'none';
        }
    });
}

// === FONCTIONS POUR LES RÉCLAMATIONS ===

// Approuver une réclamation
async function approuverReclamation(reclamationId, motif = '') {
    const btn = document.querySelector(`[onclick*="approuverReclamation(${reclamationId})"]`);
    
    if (!confirm('Approuver cette réclamation ?')) {
        return;
    }
    
    setLoading(btn);
    
    try {
        const url = API_URLS.approuver_reclamation.replace('{id}', reclamationId);
        const result = await makeRequest(url, 'POST', { motif: motif });
        
        if (result.success) {
            showAlert('Réclamation approuvée avec succès !', 'success');
            updateReclamationStatus(reclamationId, 'approuvee');
            
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert(result.message || 'Erreur lors de l\'approbation', 'error');
        }
    } catch (error) {
        showAlert('Erreur de connexion', 'error');
    } finally {
        setLoading(btn, false);
    }
}

// Rejeter une réclamation
async function rejeterReclamation(reclamationId, motif) {
    if (!motif || !motif.trim()) {
        showAlert('Le motif de rejet est obligatoire', 'warning');
        return;
    }
    
    const btn = document.querySelector(`[onclick*="rejeterReclamation(${reclamationId})"]`);
    setLoading(btn);
    
    try {
        const url = API_URLS.rejeter_reclamation.replace('{id}', reclamationId);
        const result = await makeRequest(url, 'POST', { motif: motif });
        
        if (result.success) {
            showAlert('Réclamation rejetée avec succès !', 'success');
            updateReclamationStatus(reclamationId, 'rejetee');
            
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert(result.message || 'Erreur lors du rejet', 'error');
        }
    } catch (error) {
        showAlert('Erreur de connexion', 'error');
    } finally {
        setLoading(btn, false);
    }
}

// Mettre à jour le statut visuel d'une réclamation
function updateReclamationStatus(reclamationId, newStatus) {
    const row = document.querySelector(`[data-reclamation-id="${reclamationId}"]`);
    if (!row) return;
    
    const statusBadge = row.querySelector('.badge-status');
    if (statusBadge) {
        statusBadge.className = statusBadge.className.replace(/badge-\w+/g, '');
        statusBadge.classList.add('badge-status', `badge-${newStatus}`);
        
        const statusTexts = {
            'approuvee': 'Approuvée',
            'rejetee': 'Rejetée'
        };
        statusBadge.textContent = statusTexts[newStatus] || newStatus;
    }
}

// === FONCTIONS POUR LES NOTIFICATIONS ===

// Marquer une notification comme lue
async function markAsRead(notificationId) {
    try {
        const url = API_URLS.mark_notification_read.replace('{id}', notificationId);
        const result = await makeRequest(url, 'POST');
        
        if (result.success) {
            const item = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (item) {
                item.classList.remove('unread');
                const badge = item.querySelector('.badge');
                if (badge) badge.remove();
            }
        }
    } catch (error) {
        console.error('Erreur lors du marquage:', error);
    }
}

// Supprimer une notification
async function deleteNotification(notificationId) {
    if (!confirm('Supprimer cette notification ?')) {
        return;
    }
    
    try {
        const url = API_URLS.delete_notification.replace('{id}', notificationId);
        const result = await makeRequest(url, 'POST');
        
        if (result.success) {
            const item = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (item) {
                item.style.animation = 'fadeOut 0.3s ease-out forwards';
                setTimeout(() => item.remove(), 300);
            }
        }
    } catch (error) {
        showAlert('Erreur lors de la suppression', 'error');
    }
}

// === UTILITAIRES DIVERS ===

// Formater les dates
function formatDate(dateString, includeTime = false) {
    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    };
    
    if (includeTime) {
        options.hour = '2-digit';
        options.minute = '2-digit';
    }
    
    return date.toLocaleDateString('fr-FR', options);
}

// Débouncer pour les recherches
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-refresh conditionnel
function setupAutoRefresh(interval = 300000) { // 5 minutes par défaut
    setInterval(() => {
        if (document.visibilityState === 'visible' && 
            !document.querySelector('.modal.show') && 
            !document.activeElement.matches('input, textarea, select')) {
            location.reload();
        }
    }, interval);
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    // Configuration globale des animations CSS
    if (!document.head.querySelector('#togoretrouve-animations')) {
        const style = document.createElement('style');
        style.id = 'togoretrouve-animations';
        style.textContent = `
            @keyframes fadeOut {
                from { opacity: 1; transform: translateX(0); }
                to { opacity: 0; transform: translateX(-20px); }
            }
            
            .loading {
                opacity: 0.6;
                pointer-events: none;
            }
            
            .fade-out {
                animation: fadeOut 0.3s ease-out forwards;
            }
            
            .notification-item.unread {
                background: #f8f9ff;
                border-left: 4px solid var(--primary-color, #007bff);
            }
        `;
        document.head.appendChild(style);
    }
    
    // Setup auto-refresh si pas de formulaires actifs
    if (!document.querySelector('form[method="post"]')) {
        setupAutoRefresh();
    }
    
    console.log('TogoRetrouvé JS loaded successfully');
});

// Export pour usage externe si nécessaire
window.TogoRetrouve = {
    validerDeclaration,
    rejeterDeclaration,
    publierDeclaration,
    approuverReclamation,
    rejeterReclamation,
    markAsRead,
    deleteNotification,
    showAlert,
    makeRequest,
    setLoading,
    formatDate,
    debounce
};