document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('assessment-form');
    const cityInput = document.getElementById('city-input');
    const resultsContainer = document.getElementById('results-container');
    const loadingState = document.getElementById('loading-state');
    
    // UI Elements
    const riskCard = document.getElementById('risk-card');
    const riskText = document.getElementById('risk-text');
    const statusSubtitle = document.getElementById('status-subtitle');
    const alertsContainer = document.getElementById('alerts-container');
    const recommendationList = document.getElementById('recommendation-list');
    
    // Metrics Elements
    const valTemp = document.getElementById('val-temp');
    const valHumidity = document.getElementById('val-humidity');
    const valWind = document.getElementById('val-wind');
    const valRain = document.getElementById('val-rain');
    const valAqi = document.getElementById('val-aqi');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const city = cityInput.value.trim();
        if (!city) return;
        
        // UI State update
        resultsContainer.classList.add('hidden');
        loadingState.classList.remove('hidden');
        
        // Clear previous errors
        const existingError = document.querySelector('.error-message-box');
        if (existingError) existingError.remove();
        
        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ city })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                showError(data.error || 'An unexpected error occurred.');
                loadingState.classList.add('hidden');
                return;
            }
            
            // Simulate slight delay for dramatic effect/loading
            setTimeout(() => {
                updateUI(data);
                cityInput.value = data.city; // Update input to show resolved city name
                loadingState.classList.add('hidden');
                resultsContainer.classList.remove('hidden');
            }, 600);
            
        } catch (error) {
            console.error('Error fetching prediction:', error);
            showError('Unable to reach the Whisper service. Please check your connection.');
            loadingState.classList.add('hidden');
        }
    });
    
    function showError(message) {
        const errorBox = document.createElement('div');
        errorBox.className = 'error-message-box';
        errorBox.innerHTML = `
            <i class="ph ph-warning-circle"></i>
            <p>${message}</p>
        `;
        
        // Add minimal styling inline for the error box (or add to CSS)
        errorBox.style.background = '#FFF5F5';
        errorBox.style.color = '#C53030';
        errorBox.style.padding = '1rem 1.5rem';
        errorBox.style.borderRadius = '12px';
        errorBox.style.marginTop = '1rem';
        errorBox.style.display = 'flex';
        errorBox.style.alignItems = 'center';
        errorBox.style.gap = '0.75rem';
        errorBox.style.border = '1px solid #FEB2B2';
        errorBox.style.maxWidth = '600px';
        errorBox.style.margin = '1rem auto 0';
        
        // Insert right below the form
        document.querySelector('.search-section').appendChild(errorBox);
    }
    
    function updateUI(res) {
        // Update Risk Level
        riskText.textContent = res.risk_level;
        riskCard.className = 'status-section card animate-fade-in'; // reset and animate
        riskCard.classList.add(`risk-${res.risk_level.toLowerCase()}`);
        
        if (res.risk_level === 'Low') {
            statusSubtitle.textContent = "Conditions are peaceful.";
        } else if (res.risk_level === 'Medium') {
            statusSubtitle.textContent = "Take minor precautions.";
        } else {
            statusSubtitle.textContent = "Please stay safe.";
        }
        
        // Update Metrics
        valTemp.textContent = `${res.data.Temperature}°C`;
        valHumidity.textContent = `${res.data.Humidity}%`;
        valWind.textContent = `${res.data.Wind_Speed}`;
        valRain.textContent = `${res.data.Rainfall}`;
        valAqi.textContent = res.data.AQI || '--';
        
        // Animate metric boxes with stagger
        const metricBoxes = document.querySelectorAll('.metric-box');
        metricBoxes.forEach((box, index) => {
            box.classList.remove('animate-fade-in');
            void box.offsetWidth; // trigger reflow to restart animation
            box.classList.add('animate-fade-in');
            box.style.animationDelay = `${0.1 + (index * 0.1)}s`;
        });
        
        // Update Alerts
        alertsContainer.innerHTML = '';
        if (res.alerts && res.alerts.length > 0) {
            res.alerts.forEach((alert, index) => {
                const alertEl = document.createElement('div');
                alertEl.className = 'alert-item animate-fade-in';
                alertEl.style.animationDelay = `${0.2 + (index * 0.15)}s`;
                alertEl.innerHTML = `<i class="ph ph-warning-circle"></i> <span>${alert}</span>`;
                alertsContainer.appendChild(alertEl);
            });
        }
        
        // Update Recommendations
        recommendationList.innerHTML = '';
        if (res.recommendations && res.recommendations.length > 0) {
            res.recommendations.forEach((rec, index) => {
                const li = document.createElement('li');
                li.textContent = rec;
                li.className = 'animate-fade-in';
                li.style.animationDelay = `${0.3 + (index * 0.15)}s`;
                recommendationList.appendChild(li);
            });
        }
    }
});
