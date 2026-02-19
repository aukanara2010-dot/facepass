/**
 * Landing Page JavaScript
 * Handles photo upload, camera capture, and search functionality
 */

class LandingPage {
    constructor() {
        this.stream = null;
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        // Buttons
        this.cameraBtn = document.getElementById('camera-btn');
        this.uploadBtn = document.getElementById('upload-btn');
        this.fileInput = document.getElementById('file-input');
        
        // Camera Modal
        this.cameraModal = document.getElementById('camera-modal');
        this.cameraVideo = document.getElementById('camera-video');
        this.cameraCanvas = document.getElementById('camera-canvas');
        this.captureBtn = document.getElementById('capture-photo');
        this.cancelCameraBtn = document.getElementById('cancel-camera');
        
        // Loading Modal
        this.loadingModal = document.getElementById('loading-modal');
        
        // FAQ
        this.faqToggles = document.querySelectorAll('.faq-toggle');
        
        // Toast Container
        this.toastContainer = document.getElementById('toast-container');
    }

    bindEvents() {
        // Main action buttons
        this.cameraBtn.addEventListener('click', () => this.openCamera());
        this.uploadBtn.addEventListener('click', () => this.openFileDialog());
        
        // File input
        this.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        
        // Camera modal
        this.captureBtn.addEventListener('click', () => this.capturePhoto());
        this.cancelCameraBtn.addEventListener('click', () => this.closeCamera());
        
        // FAQ toggles
        this.faqToggles.forEach(toggle => {
            toggle.addEventListener('click', () => this.toggleFAQ(toggle));
        });
        
        // Close modals on backdrop click
        this.cameraModal.addEventListener('click', (e) => {
            if (e.target === this.cameraModal) {
                this.closeCamera();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeCamera();
            }
        });
    }

    // Camera functionality
    async openCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            });
            
            this.cameraVideo.srcObject = this.stream;
            this.showModal(this.cameraModal);
            
        } catch (error) {
            console.error('Camera error:', error);
            this.showToast('Не удалось получить доступ к камере. Проверьте разрешения.', 'error');
        }
    }

    closeCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.hideModal(this.cameraModal);
    }

    capturePhoto() {
        if (!this.stream) return;

        const canvas = this.cameraCanvas;
        const context = canvas.getContext('2d');
        
        canvas.width = this.cameraVideo.videoWidth;
        canvas.height = this.cameraVideo.videoHeight;
        
        context.drawImage(this.cameraVideo, 0, 0);
        
        canvas.toBlob((blob) => {
            this.closeCamera();
            this.processPhoto(blob, 'camera-selfie.jpg');
        }, 'image/jpeg', 0.95);
    }

    // File upload functionality
    openFileDialog() {
        this.fileInput.click();
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('image/')) {
            this.processPhoto(file, file.name);
        } else {
            this.showToast('Пожалуйста, выберите изображение', 'error');
        }
        // Reset file input
        event.target.value = '';
    }

    // Photo processing and search
    async processPhoto(imageBlob, fileName) {
        this.showModal(this.loadingModal);
        
        try {
            // Get session ID from URL parameters
            const sessionId = this.getSessionIdFromUrl();
            
            if (!sessionId) {
                this.showToast('Не указан ID фотосессии в URL. Добавьте ?session_id=YOUR_SESSION_ID', 'error');
                this.hideModal(this.loadingModal);
                return;
            }
            
            // Prepare form data
            const formData = new FormData();
            formData.append('file', imageBlob, fileName);
            formData.append('session_id', sessionId);
            formData.append('threshold', '0.5');
            formData.append('limit', '50');
            
            // Make search request
            const response = await fetch('/api/v1/faces/search-session', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'Ошибка поиска');
            }
            
            this.hideModal(this.loadingModal);
            
            // Redirect to results page
            if (result.matches && result.matches.length > 0) {
                // Redirect to session page with results
                window.location.href = `/session/${sessionId}`;
            } else {
                // Show no results message
                this.showNoResultsModal(result);
            }
            
        } catch (error) {
            console.error('Search error:', error);
            this.hideModal(this.loadingModal);
            this.showToast('Ошибка при поиске фотографий. Попробуйте еще раз.', 'error');
        }
    }

    // Get session ID from URL parameters
    getSessionIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('session_id') || urlParams.get('session');
    }

    // Show no results modal
    showNoResultsModal(result) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-white rounded-2xl p-8 max-w-md w-full text-center">
                <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i class="fas fa-search text-2xl text-gray-400"></i>
                </div>
                <h3 class="text-xl font-bold text-gray-900 mb-4">Фотографии не найдены</h3>
                <p class="text-gray-600 mb-6">
                    К сожалению, мы не смогли найти ваши фотографии в этой фотосессии. 
                    Попробуйте загрузить другое селфи с лучшим качеством.
                </p>
                <div class="flex space-x-3">
                    <button onclick="this.closest('.fixed').remove()" class="flex-1 bg-blue-500 text-white py-3 rounded-xl font-semibold hover:bg-blue-600 transition-colors">
                        Попробовать снова
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Auto remove after 10 seconds
        setTimeout(() => {
            if (modal.parentElement) {
                modal.remove();
            }
        }, 10000);
    }

    // FAQ functionality
    toggleFAQ(toggle) {
        const content = toggle.nextElementSibling;
        const icon = toggle.querySelector('i');
        
        if (content.classList.contains('hidden')) {
            // Close all other FAQ items
            this.faqToggles.forEach(otherToggle => {
                if (otherToggle !== toggle) {
                    const otherContent = otherToggle.nextElementSibling;
                    const otherIcon = otherToggle.querySelector('i');
                    otherContent.classList.add('hidden');
                    otherIcon.style.transform = 'rotate(0deg)';
                }
            });
            
            // Open this FAQ item
            content.classList.remove('hidden');
            icon.style.transform = 'rotate(180deg)';
        } else {
            // Close this FAQ item
            content.classList.add('hidden');
            icon.style.transform = 'rotate(0deg)';
        }
    }

    // Modal utilities
    showModal(modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    hideModal(modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    // Toast notifications
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `bg-white border-l-4 p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full max-w-sm`;
        
        const colors = {
            success: 'border-green-500 text-green-700',
            error: 'border-red-500 text-red-700',
            info: 'border-blue-500 text-blue-700',
            warning: 'border-yellow-500 text-yellow-700'
        };
        
        toast.classList.add(...colors[type].split(' '));
        
        const icons = {
            success: '✅',
            error: '❌',
            info: 'ℹ️',
            warning: '⚠️'
        };
        
        toast.innerHTML = `
            <div class="flex items-center">
                <span class="mr-3 text-lg">${icons[type]}</span>
                <span class="flex-1">${message}</span>
                <button onclick="this.closest('div').remove()" class="ml-3 text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.classList.add('translate-x-full');
                setTimeout(() => {
                    if (toast.parentElement) {
                        toast.remove();
                    }
                }, 300);
            }
        }, 5000);
    }
}

// Initialize the landing page
document.addEventListener('DOMContentLoaded', () => {
    new LandingPage();
});

// Add some interactive effects
document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add scroll effect to header
    let lastScrollY = window.scrollY;
    window.addEventListener('scroll', () => {
        const header = document.querySelector('header');
        if (window.scrollY > lastScrollY && window.scrollY > 100) {
            header.style.transform = 'translateY(-100%)';
        } else {
            header.style.transform = 'translateY(0)';
        }
        lastScrollY = window.scrollY;
    });
});