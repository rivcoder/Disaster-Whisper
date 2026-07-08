document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('assessment-form');
    const cityInput = document.getElementById('city-input');
    const autocompleteDropdown = document.getElementById('autocomplete-suggestions');
    const resultsContainer = document.getElementById('results-container');
    const loadingState = document.getElementById('loading-state');
    const favoriteBtn = document.getElementById('favorite-btn');
    
    // Timezone-safe local date parser to avoid UTC shifting offsets
    function parseLocalDate(isoString) {
        if (!isoString) return new Date();
        const parts = isoString.split('T');
        const dateParts = parts[0].split('-');
        const year = parseInt(dateParts[0], 10);
        const month = parseInt(dateParts[1], 10) - 1;
        const day = parseInt(dateParts[2], 10);
        
        if (parts[1]) {
            const timeParts = parts[1].split(':');
            const hour = parseInt(timeParts[0], 10);
            const minute = parseInt(timeParts[1], 10);
            return new Date(year, month, day, hour, minute);
        } else {
            return new Date(year, month, day, 0, 0, 0);
        }
    }
    
    // UI Cards
    const riskCard = document.getElementById('risk-card');
    const riskText = document.getElementById('risk-text');
    const statusSubtitle = document.getElementById('status-subtitle');
    const alertsContainer = document.getElementById('alerts-container');
    const trendsCard = document.getElementById('trends-card');
    const trendsCaret = document.getElementById('trends-caret');
    
    // Metrics Elements
    const valTemp = document.getElementById('val-temp');
    const valHumidity = document.getElementById('val-humidity');
    const valWind = document.getElementById('val-wind');
    const valRain = document.getElementById('val-rain');
    const valAqi = document.getElementById('val-aqi');
    
    let trendChart = null;
    let currentTrendData = null;
    let currentCity = '';
    let currentCityData = null;


    // 1. Favorites System (localStorage)
    const favoritesList = document.getElementById('favorites-list');
    
    function loadFavorites() {
        const favs = JSON.parse(localStorage.getItem('whisper_favorites')) || ['New Delhi', 'London', 'Tokyo'];
        if (favoritesList) {
            favoritesList.innerHTML = '';
            
            favs.forEach(city => {
                const tag = document.createElement('button');
                tag.className = 'favorite-tag';
                tag.innerHTML = `<i class="ph-fill ph-star"></i> <span>${city}</span>`;
                tag.type = 'button';
                tag.addEventListener('click', () => {
                    cityInput.value = city;
                    form.dispatchEvent(new Event('submit'));
                });
                favoritesList.appendChild(tag);
            });
        }
        
        // Update active class on current resolved city
        if (currentCity && favoriteBtn) {
            const isFav = favs.some(f => f.toLowerCase() === currentCity.toLowerCase());
            if (isFav) {
                favoriteBtn.classList.add('active');
                favoriteBtn.title = 'Remove from Favorites';
            } else {
                favoriteBtn.classList.remove('active');
                favoriteBtn.title = 'Add to Favorites';
            }
        }
    }
    
    if (favoriteBtn) {
        favoriteBtn.addEventListener('click', () => {
            if (!currentCity) return;
            let favs = JSON.parse(localStorage.getItem('whisper_favorites')) || ['New Delhi', 'London', 'Tokyo'];
            
            const idx = favs.findIndex(f => f.toLowerCase() === currentCity.toLowerCase());
            if (idx > -1) {
                favs.splice(idx, 1);
                favoriteBtn.classList.remove('active');
            } else {
                favs.push(currentCity);
                favoriteBtn.classList.add('active');
            }
            
            localStorage.setItem('whisper_favorites', JSON.stringify(favs));
            loadFavorites();
        });
    }

    // 2. City Search Auto-Suggestions
    let debounceTimer;
    if (cityInput) {
        cityInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const query = cityInput.value.trim();
            if (query.length < 2) {
                autocompleteDropdown.classList.add('hidden');
                return;
            }
            
            debounceTimer = setTimeout(() => {
                fetchAutocompleteSuggestions(query);
            }, 300);
        });
    }

    async function fetchAutocompleteSuggestions(query) {
        try {
            const res = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=5&language=en&format=json`);
            if (!res.ok) return;
            const data = await res.json();
            const results = data.results || [];
            
            if (results.length === 0) {
                autocompleteDropdown.classList.add('hidden');
                return;
            }
            
            autocompleteDropdown.innerHTML = '';
            results.forEach(loc => {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                
                const name = loc.name;
                const admin1 = loc.admin1 ? `, ${loc.admin1}` : '';
                const country = loc.country ? `, ${loc.country}` : '';
                const display = `${name}${admin1}${country}`;
                
                item.innerHTML = `
                    <span>${name}${admin1}</span>
                    <span class="autocomplete-flag">${loc.country_code || ''}</span>
                `;
                
                item.addEventListener('click', () => {
                    cityInput.value = display;
                    autocompleteDropdown.classList.add('hidden');
                    form.dispatchEvent(new Event('submit'));
                });
                
                autocompleteDropdown.appendChild(item);
            });
            
            autocompleteDropdown.classList.remove('hidden');
        } catch (err) {
            console.error('Autocomplete API error:', err);
        }
    }

    // Close autocomplete on click outside
    document.addEventListener('click', (e) => {
        if (cityInput && autocompleteDropdown && !cityInput.contains(e.target) && !autocompleteDropdown.contains(e.target)) {
            autocompleteDropdown.classList.add('hidden');
        }
    });

    // 3. Form Submit & Prediction Fetch
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const city = cityInput.value.trim();
            if (!city) return;
            
            resultsContainer.classList.add('hidden');
            loadingState.classList.remove('hidden');
            autocompleteDropdown.classList.add('hidden');
            
            // Remove prior error banners
            const oldError = document.querySelector('.error-message-box');
            if (oldError) oldError.remove();
            
            try {
                const response = await fetch('/api/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ city })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    showErrorMessage(data.error || 'A service error occurred.');
                    loadingState.classList.add('hidden');
                    return;
                }
                
                currentTrendData = data.trends;
                currentCity = data.city;
                currentCityData = data;
                
                // Stagger output for high-end feel
                setTimeout(() => {
                    updateUI(data);
                    cityInput.value = data.city;
                    loadingState.classList.add('hidden');
                    resultsContainer.classList.remove('hidden');
                    
                    // Reset trends collapse state on new query search
                    if (trendsCard) trendsCard.classList.add('hidden');
                    if (trendsCaret) trendsCaret.classList.remove('rotated');
                    
                    loadFavorites();
                    
                    // Initialize Resource Allocation Console
                    initResources(data.resources);

                    // Apply saved unit preferences and check alert thresholds
                    if (typeof refreshMetricDisplays === 'function') refreshMetricDisplays();
                    if (typeof checkMetricAlerts === 'function') checkMetricAlerts();
                }, 600);
                
            } catch (error) {
                console.error('Fetch error:', error);
                showErrorMessage('Unable to connect to Disaster Whisper server.');
                loadingState.classList.add('hidden');
            }
        });
    }



    // 5. Gauge Countup Animation
    function animateGauge(score, riskLevel) {
        const fillCircle = document.getElementById('gauge-fill');
        const scoreEl = document.getElementById('risk-score');
        if (!fillCircle || !scoreEl) return;
        
        // Total circumference of circle of radius 42 is 263.89
        const circumference = 264;
        const offset = circumference - (circumference * score) / 100;
        fillCircle.style.strokeDashoffset = offset;
        
        let currentVal = 0;
        const duration = 1000; // 1 second
        const start = performance.now();
        
        function draw(time) {
            const elapsed = time - start;
            const progress = Math.min(elapsed / duration, 1);
            const ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            
            currentVal = Math.round(ease * score);
            scoreEl.textContent = `${currentVal}%`;
            
            if (progress < 1) {
                requestAnimationFrame(draw);
            } else {
                scoreEl.textContent = `${score}%`;
            }
        }
        requestAnimationFrame(draw);
    }

    // 6. Explainable AI Risk Breakdown
    function updateRiskBreakdown(breakdown) {
        const container = document.getElementById('breakdown-list');
        if (!container) return;
        container.innerHTML = '';
        
        const labelsMap = {
            'Temperature': 'Temperature Severity',
            'Wind_Speed': 'Wind Storm Threat',
            'Rainfall': 'Precipitation Severity',
            'AQI': 'Air Quality Hazard',
            'Humidity': 'Humidity Stress Factor'
        };
        
        Object.entries(breakdown).forEach(([factor, val]) => {
            const item = document.createElement('div');
            item.className = 'breakdown-item';
            
            let colorClass = 'bar-low';
            if (val > 70) colorClass = 'bar-high';
            else if (val > 35) colorClass = 'bar-medium';
            
            item.innerHTML = `
                <div class="breakdown-label-row">
                    <span class="breakdown-name">${labelsMap[factor] || factor}</span>
                    <span class="breakdown-value">${val}%</span>
                </div>
                <div class="breakdown-bar-container">
                    <div class="breakdown-bar-fill ${colorClass}" style="width: 0%"></div>
                </div>
            `;
            
            container.appendChild(item);
            
            // Stagger animation
            setTimeout(() => {
                const fill = item.querySelector('.breakdown-bar-fill');
                if (fill) fill.style.width = `${val}%`;
            }, 100);
        });
    }

    // 7. Categorized Recommendations
    function updateRecommendations(recs, alerts) {
        const recCritical = document.getElementById('rec-critical');
        const recHealth = document.getElementById('rec-health');
        const recTravel = document.getElementById('rec-travel');
        
        const advCritical = document.getElementById('adv-critical');
        const advHealth = document.getElementById('adv-health');
        const advTravel = document.getElementById('adv-travel');
        
        if (!recCritical || !recHealth || !recTravel) return;
        
        recCritical.innerHTML = '';
        recHealth.innerHTML = '';
        recTravel.innerHTML = '';
        
        let hasCritical = false;
        let hasHealth = false;
        let hasTravel = false;
        
        // Critical alerts always map to immediate actions
        if (alerts && alerts.length > 0) {
            alerts.forEach(alert => {
                const li = document.createElement('li');
                li.textContent = alert;
                recCritical.appendChild(li);
                hasCritical = true;
            });
        }
        
        // Parse recommendations into logical categories
        if (recs && recs.length > 0) {
            recs.forEach(rec => {
                const text = rec.toLowerCase();
                const li = document.createElement('li');
                li.textContent = rec;
                
                if (text.includes('dangerous') || text.includes('warning') || text.includes('hazard') || text.includes('high risk') || text.includes('critical')) {
                    recCritical.appendChild(li);
                    hasCritical = true;
                } else if (text.includes('aqi') || text.includes('air quality') || text.includes('mask') || text.includes('heat') || text.includes('temperature') || text.includes('hydrated') || text.includes('warmly') || text.includes('peaceful') || text.includes('caution')) {
                    recHealth.appendChild(li);
                    hasHealth = true;
                } else {
                    recTravel.appendChild(li);
                    hasTravel = true;
                }
            });
        }
        
        // Toggle containers
        if (hasCritical) advCritical.classList.remove('hidden');
        else advCritical.classList.add('hidden');
        
        if (hasHealth) advHealth.classList.remove('hidden');
        else advHealth.classList.add('hidden');
        
        if (hasTravel) advTravel.classList.remove('hidden');
        else advTravel.classList.add('hidden');
    }

    // 8. Trends Chart Rendering
    let activeTrendMetric = 'temp';

    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderTrends(btn.dataset.tab);
        });
    });

    const metricSelBtns = document.querySelectorAll('.metric-selector-row .metric-sel-btn');
    if (metricSelBtns) {
        metricSelBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                metricSelBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activeTrendMetric = btn.dataset.metricSel;
                
                const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab || 'hourly';
                renderTrends(activeTab);
            });
        });
    }

    function renderTrends(tabType) {
        if (!currentTrendData) return;
        
        const chartCanvas = document.getElementById('trends-chart');
        const trendsSubtitle = document.getElementById('trends-subtitle');
        if (!chartCanvas) return;
        const ctx = chartCanvas.getContext('2d');
        const rawData = currentTrendData[tabType];
        if (!rawData || !rawData.time) return;
        
        if (trendChart) {
            trendChart.destroy();
        }

        const labels = rawData.time.map(t => {
            const date = parseLocalDate(t);
            return tabType === 'hourly' 
                ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : date.toLocaleDateString([], { weekday: 'short', day: 'numeric' });
        });

        // Load units from metric settings
        const currentUnits = JSON.parse(localStorage.getItem('whisper_metric_settings') || '{}');
        const tempUnit = currentUnits.tempUnit || '°C';
        const windUnit = currentUnits.windUnit || 'km/h';
        const rainUnit = currentUnits.rainUnit || 'mm';

        // Set subtitle and select datasets
        let subtitleText = '';
        let datasets = [];
        let yLabel = '';
        let yColor = '';

        // Global Chart styling adjustments for light rose theme
        Chart.defaults.color = '#475569';
        Chart.defaults.borderColor = 'rgba(15, 23, 42, 0.06)';

        if (activeTrendMetric === 'temp') {
            subtitleText = tabType === 'hourly' 
                ? `Temperature forecast (${tempUnit}) for the next 24 hours`
                : `Daily temperature range (${tempUnit}) for the next 7 days`;
            
            yLabel = `Temperature (${tempUnit})`;
            yColor = '#e11d48';
            
            const tempGradient = ctx.createLinearGradient(0, 0, 0, 300);
            tempGradient.addColorStop(0, 'rgba(225, 29, 72, 0.25)');
            tempGradient.addColorStop(1, 'rgba(225, 29, 72, 0.0)');
            
            if (tabType === 'hourly') {
                const hourlyTemp = rawData.temp.map(v => tempUnit === '°F' ? +(v * 9/5 + 32).toFixed(1) : v);
                datasets.push({
                    label: `Temp (${tempUnit})`,
                    data: hourlyTemp,
                    borderColor: '#e11d48',
                    backgroundColor: tempGradient,
                    fill: true,
                    tension: 0.45,
                    borderWidth: 2.5,
                    pointRadius: 3,
                    pointBackgroundColor: '#e11d48',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1.5,
                    pointHoverRadius: 6
                });
            } else {
                const maxTemp = rawData.temp_max.map(v => tempUnit === '°F' ? +(v * 9/5 + 32).toFixed(1) : v);
                const minTemp = rawData.temp_min.map(v => tempUnit === '°F' ? +(v * 9/5 + 32).toFixed(1) : v);
                datasets.push({
                    label: `Max Temp (${tempUnit})`,
                    data: maxTemp,
                    borderColor: '#e11d48',
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointRadius: 4,
                    pointBackgroundColor: '#e11d48'
                });
                datasets.push({
                    label: `Min Temp (${tempUnit})`,
                    data: minTemp,
                    borderColor: '#3b82f6',
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: '#3b82f6'
                });
            }
        } 
        else if (activeTrendMetric === 'rain') {
            subtitleText = tabType === 'hourly'
                ? `Hourly rainfall forecast (${rainUnit}) for the next 24 hours`
                : `Daily rainfall sum (${rainUnit}) for the next 7 days`;
            
            yLabel = `Precipitation (${rainUnit})`;
            yColor = '#3b82f6';
            
            const rainGradient = ctx.createLinearGradient(0, 0, 0, 300);
            rainGradient.addColorStop(0, 'rgba(59, 130, 246, 0.35)');
            rainGradient.addColorStop(1, 'rgba(59, 130, 246, 0.02)');
            
            const rainData = tabType === 'hourly' ? rawData.rain : rawData.rain_sum;
            const convertedRain = rainData.map(v => rainUnit === 'in' ? +(v * 0.0393701).toFixed(2) : v);
            
            datasets.push({
                label: tabType === 'hourly' ? `Rainfall (${rainUnit})` : `Rain Sum (${rainUnit})`,
                data: convertedRain,
                borderColor: '#3b82f6',
                backgroundColor: rainGradient,
                fill: true,
                type: 'bar',
                borderRadius: 4
            });
        } 
        else if (activeTrendMetric === 'wind') {
            subtitleText = tabType === 'hourly'
                ? `Wind speed forecast (${windUnit}) for the next 24 hours`
                : `Maximum daily wind speed (${windUnit}) for the next 7 days`;
            
            yLabel = `Wind Speed (${windUnit})`;
            yColor = '#7c3aed';
            
            const windGradient = ctx.createLinearGradient(0, 0, 0, 300);
            windGradient.addColorStop(0, 'rgba(124, 58, 237, 0.25)');
            windGradient.addColorStop(1, 'rgba(124, 58, 237, 0.0)');
            
            const windData = tabType === 'hourly' ? rawData.wind : rawData.wind_max;
            const convertedWind = windData.map(v => {
                if (windUnit === 'mph') return +(v * 0.621371).toFixed(1);
                return v; // km/h
            });
            
            datasets.push({
                label: `Wind (${windUnit})`,
                data: convertedWind,
                borderColor: '#7c3aed',
                backgroundColor: windGradient,
                fill: true,
                tension: 0.4,
                borderWidth: 2.5,
                pointRadius: 3,
                pointBackgroundColor: '#7c3aed'
            });
        } 
        else if (activeTrendMetric === 'humidity') {
            subtitleText = tabType === 'hourly'
                ? 'Relative humidity (%) forecast for the next 24 hours'
                : 'Maximum daily relative humidity (%) for the next 7 days';
            
            yLabel = 'Humidity (%)';
            yColor = '#0d9488';
            
            const humidGradient = ctx.createLinearGradient(0, 0, 0, 300);
            humidGradient.addColorStop(0, 'rgba(13, 148, 136, 0.25)');
            humidGradient.addColorStop(1, 'rgba(13, 148, 136, 0.0)');
            
            const humidData = tabType === 'hourly' ? rawData.humidity : rawData.humid_max;
            
            datasets.push({
                label: 'Humidity (%)',
                data: humidData,
                borderColor: '#0d9488',
                backgroundColor: humidGradient,
                fill: true,
                tension: 0.4,
                borderWidth: 2.5,
                pointRadius: 3,
                pointBackgroundColor: '#0d9488'
            });
        }

        if (trendsSubtitle) trendsSubtitle.textContent = subtitleText;

        trendChart = new Chart(ctx, {
            type: activeTrendMetric === 'rain' ? 'bar' : 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: { family: 'Inter', size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.96)',
                        titleColor: '#ffffff',
                        bodyColor: '#e2e8f0',
                        borderColor: 'rgba(225, 29, 72, 0.25)',
                        borderWidth: 1,
                        padding: 14,
                        cornerRadius: 12,
                        titleFont: { family: 'JetBrains Mono', weight: '500', size: 12 },
                        bodyFont: { family: 'Inter', size: 12 }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(15, 23, 42, 0.04)' },
                        ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#475569', maxRotation: 0 }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: yLabel, font: { family: 'JetBrains Mono', size: 10 }, color: yColor },
                        grid: { color: 'rgba(15, 23, 42, 0.04)' },
                        ticks: { font: { family: 'JetBrains Mono', size: 10 }, color: '#475569' }
                    }
                }
            }
        });
    }

    // 9. Error Rendering Banner
    function showErrorMessage(message) {
        const oldBox = document.querySelector('.error-message-box');
        if (oldBox) oldBox.remove();
        
        const box = document.createElement('div');
        box.className = 'error-message-box animate-fade-in';
        box.innerHTML = `
            <i class="ph ph-warning-circle" style="font-size: 1.3rem;"></i>
            <p>${message}</p>
        `;
        
        box.style.background = 'rgba(239, 68, 68, 0.1)';
        box.style.color = '#FCA5A5';
        box.style.padding = '1.1rem 1.5rem';
        box.style.borderRadius = '18px';
        box.style.border = '1px solid rgba(239, 68, 68, 0.25)';
        box.style.display = 'flex';
        box.style.alignItems = 'center';
        box.style.gap = '0.75rem';
        box.style.maxWidth = '600px';
        box.style.margin = '1rem auto 0';
        
        const searchSec = document.querySelector('.search-section');
        if (searchSec) searchSec.appendChild(box);
    }

    // 10. UI Update coordinator
    function updateUI(res) {
        // Location text
        const loc = document.getElementById('resolved-location');
        if (loc) loc.textContent = res.city;
        
        // Updated timestamp
        const timeEl = document.getElementById('last-updated');
        if (timeEl && res.data.timestamp) {
            const date = parseLocalDate(res.data.timestamp);
            timeEl.textContent = `Updated: ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        }
        
        // Gauge and classes
        const riskVal = res.risk_score || 0;
        if (riskText) riskText.textContent = res.risk_level;
        
        if (riskCard) {
            riskCard.className = 'status-section card animate-fade-in';
            riskCard.classList.add(`risk-${res.risk_level.toLowerCase()}`);
        }
        
        // Set page-wide risk ambient theme
        document.body.className = `theme-${res.risk_level.toLowerCase()}`;
        
        animateGauge(riskVal, res.risk_level);
        
        // Update subtitle details
        if (statusSubtitle) {
            if (res.risk_level === 'Low') {
                statusSubtitle.textContent = "Peaceful atmospheric conditions detected.";
            } else if (res.risk_level === 'Medium') {
                statusSubtitle.textContent = "Mild risk detected. Stay aware of local conditions.";
            } else {
                statusSubtitle.textContent = "High alert! Follow safety advice immediately.";
            }
        }
        
        // Update raw numbers
        if (valTemp) valTemp.textContent = `${res.data.Temperature}°C`;
        if (valHumidity) valHumidity.textContent = `${res.data.Humidity}%`;
        if (valWind) valWind.textContent = `${res.data.Wind_Speed} km/h`;
        if (valRain) valRain.textContent = `${res.data.Rainfall} mm`;
        if (valAqi) valAqi.textContent = res.data.AQI || '0';
        
        // Metrics card stagger load
        const boxes = document.querySelectorAll('.metric-box');
        boxes.forEach((box, index) => {
            box.classList.remove('animate-fade-in');
            void box.offsetWidth; // trigger layout reflow
            box.classList.add('animate-fade-in');
            box.style.animationDelay = `${0.05 + (index * 0.08)}s`;
        });
        
        // Trigger update for other panels
        updateRiskBreakdown(res.risk_breakdown || {});
        updateRecommendations(res.recommendations || [], res.alerts || []);

        // --- Update Command Center Panels ---
        
        // 1. Localized Flood Threat Meter
        const floodThreatBar = document.getElementById('flood-threat-bar');
        const floodThreatVal = document.getElementById('flood-threat-val');
        const floodThreatDesc = document.getElementById('flood-threat-description');
        const floodAccRain = document.getElementById('flood-acc-rain');
        
        if (floodAccRain) {
            floodAccRain.textContent = `${res.data.Rainfall} mm`;
        }
        
        const rain = res.data.Rainfall || 0;
        let floodScore = Math.min(100, Math.round(rain * 1.5));
        
        if (floodThreatBar && floodThreatVal) {
            floodThreatBar.style.width = `${floodScore}%`;
            floodThreatVal.textContent = `${floodScore}%`;
            
            if (floodThreatDesc) {
                if (floodScore >= 70) {
                    floodThreatDesc.textContent = "High flood warning! River levels rising, soil saturated. Stay away from low-lying areas.";
                    floodThreatBar.style.background = 'linear-gradient(90deg, #EF4444, #DC2626)';
                } else if (floodScore >= 35) {
                    floodThreatDesc.textContent = "Moderate flood watch. High probability of surface pooling and road blockages.";
                    floodThreatBar.style.background = 'linear-gradient(90deg, #F59E0B, #D97706)';
                } else {
                    floodThreatDesc.textContent = "Low flood danger. Standard surface absorption and drainage operating fully.";
                    floodThreatBar.style.background = 'linear-gradient(90deg, #22D3EE, #06B6D4)';
                }
            }
        }

        // 2. Outbreaks & Heatwave Status
        const heatwaveItem = document.getElementById('heatwave-item');
        const heatwaveDesc = document.getElementById('heatwave-status-desc');
        if (heatwaveItem && heatwaveDesc) {
            if (res.data.Temperature >= 38 || (res.alerts && res.alerts.some(a => a.toLowerCase().includes("heat")))) {
                heatwaveItem.classList.add('active');
                heatwaveDesc.textContent = "Extreme heat active in forecast. Keep cooling systems active.";
            } else {
                heatwaveItem.classList.remove('active');
                heatwaveDesc.textContent = "No active heat hazards detected.";
            }
        }
    }

    // --- Command Center Tab Swapper ---
    const commandTabs = document.querySelectorAll('.command-tab');
    const tabPanels = document.querySelectorAll('.tab-panel');
    
    commandTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const panelId = tab.dataset.panel;

            // Special case: "Trend Analysis" tab — scroll + open chart, don't switch panels
            if (panelId === 'trends-anchor') {
                // Activate tab visually
                commandTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Ensure Risk Radar panel stays visible (trends live inside it)
                tabPanels.forEach(panel => {
                    if (panel.id === 'panel-radar') {
                        panel.classList.remove('hidden');
                        panel.classList.add('active');
                    } else {
                        panel.classList.add('hidden');
                        panel.classList.remove('active');
                    }
                });

                // Open the trends card if it's collapsed
                const tc = document.getElementById('trends-card');
                const caret = document.getElementById('trends-caret');
                const toggleWrapper = document.getElementById('btn-toggle-trends');
                if (tc && tc.classList.contains('hidden')) {
                    tc.classList.remove('hidden');
                    if (caret) caret.classList.add('rotated');
                    const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab || 'hourly';
                    renderTrends(activeTab);
                }

                // Smooth scroll down to the trends toggle bar
                const trendsWrapper = document.querySelector('.trends-toggle-wrapper');
                if (trendsWrapper) {
                    setTimeout(() => {
                        trendsWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 80);
                }
                return;
            }

            commandTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            tabPanels.forEach(panel => {
                if (panel.id === `panel-${panelId}`) {
                    panel.classList.remove('hidden');
                    panel.classList.add('active');
                } else {
                    panel.classList.add('hidden');
                    panel.classList.remove('active');
                }
            });
        });
    });



    // --- Resource Dispatching sliders & Console ---
    const sliderRescue = document.getElementById('slider-rescue');
    const sliderMedical = document.getElementById('slider-medical');
    const sliderFire = document.getElementById('slider-fire');
    const sliderShelter = document.getElementById('slider-shelter');
    const sliderSupplies = document.getElementById('slider-supplies');

    const maxRescueEl = document.getElementById('max-rescue');
    const maxMedicalEl = document.getElementById('max-medical');
    const maxFireEl = document.getElementById('max-fire');
    const maxShelterEl = document.getElementById('max-shelter');
    const maxSuppliesEl = document.getElementById('max-supplies');

    const valAllocatedRescue = document.getElementById('val-allocated-rescue');
    const valAllocatedMedical = document.getElementById('val-allocated-medical');
    const valAllocatedFire = document.getElementById('val-allocated-fire');
    const valAllocatedShelter = document.getElementById('val-allocated-shelter');
    const valAllocatedSupplies = document.getElementById('val-allocated-supplies');

    const statPersonnel = document.getElementById('stat-personnel');
    const statShelterCapacity = document.getElementById('stat-shelter-capacity');
    const statRemainingRisk = document.getElementById('stat-remaining-risk');
    const mitigationScore = document.getElementById('mitigation-score');
    const mitigationFill = document.getElementById('mitigation-fill');

    function initResources(resources) {
        if (!resources) return;
        
        // Update max limit indicators
        if (maxRescueEl) maxRescueEl.textContent = resources.Rescue_Squads;
        if (maxMedicalEl) maxMedicalEl.textContent = resources.Medical_Units;
        if (maxFireEl) maxFireEl.textContent = resources.Fire_Engines;
        if (maxShelterEl) maxShelterEl.textContent = resources.Emergency_Shelters;
        if (maxSuppliesEl) maxSuppliesEl.textContent = resources.Supply_Kits;

        // Reset values
        if (sliderRescue) {
            sliderRescue.max = resources.Rescue_Squads;
            sliderRescue.value = 0;
        }
        if (valAllocatedRescue) valAllocatedRescue.textContent = 0;

        if (sliderMedical) {
            sliderMedical.max = resources.Medical_Units;
            sliderMedical.value = 0;
        }
        if (valAllocatedMedical) valAllocatedMedical.textContent = 0;

        if (sliderFire) {
            sliderFire.max = resources.Fire_Engines;
            sliderFire.value = 0;
        }
        if (valAllocatedFire) valAllocatedFire.textContent = 0;

        if (sliderShelter) {
            sliderShelter.max = resources.Emergency_Shelters;
            sliderShelter.value = 0;
        }
        if (valAllocatedShelter) valAllocatedShelter.textContent = 0;

        if (sliderSupplies) {
            sliderSupplies.max = resources.Supply_Kits;
            sliderSupplies.value = 0;
        }
        if (valAllocatedSupplies) valAllocatedSupplies.textContent = 0;

        updateMitigation();
    }

    function updateMitigation() {
        if (!sliderRescue || !sliderMedical || !sliderFire || !sliderShelter || !sliderSupplies) return;

        const rescueVal = parseInt(sliderRescue.value) || 0;
        const medicalVal = parseInt(sliderMedical.value) || 0;
        const fireVal = parseInt(sliderFire.value) || 0;
        const shelterVal = parseInt(sliderShelter.value) || 0;
        const suppliesVal = parseInt(sliderSupplies.value) || 0;

        // Display current allocations
        if (valAllocatedRescue) valAllocatedRescue.textContent = rescueVal;
        if (valAllocatedMedical) valAllocatedMedical.textContent = medicalVal;
        if (valAllocatedFire) valAllocatedFire.textContent = fireVal;
        if (valAllocatedShelter) valAllocatedShelter.textContent = shelterVal;
        if (valAllocatedSupplies) valAllocatedSupplies.textContent = suppliesVal;

        // Deployed personnel count
        const personnel = (rescueVal * 6) + (medicalVal * 4) + (fireVal * 5);
        if (statPersonnel) statPersonnel.textContent = personnel;

        // Shelter capacity (100 people per shelter)
        const maxShelter = maxShelterEl ? (parseInt(maxShelterEl.textContent) || 0) : 0;
        if (statShelterCapacity) {
            statShelterCapacity.textContent = `${shelterVal * 100} / ${maxShelter * 100}`;
        }

        // Compute mitigation score
        const maxRescue = maxRescueEl ? (parseInt(maxRescueEl.textContent) || 10) : 10;
        const maxMedical = maxMedicalEl ? (parseInt(maxMedicalEl.textContent) || 10) : 10;
        const maxFire = maxFireEl ? (parseInt(maxFireEl.textContent) || 10) : 10;
        const maxShelterVal = maxShelterEl ? (parseInt(maxShelterEl.textContent) || 5) : 5;
        const maxSupplies = maxSuppliesEl ? (parseInt(maxSuppliesEl.textContent) || 300) : 300;

        const maxStrength = (maxRescue * 10) + (maxMedical * 8) + (maxFire * 8) + (maxShelterVal * 15) + (maxSupplies * 0.15);
        const currentStrength = (rescueVal * 10) + (medicalVal * 8) + (fireVal * 8) + (shelterVal * 15) + (suppliesVal * 0.15);

        const mitigationVal = maxStrength > 0 ? Math.min(100, Math.round((currentStrength / maxStrength) * 100)) : 0;
        if (mitigationScore) mitigationScore.textContent = `${mitigationVal}%`;

        // Update mitigation ring fill (dasharray is 264)
        if (mitigationFill) {
            const offset = 264 - (264 * mitigationVal) / 100;
            mitigationFill.style.strokeDashoffset = offset;
        }

        // Calculate remaining risk
        if (statRemainingRisk) {
            if (currentCityData) {
                const initialRisk = currentCityData.risk_score || 0;
                const remainingRiskVal = Math.max(0, Math.round(initialRisk * (1 - (mitigationVal / 100))));
                statRemainingRisk.textContent = `${remainingRiskVal}%`;
            } else {
                statRemainingRisk.textContent = '--';
            }
        }
    }

    if (sliderRescue) {
        [sliderRescue, sliderMedical, sliderFire, sliderShelter, sliderSupplies].forEach(slider => {
            slider.addEventListener('input', updateMitigation);
        });
    }

    const btnDispatchSubmit = document.getElementById('btn-dispatch-submit');
    if (btnDispatchSubmit) {
        btnDispatchSubmit.addEventListener('click', () => {
            if (!currentCity) {
                showErrorMessage("No active command session. Please search for a city first.");
                return;
            }
            
            const btnText = btnDispatchSubmit.innerHTML;
            btnDispatchSubmit.innerHTML = `<i class="ph ph-circle-notch animate-spin"></i> Broadcasting...`;
            btnDispatchSubmit.disabled = true;
            
            setTimeout(() => {
                btnDispatchSubmit.innerHTML = `<i class="ph ph-check"></i> Orders Transmitted`;
                btnDispatchSubmit.style.background = '#10B981';
                
                setTimeout(() => {
                    btnDispatchSubmit.innerHTML = btnText;
                    btnDispatchSubmit.style.background = '';
                    btnDispatchSubmit.disabled = false;
                }, 2500);
            }, 1500);
        });
    }


    // Load favorites bar tags on boot
    loadFavorites();

    // Load API Key on boot
    if (apiKeyInput) {
        const storedKey = localStorage.getItem('whisper_gemini_key');
        if (storedKey) apiKeyInput.value = storedKey;
        
        apiKeyInput.addEventListener('input', () => {
            localStorage.setItem('whisper_gemini_key', apiKeyInput.value.trim());
        });
    }

    if (toggleKeyVisibility && apiKeyInput) {
        toggleKeyVisibility.addEventListener('click', () => {
            if (apiKeyInput.type === 'password') {
                apiKeyInput.type = 'text';
                toggleKeyVisibility.innerHTML = '<i class="ph ph-eye-slash"></i>';
            } else {
                apiKeyInput.type = 'password';
                toggleKeyVisibility.innerHTML = '<i class="ph ph-eye"></i>';
            }
        });
    }

    async function sendCommandMessage() {
        if (!panelChatUserInput || !panelChatMessages) return;
        const text = panelChatUserInput.value.trim();
        if (!text) return;
        
        panelChatUserInput.value = '';
        
        // Add user message
        appendChatMessage(panelChatMessages, text, 'user');
        
        // Add loading assistant message
        const loadingId = 'loading-' + Date.now();
        const loadingMsg = appendChatMessage(panelChatMessages, 'Gemini is formulating emergency advice...', 'assistant', loadingId);
        
        try {
            const key = localStorage.getItem('whisper_gemini_key') || '';
            let responseText = '';
            
            if (key) {
                // Call actual Gemini Flash API client-side
                let context = `You are Gemini Emergency Assistant, an expert disaster response AI coordinator. The user is managing conditions for the city: ${currentCity || 'Unknown'}. `;
                if (currentCityData && currentCityData.data) {
                    context += `Current weather metrics: Temperature: ${currentCityData.data.Temperature}°C, Rainfall: ${currentCityData.data.Rainfall} mm, Wind: ${currentCityData.data.Wind_Speed} km/h, AQI: ${currentCityData.data.AQI}, Risk: ${currentCityData.risk_level} (${currentCityData.risk_score}%). `;
                }
                context += `Answer the user's question with highly specific, bulleted, action-oriented items. Question: ${text}`;
                
                const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${key}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        contents: [{
                            parts: [{ text: context }]
                        }]
                    })
                });
                
                if (!response.ok) {
                    const errorDetails = await response.json();
                    throw new Error(errorDetails.error?.message || "Gemini API rejected request");
                }
                
                const resData = await response.json();
                responseText = resData.candidates?.[0]?.content?.parts?.[0]?.text || "No advice returned.";
            } else {
                // Intelligent rule-based fallback if no key is supplied
                responseText = generateLocalFallbackAdvice(text);
            }
            
            loadingMsg.remove();
            
            const formatted = formatAIResponseHTML(responseText);
            appendChatMessage(panelChatMessages, formatted, 'assistant', null, true);
            
        } catch (err) {
            console.error("Gemini Assistant error:", err);
            loadingMsg.remove();
            appendChatMessage(panelChatMessages, `Error: ${err.message || 'Gemini system offline.'} Please ensure your API Key is valid or clear it to use rule-based guidance.`, 'assistant');
        }
    }

    function appendChatMessage(container, text, sender, id = null, isHTML = false) {
        if (!container) return null;
        const msg = document.createElement('div');
        msg.className = `chat-message ${sender} animate-fade-in`;
        if (id) msg.id = id;
        
        if (isHTML) {
            msg.innerHTML = text;
        } else {
            msg.textContent = text;
        }
        
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
        return msg;
    }

    function formatAIResponseHTML(text) {
        let html = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^- (.*?)$/gm, '<li>$1</li>')
            .replace(/^\* (.*?)$/gm, '<li>$1</li>')
            .replace(/\n/g, '<br>');
            
        html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');
        return html;
    }

    function generateLocalFallbackAdvice(prompt) {
        const query = prompt.toLowerCase();
        let intro = `[Rule-based Emergency Advisor] Here is standard safety advice for ${currentCity || 'your region'}:<br><br>`;
        
        const rainVal = currentCityData?.data?.Rainfall || 0;
        const tempVal = currentCityData?.data?.Temperature || 20;
        
        if (query.includes('flood') || query.includes('rain') || query.includes('water')) {
            return intro + `<strong>FLOOD EMERGENCY CHECKLIST:</strong><br>
            <ul>
                <li><strong>Evacuate immediately</strong> if ordered by local authorities.</li>
                <li><strong>Move to higher ground</strong>. Never walk or drive through floodwaters (Turn Around, Don't Drown).</li>
                <li><strong>Turn off utilities</strong> at main switches if safe to do so.</li>
                <li><strong>Prepare emergency supplies</strong>: fresh water, canned rations, batteries, and blankets.</li>
            </ul><br>
            <em>Note: The current rainfall in ${currentCity} is ${rainVal} mm, indicating a flood safety mitigation baseline of ${Math.round(rainVal * 1.5)}%.</em>`;
        } else if (query.includes('earthquake') || query.includes('seismic') || query.includes('shake')) {
            return intro + `<strong>EARTHQUAKE SAFETY ACTION LIST:</strong><br>
            <ul>
                <li><strong>DROP, COVER, AND HOLD ON</strong> under heavy furniture.</li>
                <li><strong>Stay indoors</strong> until the shaking stops. Avoid glass windows.</li>
                <li><strong>If outdoors</strong>, move to an open area away from buildings, powerlines, and trees.</li>
                <li><strong>Expect aftershocks</strong> and keep a solid hardhat or shield nearby.</li>
            </ul>`;
        } else if (query.includes('heat') || query.includes('hot') || query.includes('heatwave')) {
            return intro + `<strong>HEAT STRESS SAFETY PROTOCOL:</strong><br>
            <ul>
                <li><strong>Stay hydrated</strong>: drink plenty of water even if you do not feel thirsty.</li>
                <li><strong>Minimize sun exposure</strong>: stay indoors during high peak heat hours (11 AM to 4 PM).</li>
                <li><strong>Use fans/AC units</strong>. If not available, go to local public cool centers.</li>
                <li><strong>Check on vulnerable people</strong>: infants, elderly, and pets.</li>
            </ul><br>
            <em>Note: The current temperature in ${currentCity} is ${tempVal}°C.</em>`;
        } else if (query.includes('wind') || query.includes('storm') || query.includes('hurricane')) {
            return intro + `<strong>STORM & SEVERE WIND PROTOCOLS:</strong><br>
            <ul>
                <li><strong>Secure outdoor assets</strong> like trash bins, patio furniture, and bikes.</li>
                <li><strong>Stay away from glass windows</strong>. Move to an interior room if winds are violent.</li>
                <li><strong>Keep devices charged</strong> in anticipation of power line outages.</li>
                <li><strong>Never approach downed wires</strong>; report them immediately.</li>
            </ul>`;
        } else {
            return intro + `<strong>GENERAL DISASTER PROTOCOLS:</strong><br>
            <ul>
                <li><strong>Monitor local radio</strong> or official advisory channels for alerts.</li>
                <li><strong>Keep a disaster supply kit</strong> ready (first aid, water, non-perishable foods).</li>
                <li><strong>Establish a family emergency contact plan</strong> to sync locations.</li>
                <li><strong>Clear exit pathways</strong> in your residence for swift egress.</li>
            </ul><br>
            <em>TIP: To ask Gemini live questions, input your Gemini API Key in the panel on the left!</em>`;
        }
    }

    if (panelSendChatBtn) {
        panelSendChatBtn.addEventListener('click', sendCommandMessage);
        panelChatUserInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendCommandMessage();
        });
    }

    // Load favorites bar tags on boot
    loadFavorites();

    // ─── METRIC OPTIONS CONSOLE ─────────────────────────────────────
    // Stores user preferences: unit system per metric, alert thresholds, alert enabled
    const metricSettings = JSON.parse(localStorage.getItem('whisper_metric_settings') || '{}');

    const metricConfig = {
        temp: {
            label: 'Temperature',
            icon: 'ph-thermometer',
            units: ['°C', '°F'],
            unitKey: 'tempUnit',
            thresholdKey: 'tempThreshold',
            alertKey: 'tempAlertOn',
            thresholdDefault: 38,
            thresholdMin: 20,
            thresholdMax: 55,
            thresholdStep: 1,
            thresholdUnit: (u) => u,
            alertLabel: 'Heatwave Alert',
            description: 'Toggle between Celsius and Fahrenheit. Set an alert threshold — you will be notified when temperature exceeds this value.',
        },
        humidity: {
            label: 'Humidity',
            icon: 'ph-drop',
            units: null,
            thresholdKey: 'humidityThreshold',
            alertKey: 'humidityAlertOn',
            thresholdDefault: 85,
            thresholdMin: 40,
            thresholdMax: 100,
            thresholdStep: 1,
            thresholdUnit: () => '%',
            alertLabel: 'High Humidity Alert',
            description: 'Set an alert threshold for relative humidity. Values above 85% indicate poor comfort conditions.',
        },
        wind: {
            label: 'Wind Speed',
            icon: 'ph-wind',
            units: ['km/h', 'mph'],
            unitKey: 'windUnit',
            thresholdKey: 'windThreshold',
            alertKey: 'windAlertOn',
            thresholdDefault: 50,
            thresholdMin: 10,
            thresholdMax: 150,
            thresholdStep: 5,
            thresholdUnit: (u) => u,
            alertLabel: 'Strong Wind Alert',
            description: 'Toggle between km/h and mph. Winds above 50 km/h can uproot trees and cause structural damage.',
        },
        rain: {
            label: 'Rainfall',
            icon: 'ph-cloud-rain',
            units: ['mm', 'in'],
            unitKey: 'rainUnit',
            thresholdKey: 'rainThreshold',
            alertKey: 'rainAlertOn',
            thresholdDefault: 10,
            thresholdMin: 1,
            thresholdMax: 100,
            thresholdStep: 1,
            thresholdUnit: (u) => u,
            alertLabel: 'Heavy Rain Alert',
            description: 'Toggle between millimetres and inches. Set a per-hour threshold to flag heavy rainfall.',
        },
        aqi: {
            label: 'Air Quality Index',
            icon: 'ph-leaf',
            units: null,
            thresholdKey: 'aqiThreshold',
            alertKey: 'aqiAlertOn',
            thresholdDefault: 100,
            thresholdMin: 20,
            thresholdMax: 300,
            thresholdStep: 5,
            thresholdUnit: () => 'AQI',
            alertLabel: 'Poor Air Quality Alert',
            description: 'AQI above 100 is considered unhealthy for sensitive groups. Set your personal alert level.',
        },
    };

    // Unit conversion helpers
    function convertValue(metric, rawVal) {
        const cfg = metricConfig[metric];
        if (!cfg || !cfg.units) return rawVal;
        const selectedUnit = metricSettings[cfg.unitKey] || cfg.units[0];
        if (metric === 'temp' && selectedUnit === '°F') return +(rawVal * 9 / 5 + 32).toFixed(1);
        if (metric === 'wind' && selectedUnit === 'mph') return +(rawVal * 0.621371).toFixed(1);
        if (metric === 'rain' && selectedUnit === 'in') return +(rawVal * 0.0393701).toFixed(2);
        return rawVal;
    }

    function getUnit(metric) {
        const cfg = metricConfig[metric];
        if (!cfg || !cfg.units) return '';
        return metricSettings[cfg.unitKey] || cfg.units[0];
    }

    // Re-render the 5 metric display values according to current unit settings
    function refreshMetricDisplays() {
        if (!currentCityData) return;
        const d = currentCityData.data;
        if (valTemp) valTemp.textContent = `${convertValue('temp', d.Temperature)}${getUnit('temp')}`;
        if (valHumidity) valHumidity.textContent = `${d.Humidity}%`;
        if (valWind) valWind.textContent = `${convertValue('wind', d.Wind_Speed)} ${getUnit('wind')}`;
        if (valRain) valRain.textContent = `${convertValue('rain', d.Rainfall)} ${getUnit('rain')}`;
        if (valAqi) valAqi.textContent = d.AQI || '0';
    }

    // Check and surface console-threshold alerts as visual indicators on metric boxes
    function checkMetricAlerts() {
        if (!currentCityData) return;
        const d = currentCityData.data;
        const rawVals = { temp: d.Temperature, humidity: d.Humidity, wind: d.Wind_Speed, rain: d.Rainfall, aqi: d.AQI };

        document.querySelectorAll('.metric-box').forEach(box => {
            const key = box.dataset.metric;
            const cfg = metricConfig[key];
            if (!cfg) return;
            const alertOn = metricSettings[cfg.alertKey] !== false; // default true
            const threshold = metricSettings[cfg.thresholdKey] ?? cfg.thresholdDefault;
            const rawVal = rawVals[key] ?? 0;
            const exceeded = alertOn && rawVal >= threshold;
            box.classList.toggle('metric-alert-active', exceeded);
        });
    }

    // ── Console open/close ────────────────────────────────────────────
    const metricsGrid = document.getElementById('metrics-grid');
    const optionsConsole = document.getElementById('metric-options-console');
    const consoleBack = document.getElementById('btn-console-back');
    const consoleTitleEl = document.getElementById('console-metric-title');
    const consoleBody = document.getElementById('console-body');

    let activeMetricKey = null;

    function openConsole(metricKey) {
        activeMetricKey = metricKey;
        const cfg = metricConfig[metricKey];
        if (!cfg || !optionsConsole || !metricsGrid) return;

        consoleTitleEl.textContent = `${cfg.label} Settings`;

        // Build settings UI
        let html = `<p class="console-desc">${cfg.description}</p>`;

        // Unit toggle (if applicable)
        if (cfg.units) {
            const currentUnit = metricSettings[cfg.unitKey] || cfg.units[0];
            html += `
            <div class="setting-row">
                <span class="setting-label">Unit of Measure</span>
                <div class="unit-toggle-group" id="unit-toggle-${metricKey}">
                    ${cfg.units.map(u => `
                        <button class="btn-unit-opt${u === currentUnit ? ' active' : ''}"
                            data-unit="${u}" type="button">${u}</button>`).join('')}
                </div>
            </div>`;
        }

        // Alert threshold slider
        const currentThreshold = metricSettings[cfg.thresholdKey] ?? cfg.thresholdDefault;
        const currentUnit = cfg.units ? (metricSettings[cfg.unitKey] || cfg.units[0]) : '';
        html += `
        <div class="setting-row">
            <span class="setting-label">Alert Threshold</span>
            <div class="setting-input-wrapper">
                <input type="range" class="console-slider" id="slider-${metricKey}"
                    min="${cfg.thresholdMin}" max="${cfg.thresholdMax}" step="${cfg.thresholdStep}"
                    value="${currentThreshold}">
                <span class="slider-value-display" id="sliderval-${metricKey}">
                    ${currentThreshold} ${cfg.thresholdUnit(currentUnit)}
                </span>
            </div>
        </div>`;

        // Alert enable toggle
        const alertOn = metricSettings[cfg.alertKey] !== false;
        html += `
        <div class="toggle-switch-wrapper">
            <span class="toggle-switch-label">${cfg.alertLabel}</span>
            <input type="checkbox" class="switch-input" id="alert-toggle-${metricKey}"
                ${alertOn ? 'checked' : ''}>
        </div>`;

        html += `<button class="btn-console-apply" id="btn-apply-${metricKey}" type="button">
            <i class="ph ph-check"></i> Apply &amp; Save
        </button>`;

        consoleBody.innerHTML = html;

        // Wire up unit toggle buttons
        if (cfg.units) {
            const unitBtns = consoleBody.querySelectorAll(`#unit-toggle-${metricKey} .btn-unit-opt`);
            unitBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    unitBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                });
            });
        }

        // Wire up slider live label
        const slider = document.getElementById(`slider-${metricKey}`);
        const sliderVal = document.getElementById(`sliderval-${metricKey}`);
        if (slider && sliderVal) {
            slider.addEventListener('input', () => {
                const unit = cfg.units
                    ? (consoleBody.querySelector('.btn-unit-opt.active')?.dataset.unit || cfg.units[0])
                    : '';
                sliderVal.textContent = `${slider.value} ${cfg.thresholdUnit(unit)}`;
            });
        }

        // Wire up apply button
        const applyBtn = document.getElementById(`btn-apply-${metricKey}`);
        if (applyBtn) {
            applyBtn.addEventListener('click', () => {
                // Save unit preference
                if (cfg.units) {
                    const selectedUnit = consoleBody.querySelector('.btn-unit-opt.active')?.dataset.unit || cfg.units[0];
                    metricSettings[cfg.unitKey] = selectedUnit;
                }
                // Save threshold
                metricSettings[cfg.thresholdKey] = Number(slider?.value ?? cfg.thresholdDefault);
                // Save alert toggle
                const alertToggle = document.getElementById(`alert-toggle-${metricKey}`);
                metricSettings[cfg.alertKey] = alertToggle ? alertToggle.checked : true;

                localStorage.setItem('whisper_metric_settings', JSON.stringify(metricSettings));

                // Reflect changes immediately
                refreshMetricDisplays();
                checkMetricAlerts();

                // Flash apply button as confirmation
                applyBtn.textContent = '✓ Saved!';
                setTimeout(() => {
                    applyBtn.innerHTML = '<i class="ph ph-check"></i> Apply & Save';
                }, 1400);
            });
        }

        // Swap grid ↔ console
        metricsGrid.classList.add('hidden');
        optionsConsole.classList.remove('hidden');
    }

    function closeConsole() {
        activeMetricKey = null;
        if (metricsGrid) metricsGrid.classList.remove('hidden');
        if (optionsConsole) optionsConsole.classList.add('hidden');
    }

    // Attach click handlers to every metric box
    document.querySelectorAll('.metric-box').forEach(box => {
        box.addEventListener('click', () => openConsole(box.dataset.metric));
    });

    if (consoleBack) consoleBack.addEventListener('click', closeConsole);

    // --- Trends Toggle Bar Click Handler ---
    const btnToggleTrends = document.getElementById('btn-toggle-trends');
    if (btnToggleTrends && trendsCard) {
        btnToggleTrends.addEventListener('click', () => {
            const isHidden = trendsCard.classList.contains('hidden');
            if (isHidden) {
                trendsCard.classList.remove('hidden');
                if (trendsCaret) trendsCaret.classList.add('rotated');
                
                // Render trends chart on open
                const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab || 'hourly';
                renderTrends(activeTab);
            } else {
                trendsCard.classList.add('hidden');
                if (trendsCaret) trendsCaret.classList.remove('rotated');
            }
        });
    }
});

