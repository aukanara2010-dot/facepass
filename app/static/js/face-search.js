/**
 * FacePass Interactive Photo Search Interface
 * Inspired by super.photo UI/UX
 */

class FacePassGallery {
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
        const urlParams = new URLSearchParams(window.location.search);
        const pathId = window.location.pathname.split('/').pop();
        const sessionId = urlParams.get('id') || pathId;
        
        console.log('URL pathname:', window.location.pathname);
        console.log('URL search params:', window.location.search);
        console.log('Path ID:', pathId);
        console.log('Session ID from URL params:', urlParams.get('id'));
        console.log('Final session ID:', sessionId);
        
        return sessionId;
    }

    initializeElements() {
        // States
        this.loadingState = document.getElementById('loading-state');
        this.errorState = document.getElementById('error-state');
        this.mainInterface = document.getElementById('main-interface');
        this.heroSection = document.getElementById('hero-section');
        this.cameraSection = document.getElementById('camera-section');
        this.searchLoading = document.getElementById('search-loading');
        this.noResults = document.getElementById('no-results');
        this.resultsSection = document.getElementById('results-section');

        // Elements
        this.errorMessage = document.getElementById('error-message');
        this.sessionTitle = document.getElementById('session-title');
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.fileInput = document.getElementById('file-input');
        this.photosGrid = document.getElementById('photos-grid');
        this.resultsCount = document.getElementById('results-count');
        this.selectedCount = document.getElementById('selected-count');

        // Buttons
        this.cameraBtn = document.getElementById('camera-btn');
        this.uploadBtn = document.getElementById('upload-btn');
        this.captureBtn = document.getElementById('capture-btn');
        this.cancelCameraBtn = document.getElementById('cancel-camera-btn');
        this.tryAgainBtn = document.getElementById('try-again-btn');
        this.selectAllBtn = document.getElementById('select-all-btn');
        this.buySelectedBtn = document.getElementById('buy-selected-btn');

        // Modal
        this.photoModal = document.getElementById('photo-modal');
        this.modalImage = document.getElementById('modal-image');
        this.modalTitle = document.getElementById('modal-title');
        this.modalSimilarity = document.getElementById('modal-similarity');
        this.modalSelectBtn = document.getElementById('modal-select-btn');
        this.closeModal = document.getElementById('close-modal');

        // Toast container
        this.toastContainer = document.getElementById('toast-container');
    }

    bindEvents() {
        this.cameraBtn.addEventListener('click', () => this.startCamera());
        this.uploadBtn.addEventListener('click', () => this.fileInput.click());
        this.captureBtn.addEventListener('click', () => this.capturePhoto());
        this.cancelCameraBtn.addEventListener('click', () => this.stopCamera());
        this.tryAgainBtn.addEventListener('click', () => this.resetToHero());
        this.selectAllBtn.addEventListener('click', () => this.selectAllPhotos());
        this.buySelectedBtn.addEventListener('click', () => this.buySelectedPhotos());
        
        this.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        this.closeModal.addEventListener('click', () => this.hideModal());
        
        // Close modal on backdrop click
        this.photoModal.addEventListener('click', (e) => {
            if (e.target === this.photoModal) {
                this.hideModal();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideModal();
            }
        });
    }

    async validateSession() {
        this.showState('loading');
        
        try {
            const response = await fetch(`/api/v1/sessions/validate/${this.sessionId}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Ошибка сервера');
            }
            
            if (!data.valid) {
                this.showError(data.error || 'Сессия недоступна');
                return;
            }
            
            this.sessionData = data.session;
            this.sessionTitle.textContent = `Найдите себя на фотосессии "${data.session.name}"!`;
            this.showState('main');
            
        } catch (error) {
            console.error('Session validation error:', error);
            this.showError('Не удалось проверить сессию. Проверьте подключение к интернету.');
        }
    }

    showState(state) {
        // Hide all states
        this.loadingState.classList.add('hidden');
        this.errorState.classList.add('hidden');
        this.mainInterface.classList.add('hidden');
        this.heroSection.classList.add('hidden');
        this.cameraSection.classList.add('hidden');
        this.searchLoading.classList.add('hidden');
        this.noResults.classList.add('hidden');
        this.resultsSection.classList.add('hidden');

        // Show requested state
        switch (state) {
            case 'loading':
                this.loadingState.classList.remove('hidden');
                break;
            case 'error':
                this.errorState.classList.remove('hidden');
                break;
            case 'main':
                this.mainInterface.classList.remove('hidden');
                this.heroSection.classList.remove('hidden');
                break;
            case 'camera':
                this.mainInterface.classList.remove('hidden');
                this.cameraSection.classList.remove('hidden');
                break;
            case 'searching':
                this.mainInterface.classList.remove('hidden');
                this.searchLoading.classList.remove('hidden');
                break;
            case 'no-results':
                this.mainInterface.classList.remove('hidden');
                this.noResults.classList.remove('hidden');
                break;
            case 'results':
                this.mainInterface.classList.remove('hidden');
                this.resultsSection.classList.remove('hidden');
                break;
        }
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.showState('error');
    }

    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            });
            
            this.video.srcObject = this.stream;
            this.showState('camera');
            
        } catch (error) {
            console.error('Camera error:', error);
            this.showToast('Не удалось получить доступ к камере. Проверьте разрешения.', 'error');
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.showState('main');
    }

    capturePhoto() {
        if (!this.stream) return;

        const canvas = this.canvas;
        const context = canvas.getContext('2d');
        
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;
        
        context.drawImage(this.video, 0, 0);
        
        canvas.toBlob((blob) => {
            this.stopCamera();
            this.searchFaces(blob);
        }, 'image/jpeg', 0.95);
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('image/')) {
            this.searchFaces(file);
        }
        // Reset file input
        event.target.value = '';
    }

    async searchFaces(imageBlob) {
        this.showState('searching');
        
        try {
            const formData = new FormData();
            formData.append('file', imageBlob, 'search_image.jpg');
            formData.append('session_id', this.sessionId);
            formData.append('threshold', '0.6'); // Lower threshold for better results
            formData.append('limit', '50');
            
            // Show indexing status if needed
            this.updateSearchStatus('Обрабатываем ваше селфи...');
            
            const response = await fetch('/api/v1/faces/search-session', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                // Handle timeout specifically
                if (response.status === 408) {
                    this.showToast('Обработка заняла слишком много времени. Попробуйте позже.', 'error');
                    this.showState('main');
                    return;
                }
                throw new Error(result.detail || 'Ошибка поиска');
            }
            
            // Handle indexing status
            if (result.indexing_status) {
                this.handleIndexingStatus(result);
            }
            
            // Log API response for debugging
            console.log('Search API response:', {
                session_id: result.session_id,
                matches_count: result.matches ? result.matches.length : 0,
                indexing_status: result.indexing_status
            });
            
            if (result.matches && result.matches.length > 0) {
                this.displayResults(result.matches);
                
                // Show indexing info if it happened
                if (result.indexing_status === 'completed' && result.indexing_progress) {
                    const progress = result.indexing_progress;
                    this.showToast(
                        `Проиндексировано ${progress.successful_photos} фотографий за ${Math.round(progress.indexing_time_seconds)}с`, 
                        'success'
                    );
                }
            } else {
                this.showState('no-results');
                
                // Show helpful message if indexing failed
                if (result.indexing_status === 'indexing_failed') {
                    this.showToast('Не удалось обработать фотографии сессии. Попробуйте позже.', 'error');
                }
            }
            
        } catch (error) {
            console.error('Search error:', error);
            this.showToast('Ошибка при поиске фотографий. Попробуйте еще раз.', 'error');
            this.showState('main');
        }
    }
    
    handleIndexingStatus(result) {
        const status = result.indexing_status;
        const progress = result.indexing_progress;
        
        switch (status) {
            case 'indexing':
            case 'completed':
                if (progress && progress.total_photos) {
                    this.updateSearchStatus(
                        `Индексируем ${progress.total_photos} фотографий... Это может занять несколько минут.`
                    );
                }
                break;
                
            case 'already_indexed':
                this.updateSearchStatus('Ищем ваши фотографии...');
                break;
                
            case 'no_photos':
                this.updateSearchStatus('В этой сессии нет фотографий.');
                break;
                
            case 'scan_error':
            case 'indexing_error':
                this.updateSearchStatus('Ошибка при обработке фотографий.');
                break;
                
            default:
                this.updateSearchStatus('Обрабатываем запрос...');
        }
    }
    
    updateSearchStatus(message) {
        const searchingDiv = this.searchLoading; // Используем правильную ссылку на элемент
        if (searchingDiv) {
            const statusElement = searchingDiv.querySelector('.status-message');
            if (statusElement) {
                // Сохраняем анимацию точек для некоторых сообщений
                if (message.includes('Ищем') || message.includes('анализирует') || message.includes('Обрабатываем')) {
                    statusElement.innerHTML = message + '<span class="loading-dots"></span>';
                } else {
                    statusElement.textContent = message;
                }
            }
        }
    }

    displayResults(matches) {
        this.searchResults = matches.sort((a, b) => b.similarity - a.similarity);
        this.selectedPhotos.clear();
        
        this.resultsCount.textContent = `Найдено ${matches.length} фотографий`;
        this.photosGrid.innerHTML = '';
        
        matches.forEach((photo, index) => {
            const photoCard = this.createPhotoCard(photo, index);
            this.photosGrid.appendChild(photoCard);
        });
        
        this.updateSelectedCount();
        this.showState('results');
        
        // Animate cards appearance
        setTimeout(() => {
            const cards = this.photosGrid.querySelectorAll('.photo-card');
            cards.forEach((card, index) => {
                setTimeout(() => {
                    card.classList.add('animate-slide-up');
                }, index * 100);
            });
        }, 100);
    }

    createPhotoCard(photo, index) {
        const card = document.createElement('div');
        card.className = 'photo-card bg-white rounded-xl overflow-hidden shadow-lg cursor-pointer transform transition-all duration-300';
        
        const similarityPercent = Math.round(photo.similarity * 100);
        const isSelected = this.selectedPhotos.has(photo.id);
        
        card.innerHTML = `
            <div class="relative">
                <img src="${photo.preview_path || photo.file_path}" 
                     alt="Фото ${index + 1}" 
                     class="w-full h-48 object-cover"
                     loading="lazy">
                <div class="absolute top-2 right-2">
                    <span class="similarity-badge text-white px-2 py-1 rounded-full text-xs font-semibold">
                        ${similarityPercent}%
                    </span>
                </div>
                <div class="absolute top-2 left-2">
                    <input type="checkbox" 
                           class="photo-checkbox w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
                           ${isSelected ? 'checked' : ''}
                           data-photo-id="${photo.id}">
                </div>
            </div>
            <div class="p-4">
                <div class="flex justify-between items-center">
                    <span class="text-sm text-gray-600">Схожесть: ${similarityPercent}%</span>
                    <button class="select-photo-btn bg-purple-600 text-white px-3 py-1 rounded-lg text-sm hover:bg-purple-700 transition-colors"
                            data-photo-id="${photo.id}">
                        ${isSelected ? 'Убрать' : 'Выбрать'}
                    </button>
                </div>
            </div>
        `;
        
        // Event listeners
        const img = card.querySelector('img');
        const checkbox = card.querySelector('.photo-checkbox');
        const selectBtn = card.querySelector('.select-photo-btn');
        
        img.addEventListener('click', () => this.showModal(photo));
        
        checkbox.addEventListener('change', () => {
            this.togglePhotoSelection(photo.id);
            selectBtn.textContent = checkbox.checked ? 'Убрать' : 'Выбрать';
        });
        
        selectBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.togglePhotoSelection(photo.id);
            checkbox.checked = this.selectedPhotos.has(photo.id);
            selectBtn.textContent = checkbox.checked ? 'Убрать' : 'Выбрать';
        });
        
        return card;
    }

    showModal(photo) {
        this.modalImage.src = photo.preview_path || photo.file_path;
        this.modalTitle.textContent = `Фото - Схожесть ${Math.round(photo.similarity * 100)}%`;
        this.modalSimilarity.textContent = `${Math.round(photo.similarity * 100)}% схожести`;
        
        this.modalSelectBtn.onclick = () => {
            this.togglePhotoSelection(photo.id);
            this.updatePhotoCard(photo.id);
            this.modalSelectBtn.textContent = this.selectedPhotos.has(photo.id) ? 'Убрать из выбранных' : 'Выбрать для покупки';
        };
        
        this.modalSelectBtn.textContent = this.selectedPhotos.has(photo.id) ? 'Убрать из выбранных' : 'Выбрать для покупки';
        this.photoModal.classList.remove('hidden');
    }

    hideModal() {
        this.photoModal.classList.add('hidden');
    }

    togglePhotoSelection(photoId) {
        if (this.selectedPhotos.has(photoId)) {
            this.selectedPhotos.delete(photoId);
        } else {
            this.selectedPhotos.add(photoId);
        }
        this.updateSelectedCount();
    }

    updatePhotoCard(photoId) {
        const checkbox = document.querySelector(`input[data-photo-id="${photoId}"]`);
        const selectBtn = document.querySelector(`button[data-photo-id="${photoId}"]`);
        
        if (checkbox && selectBtn) {
            checkbox.checked = this.selectedPhotos.has(photoId);
            selectBtn.textContent = checkbox.checked ? 'Убрать' : 'Выбрать';
        }
    }

    updateSelectedCount() {
        this.selectedCount.textContent = this.selectedPhotos.size;
        this.buySelectedBtn.disabled = this.selectedPhotos.size === 0;
        
        if (this.selectedPhotos.size === 0) {
            this.buySelectedBtn.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            this.buySelectedBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }

    selectAllPhotos() {
        this.searchResults.forEach(photo => {
            this.selectedPhotos.add(photo.id);
        });
        
        // Update all checkboxes and buttons
        this.searchResults.forEach(photo => {
            this.updatePhotoCard(photo.id);
        });
        
        this.updateSelectedCount();
        this.showToast(`Выбрано ${this.selectedPhotos.size} фотографий`, 'success');
    }

    buySelectedPhotos() {
        if (this.selectedPhotos.size === 0) return;
        
        console.log('Current session ID for purchase:', this.sessionId);
        
        if (!this.sessionId || this.sessionId === 'undefined') {
            this.showToast('Ошибка: ID сессии не найден. Обновите страницу.', 'error');
            return;
        }
        
        const selectedFileNames = this.searchResults
            .filter(photo => this.selectedPhotos.has(photo.id))
            .map(photo => photo.file_name || photo.id)
            .join(',');
        
        // Use staging domain for now, will be changed to production later
        const purchaseUrl = `https://staging.pixorasoft.ru/session/${this.sessionId}?selected=${selectedFileNames}`;
        
        console.log('Purchase URL:', purchaseUrl);
        
        this.showToast(`Перенаправление на страницу покупки...`, 'info');
        
        setTimeout(() => {
            window.open(purchaseUrl, '_blank');
        }, 1000);
    }

    resetToHero() {
        this.selectedPhotos.clear();
        this.searchResults = [];
        this.showState('main');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast bg-white border-l-4 p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full`;
        
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
                <span class="mr-2">${icons[type]}</span>
                <span>${message}</span>
                <button class="ml-4 text-gray-400 hover:text-gray-600" onclick="this.parentElement.parentElement.remove()">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
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
            toast.classList.add('translate-x-full');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 300);
        }, 5000);
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new FacePassGallery();
});