/**
 * FacePass Session Interface with Landing Design
 * Combines landing page functionality with session-specific search
 */

class FacePassSession {
    constructor() {
        this.sessionId = this.getSessionIdFromUrl();
        this.sessionData = null;
        this.stream = null;
        this.selectedPhotos = new Set();
        this.searchResults = [];
        
        this.initializeElements();
        this.bindEvents();
        this.validateSession();
    }

    getSessionIdFromUrl() {
        // Extract session ID from URL path: /session/{session_id}
        const pathParts = window.location.pathname.split('/');
        const sessionId = pathParts[pathParts.length - 1];
        
        console.log('URL pathname:', window.location.pathname);
        console.log('Extracted session ID:', sessionId);
        
        return sessionId;
    }

    initializeElements() {
        // Main sections
        this.heroSection = document.getElementById('hero-section');
        this.searchLoading = document.getElementById('search-loading');
        this.noResults = document.getElementById('no-results');
        this.resultsSection = document.getElementById('results-section');
        this.howItWorks = document.getElementById('how-it-works');
        this.faqSection = document.getElementById('faq-section');

        // Elements
        this.sessionTitle = document.getElementById('session-title');
        this.fileInput = document.getElementById('file-input');
        this.fallbackInput = document.getElementById('fallback-input');
        this.photosGrid = document.getElementById('photos-grid');
        this.resultsCount = document.getElementById('results-count');
        this.selectedCount = document.getElementById('selected-count');

        // Buttons
        this.cameraBtn = document.getElementById('camera-btn');
        this.uploadBtn = document.getElementById('upload-btn');
        this.tryAgainBtn = document.getElementById('try-again-btn');
        this.selectAllBtn = document.getElementById('select-all-btn');
        this.buySelectedBtn = document.getElementById('buy-selected-btn');

        // Privacy agreement
        this.privacyAgreement = document.getElementById('privacy-agreement');

        // Camera modal
        this.cameraModal = document.getElementById('camera-modal');
        this.cameraVideo = document.getElementById('camera-video');
        this.cameraCanvas = document.getElementById('camera-canvas');
        this.capturePhoto = document.getElementById('capture-photo');
        this.cancelCamera = document.getElementById('cancel-camera');

        // Photo modal
        this.photoModal = document.getElementById('photo-modal');
        this.modalImage = document.getElementById('modal-image');
        this.modalTitle = document.getElementById('modal-title');
        this.modalSimilarity = document.getElementById('modal-similarity');
        this.modalSelectBtn = document.getElementById('modal-select-btn');
        this.closeModal = document.getElementById('close-modal');

        // Toast container
        this.toastContainer = document.getElementById('toast-container');

        // FAQ toggles
        this.faqToggles = document.querySelectorAll('.faq-toggle');
    }

    bindEvents() {
        // Privacy agreement checkbox
        if (this.privacyAgreement) {
            this.privacyAgreement.addEventListener('change', () => this.toggleActionButtons());
        }
        
        // Main action buttons
        this.cameraBtn.addEventListener('click', () => this.openCamera());
        this.uploadBtn.addEventListener('click', () => this.openFileDialog());
        
        // File input
        this.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        if (this.fallbackInput) {
            this.fallbackInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }
        
        // Camera modal
        this.capturePhoto.addEventListener('click', () => this.capturePhotoFromCamera());
        this.cancelCamera.addEventListener('click', () => this.closeCamera());
        
        // Try again button
        if (this.tryAgainBtn) {
            this.tryAgainBtn.addEventListener('click', () => this.resetToHero());
        }
        
        // Photo selection buttons
        if (this.selectAllBtn) {
            this.selectAllBtn.addEventListener('click', () => this.selectAllPhotos());
        }
        if (this.buySelectedBtn) {
            this.buySelectedBtn.addEventListener('click', () => this.buySelectedPhotos());
        }
        
        // Photo modal
        if (this.closeModal) {
            this.closeModal.addEventListener('click', () => this.hidePhotoModal());
        }
        
        // FAQ toggles
        this.faqToggles.forEach(toggle => {
            toggle.addEventListener('click', () => this.toggleFAQ(toggle));
        });
        
        // Close modals on backdrop click
        if (this.cameraModal) {
            this.cameraModal.addEventListener('click', (e) => {
                if (e.target === this.cameraModal) {
                    this.closeCamera();
                }
            });
        }
        
        if (this.photoModal) {
            this.photoModal.addEventListener('click', (e) => {
                if (e.target === this.photoModal) {
                    this.hidePhotoModal();
                }
            });
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeCamera();
                this.hidePhotoModal();
            }
        });
    }

    async validateSession() {
        if (!this.sessionId || this.sessionId === 'session') {
            this.showError('Неверный ID сессии');
            return;
        }

        try {
            // Validate session exists and is active
            const response = await fetch(`/api/v1/faces/session-index-status/${this.sessionId}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('Сессия не найдена');
                } else if (response.status === 403) {
                    this.showError('FacePass не активен для этой сессии');
                } else {
                    this.showError('Ошибка загрузки сессии');
                }
                return;
            }

            this.sessionData = await response.json();
            this.updateSessionTitle();
            
        } catch (error) {
            console.error('Session validation error:', error);
            this.showError('Ошибка подключения к серверу');
        }
    }

    updateSessionTitle() {
        if (this.sessionData && this.sessionData.session_name) {
            this.sessionTitle.innerHTML = `
                Найдите себя на 
                <span class="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    фотосессии по лицу
                </span>
                <br><br>
                <span class="text-2xl sm:text-3xl lg:text-4xl font-semibold text-gray-700">
                    "${this.sessionData.session_name}"
                </span>
            `;
        }
    }

    showError(message) {
        // Show error in a toast notification
        this.showToast(message, 'error');
        
        // Also update the hero section with error message
        if (this.sessionTitle) {
            this.sessionTitle.innerHTML = `
                <span class="text-red-600">Ошибка: ${message}</span>
            `;
        }
    }

    toggleActionButtons() {
        const isAgreed = this.privacyAgreement && this.privacyAgreement.checked;
        
        if (isAgreed) {
            // Enable buttons
            this.cameraBtn.disabled = false;
            this.uploadBtn.disabled = false;
            this.cameraBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            this.uploadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            this.cameraBtn.classList.add('hover:shadow-lg', 'hover:-translate-y-1');
            this.uploadBtn.classList.add('hover:shadow-lg', 'hover:-translate-y-1');
        } else {
            // Disable buttons
            this.cameraBtn.disabled = true;
            this.uploadBtn.disabled = true;
            this.cameraBtn.classList.add('opacity-50', 'cursor-not-allowed');
            this.uploadBtn.classList.add('opacity-50', 'cursor-not-allowed');
            this.cameraBtn.classList.remove('hover:shadow-lg', 'hover:-translate-y-1');
            this.uploadBtn.classList.remove('hover:shadow-lg', 'hover:-translate-y-1');
        }
    }

    // Camera functionality with Android compatibility
    async openCamera() {
        if (!this.privacyAgreement || !this.privacyAgreement.checked) {
            this.showToast('Пожалуйста, примите условия обработки персональных данных', 'warning');
            return;
        }
        
        // Detect Android Chrome for special handling
        const isAndroidChrome = /Android.*Chrome/.test(navigator.userAgent);
        let cameraTimeout;
        
        if (isAndroidChrome) {
            // Set timeout for Android Chrome camera activation
            cameraTimeout = setTimeout(() => {
                this.showAndroidCameraFallback();
            }, 2000);
        }
        
        try {
            // Enhanced constraints for better Android compatibility
            const constraints = {
                video: {
                    width: { ideal: 640, max: 1280 },
                    height: { ideal: 480, max: 720 },
                    facingMode: "user", // Explicitly request front camera
                    aspectRatio: { ideal: 1.33 }
                },
                audio: false
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            // Clear timeout if camera opened successfully
            if (cameraTimeout) {
                clearTimeout(cameraTimeout);
            }
            
            this.cameraVideo.srcObject = this.stream;
            this.showModal(this.cameraModal);
            
        } catch (error) {
            console.error('Camera error:', error);
            
            // Clear timeout
            if (cameraTimeout) {
                clearTimeout(cameraTimeout);
            }
            
            // Handle different error types
            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                this.showCameraPermissionError();
            } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                this.showToast('Камера не найдена на устройстве', 'error');
                this.showCameraFallback();
            } else if (error.name === 'NotSupportedError' || error.name === 'NotReadableError') {
                this.showToast('Камера недоступна или используется другим приложением', 'error');
                this.showCameraFallback();
            } else {
                this.showToast('Не удалось получить доступ к камере', 'error');
                this.showCameraFallback();
            }
        }
    }

    showAndroidCameraFallback() {
        this.showToast('Нажмите "Загрузить фото" и выберите "Камера"', 'info');
        // Highlight the upload button
        this.uploadBtn.classList.add('animate-pulse');
        setTimeout(() => {
            this.uploadBtn.classList.remove('animate-pulse');
        }, 3000);
    }

    showCameraPermissionError() {
        this.showToast('Разрешите доступ к камере в настройках браузера', 'warning');
        this.showCameraFallback();
    }

    showCameraFallback() {
        // Automatically show file input as fallback
        setTimeout(() => {
            this.openFileDialog();
        }, 1000);
    }

    closeCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.hideModal(this.cameraModal);
    }

    capturePhotoFromCamera() {
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

    // File upload functionality with Android optimization
    openFileDialog() {
        if (!this.privacyAgreement || !this.privacyAgreement.checked) {
            this.showToast('Пожалуйста, примите условия обработки персональных данных', 'warning');
            return;
        }
        
        // For Android devices, ensure proper file input attributes
        const isAndroid = /Android/.test(navigator.userAgent);
        if (isAndroid) {
            // Ensure capture attribute is set for Android
            this.fileInput.setAttribute('capture', 'user');
            this.fileInput.setAttribute('accept', 'image/*');
        }
        
        this.fileInput.click();
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('image/')) {
            // Show mobile loading indicator immediately
            this.showMobileLoadingIndicator('Обработка изображения...');
            
            // Validate file size (max 10MB for mobile compatibility)
            const maxSize = 10 * 1024 * 1024; // 10MB
            if (file.size > maxSize) {
                this.hideMobileLoadingIndicator();
                this.showToast('Файл слишком большой. Максимальный размер: 10MB', 'error');
                return;
            }
            
            // Add small delay for Android processing
            setTimeout(() => {
                this.processPhoto(file, file.name);
            }, 100);
        } else {
            this.showToast('Пожалуйста, выберите изображение', 'error');
        }
        // Reset file input
        event.target.value = '';
    }

    showMobileLoadingIndicator(message = 'Подготовка к поиску...') {
        // Remove existing indicator
        this.hideMobileLoadingIndicator();
        
        const overlay = document.createElement('div');
        overlay.id = 'mobile-loading-overlay';
        overlay.className = 'fixed top-0 left-0 right-0 bottom-0 flex items-center justify-center z-50';
        overlay.style.background = 'rgba(248, 250, 252, 0.95)';
        overlay.style.backdropFilter = 'blur(20px)';
        
        overlay.innerHTML = `
            <div class="glass-card p-8 rounded-2xl text-center max-w-sm mx-4">
                <div class="pixora-spinner mx-auto mb-4"></div>
                <p class="text-pixora-primary font-medium">${message}</p>
                <p class="text-sm text-pixora-secondary mt-2">Пожалуйста, подождите...</p>
            </div>
        `;
        
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';
    }

    hideMobileLoadingIndicator() {
        const overlay = document.getElementById('mobile-loading-overlay');
        if (overlay) {
            overlay.remove();
            document.body.style.overflow = '';
        }
    }

    // Photo processing and search
    async processPhoto(imageBlob, fileName) {
        // Hide mobile loading indicator if it was shown
        this.hideMobileLoadingIndicator();
        
        // Hide hero section and show loading
        this.hideSection(this.heroSection);
        this.hideSection(this.howItWorks);
        this.hideSection(this.faqSection);
        this.showSection(this.searchLoading);
        
        try {
            // Prepare form data
            const formData = new FormData();
            formData.append('file', imageBlob, fileName);
            formData.append('session_id', this.sessionId);
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
            
            this.hideSection(this.searchLoading);
            
            // Handle results
            if (result.matches && result.matches.length > 0) {
                this.searchResults = result.matches;
                this.displayResults();
            } else {
                this.showSection(this.noResults);
            }
            
        } catch (error) {
            console.error('Search error:', error);
            this.hideSection(this.searchLoading);
            this.hideMobileLoadingIndicator(); // Ensure loading is hidden on error
            this.showToast('Не удалось распознать изображение. Попробуйте другое селфи.', 'error');
            this.resetToHero();
        }
    }

    displayResults() {
        this.showSection(this.resultsSection);
        
        // Update results count
        this.resultsCount.textContent = `Найдено ${this.searchResults.length} фотографий с вашим лицом`;
        
        // Clear previous results
        this.photosGrid.innerHTML = '';
        this.selectedPhotos.clear();
        
        // Create photo cards
        this.searchResults.forEach((photo, index) => {
            const photoCard = this.createPhotoCard(photo, index);
            this.photosGrid.appendChild(photoCard);
        });
        
        this.updateSelectedCount();
    }

    createPhotoCard(photo, index) {
        const card = document.createElement('div');
        card.className = 'photo-card-pixora cursor-pointer';
        card.dataset.photoId = photo.id;
        card.dataset.index = index;
        
        const similarityPercent = Math.round(photo.similarity * 100);
        
        // Use S3 URL from environment or construct from preview_path
        let previewUrl;
        if (photo.preview_path) {
            // If preview_path is a full URL, use it directly
            if (photo.preview_path.startsWith('http')) {
                previewUrl = photo.preview_path;
            } else {
                // Construct S3 URL from preview_path
                const s3BaseUrl = 'https://de45bff1c874-pixora-store.s3.ru1.storage.beget.cloud';
                previewUrl = `${s3BaseUrl}/${photo.preview_path}`;
            }
        } else {
            // Fallback: construct from session and file_name
            const s3BaseUrl = 'https://de45bff1c874-pixora-store.s3.ru1.storage.beget.cloud';
            previewUrl = `${s3BaseUrl}/staging/photos/${this.sessionId}/previews/${photo.file_name}`;
        }
        
        card.innerHTML = `
            <div class="photo-container relative">
                <img src="${previewUrl}" alt="Фото ${index + 1}" class="photo-image" loading="lazy">
                <div class="absolute top-3 right-3">
                    <span class="similarity-badge">
                        ${similarityPercent}%
                    </span>
                </div>
                <div class="absolute top-3 left-3">
                    <div class="photo-checkbox-container">
                        <input type="checkbox" class="pixora-checkbox" data-photo-id="${photo.id}">
                    </div>
                </div>
            </div>
            <div class="p-4">
                <div class="flex justify-between items-start mb-3">
                    <h3 class="font-semibold text-pixora-primary">Фото ${index + 1}</h3>
                    <span class="text-sm font-medium text-gradient-simple">Точность: ${similarityPercent}%</span>
                </div>
                <button class="w-full btn-pixora view-photo-btn font-medium">
                    <i class="fas fa-eye mr-2"></i>
                    Просмотреть
                </button>
            </div>
        `;
        
        // Add event listeners
        const checkbox = card.querySelector('.pixora-checkbox');
        const viewBtn = card.querySelector('.view-photo-btn');
        
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.selectedPhotos.add(photo.id);
                card.classList.add('selected');
            } else {
                this.selectedPhotos.delete(photo.id);
                card.classList.remove('selected');
            }
            this.updateSelectedCount();
        });
        
        viewBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showPhotoModal(photo, index);
        });
        
        card.addEventListener('click', () => {
            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event('change'));
        });
        
        return card;
    }

    showPhotoModal(photo, index) {
        // Use S3 URL from environment or construct from preview_path
        let previewUrl;
        if (photo.preview_path) {
            // If preview_path is a full URL, use it directly
            if (photo.preview_path.startsWith('http')) {
                previewUrl = photo.preview_path;
            } else {
                // Construct S3 URL from preview_path
                const s3BaseUrl = 'https://de45bff1c874-pixora-store.s3.ru1.storage.beget.cloud';
                previewUrl = `${s3BaseUrl}/${photo.preview_path}`;
            }
        } else {
            // Fallback: construct from session and file_name
            const s3BaseUrl = 'https://de45bff1c874-pixora-store.s3.ru1.storage.beget.cloud';
            previewUrl = `${s3BaseUrl}/staging/photos/${this.sessionId}/previews/${photo.file_name}`;
        }
        
        const similarityPercent = Math.round(photo.similarity * 100);
        
        this.modalImage.src = previewUrl;
        this.modalTitle.textContent = `Фото ${index + 1}`;
        this.modalSimilarity.innerHTML = `Точность: ${similarityPercent}%`;
        this.modalSimilarity.className = 'similarity-badge';
        
        // Update modal select button
        const isSelected = this.selectedPhotos.has(photo.id);
        this.modalSelectBtn.textContent = isSelected ? 'Убрать из выбранных' : 'Выбрать для покупки';
        this.modalSelectBtn.onclick = () => {
            const checkbox = document.querySelector(`input[data-photo-id="${photo.id}"]`);
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change'));
                this.modalSelectBtn.textContent = checkbox.checked ? 'Убрать из выбранных' : 'Выбрать для покупки';
            }
        };
        
        this.showModal(this.photoModal);
    }

    hidePhotoModal() {
        this.hideModal(this.photoModal);
    }

    selectAllPhotos() {
        const checkboxes = document.querySelectorAll('.pixora-checkbox[data-photo-id]');
        const cards = document.querySelectorAll('.photo-card-pixora');
        
        checkboxes.forEach((checkbox, index) => {
            checkbox.checked = true;
            this.selectedPhotos.add(checkbox.dataset.photoId);
            
            // Add visual selection state
            if (cards[index]) {
                cards[index].classList.add('selected');
            }
        });
        
        this.updateSelectedCount();
    }

    updateSelectedCount() {
        if (this.selectedCount) {
            this.selectedCount.textContent = this.selectedPhotos.size;
        }
    }

    buySelectedPhotos() {
        if (this.selectedPhotos.size === 0) {
            this.showToast('Выберите хотя бы одну фотографию', 'warning');
            return;
        }
        
        // Create purchase URL with selected photo IDs
        const selectedIds = Array.from(this.selectedPhotos);
        const purchaseUrl = `https://staging.pixorasoft.ru/purchase?session_id=${this.sessionId}&photos=${selectedIds.join(',')}`;
        
        // Open purchase page
        window.open(purchaseUrl, '_blank');
        
        this.showToast(`Переход к покупке ${this.selectedPhotos.size} фотографий`, 'success');
    }

    resetToHero() {
        // Hide all sections except hero
        this.hideSection(this.searchLoading);
        this.hideSection(this.noResults);
        this.hideSection(this.resultsSection);
        
        // Show hero and info sections
        this.showSection(this.heroSection);
        this.showSection(this.howItWorks);
        this.showSection(this.faqSection);
        
        // Clear results
        this.searchResults = [];
        this.selectedPhotos.clear();
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

    // Utility methods
    showSection(section) {
        if (section) {
            section.classList.remove('hidden');
        }
    }

    hideSection(section) {
        if (section) {
            section.classList.add('hidden');
        }
    }

    showModal(modal) {
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }

    hideModal(modal) {
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        
        // Check if mobile device for special positioning
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            toast.className = `pixora-toast fixed top-4 left-4 right-4 p-4 rounded-lg transform transition-all duration-300 translate-x-full z-50`;
        } else {
            toast.className = `pixora-toast p-4 rounded-lg transform transition-all duration-300 translate-x-full max-w-sm`;
        }
        
        // Add type-specific styling
        toast.classList.add(type);
        
        const icons = {
            success: '✅',
            error: '❌',
            info: 'ℹ️',
            warning: '⚠️'
        };
        
        toast.innerHTML = `
            <div class="flex items-center">
                <span class="mr-3 text-lg">${icons[type]}</span>
                <span class="flex-1 text-pixora-primary">${message}</span>
                <button onclick="this.closest('div').remove()" class="ml-3 text-pixora-secondary hover:text-pixora-primary">
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

// Initialize the session interface
document.addEventListener('DOMContentLoaded', () => {
    new FacePassSession();
});

// Add smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', () => {
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