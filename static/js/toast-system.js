/**
 * Custom Toast and Confirm System
 * Replace browser's native alert and confirm with custom styled components
 */

class ToastManager {
    constructor() {
        this.container = document.getElementById('toastContainer');
        this.toastId = 0;
    }

    show(message, type = 'info', duration = 5000) {
        this.toastId++;
        const toastId = `toast-${this.toastId}`;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        const titles = {
            success: 'Thành công',
            error: 'Lỗi',
            warning: 'Cảnh báo',
            info: 'Thông báo'
        };

        const toastHTML = `
            <div class="toast custom-toast toast-${type}" id="${toastId}" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header">
                    <i class="${icons[type]} me-2"></i>
                    <strong class="me-auto">${titles[type]}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;

        this.container.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: duration
        });

        // Show toast with animation
        setTimeout(() => {
            toastElement.classList.add('show');
        }, 100);

        toast.show();

        // Remove from DOM after hiding
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });

        return toast;
    }

    success(message, duration = 4000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 6000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 5000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 4000) {
        return this.show(message, 'info', duration);
    }
}

class ConfirmManager {
    constructor() {
        this.modal = document.getElementById('confirmModal');
        this.modalBody = document.getElementById('confirmModalBody');
        this.confirmButton = document.getElementById('confirmButton');
        this.currentCallback = null;

        // Ensure elements exist
        if (!this.modal || !this.modalBody || !this.confirmButton) {
            console.error('Confirm modal elements not found!');
            return;
        }

        this.bsModal = new bootstrap.Modal(this.modal);

        // Add click event listener for confirm button
        this.confirmButton.addEventListener('click', () => {
            if (this.currentCallback && typeof this.currentCallback === 'function') {
                try {
                    this.currentCallback();
                } catch (error) {
                    console.error('Error executing callback:', error);
                }
            }
            this.bsModal.hide();
            this.currentCallback = null; // Clear callback after execution
        });
    }

    show(message, callback, title = 'Xác nhận', confirmText = 'Xác nhận') {
        if (!this.modal) return;
        
        this.modalBody.textContent = message;
        this.confirmButton.textContent = confirmText;
        this.currentCallback = callback;
        this.bsModal.show();
    }

    confirm(message, callback) {
        this.show(message, callback, 'Xác nhận', 'Xác nhận');
    }

    confirmDelete(message, callback) {
        this.show(message, callback, 'Xác nhận xóa', 'Xóa');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if required elements exist
    const toastContainer = document.getElementById('toastContainer');
    const confirmModal = document.getElementById('confirmModal');
    
    if (!toastContainer) {
        console.error('Toast container not found!');
        return;
    }
    
    if (!confirmModal) {
        console.error('Confirm modal not found!');
        return;
    }

    // Initialize global instances
    window.Toast = new ToastManager();
    window.Confirm = new ConfirmManager();

    // Store original functions
    window.originalAlert = window.alert;
    window.originalConfirm = window.confirm;

    // Override alert function
    window.alert = function(message) {
        if (typeof message === 'string') {
            Toast.info(message);
        } else {
            Toast.info(String(message));
        }
    };

    // Override confirm function (returns Promise for async handling)
    window.confirm = function(message) {
        return new Promise((resolve) => {
            Confirm.confirm(message, () => resolve(true));
            // If modal is closed without confirmation, resolve false
            const modal = document.getElementById('confirmModal');
            const handleClose = () => {
                modal.removeEventListener('hidden.bs.modal', handleClose);
                resolve(false);
            };
            modal.addEventListener('hidden.bs.modal', handleClose, { once: true });
        });
    };

    // Custom functions for different types
    window.showSuccess = (message) => Toast.success(message);
    window.showError = (message) => Toast.error(message);
    window.showWarning = (message) => Toast.warning(message);
    window.showInfo = (message) => Toast.info(message);
    window.confirmAction = (message, callback) => Confirm.confirm(message, callback);
    window.confirmDelete = (message, callback) => Confirm.confirmDelete(message, callback);

    // Helper function for async confirm in onclick handlers
    window.asyncConfirm = async function(message) {
        return await window.confirm(message);
    };
});

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ToastManager, ConfirmManager };
}
