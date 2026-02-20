/**
 * FacePass Session Interface with Pricing Integration
 * Integrates with Pixora API for services and pricing
 */

class FacePassSession {
    constructor() {
        this.sessionId = this.getSessionIdFromUrl();
        this.sessionData = null;
        this.servicesData = null;
        this.stream = null;
        this.selectedPhotos = new Set();
        this.searchResults = [];
        this.photoPrice = 0;
        this.priceAll = 0;
        this.defaultService = null;
        this.mainUrl = '';
        this.servicesLoading = true;
        this.servicesError = false;
        
        this.initializeElements();
        this.bindEvents();
        this.validateSession();
        this.loadServicesFromPixora();
    }

    getSessionIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        const sessionId = pathParts[pathParts.length - 1];
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
        this.totalPrice = document.getElementById('total-price');

        // Buttons
        this.cameraBtn = document.getElementById('camera-btn');
        this.uploadBtn = document.getElementById('upload-btn');
        this.tryAgainBtn = document.getElementById('try-again-btn');
        this.selectAllBtn = document.getElementById('select-all-btn');
        this.buySelectedBtn = document.getElementById('buy-selected-btn');
        this.buyArchiveBtn = document.getElementById('buy-archive-btn');

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
        
        // Floating bar
        this.floatingBar = document.getElementById('floating-bar');
    }

    bindEvents() {
        if (this.privacyAgreement) {
            this.privacyAgreement.addEventListener('change', () => this.toggleActionButtons());
        }
        
        this.cameraBtn.addEventListener('click', () => this.openCamera());
        this.uploadBtn.addEventListener('click', () => this.openFileDialog());
        
        this.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        if (this.fallbackInput) {
            this.fallbackInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }
        
        this.capturePhoto.addEventListener('click', () => this.capturePhotoFromCamera());
        this.cancelCamera.addEventListener('click', () => this.closeCamera());
        
        if (this.tryAgainBtn) {
            this.tryAgainBtn.addEventListener('click', () => this.resetToHero());
        }
        
        if (this.selectAllBtn) {
            this.selectAllBtn.addEventListener('click', () => this.selectAllPhotos());
        }
        if (this.buySelectedBtn) {
            this.buySelectedBtn.addEventListener('click', () => this.buySelectedPhotos());
        }
        if (this.buyArchiveBtn) {
            this.buyArchiveBtn.addEventListener('click', () => this.buyArchive());
        }
        
        if (this.closeModal) {
            this.closeModal.addEventListener('click', () => this.hidePhotoModal());
        }
        
        this.faqToggles.forEach(toggle => {
            toggle.addEventListener('click', () => this.toggleFAQ(toggle));
        });
        
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
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeCamera();
                this.hidePhotoModal();
            }
        });
    }

    async loadServicesFromPixora() {
        /**
         * Load services directly from Pixora main API
         * Always fetch fresh data - never use cached/local prices
         */
        this.servicesLoading = true;
        this.servicesError = false;
        
        try {
            // Get MAIN_API_URL from environment or use hardcoded fallback
            // Check if template variable wasn't replaced (contains {{ or }})
            let mainApiUrl = window.MAIN_API_URL && 
                            !window.MAIN_API_URL.includes('{{') && 
                            !window.MAIN_API_URL.includes('}}')
                ? window.MAIN_API_URL 
                : 'https://staging.pixorasoft.ru';
            
            // Ensure URL doesn't have trailing slash and starts with http
            mainApiUrl = mainApiUrl.replace(/\/$/, '');
            
            // Construct correct API path - ensure it's absolute URL
            const servicesUrl = `${mainApiUrl}/api/session/${this.sessionId}/services`;
            
            console.log('MAIN_API_URL from window:', window.MAIN_API_URL);
            console.log('Using API URL:', mainApiUrl);
            console.log('Fetching services from Pixora API:', servicesUrl);
            
            const response = await fetch(servicesUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
                // Add credentials if needed for CORS
                credentials: 'omit'
            });
            
            if (!response.ok) {
                console.warn(`Services API returned ${response.status}, running in view-only mode`);
                this.servicesLoading = false;
                this.servicesError = true;
                this.updateUIForViewOnlyMode();
                return;
            }

            const data = await response.json();
            console.log('Services loaded from Pixora:', data);
            
            this.servicesData = data;
            this.mainUrl = mainApiUrl;
            
            // Extract prices using helper function
            const prices = this.getServicePrices(data.services || []);
            this.photoPrice = prices.price_single;
            this.priceAll = prices.price_all;
            this.defaultService = data.services?.find(s => s.isDefault);
            
            this.servicesLoading = false;
            
            console.log('Pricing configured:', {
                photoPrice: this.photoPrice,
                priceAll: this.priceAll,
                defaultService: this.defaultService,
                mainUrl: this.mainUrl
            });
            
            // Update UI if results are already displayed
            if (this.searchResults.length > 0) {
                this.updateFloatingBar();
            }
            
        } catch (error) {
            console.error('Error loading services from Pixora:', error);
            this.servicesLoading = false;
            this.servicesError = true;
            this.updateUIForViewOnlyMode();
        }
    }

    getServicePrices(services) {
        /**
         * Extract pricing from services array
         * Returns: { price_single, price_all }
         */
        if (!services || services.length === 0) {
            return { price_single: 0, price_all: 0 };
        }
        
        // Find default service (full archive)
        const defaultService = services.find(s => s.isDefault === true);
        const price_all = defaultService ? defaultService.price : 0;
        
        // Find single photo service (digital copy)
        // Priority: 1) type='digital', 2) name contains 'цифровая' or 'digital', 3) first service
        let singleService = services.find(s => 
            s.type === 'digital' || 
            s.type === 'single' ||
            s.name?.toLowerCase().includes('цифровая') ||
            s.name?.toLowerCase().includes('digital') ||
            s.name?.toLowerCase().includes('копия')
        );
        
        // Fallback to first non-default service
        if (!singleService) {
            singleService = services.find(s => !s.isDefault);
        }
        
        // Last resort: use first service
        if (!singleService && services.length > 0) {
            singleService = services[0];
        }
        
        const price_single = singleService ? singleService.price : 0;
        
        console.log('Extracted prices:', {
            price_single,
            price_all,
            singleService: singleService?.name,
            defaultService: defaultService?.name
        });
        
        return { price_single, price_all };
    }

    updateUIForViewOnlyMode() {
        /**
         * Update UI when services are not available
         * Hide pricing elements, show view-only mode
         */
        console.log('Running in view-only mode (no pricing available)');
        
        // Hide floating bar if it exists
        if (this.floatingBar) {
            this.floatingBar.classList.add('hidden');
        }
        
        // Remove price badges from existing cards
        document.querySelectorAll('.price-badge').forEach(badge => {
            badge.style.display = 'none';
        });
    }

    async validateSession() {
        if (!this.sessionId || this.sessionId === 'session') {
            this.showError('Неверный ID сессии');
            return;
        }

        try {
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
                <span class="text-gradient">
                    фотосессии по лицу
                </span>
                <br><br>
                <span class="text-2xl sm:text-3xl lg:text-4xl font-semibold text-pixora-primary">
                    "${this.sessionData.session_name}"
                </span>
            `;
        }
    }

    showError(message) {
        this.showToast(message, 'error');
        if (this.sessionTitle) {
            this.sessionTitle.innerHTML = `
                <span class="text-red-600">Ошибка: ${message}</span>
            `;
        }
    }

    toggleActionButtons() {
        const isAgreed = this.privacyAgreement && this.privacyAgreement.checked;
        
        [this.cameraBtn, this.uploadBtn].forEach(btn => {
            if (isAgreed) {
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
                btn.classList.add('hover:shadow-lg', 'hover:-translate-y-1');
            } else {
                btn.disabled = true;
                btn.classList.add('opacity-50', 'cursor-not-allowed');
                btn.classList.remove('hover:shadow-lg', 'hover:-translate-y-1');
            }
        });
    }

    // Camera functionality
    async openCamera() {
        if (!this.privacyAgreement || !this.privacyAgreement.checked) {
            this.showToast('Пожалуйста, примите условия обработки персональных данных', 'warning');
            return;
        }
        
        const isAndroidChrome = /Android.*Chrome/.test(navigator.userAgent);
        let cameraTimeout;
        
        if (isAndroidChrome) {
            cameraTimeout = setTimeout(() => {
                this.showAndroidCameraFallback();
            }, 2000);
        }
        
        try {
            const constraints = {
                video: {
                    width: { ideal: 640, max: 1280 },
                    height: { ideal: 480, max: 720 },
                    facingMode: "user",
                    aspectRatio: { ideal: 1.33 }
                },
                audio: false
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            if (cameraTimeout) {
                clearTimeout(cameraTimeout);
            }
            
            this.cameraVideo.srcObject = this.stream;
            this.showModal(this.cameraModal);
            
        } catch (error) {
            console.error('Camera error:', error);
            
            if (cameraTimeout) {
                clearTimeout(cameraTimeout);
            }
            
            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                this.showCameraPermissionError();
            } else {
                this.showToast('Не удалось получить доступ к камере', 'error');
                this.showCameraFallback();
            }
        }
    }

    showAndroidCameraFallback() {
        this.showToast('Нажмите "Загрузить фото" и выберите "Камера"', 'info');
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

    openFileDialog() {
        if (!this.privacyAgreement || !this.privacyAgreement.checked) {
            this.showToast('Пожалуйста, примите условия обработки персональных данных', 'warning');
            return;
        }
        
        const isAndroid = /Android/.test(navigator.userAgent);
        if (isAndroid) {
            this.fileInput.setAttribute('capture', 'user');
            this.fileInput.setAttribute('accept', 'image/*');
        }
        
        this.fileInput.click();
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('image/')) {
            this.showMobileLoadingIndicator('Обработка изображения...');
            
            const maxSize = 10 * 1024 * 1024;
            if (file.size > maxSize) {
                this.hideMobileLoadingIndicator();
                this.showToast('Файл слишком большой. Максимальный размер: 10MB', 'error');
                return;
            }
            
            setTimeout(() => {
                this.processPhoto(file, file.name);
            }, 100);
        } else {
            this.showToast('Пожалуйста, выберите изображение', 'error');
        }
        event.target.value = '';
    }

    showMobileLoadingIndicator(message = 'Подготовка к поиску...') {
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

    async processPhoto(imageBlob, fileName) {
        this.hideMobileLoadingIndicator();
        
        this.hideSection(this.heroSection);
        this.hideSection(this.howItWorks);
        this.hideSection(this.faqSection);
        this.showSection(this.searchLoading);
        
        try {
            const formData = new FormData();
            formData.append('file', imageBlob, fileName);
            formData.append('session_id', this.sessionId);
            formData.append('threshold', '0.5');
            formData.append('limit', '50');
            
            const response = await fetch('/api/v1/faces/search-session', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'Ошибка поиска');
            }
            
            this.hideSection(this.searchLoading);
            
            if (result.matches && result.matches.length > 0) {
                this.searchResults = result.matches;
                this.displayResults();
            } else {
                this.showSection(this.noResults);
            }
            
        } catch (error) {
            console.error('Search error:', error);
            this.hideSection(this.searchLoading);
            this.hideMobileLoadingIndicator();
            this.showToast('Не удалось распознать изображение. Попробуйте другое селфи.', 'error');
            this.resetToHero();
        }
    }

    displayResults() {
        this.showSection(this.resultsSection);
        
        this.resultsCount.textContent = `Найдено ${this.searchResults.length} фотографий с вашим лицом`;
        
        this.photosGrid.innerHTML = '';
        this.selectedPhotos.clear();
        
        this.searchResults.forEach((photo, index) => {
            const photoCard = this.createPhotoCard(photo, index);
            this.photosGrid.appendChild(photoCard);
        });
        
        this.updateSelectedCount();
        this.updateFloatingBar();
    }

    createPhotoCard(photo, index) {
        const card = document.createElement('div');
        card.className = 'photo-card-pixora cursor-pointer';
        card.dataset.photoId = photo.id;
        card.dataset.index = index;
        
        const similarityPercent = Math.round(photo.similarity * 100);
        
        let previewUrl;
        if (photo.preview_path) {
            if (photo.preview_path.startsWith('http')) {
                previewUrl = photo.preview_path;
            } else {
                const s3BaseUrl = 'https://de45bff1c874-pixora-store.s3.ru1.storage.beget.cloud';
                previewUrl = `${s3BaseUrl}/${photo.preview_path}`;
            }
        } else {
            const s3BaseUrl = 'https://de45bff1c874-pixora-store.s3.ru1.storage.beget.cloud';
            previewUrl = `${s3BaseUrl}/staging/photos/${this.sessionId}/previews/${photo.file_name}`;
        }
        
        // Price badge HTML - show skeleton while loading, hide if no pricing
        let priceBadge = '';
        if (this.servicesLoading) {
            // Skeleton loader
            priceBadge = `
                <div class="absolute top-3 left-3">
                    <div class="price-badge-skeleton bg-gray-300 animate-pulse rounded-full" style="width: 60px; height: 28px;"></div>
                </div>
            `;
        } else if (this.photoPrice > 0 && !this.servicesError) {
            // Actual price
            priceBadge = `
                <div class="absolute top-3 left-3">
                    <span class="price-badge bg-gradient-to-r from-indigo-500 to-purple-600 text-white px-3 py-1 rounded-full text-sm font-semibold shadow-lg">
                        ${this.photoPrice} ₽
                    </span>
                </div>
            `;
        }
        // else: no pricing available, don't show badge
        
        card.innerHTML = `
            <div class="photo-container relative">
                <img src="${previewUrl}" alt="Фото ${index + 1}" class="photo-image" loading="lazy">
                ${priceBadge}
                <div class="absolute top-3 right-3">
                    <span class="similarity-badge">
                        ${similarityPercent}%
                    </span>
                </div>
                <div class="absolute bottom-3 left-3">
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
            this.updateFloatingBar();
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
        let previewUrl;
        if (photo.preview_path) {
            if (photo.preview_path.startsWith('http')) {
                previewUrl = photo.preview_path;
            } else {
                const s3BaseUrl = 'https://de45bff1c874-pixora-store.s3.ru1.storage.beget.cloud';
                previewUrl = `${s3BaseUrl}/${photo.preview_path}`;
            }
        } else {
            const s3BaseUrl = 'https://de45bff1c874-pixora-store.s3.ru1.storage.beget.cloud';
            previewUrl = `${s3BaseUrl}/staging/photos/${this.sessionId}/previews/${photo.file_name}`;
        }
        
        const similarityPercent = Math.round(photo.similarity * 100);
        
        this.modalImage.src = previewUrl;
        this.modalTitle.textContent = `Фото ${index + 1}`;
        this.modalSimilarity.innerHTML = `Точность: ${similarityPercent}%`;
        this.modalSimilarity.className = 'similarity-badge';
        
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
            
            if (cards[index]) {
                cards[index].classList.add('selected');
            }
        });
        
        this.updateSelectedCount();
        this.updateFloatingBar();
    }

    updateSelectedCount() {
        if (this.selectedCount) {
            this.selectedCount.textContent = this.selectedPhotos.size;
        }
        if (this.totalPrice) {
            const total = this.selectedPhotos.size * this.photoPrice;
            this.totalPrice.textContent = total.toFixed(0);
        }
    }

    updateFloatingBar() {
        if (!this.floatingBar) return;
        
        // Show floating bar only if:
        // 1. We have search results
        // 2. Services are loaded (not loading)
        // 3. We have valid pricing (photoPrice > 0)
        // 4. No services error
        const shouldShow = this.searchResults.length > 0 && 
                          !this.servicesLoading && 
                          this.photoPrice > 0 && 
                          !this.servicesError;
        
        if (shouldShow) {
            this.floatingBar.classList.remove('hidden');
        } else {
            this.floatingBar.classList.add('hidden');
        }
        
        // Update button states
        if (this.buySelectedBtn) {
            this.buySelectedBtn.disabled = this.selectedPhotos.size === 0;
        }
        
        if (this.buyArchiveBtn) {
            // Disable if no default service or price_all is 0
            this.buyArchiveBtn.disabled = !this.defaultService || this.priceAll === 0;
        }
    }

    buySelectedPhotos() {
        if (this.selectedPhotos.size === 0) {
            this.showToast('Выберите хотя бы одну фотографию', 'warning');
            return;
        }
        
        const selectedIds = Array.from(this.selectedPhotos);
        const purchaseUrl = `${this.mainUrl}/session/${this.sessionId}/cart?selected=${selectedIds.join(',')}&source=facepass`;
        
        window.location.href = purchaseUrl;
        
        this.showToast(`Переход к покупке ${this.selectedPhotos.size} фотографий`, 'success');
    }

    buyArchive() {
        if (!this.defaultService) {
            this.showToast('Услуга недоступна', 'warning');
            return;
        }
        
        const purchaseUrl = `${this.mainUrl}/session/${this.sessionId}/cart?package=digital&source=facepass`;
        
        window.location.href = purchaseUrl;
        
        this.showToast('Переход к покупке всего архива', 'success');
    }

    resetToHero() {
        this.hideSection(this.searchLoading);
        this.hideSection(this.noResults);
        this.hideSection(this.resultsSection);
        
        this.showSection(this.heroSection);
        this.showSection(this.howItWorks);
        this.showSection(this.faqSection);
        
        this.searchResults = [];
        this.selectedPhotos.clear();
        this.updateFloatingBar();
    }

    toggleFAQ(toggle) {
        const content = toggle.nextElementSibling;
        const icon = toggle.querySelector('i');
        
        if (content.classList.contains('hidden')) {
            this.faqToggles.forEach(otherToggle => {
                if (otherToggle !== toggle) {
                    const otherContent = otherToggle.nextElementSibling;
                    const otherIcon = otherToggle.querySelector('i');
                    otherContent.classList.add('hidden');
                    otherIcon.style.transform = 'rotate(0deg)';
                }
            });
            
            content.classList.remove('hidden');
            icon.style.transform = 'rotate(180deg)';
        } else {
            content.classList.add('hidden');
            icon.style.transform = 'rotate(0deg)';
        }
    }

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
        
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            toast.className = `pixora-toast fixed top-4 left-4 right-4 p-4 rounded-lg transform transition-all duration-300 translate-x-full z-50`;
        } else {
            toast.className = `pixora-toast p-4 rounded-lg transform transition-all duration-300 translate-x-full max-w-sm`;
        }
        
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
        
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 100);
        
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    new FacePassSession();
});

// Smooth scrolling
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
    
    // Header scroll effect
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
