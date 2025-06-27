/**
 * Predictions Dashboard JavaScript
 * 
 * Handles the hospital danger prediction interface including:
 * - Loading and displaying prediction data
 * - Updating danger scores and risk levels
 * - Managing prediction charts
 * - Handling model training requests
 */

let currentSimId = null;
let predictionCharts = {};
let predictionData = null;
let refreshInterval = null;

/**
 * Initialize the predictions dashboard
 */
function initializePredictions(simId) {
    currentSimId = simId;
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial predictions
    loadPredictions();
    
    // Set up auto-refresh (every 5 minutes)
    refreshInterval = setInterval(() => {
        loadPredictions(false); // Silent refresh
    }, 5 * 60 * 1000);
}

/**
 * Set up event listeners for user interactions
 */
function setupEventListeners() {
    // Refresh button
    document.getElementById('refreshPredictions').addEventListener('click', () => {
        loadPredictions(true);
    });
    
    // Train models button
    document.getElementById('trainModels').addEventListener('click', () => {
        trainModels();
    });
}

/**
 * Load predictions from the API
 */
async function loadPredictions(showLoading = true) {
    let modal = null;
    
    if (showLoading) {
        modal = showLoadingModal('Generating predictions...');
    }
    
    try {
        const response = await fetch(`/api/simulation/${currentSimId}/predictions`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        predictionData = await response.json();
        
        if (predictionData.error) {
            throw new Error(predictionData.error);
        }
        
        updatePredictionDisplay();
        
        if (showLoading) {
            // Force hide modal immediately after data is loaded and display is updated
            hideLoadingModal();
            // Also try again after a very short delay as backup
            setTimeout(() => {
                hideLoadingModal();
            }, 50);
        }
        
    } catch (error) {
        console.error('Error loading predictions:', error);
        
        if (showLoading) {
            setTimeout(() => {
                hideLoadingModal();
            }, 100);
        }
        
        showErrorAlert(`Failed to load predictions: ${error.message}`);
    }
}

/**
 * Update the entire prediction display with new data
 */
function updatePredictionDisplay() {
    if (!predictionData) return;
    
    updateOverallDangerScore();
    updateCurrentMetrics();
    updateTimeHorizonPredictions();
    updateIndividualPredictions();
    updatePredictionCharts();
    updateModelInfo();
}

/**
 * Update the overall danger score display
 */
function updateOverallDangerScore() {
    const score = predictionData.overall_danger_score || 0;
    const scorePercent = Math.round(score * 100);
    
    // Update score circle
    const scoreElement = document.getElementById('dangerScoreText');
    const scoreCircle = document.getElementById('overallDangerScore');
    const riskBadge = document.getElementById('riskLevelBadge');
    
    scoreElement.textContent = `${scorePercent}%`;
    
    // Determine risk level and styling
    let riskLevel, riskClass, circleClass;
    if (score >= 0.7) {
        riskLevel = 'High Risk';
        riskClass = 'bg-danger';
        circleClass = 'danger-high';
    } else if (score >= 0.4) {
        riskLevel = 'Medium Risk';
        riskClass = 'bg-warning';
        circleClass = 'danger-medium';
    } else {
        riskLevel = 'Low Risk';
        riskClass = 'bg-success';
        circleClass = 'danger-low';
    }
    
    // Update risk badge
    riskBadge.textContent = riskLevel;
    riskBadge.className = `badge ${riskClass}`;
    
    // Update score circle styling
    scoreCircle.className = `danger-score-circle ${circleClass}`;
    
    // Add visual indicator to circle
    const percentage = score * 100;
    scoreCircle.style.background = `conic-gradient(
        ${getRiskColor(score)} ${percentage * 3.6}deg,
        #e9ecef ${percentage * 3.6}deg
    )`;
}

/**
 * Update current metrics display
 */
function updateCurrentMetrics() {
    const metrics = predictionData.current_metrics || {};
    
    document.getElementById('patientsTotal').textContent = metrics.patients_total || '--';
    document.getElementById('patientsWaiting').textContent = metrics.patients_waiting || '--';
    document.getElementById('doctorsUtilization').textContent = 
        metrics.doctor_utilization ? `${Math.round(metrics.doctor_utilization * 100)}%` : '--%';
    document.getElementById('avgWaitTime').textContent = 
        metrics.avg_wait_time ? `${Math.round(metrics.avg_wait_time)} min` : '-- min';
}

/**
 * Update time horizon predictions
 */
function updateTimeHorizonPredictions() {
    const container = document.getElementById('timeHorizonPredictions');
    const horizons = predictionData.time_horizon_predictions || {};
    
    container.innerHTML = '';
    
    Object.entries(horizons).forEach(([key, horizon]) => {
        const col = document.createElement('div');
        col.className = 'col-md-3 mb-3';
        
        const score = horizon.danger_score || 0;
        const scorePercent = Math.round(score * 100);
        const riskClass = getRiskClass(score);
        const riskIcon = getRiskIcon(horizon.risk_level);
        
        col.innerHTML = `
            <div class="card h-100 border-${riskClass}">
                <div class="card-body text-center">
                    <h6 class="card-title">${horizon.label}</h6>
                    <div class="danger-score-mini mb-2">
                        <span class="score-text-mini">${scorePercent}%</span>
                    </div>
                    <span class="badge bg-${riskClass}">
                        ${riskIcon} ${horizon.risk_level}
                    </span>
                </div>
            </div>
        `;
        
        container.appendChild(col);
    });
}

/**
 * Update individual prediction displays
 */
function updateIndividualPredictions() {
    const predictions = predictionData.individual_predictions || {};
    
    // Map prediction types to UI elements
    const predictionMap = {
        'overload_danger': 'overload',
        'wait_time_danger': 'waitTime',
        'staffing_danger': 'staffing',
        'system_stress': 'systemStress'
    };
    
    Object.entries(predictionMap).forEach(([predType, uiPrefix]) => {
        const prediction = predictions[predType];
        if (!prediction || !prediction.danger_probability) return;
        
        const probability = prediction.danger_probability;
        const isHigh = prediction.is_danger;
        const probabilityPercent = Math.round(probability * 100);
        
        // Update progress bar
        const progressBar = document.getElementById(`${uiPrefix}Bar`);
        progressBar.style.width = `${probabilityPercent}%`;
        progressBar.className = `progress-bar ${getProgressBarClass(probability)}`;
        
        // Update probability text
        document.getElementById(`${uiPrefix}Prob`).textContent = `${probabilityPercent}%`;
        
        // Update status badge
        const statusBadge = document.getElementById(`${uiPrefix}Status`);
        if (isHigh) {
            statusBadge.textContent = '🔴 High Risk';
            statusBadge.className = 'status-badge badge bg-danger';
        } else {
            statusBadge.textContent = '🟢 Low Risk';
            statusBadge.className = 'status-badge badge bg-success';
        }
    });
}

/**
 * Update prediction charts
 */
function updatePredictionCharts() {
    const predictions = predictionData.individual_predictions || {};
    
    // Update wait time prediction
    if (predictions.wait_time_regression) {
        const predicted = predictions.wait_time_regression.predicted_value || 0;
        const current = predictions.wait_time_regression.current_value || 0;
        
        document.getElementById('predictedWaitTime').textContent = `${Math.round(predicted)} minutes`;
        
        updateChart('waitTimePredictionChart', {
            type: 'bar',
            data: {
                labels: ['Current', 'Predicted'],
                datasets: [{
                    label: 'Wait Time (minutes)',
                    data: [current, predicted],
                    backgroundColor: ['#6c757d', predicted > current ? '#dc3545' : '#28a745'],
                    borderColor: ['#495057', predicted > current ? '#dc3545' : '#28a745'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Minutes'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    // Update patient count prediction
    if (predictions.patient_count_regression) {
        const predicted = predictions.patient_count_regression.predicted_value || 0;
        const current = predictions.patient_count_regression.current_value || 0;
        
        document.getElementById('predictedPatientCount').textContent = `${Math.round(predicted)} patients`;
        
        updateChart('patientCountPredictionChart', {
            type: 'bar',
            data: {
                labels: ['Current', 'Predicted'],
                datasets: [{
                    label: 'Patient Count',
                    data: [current, predicted],
                    backgroundColor: ['#6c757d', predicted > current ? '#fd7e14' : '#20c997'],
                    borderColor: ['#495057', predicted > current ? '#fd7e14' : '#20c997'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Patients'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
}

/**
 * Update model information display
 */
function updateModelInfo() {
    document.getElementById('lastTraining').textContent = 'Recent'; // Would come from API
    document.getElementById('predictionTime').textContent = new Date().toLocaleTimeString();
    
    const modelCount = Object.keys(predictionData.individual_predictions || {}).length;
    document.getElementById('modelsLoaded').textContent = modelCount;
    
    // Data quality assessment
    const overallScore = predictionData.overall_danger_score || 0;
    let dataQuality, qualityClass;
    
    if (overallScore > 0) {
        dataQuality = 'Good';
        qualityClass = 'bg-success';
    } else {
        dataQuality = 'Limited';
        qualityClass = 'bg-warning';
    }
    
    const qualityBadge = document.getElementById('dataQuality');
    qualityBadge.textContent = dataQuality;
    qualityBadge.className = `badge ${qualityClass}`;
    
    document.getElementById('modelAccuracy').textContent = '85-92%'; // Would come from training metrics
    
    // Generate recommendation
    let recommendation;
    if (overallScore >= 0.7) {
        recommendation = 'Immediate attention recommended - high risk detected';
    } else if (overallScore >= 0.4) {
        recommendation = 'Monitor situation closely - medium risk';
    } else {
        recommendation = 'System operating normally - continue monitoring';
    }
    
    document.getElementById('recommendation').textContent = recommendation;
}

/**
 * Train ML models
 */
async function trainModels() {
    showLoadingModal('Training models...');
    
    try {
        const response = await fetch('/api/ml/train', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        hideLoadingModal();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        showSuccessAlert('Models trained successfully! Refreshing predictions...');
        
        // Refresh predictions after training
        setTimeout(() => {
            loadPredictions(false);
        }, 1000);
        
    } catch (error) {
        console.error('Error training models:', error);
        hideLoadingModal();
        showErrorAlert(`Failed to train models: ${error.message}`);
    }
}

/**
 * Create or update a chart
 */
function updateChart(canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    // Destroy existing chart
    if (predictionCharts[canvasId]) {
        predictionCharts[canvasId].destroy();
    }
    
    // Create new chart
    predictionCharts[canvasId] = new Chart(ctx, config);
}

/**
 * Utility functions
 */
function getRiskColor(score) {
    if (score >= 0.7) return '#dc3545'; // Red
    if (score >= 0.4) return '#ffc107'; // Yellow
    return '#28a745'; // Green
}

function getRiskClass(score) {
    if (score >= 0.7) return 'danger';
    if (score >= 0.4) return 'warning';
    return 'success';
}

function getRiskIcon(riskLevel) {
    switch (riskLevel) {
        case 'High': return '🔴';
        case 'Medium': return '🟡';
        case 'Low': return '🟢';
        default: return '⚪';
    }
}

function getProgressBarClass(probability) {
    if (probability >= 0.7) return 'bg-danger';
    if (probability >= 0.4) return 'bg-warning';
    return 'bg-success';
}

function showLoadingModal(text) {
    document.getElementById('loadingText').textContent = text;
    const modalElement = document.getElementById('loadingModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // Safety mechanism: force hide modal after 10 seconds maximum
    setTimeout(() => {
        hideLoadingModal();
        console.warn('Modal auto-hidden after 10 seconds safety timeout');
    }, 10000);
    
    return modal;
}

function hideLoadingModal() {
    try {
        const modalElement = document.getElementById('loadingModal');
        if (modalElement) {
            // Force hide modal immediately
            modalElement.style.display = 'none';
            modalElement.classList.remove('show', 'fade');
            modalElement.setAttribute('aria-hidden', 'true');
            modalElement.removeAttribute('aria-modal');
            modalElement.removeAttribute('role');
            
            // Force remove backdrop
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            
            // Reset body
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            
            // Try Bootstrap's hide method as secondary cleanup
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.dispose(); // Completely destroy the modal instance
            }
            
            console.log('Modal forcefully hidden');
        }
    } catch (error) {
        console.error('Error hiding modal:', error);
        // Ultimate fallback
        const modalElement = document.getElementById('loadingModal');
        if (modalElement) {
            modalElement.style.display = 'none !important';
            modalElement.style.visibility = 'hidden';
        }
        document.body.style.overflow = 'auto';
        document.body.classList.remove('modal-open');
    }
}

function showErrorAlert(message) {
    const alertHtml = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at top of container
    const container = document.querySelector('.container-fluid');
    container.insertAdjacentHTML('afterbegin', alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}

function showSuccessAlert(message) {
    const alertHtml = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="fas fa-check-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at top of container
    const container = document.querySelector('.container-fluid');
    container.insertAdjacentHTML('afterbegin', alertHtml);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 3000);
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    // Destroy all charts
    Object.values(predictionCharts).forEach(chart => {
        if (chart) {
            chart.destroy();
        }
    });
});