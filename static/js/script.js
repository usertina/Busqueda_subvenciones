// JavaScript moderno para SubvencionesFinder - Versión completa corregida
class Subvenciones {
    constructor() {
        this.init();
        this.setupEventListeners();
        this.setupAnimations();
        this.setupMobileOptimizations();
        this.setupLiveFiltering();
    }

    init() {
        console.log('🚀 SubvencionesFinder iniciado');
        this.initTooltips();
        this.setupThemeToggle();
        this.setupLazyLoading();
        this.setupServiceWorker();
        this.setupRegionFilter(); // Filtro de país y comunidad
    }

    initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(el => new bootstrap.Tooltip(el, { trigger: 'hover focus', delay: { show: 200, hide: 100 } }));
    }

    setupEventListeners() {
        this.setupSearchForm();
        this.setupGrantCards();
        this.setupFilters();
        this.setupExportHandlers();
        this.setupLiveSearch();
        this.setupNavigation();
        this.setupResultPageEvents();
        this.setupIndexPageEvents();
    }

    // ---------------------- FORMULARIO ----------------------
    setupSearchForm() {
        const searchForm = document.getElementById('searchForm');
        if (!searchForm) return;

        searchForm.addEventListener('submit', (e) => this.handleFormSubmit(e, searchForm));

        // Validación en tiempo real
        searchForm.querySelectorAll('select[required]').forEach(field =>
            field.addEventListener('change', () => this.validateForm(searchForm))
        );

        // Persistencia en localStorage
        if (typeof Storage !== 'undefined') this.setupFormPersistence(searchForm);
    }

    handleFormSubmit(e, form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (!this.validateForm(form)) {
            e.preventDefault();
            this.showNotification('Por favor, completa todos los campos requeridos', 'warning');
            return;
        }

        this.showLoadingState(submitBtn);
        if (window.SubvencionesFinder && window.SubvencionesFinder.showLoading) window.SubvencionesFinder.showLoading(true);
        this.showSearchProgress(form);

        setTimeout(() => this.hideLoadingState(submitBtn), 45000); // Timeout máximo
    }

    validateForm(form) {
        let isValid = true;
        form.querySelectorAll('select[required]').forEach(field => {
            if (!field.value || field.value === '') {
                isValid = false;
                field.classList.add('is-invalid');
            } else field.classList.remove('is-invalid');
        });

        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = !isValid;
            submitBtn.classList.toggle('btn-primary', isValid);
            submitBtn.classList.toggle('btn-secondary', !isValid);
        }

        this.showFieldProgress(form);
        return isValid;
    }

    setupFormPersistence(form) {
        const formId = form.id || 'searchForm';
        const savedData = localStorage.getItem(formId);
        if (savedData) {
            try {
                const data = JSON.parse(savedData);
                Object.keys(data).forEach(key => {
                    const field = form.querySelector(`[name="${key}"]`);
                    if (field) field.value = data[key];
                });
                this.validateForm(form);
                // Llamar a updateRegionAvailability después de cargar los datos
                setTimeout(() => this.updateRegionAvailability(), 100);
            } catch (e) { console.warn('Error cargando datos guardados:', e); }
        }

        form.addEventListener('change', (e) => {
            if (['SELECT', 'INPUT'].includes(e.target.tagName)) {
                const data = Object.fromEntries(new FormData(form));
                localStorage.setItem(formId, JSON.stringify(data));
                this.applyAllFilters(); // Aplicar filtros combinados en tiempo real
            }
        });
    }

    // ---------------------- FILTROS EN TIEMPO REAL ----------------------
    setupRegionFilter() {
        this.countrySelect = document.querySelector('select[name="location"]');
        this.regionSelect = document.querySelector('select[name="region"]');
        this.grantItems = document.querySelectorAll('.grant-item');

        // Buscar contenedores alternativos si no existen
        if (!this.countrySelect) this.countrySelect = document.getElementById('location');
        if (!this.regionSelect) this.regionSelect = document.getElementById('region');

        if (!this.countrySelect || !this.regionSelect) {
            console.warn('No se encontraron selectores de ubicación/región');
            return;
        }

        // Mostrar/ocultar regiones según país seleccionado
        this.countrySelect.addEventListener('change', () => {
            this.updateRegionAvailability();
            this.applyLocationFilter();
        });

        this.regionSelect.addEventListener('change', () => {
            this.applyLocationFilter();
        });

        // Configuración inicial
        this.updateRegionAvailability();
    }

    updateRegionAvailability() {
        const selectedCountry = this.countrySelect.value;
        
        // Buscar diferentes posibles contenedores
        let regionContainer = document.getElementById('regionContainer') || 
                             document.getElementById('regionRow') ||
                             this.regionSelect?.closest('.col-md-4') ||
                             this.regionSelect?.closest('.form-floating-modern');

        console.log('País seleccionado:', selectedCountry);
        console.log('Contenedor de región:', regionContainer);

        if (selectedCountry === 'España' || selectedCountry === 'Todas') {
            // Mostrar selector de comunidades autónomas
            if (regionContainer) {
                regionContainer.style.display = 'block';
                regionContainer.style.opacity = '0';
                
                // Animación suave
                setTimeout(() => {
                    regionContainer.style.opacity = '1';
                }, 50);
                
                this.regionSelect.disabled = false;
                this.regionSelect.required = false; // Opcional
                
                // Mostrar notificación solo para España específicamente
                if (selectedCountry === 'España') {
                    this.showNotification('Ahora puedes seleccionar una Comunidad Autónoma específica', 'info');
                }
            } else {
                console.warn('No se encontró el contenedor de regiones');
            }
        } else {
            // Ocultar selector de comunidades
            if (regionContainer) {
                regionContainer.style.opacity = '0';
                
                setTimeout(() => {
                    regionContainer.style.display = 'none';
                    this.regionSelect.value = 'Todas';
                }, 300);
                
                this.regionSelect.disabled = true;
            }
        }

        // Re-validar formulario después del cambio
        const form = this.countrySelect.closest('form');
        if (form) {
            setTimeout(() => this.validateForm(form), 100);
        }
    }

    // Aplicar filtro de ubicación
    applyLocationFilter() {
        const selectedCountry = this.countrySelect?.value || 'Todas';
        const selectedRegion = this.regionSelect?.value || 'Todas';

        // Si tenemos resultados cargados, filtrarlos
        if (this.grantItems && this.grantItems.length > 0) {
            this.grantItems.forEach(item => {
                let show = true;

                const itemLocation = item.dataset.location || '';
                const itemRegion = item.dataset.region || '';

                // Filtro por país
                if (selectedCountry !== 'Todas') {
                    if (selectedCountry === 'España' && !this.isSpanishLocation(itemLocation)) {
                        show = false;
                    } else if (selectedCountry === 'UE' && !this.isEuropeanLocation(itemLocation)) {
                        show = false;
                    } else if (selectedCountry === 'Internacional' && !this.isInternationalLocation(itemLocation)) {
                        show = false;
                    }
                }

                // Filtro por región española
                if (show && selectedCountry === 'España' && selectedRegion !== 'Todas') {
                    if (itemRegion !== selectedRegion && !this.matchesRegion(itemLocation, selectedRegion)) {
                        show = false;
                    }
                }

                item.style.display = show ? '' : 'none';
            });

            this.updateVisibleCount();
        }
    }

    // Métodos auxiliares de ubicación
    isSpanishLocation(location) {
        const spanishKeywords = [
            'españa', 'madrid', 'barcelona', 'valencia', 'sevilla',
            'andalucía', 'cataluña', 'galicia', 'país vasco', 'aragón',
            'castilla', 'extremadura', 'murcia', 'canarias', 'baleares',
            'asturias', 'cantabria', 'navarra', 'rioja', 'ceuta', 'melilla'
        ];

        const locationLower = location.toLowerCase();
        return spanishKeywords.some(keyword => locationLower.includes(keyword)) ||
               location === 'España' || location === 'Todas';
    }

    isEuropeanLocation(location) {
        const europeanKeywords = [
            'unión europea', 'europa', 'european', 'ue', 'horizon',
            'erasmus', 'interreg', 'life'
        ];

        const locationLower = location.toLowerCase();
        return europeanKeywords.some(keyword => locationLower.includes(keyword));
    }

    isInternationalLocation(location) {
        const internationalKeywords = [
            'internacional', 'mundial', 'global', 'iberoamérica',
            'latinoamérica', 'mundial', 'world bank', 'onu', 'oea'
        ];

        const locationLower = location.toLowerCase();
        return internationalKeywords.some(keyword => locationLower.includes(keyword));
    }

    matchesRegion(location, targetRegion) {
        // Mapeo de ubicaciones a regiones
        const regionMappings = {
            'Andalucía': ['sevilla', 'córdoba', 'granada', 'málaga', 'cádiz', 'huelva', 'jaén', 'almería'],
            'Cataluña': ['barcelona', 'girona', 'lleida', 'tarragona', 'catalunya'],
            'Madrid': ['madrid', 'comunidad de madrid'],
            'Valencia': ['valencia', 'castellón', 'alicante', 'comunidad valenciana'],
            'Galicia': ['coruña', 'lugo', 'ourense', 'pontevedra'],
            'País Vasco': ['bilbao', 'vitoria', 'san sebastián', 'euskadi'],
            'Aragón': ['zaragoza', 'huesca', 'teruel'],
            'Asturias': ['oviedo', 'asturias'],
            'Cantabria': ['santander', 'cantabria'],
            'Castilla-La Mancha': ['toledo', 'ciudad real', 'albacete', 'cuenca', 'guadalajara'],
            'Castilla y León': ['valladolid', 'salamanca', 'león', 'burgos', 'zamora', 'palencia', 'ávila', 'segovia', 'soria'],
            'Extremadura': ['badajoz', 'cáceres'],
            'Islas Baleares': ['palma', 'mallorca', 'menorca', 'ibiza', 'formentera'],
            'Canarias': ['las palmas', 'santa cruz', 'tenerife', 'gran canaria'],
            'La Rioja': ['logroño', 'rioja'],
            'Murcia': ['murcia', 'cartagena'],
            'Navarra': ['pamplona', 'navarra'],
            'Ceuta': ['ceuta'],
            'Melilla': ['melilla']
        };

        const locationLower = location.toLowerCase();
        const regionKeywords = regionMappings[targetRegion] || [targetRegion.toLowerCase()];

        return regionKeywords.some(keyword => locationLower.includes(keyword));
    }

    // ---------------------- FILTROS RÁPIDOS ----------------------
    setupFilters() {
        this.setupQuickFilters();
    }

    setupQuickFilters() {
        const resultsContainer = document.getElementById('results-container');
        if (!resultsContainer) return;

        // Verificar si ya existen filtros rápidos
        if (resultsContainer.querySelector('.quick-filters')) return;

        const container = document.createElement('div');
        container.className = 'quick-filters mb-3';
        container.innerHTML = `
            <div class="d-flex flex-wrap gap-2 align-items-center">
                <small class="text-muted me-2">Filtros rápidos:</small>
                <button class="btn btn-sm btn-outline-danger" data-filter="urgent">🔥 Urgentes</button>
                <button class="btn btn-sm btn-outline-success" data-filter="high-amount">💰 Montos altos</button>
                <button class="btn btn-sm btn-outline-info" data-filter="recent">🆕 Recientes</button>
                <button class="btn btn-sm btn-outline-secondary" data-filter="clear">✨ Limpiar filtros</button>
            </div>
        `;

        resultsContainer.insertBefore(container, resultsContainer.firstChild);

        container.addEventListener('click', e => {
            if (e.target.dataset.filter) {
                this.currentQuickFilter = e.target.dataset.filter;
                this.applyAllFilters();
                container.querySelectorAll('[data-filter]').forEach(btn => btn.classList.remove('active'));
                if (e.target.dataset.filter !== 'clear') e.target.classList.add('active');
            }
        });
    }

    // ---------------------- APLICAR FILTROS COMBINADOS ----------------------
    applyAllFilters() {
        const country = this.countrySelect?.value || 'Todas';
        const region = this.regionSelect?.value || 'Todas';
        const quick = this.currentQuickFilter || null;
        const now = new Date();
        const sevenDaysAgo = new Date(); 
        sevenDaysAgo.setDate(now.getDate() - 7);

        if (!this.grantItems) {
            this.grantItems = document.querySelectorAll('.grant-item');
        }

        this.grantItems.forEach(item => {
            let show = true;

            const itemCountry = item.dataset.country || item.dataset.location || '';
            const itemRegion = item.dataset.region || '';
            const itemUrgency = item.dataset.urgency || '';
            const pubDate = new Date(item.dataset.publication || now);
            const amountText = item.querySelector('.text-success.fw-bold')?.textContent || '';

            // Filtros país/región
            if (country !== 'Todos' && country !== 'Todas') {
                if (country === 'España' && !this.isSpanishLocation(itemCountry)) show = false;
                else if (country === 'UE' && !this.isEuropeanLocation(itemCountry)) show = false;
                else if (country === 'Internacional' && !this.isInternationalLocation(itemCountry)) show = false;
            }

            if (show && country === 'España' && region !== 'Todas') {
                if (itemRegion !== region && !this.matchesRegion(itemCountry, region)) show = false;
            }

            // Filtros rápidos
            if (quick === 'urgent' && !['critical','high'].includes(itemUrgency)) show = false;
            if (quick === 'high-amount' && !(/\d{6,}|[5-9]\d{5}/.test(amountText.replace(/\D/g,'')))) show = false;
            if (quick === 'recent' && pubDate < sevenDaysAgo) show = false;

            item.style.display = show ? '' : 'none';
        });

        // Limpiar filtro rápido si se presiona "clear"
        if (quick === 'clear') this.currentQuickFilter = null;

        this.updateVisibleCount();
    }

    updateVisibleCount() {
        const visibleItems = document.querySelectorAll('.grant-item:not([style*="none"])');
        const totalItems = document.querySelectorAll('.grant-item').length;

        let counter = document.querySelector('.results-counter');
        if (!counter && totalItems > 0) {
            counter = document.createElement('div');
            counter.className = 'results-counter alert alert-info mt-3';
            const resultsContainer = document.getElementById('results-container') || document.querySelector('.main-container');
            if (resultsContainer) {
                resultsContainer.appendChild(counter);
            }
        }

        if (counter && totalItems > 0) {
            const country = this.countrySelect?.value || 'Todas';
            const region = this.regionSelect?.value || 'Todas';

            let locationText = country;
            if (country === 'España' && region !== 'Todas') {
                locationText = `${region} (${country})`;
            }

            counter.innerHTML = `
                <div class="d-flex align-items-center justify-content-between flex-wrap">
                    <div>
                        <i class="fas fa-filter me-2"></i>
                        Mostrando <strong>${visibleItems.length}</strong> de <strong>${totalItems}</strong> subvenciones
                    </div>
                    <div>
                        <small class="text-muted">
                            <i class="fas fa-map-marker-alt me-1"></i>
                            Filtrado por: ${locationText}
                        </small>
                    </div>
                </div>
            `;
        }
    }

    // ---------------------- TARJETAS ----------------------
    setupGrantCards() {
        document.addEventListener('click', e => {
            if (e.target.classList.contains('toggle-details')) this.toggleCardDetails(e.target);
        });

        this.setupCardLazyLoading();
        this.setupCardHoverEffects();
        this.setupFavoritesSystem();
    }

    toggleCardDetails(button) {
        const card = button.closest('.grant-card');
        const details = card.querySelector('.card-text');
        const expanded = details.classList.contains('expanded');

        if (expanded) {
            details.classList.remove('expanded');
            button.innerHTML = '<i class="fas fa-chevron-down me-1"></i>Ver más';
            button.classList.replace('btn-outline-primary','btn-outline-secondary');
        } else {
            details.classList.add('expanded');
            button.innerHTML = '<i class="fas fa-chevron-up me-1"></i>Ver menos';
            button.classList.replace('btn-outline-secondary','btn-outline-primary');
        }

        setTimeout(() => card.scrollIntoView({behavior:'smooth', block:'nearest'}),100);
    }

    setupCardLazyLoading() {
        if (!('IntersectionObserver' in window)) return;
        const obs = new IntersectionObserver(entries => {
            entries.forEach(e => { 
                if (e.isIntersecting) { 
                    e.target.classList.add('visible'); 
                    obs.unobserve(e.target); 
                } 
            });
        }, {threshold:0.1});
        document.querySelectorAll('.grant-card').forEach(card => obs.observe(card));
    }

    setupCardHoverEffects() {
        document.querySelectorAll('.grant-card').forEach(card => {
            let hoverTimeout;
            card.addEventListener('mouseenter',()=>{
                clearTimeout(hoverTimeout); 
                card.classList.add('hovered');
            });
            card.addEventListener('mouseleave',()=>{
                hoverTimeout=setTimeout(()=>{
                    card.classList.remove('hovered');
                },200);
            });
        });
    }

    setupFavoritesSystem() {
        if (typeof Storage==='undefined') return;
        const favs=JSON.parse(localStorage.getItem('favoriteGrants')||'[]');
        document.querySelectorAll('.grant-card').forEach(card=>{
            const footer=card.querySelector('.card-footer'); 
            if(!footer) return;
            const titleEl = card.querySelector('.card-title');
            if (!titleEl) return;
            const title = titleEl.textContent;
            const isFav=favs.includes(title);
            const btn=document.createElement('button');
            btn.className=`btn btn-outline-warning btn-sm favorite-btn ${isFav?'active':''}`;
            btn.innerHTML=`<i class="fas fa-heart"></i>`;
            btn.title=isFav?'Quitar de favoritos':'Agregar a favoritos';
            btn.addEventListener('click',()=>this.toggleFavorite(title,btn));
            footer.insertBefore(btn,footer.lastElementChild);
        });
    }

    toggleFavorite(title,btn){
        let favs=JSON.parse(localStorage.getItem('favoriteGrants')||'[]');
        if(favs.includes(title)){
            favs=favs.filter(f=>f!==title); 
            btn.classList.remove('active'); 
            btn.title='Agregar a favoritos'; 
            this.showNotification('Eliminado de favoritos','info');
        }
        else{
            favs.push(title); 
            btn.classList.add('active'); 
            btn.title='Quitar de favoritos'; 
            this.showNotification('Agregado a favoritos','success');
        }
        localStorage.setItem('favoriteGrants',JSON.stringify(favs));
    }

    // ---------------------- MÉTODOS ADICIONALES ----------------------
    setupExportHandlers() {
        // Los manejadores de exportación están en el HTML como formularios
        console.log('Export handlers configurados via formularios');
    }

    setupLiveSearch() {
        const searchInputs = document.querySelectorAll('input[type="search"], #searchFilter');
        searchInputs.forEach(input => {
            let timeout;
            input.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.filterResults(e.target.value);
                }, 300);
            });
        });
    }

    filterResults(searchTerm = '') {
        if (!this.grantItems) {
            this.grantItems = document.querySelectorAll('.grant-item');
        }

        searchTerm = searchTerm.toLowerCase();

        this.grantItems.forEach(item => {
            if (!searchTerm) {
                item.style.display = '';
                return;
            }

            const text = item.textContent.toLowerCase();
            const show = text.includes(searchTerm);
            item.style.display = show ? '' : 'none';
        });

        this.updateVisibleCount();
    }

    setupNavigation() {
        // Smooth scroll para enlaces internos
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
    }

    setupLiveFiltering() {
        // Observar cambios en el DOM para nuevos elementos
        if (window.MutationObserver) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        // Se añadieron nuevos elementos, reconfigurar
                        this.grantItems = document.querySelectorAll('.grant-item');
                        this.applyLocationFilter();
                    }
                });
            });

            const resultsContainer = document.getElementById('results-container');
            if (resultsContainer) {
                observer.observe(resultsContainer, {
                    childList: true,
                    subtree: true
                });
            }
        }
    }

    setupAnimations() {
        // Configurar animaciones de entrada
        const animatedElements = document.querySelectorAll('.fade-in-up, .fade-in-left');
        animatedElements.forEach((el, index) => {
            el.style.animationDelay = (index * 0.1) + 's';
            el.classList.add('animated');
        });
    }

    setupMobileOptimizations() {
        // Optimizaciones para móviles
        if ('ontouchstart' in window) {
            document.body.classList.add('touch-device');
        }

        // Detectar orientación
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.updateVisibleCount();
            }, 500);
        });
    }

    setupThemeToggle() {
        // Futuro: toggle tema claro/oscuro
        console.log('Theme toggle preparado para implementación futura');
    }

    setupLazyLoading() {
        // Lazy loading de imágenes si las hay
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    setupServiceWorker() {
        // Service Worker para PWA (futuro)
        if ('serviceWorker' in navigator) {
            console.log('Service Worker disponible para implementación futura');
        }
    }

    showLoadingState(button) {
        if (button) {
            button.disabled = true;
            button.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Buscando...';
        }
    }

    hideLoadingState(button) {
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-search me-2"></i>Buscar Subvenciones';
        }
    }

    showSearchProgress(form) {
        // Mostrar barra de progreso simulada
        const progressContainer = document.createElement('div');
        progressContainer.className = 'progress mt-3';
        progressContainer.innerHTML = `
            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                 role="progressbar" style="width: 0%"></div>
        `;

        form.appendChild(progressContainer);

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 30;
            if (progress > 90) progress = 90;

            const bar = progressContainer.querySelector('.progress-bar');
            bar.style.width = progress + '%';

            if (progress >= 90) {
                clearInterval(interval);
            }
        }, 500);

        // Limpiar después de un tiempo
        setTimeout(() => {
            if (progressContainer.parentNode) {
                progressContainer.remove();
            }
        }, 30000);
    }

    // ---------------------- UTILIDADES ----------------------
    showNotification(msg, type='info', duration=5000) {
        if (window.SubvencionesFinder && window.SubvencionesFinder.showToast) {
            window.SubvencionesFinder.showToast(msg, type);
        } else {
            console.log(`${type.toUpperCase()}: ${msg}`);
        }
    }

    static formatCurrency(amount) {
        return new Intl.NumberFormat('es-ES', {
            style: 'currency',
            currency: 'EUR'
        }).format(amount);
    }

    static formatDate(dateStr) {
        return new Intl.DateTimeFormat('es-ES', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        }).format(new Date(dateStr));
    }
    
    // ------------------- LÓGICA DE LA PÁGINA DE INICIO -------------------
    setupIndexPageEvents() {
        const locationSelect = document.getElementById('location');
        if (!locationSelect) return;
        const regionContainer = document.getElementById('regionContainer');
        const regionSelect = document.getElementById('region');
        const form = document.getElementById('searchForm');
        const submitBtn = form.querySelector('button[type="submit"]');

        function toggleRegionVisibility() {
            const selectedLocation = locationSelect.value;
            const shouldShow = selectedLocation === 'España' || selectedLocation === 'Todas';

            if (shouldShow) {
                regionContainer.style.display = 'block';
                regionContainer.classList.remove('hiding');
                regionContainer.classList.add('showing');

                setTimeout(() => {
                    regionContainer.style.opacity = '1';
                }, 50);

                if (selectedLocation === 'España' && window.SubvencionesFinder) {
                    window.SubvencionesFinder.showToast('Ahora puedes seleccionar una Comunidad Autónoma específica', 'info');
                }
            } else {
                regionContainer.classList.remove('showing');
                regionContainer.classList.add('hiding');
                regionContainer.style.opacity = '0';

                setTimeout(() => {
                    regionContainer.style.display = 'none';
                    regionSelect.value = 'Todas';
                }, 300);
            }
            validateFormFields();
        }

        function validateFormFields() {
            const sector = document.getElementById('sector').value;
            const location = document.getElementById('location').value;
            const company_type = document.getElementById('company_type').value;

            const isValid = sector && location && company_type;

            submitBtn.disabled = !isValid;
            submitBtn.classList.toggle('btn-primary', isValid);
            submitBtn.classList.toggle('btn-secondary', !isValid);

            return isValid;
        }
        
        // Indicador de progreso visual
        function showFieldProgress() {
            const fields = ['sector', 'location', 'company_type'];
            const completed = fields.filter(field => document.getElementById(field).value).length;
            const progress = (completed / fields.length) * 100;

            let progressBar = document.querySelector('.form-progress');
            if (!progressBar) {
                progressBar = document.createElement('div');
                progressBar.className = 'form-progress mt-3';
                progressBar.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <small class="text-muted">Progreso del formulario</small>
                        <small class="text-primary">${Math.round(progress)}%</small>
                    </div>
                    <div class="progress" style="height: 4px;">
                        <div class="progress-bar bg-primary transition-all" role="progressbar" style="width: ${progress}%"></div>
                    </div>
                `;
                form.insertBefore(progressBar, form.querySelector('.text-center'));
            } else {
                progressBar.querySelector('.text-primary').textContent = `${Math.round(progress)}%`;
                progressBar.querySelector('.progress-bar').style.width = `${progress}%`;
            }
        }
        this.showFieldProgress = showFieldProgress;

        // Easter egg
        let keySequence = '';
        document.addEventListener('keydown', function(e) {
            keySequence += e.key.toLowerCase();
            if (keySequence.includes('quicksearch')) {
                document.getElementById('sector').value = 'Tecnología';
                document.getElementById('location').value = 'España';
                document.getElementById('company_type').value = 'PYME';
                document.querySelectorAll('select').forEach(s => s.dispatchEvent(new Event('change')));
                if (window.SubvencionesFinder) {
                    window.SubvencionesFinder.showToast('Búsqueda rápida configurada! 🚀', 'success');
                }
                keySequence = '';
            }
            if (keySequence.length > 20) {
                keySequence = '';
            }
        });

        // Sugerencias inteligentes
        const sectorSelect = document.getElementById('sector');
        const companyTypeSelect = document.getElementById('company_type');
        sectorSelect.addEventListener('change', function() {
            const sector = this.value;
            const suggestions = {
                'Tecnología': 'España', 'Energía': 'España', 'Agricultura': 'España', 'Turismo': 'España'
            };
            if (suggestions[sector] && !locationSelect.value) {
                setTimeout(() => {
                    locationSelect.value = suggestions[sector];
                    locationSelect.dispatchEvent(new Event('change'));
                    if (window.SubvencionesFinder) {
                        window.SubvencionesFinder.showToast(`Sugerencia: ${suggestions[sector]} es común para ${sector}`, 'info');
                    }
                }, 1000);
            }
            const sectorCompanyMapping = {
                'Tecnología': 'Startup', 'Agricultura': 'PYME', 'Comercio': 'Microempresa',
                'Industria': 'PYME', 'Servicios': 'Autónomo', 'Construcción': 'PYME',
                'Salud': 'Universidad', 'Educación': 'Universidad'
            };
            if (sectorCompanyMapping[sector] && !companyTypeSelect.value) {
                setTimeout(() => {
                    const suggestedType = sectorCompanyMapping[sector];
                    companyTypeSelect.value = suggestedType;
                    companyTypeSelect.dispatchEvent(new Event('change'));
                    if (window.SubvencionesFinder) {
                        window.SubvencionesFinder.showToast(`Sugerencia: ${suggestedType} es común para ${sector}`, 'info');
                    }
                }, 1500);
            }
        });

        // Accesibilidad
        document.querySelectorAll('select').forEach(select => {
            select.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && this.value) {
                    const nextSelect = this.closest('.col-md-4').nextElementSibling?.querySelector('select');
                    if (nextSelect && !nextSelect.disabled) {
                        nextSelect.focus();
                    }
                }
            });
            select.addEventListener('change', showFieldProgress);
            select.addEventListener('change', function() {
                this.classList.add('active');
                setTimeout(() => this.classList.remove('active'), 600);
            });
        });

        // Persistencia
        function saveFormProgress() {
            if (typeof Storage !== 'undefined') {
                const formData = {
                    sector: document.getElementById('sector').value,
                    location: document.getElementById('location').value,
                    company_type: document.getElementById('company_type').value,
                    region: document.getElementById('region').value,
                    timestamp: Date.now()
                };
                localStorage.setItem('searchFormProgress', JSON.stringify(formData));
            }
        }
        function restoreFormProgress() {
            if (typeof Storage !== 'undefined') {
                const saved = localStorage.getItem('searchFormProgress');
                if (saved) {
                    try {
                        const formData = JSON.parse(saved);
                        const hourAgo = Date.now() - (60 * 60 * 1000);
                        if (formData.timestamp > hourAgo) {
                            if (formData.sector) document.getElementById('sector').value = formData.sector;
                            if (formData.location) document.getElementById('location').value = formData.location;
                            if (formData.company_type) document.getElementById('company_type').value = formData.company_type;
                            if (formData.region) document.getElementById('region').value = formData.region;
                            setTimeout(() => document.querySelectorAll('select').forEach(s => {
                                if (s.value) s.dispatchEvent(new Event('change'));
                            }), 100);
                            if (window.SubvencionesFinder) {
                                window.SubvencionesFinder.showToast('Formulario restaurado desde la última sesión', 'info');
                            }
                        }
                    } catch (e) {
                        console.warn('Error restaurando progreso del formulario:', e);
                    }
                }
            }
        }
        document.querySelectorAll('select').forEach(select => select.addEventListener('change', saveFormProgress));
        setTimeout(restoreFormProgress, 200);
        form.addEventListener('submit', function() {
            if (typeof Storage !== 'undefined') localStorage.removeItem('searchFormProgress');
        });
        showFieldProgress();
    }
    
    // ------------------- LÓGICA DE LA PÁGINA DE RESULTADOS -------------------
    setupResultPageEvents() {
        if (!document.getElementById('grants-grid')) return;
        this.updateVisibleCount();

        const searchFilter = document.getElementById('searchFilter');
        if (searchFilter) {
            let timeout;
            searchFilter.addEventListener('keyup', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => this.filterResults(e.target.value), 300);
            });
        }
    }

    sortResults() {
        const sortBy = document.getElementById('sortBy').value;
        const container = document.getElementById('grants-grid');
        const items = Array.from(container.querySelectorAll('.grant-item'));
        
        items.sort((a, b) => {
            switch(sortBy) {
                case 'deadline':
                    const dateA = new Date(a.dataset.deadline);
                    const dateB = new Date(b.dataset.deadline);
                    return dateA - dateB;
                case 'publication':
                    const pubA = new Date(a.dataset.publication);
                    const pubB = new Date(b.dataset.publication);
                    return pubB - pubA;
                case 'alphabetical':
                    const titleA = a.querySelector('.card-title').textContent.toLowerCase();
                    const titleB = b.querySelector('.card-title').textContent.toLowerCase();
                    return titleA.localeCompare(titleB);
                default:
                    return 0;
            }
        });
        
        items.forEach(item => container.appendChild(item));
        items.forEach((item, index) => {
            item.style.animationDelay = (index * 0.05) + 's';
            item.classList.remove('fade-in-up');
            setTimeout(() => item.classList.add('fade-in-up'), 10);
        });
    }

    filterByUrgency() {
        const urgencyFilter = document.getElementById('filterUrgency').value;
        const items = document.querySelectorAll('.grant-item');
        items.forEach(item => {
            const urgency = item.dataset.urgency;
            let show = true;
            switch(urgencyFilter) {
                case 'critical': show = urgency === 'critical'; break;
                case 'high': show = urgency === 'critical' || urgency === 'high'; break;
                case 'medium': show = urgency !== 'low'; break;
                case 'active': show = urgency !== 'expired'; break;
                default: show = true;
            }
            item.style.display = show ? '' : 'none';
        });
        this.updateVisibleCount();
    }

    filterBySource() {
        const sourceFilter = document.getElementById('filterSource').value;
        const items = document.querySelectorAll('.grant-item');
        items.forEach(item => {
            const source = item.dataset.source;
            let show = sourceFilter === 'all' || source.toLowerCase().includes(sourceFilter.toLowerCase());
            item.style.display = show ? '' : 'none';
        });
        this.updateVisibleCount();
    }

    shareGrant(title, link) {
        if (navigator.share) {
            navigator.share({
                title: title,
                text: 'Subvención encontrada en SubvencionesFinder',
                url: link
            }).then(() => {
                this.showNotification('Compartido exitosamente', 'success');
            }).catch((error) => {
                console.log('Error sharing:', error);
                window.SubvencionesFinder.copyToClipboard(link);
            });
        } else {
            window.SubvencionesFinder.copyToClipboard(link);
        }
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => new Subvenciones());
window.Subvenciones = Subvenciones;

// Utilidades globales
window.SubvencionesFinder = {
    showToast: function(message, type = 'info') {
        const toastEl = document.getElementById('liveToast');
        if (!toastEl) return;
        const toastBody = toastEl.querySelector('.toast-body');
        toastBody.textContent = message;
        toastEl.className = `toast text-white bg-${type}`;
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    },
    showLoading: function(show = true) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            if (show) overlay.classList.remove('d-none');
            else overlay.classList.add('d-none');
        }
    },
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copiado al portapapeles', 'success');
        }).catch(() => {
            this.showToast('Error al copiar', 'danger');
        });
    },
    formatDate: function(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('es-ES');
        } catch (e) {
            return dateString;
        }
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    const animatedElements = document.querySelectorAll('.fade-in-up, .fade-in-left');
    animatedElements.forEach((el, index) => {
        el.style.animationDelay = (index * 0.1) + 's';
        el.classList.add('animated');
    });

    const forms = document.querySelectorAll('form[method="post"]');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<div class="spinner me-2"></div>Procesando...';
                submitBtn.disabled = true;
                
                window.SubvencionesFinder.showLoading(true);
                
                setTimeout(() => {
                    window.SubvencionesFinder.showLoading(false);
                    if (submitBtn.disabled) {
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = false;
                    }
                }, 30000);
            }
        });
    });

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

    window.addEventListener('error', function(e) {
        console.error('Error capturado:', e);
        window.SubvencionesFinder.showToast('Ha ocurrido un error inesperado', 'warning');
    });

    const resultsPageContainer = document.getElementById('results-container');
    if (resultsPageContainer) {
      document.getElementById('sortBy').addEventListener('change', () => new Subvenciones().sortResults());
      document.getElementById('filterUrgency').addEventListener('change', () => new Subvenciones().filterByUrgency());
      document.getElementById('filterSource').addEventListener('change', () => new Subvenciones().filterBySource());
    }
});