/**
 * J. Austin Front Desk Processing - Main JavaScript
 */

// CSRF token helper (also defined in base.html, this is a fallback)
if (typeof csrftoken === 'undefined') {
    var csrftoken = '';
    const csrfCookie = document.cookie.split('; ').find(c => c.startsWith('csrftoken='));
    if (csrfCookie) {
        csrftoken = csrfCookie.split('=')[1];
    }
}

/**
 * Format currency values
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(value);
}

/**
 * Format weight in ounces
 */
function formatOz(value) {
    if (!value) return '--';
    return parseFloat(value).toFixed(2) + ' oz';
}

/**
 * Show a toast notification
 */
function showToast(message, type) {
    type = type || 'success';
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
        document.body.appendChild(container);
    }

    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning text-dark',
        'info': 'bg-info'
    }[type] || 'bg-success';

    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-white ' + bgClass + ' border-0';
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML =
        '<div class="d-flex">' +
            '<div class="toast-body">' + message + '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
        '</div>';

    document.getElementById('toastContainer').appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

/**
 * Confirm action dialog
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Mobile sidebar toggle
 */
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.querySelector('[data-toggle-sidebar]');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('show');
        });
    }
});
