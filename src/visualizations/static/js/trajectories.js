/* filepath: /Users/arsnm/Programming/repos/gitlab/telecom-paris/ia-medical/src/visualizations/static/js/trajectories.js */

// Global variables
let trajectoryData = null;
let currentMetric = 'patients_total';
let currentTimeRange = 'all';
let currentChartType = 'line';
let trajectoryEvolutionChart = null;
let distributionChart = null;
let confidenceChart = null;

/**
 * Initialize the trajectories page
 */
function initTrajectories(simId) {
    console.log('Initializing trajectories for simulation:', simId);
    loadTrajectoryData(simId);
    setupEventListeners();
}

/**
 * Load trajectory data from the API
 */
async function loadTrajectoryData(simId) {
    try {
        updateStatus('Loading trajectory data...', 'loading');
        
        const response = await fetch(`/api/simulation/${simId}/trajectories`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        trajectoryData = await response.json();
        
        if (trajectoryData.trajectories && trajectoryData.trajectories.length > 0) {
            updateStatus(`${trajectoryData.trajectories.length} trajectories loaded`, 'success');
            renderTrajectoryOverview();
            renderTrajectoryCharts();
            renderStatistics();
            renderExtremeScenarios();
            populateTrajectorySelector();
            setupEventListeners();
        } else {
            updateStatus('No trajectories found', 'warning');
            showNoDataMessage();
        }
    } catch (error) {
        console.error('Error loading trajectory data:', error);
        updateStatus('Error loading data', 'error');
        showErrorMessage(error.message);
    }
}

/**
 * Update the status display
 */
function updateStatus(message, type) {
    const statusElement = document.getElementById('trajectory-status');
    
    let iconClass = 'fas fa-info-circle';
    let textClass = 'text-info';
    
    switch(type) {
        case 'loading':
            iconClass = 'spinner-border spinner-border-sm';
            textClass = 'text-primary';
            break;
        case 'success':
            iconClass = 'fas fa-check-circle';
            textClass = 'text-success';
            break;
        case 'warning':
            iconClass = 'fas fa-exclamation-triangle';
            textClass = 'text-warning';
            break;
        case 'error':
            iconClass = 'fas fa-times-circle';
            textClass = 'text-danger';
            break;
    }
    
    statusElement.innerHTML = `
        <i class="${iconClass}"></i>
        <span class="ms-2 ${textClass}">${message}</span>
    `;
}

/**
 * Render trajectory overview metrics
 */
function renderTrajectoryOverview() {
    const data = trajectoryData;
    
    document.getElementById('total-trajectories').textContent = data.total_trajectories;
    document.getElementById('trajectory-duration').textContent = Math.round(data.duration_days);
    document.getElementById('avg-patients').textContent = Math.round(data.statistics.patients_total.mean);
    document.getElementById('avg-wait-time').textContent = Math.round(data.statistics.avg_wait_time.mean);
}

/**
 * Render main trajectory charts
 */
function renderTrajectoryCharts() {
    renderEvolutionChart();
    renderDistributionChart();
    renderConfidenceChart();
}

/**
 * Render trajectory evolution chart
 */
function renderEvolutionChart() {
    updateEvolutionChart(trajectoryData.trajectories);
}

/**
 * Update evolution chart with filtered trajectories
 */
function updateEvolutionChart(trajectories) {
    const ctx = document.getElementById('trajectoryEvolutionChart').getContext('2d');
    
    if (trajectoryEvolutionChart) {
        trajectoryEvolutionChart.destroy();
    }
    
    const datasets = [];
    
    // Add a sample of trajectories (max 10 for clarity)
    const sampleTrajectories = trajectories.slice(0, 10);
    
    sampleTrajectories.forEach((traj, index) => {
        const color = `hsl(${(index * 360) / sampleTrajectories.length}, 70%, 50%)`;
        
        datasets.push({
            label: `Trajectory ${traj.trajectory_id}`,
            data: traj.data.map(point => ({
                x: point.sim_time,
                y: point[currentMetric]
            })),
            borderColor: color,
            backgroundColor: color + '20',
            borderWidth: 1,
            fill: currentChartType === 'area',
            pointRadius: 0,
            tension: 0.1
        });
    });
    
    // Add average line if available
    if (trajectoryData.average_trajectory) {
        const filteredAverage = getFilteredTrajectoryData(trajectoryData.average_trajectory, currentTimeRange);
        datasets.push({
            label: 'Average',
            data: filteredAverage.map(point => ({
                x: point.sim_time,
                y: point[currentMetric]
            })),
            borderColor: '#000',
            backgroundColor: '#000',
            borderWidth: 3,
            fill: false,
            pointRadius: 0,
            tension: 0.1
        });
    }
    
    trajectoryEvolutionChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: getMetricLabel(currentMetric)
                },
                legend: {
                    display: false // Too many trajectories for useful legend
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Temps de simulation (minutes)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: getMetricLabel(currentMetric)
                    }
                }
            },
            elements: {
                line: {
                    borderWidth: 1
                }
            }
        }
    });
}

/**
 * Render distribution chart (histogram of final values)
 */
function renderDistributionChart() {
    updateDistributionChart(trajectoryData.trajectories);
}

/**
 * Update distribution chart with filtered trajectories
 */
function updateDistributionChart(trajectories) {
    const ctx = document.getElementById('distributionChart').getContext('2d');
    
    if (distributionChart) {
        distributionChart.destroy();
    }
    
    // Get final values for current metric from filtered data
    const finalValues = trajectories.map(traj => {
        const filteredData = getFilteredTrajectoryData(traj.data, currentTimeRange);
        if (filteredData.length === 0) return 0;
        const lastPoint = filteredData[filteredData.length - 1];
        return lastPoint[currentMetric];
    }).filter(value => value !== undefined && value !== null);
    
    // Create histogram bins
    const min = Math.min(...finalValues);
    const max = Math.max(...finalValues);
    const numBins = Math.min(20, Math.ceil(Math.sqrt(finalValues.length)));
    const binSize = (max - min) / numBins;
    
    const bins = Array(numBins).fill(0);
    const binLabels = [];
    
    for (let i = 0; i < numBins; i++) {
        const binStart = min + i * binSize;
        const binEnd = min + (i + 1) * binSize;
        binLabels.push(`${Math.round(binStart)}-${Math.round(binEnd)}`);
    }
    
    finalValues.forEach(value => {
        const binIndex = Math.min(Math.floor((value - min) / binSize), numBins - 1);
        bins[binIndex]++;
    });
    
    distributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: binLabels,
            datasets: [{
                label: 'Frequency',
                data: bins,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Distribution - ${getMetricLabel(currentMetric)}`
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Number of trajectories'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: getMetricLabel(currentMetric)
                    }
                }
            }
        }
    });
}

/**
 * Render confidence intervals chart
 */
function renderConfidenceChart() {
    updateConfidenceChart(trajectoryData.trajectories);
}

/**
 * Update confidence chart with filtered trajectories
 */
function updateConfidenceChart(trajectories) {
    const ctx = document.getElementById('confidenceChart').getContext('2d');
    
    if (confidenceChart) {
        confidenceChart.destroy();
    }
    
    // Get filtered data for all trajectories
    const filteredTrajectories = trajectories.map(traj => 
        getFilteredTrajectoryData(traj.data, currentTimeRange)
    );
    
    // Get all unique time points from filtered data
    const allTimes = new Set();
    filteredTrajectories.forEach(trajData => {
        trajData.forEach(point => allTimes.add(point.sim_time));
    });
    
    const timePoints = Array.from(allTimes).sort((a, b) => a - b);
    
    // Calculate percentiles for each time point
    const percentileData = timePoints.map(time => {
        const valuesAtTime = filteredTrajectories.map(trajData => {
            const point = trajData.find(p => p.sim_time === time);
            return point ? point[currentMetric] : null;
        }).filter(v => v !== null);
        
        valuesAtTime.sort((a, b) => a - b);
        
        const p25 = valuesAtTime[Math.floor(valuesAtTime.length * 0.25)];
        const p50 = valuesAtTime[Math.floor(valuesAtTime.length * 0.5)];
        const p75 = valuesAtTime[Math.floor(valuesAtTime.length * 0.75)];
        
        return { time, p25, p50, p75 };
    });
    
    confidenceChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: '75th percentile',
                    data: percentileData.map(p => ({ x: p.time, y: p.p75 })),
                    borderColor: 'rgba(255, 99, 132, 0.8)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    fill: '+1'
                },
                {
                    label: 'Median',
                    data: percentileData.map(p => ({ x: p.time, y: p.p50 })),
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.3)',
                    fill: '+1'
                },
                {
                    label: '25th percentile',
                    data: percentileData.map(p => ({ x: p.time, y: p.p25 })),
                    borderColor: 'rgba(75, 192, 192, 0.8)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    fill: 'origin'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Intervalles de confiance - ${getMetricLabel(currentMetric)}`
                },
                legend: {
                    display: true
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Temps de simulation (minutes)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: getMetricLabel(currentMetric)
                    }
                }
            },
            elements: {
                line: {
                    borderWidth: 2
                },
                point: {
                    radius: 0
                }
            }
        }
    });
}

/**
 * Render statistics table
 */
function renderStatistics() {
    const tbody = document.getElementById('statistics-table');
    
    const metrics = ['patients_total', 'patients_treated', 'waiting_patients', 'avg_wait_time'];
    const rows = metrics.map(metric => {
        const stats = trajectoryData.statistics[metric];
        if (!stats) return '';
        
        return `
            <tr>
                <td><strong>${getMetricLabel(metric)}</strong></td>
                <td>${stats.mean.toFixed(1)}</td>
                <td>${stats.median.toFixed(1)}</td>
                <td>${stats.std.toFixed(1)}</td>
                <td>${stats.min.toFixed(0)} / ${stats.max.toFixed(0)}</td>
            </tr>
        `;
    }).join('');
    
    tbody.innerHTML = rows;
}

/**
 * Render extreme scenarios
 */
function renderExtremeScenarios() {
    const container = document.getElementById('extreme-scenarios');
    
    // Find best and worst scenarios for each metric
    const scenarios = [];
    
    ['patients_total', 'avg_wait_time'].forEach(metric => {
        const finalValues = trajectoryData.trajectories.map((traj, index) => {
            const lastPoint = traj.data[traj.data.length - 1];
            return { 
                trajectory_id: traj.trajectory_id,
                value: lastPoint[metric],
                index: index
            };
        });
        
        finalValues.sort((a, b) => a.value - b.value);
        
        const best = finalValues[0];
        const worst = finalValues[finalValues.length - 1];
        
        scenarios.push({
            metric: getMetricLabel(metric),
            best: best,
            worst: worst,
            isBetter: metric === 'avg_wait_time' ? 'lower' : 'higher'
        });
    });
    
    const html = scenarios.map(scenario => `
        <div class="mb-3">
            <h6>${scenario.metric}</h6>
            <div class="row">
                <div class="col-6">
                    <div class="alert alert-success alert-sm">
                        <strong>Best:</strong> Trajectory ${scenario.best.trajectory_id}<br>
                        <small>${scenario.best.value.toFixed(1)}</small>
                    </div>
                </div>
                <div class="col-6">
                    <div class="alert alert-danger alert-sm">
                        <strong>Worst:</strong> Trajectory ${scenario.worst.trajectory_id}<br>
                        <small>${scenario.worst.value.toFixed(1)}</small>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

/**
 * Populate trajectory selector
 */
function populateTrajectorySelector() {
    const selector = document.getElementById('trajectory-selector');
    
    const options = trajectoryData.trajectories.map(traj => 
        `<option value="${traj.trajectory_id}">Trajectory ${traj.trajectory_id}</option>`
    ).join('');
    
    selector.innerHTML = '<option value="">Select a trajectory...</option>' + options;
}

/**
 * Setup all event listeners for trajectory controls
 */
function setupEventListeners() {
    // Chart controls - similar to analytics
    document.getElementById('timeRangeSelect').addEventListener('change', function() {
        currentTimeRange = this.value;
        console.log('Time range changed to:', currentTimeRange);
        updateChartsWithFilters();
    });
    
    document.getElementById('metricSelect').addEventListener('change', function() {
        currentMetric = this.value;
        console.log('Metric changed to:', currentMetric);
        updateChartsWithFilters();
    });
    
    document.getElementById('chartTypeSelect').addEventListener('change', function() {
        currentChartType = this.value;
        console.log('Chart type changed to:', currentChartType);
        updateChartTypes(this.value);
    });
    
    // Trajectory selector
    document.getElementById('trajectory-selector').addEventListener('change', function() {
        const trajectoryId = this.value;
        if (trajectoryId) {
            showTrajectoryDetails(parseInt(trajectoryId));
        } else {
            clearDetailedAnalysis();
        }
    });
    
    // Compare button
    document.getElementById('compare-btn').addEventListener('click', function() {
        // Implementation for trajectory comparison
        alert('Trajectory comparison feature to be implemented');
    });
}

/**
 * Show detailed analysis for a specific trajectory
 */
function showTrajectoryDetails(trajectoryId) {
    const trajectory = trajectoryData.trajectories.find(t => t.trajectory_id === trajectoryId);
    if (!trajectory) return;
    
    const container = document.getElementById('detailed-analysis');
    
    const lastPoint = trajectory.data[trajectory.data.length - 1];
    
    const html = `
        <div class="row">
            <div class="col-md-6">
                <h6>Final Results</h6>
                <table class="table table-sm">
                    <tr>
                        <td>Total Patients:</td>
                        <td><strong>${lastPoint.patients_total}</strong></td>
                    </tr>
                    <tr>
                        <td>Patients Treated:</td>
                        <td><strong>${lastPoint.patients_treated}</strong></td>
                    </tr>
                    <tr>
                        <td>Waiting:</td>
                        <td><strong>${lastPoint.waiting_patients}</strong></td>
                    </tr>
                    <tr>
                        <td>Avg Wait Time:</td>
                        <td><strong>${lastPoint.avg_wait_time.toFixed(1)} min</strong></td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6>Trajectory Parameters</h6>
                <div class="small">
                    <pre>${JSON.stringify(JSON.parse(trajectory.parameters), null, 2)}</pre>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Clear trajectory details
 */
function clearDetailedAnalysis() {
    const container = document.getElementById('detailed-analysis');
    container.innerHTML = `
        <div class="text-center text-muted">
            <i class="fas fa-arrow-up fa-2x mb-3"></i>
            <p>Select a trajectory to view detailed analysis</p>
        </div>
    `;
}

/**
 * Show no data message
 */
function showNoDataMessage() {
    document.querySelector('.container-fluid').innerHTML = `
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body text-center">
                        <i class="fas fa-project-diagram fa-3x text-muted mb-3"></i>
                        <h4>No Trajectories Available</h4>
                        <p class="text-muted">
                            No trajectories have been generated for this simulation.
                            To generate trajectories, use the command:
                        </p>
                        <code>python -m src.simulation.sim_utils trajectories ${SIM_ID} --num=50 --days=30</code>
                        <div class="mt-3">
                            <a href="/" class="btn btn-primary">Back to Home</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Show error message
 */
function showErrorMessage(error) {
    document.querySelector('.container-fluid').innerHTML = `
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="alert alert-danger text-center">
                    <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                    <h4>Loading Error</h4>
                    <p>${error}</p>
                    <button onclick="location.reload()" class="btn btn-outline-danger">
                        Retry
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Get human-readable label for metric
 */
function getMetricLabel(metric) {
    const labels = {
        'patients_total': 'Total Patients',
        'patients_treated': 'Patients Treated',
        'waiting_patients': 'Waiting Patients',
        'busy_doctors': 'Busy Doctors',
        'avg_wait_time': 'Average Wait Time (min)'
    };
    
    return labels[metric] || metric;
}

/**
 * Filter trajectory data points based on time scale
 */
function filterDataByTimeScale(trajectory, timeScale) {
    if (timeScale === 'all') {
        return trajectory.data_points;
    }
    
    const maxTime = parseInt(timeScale);
    return trajectory.data_points.filter(point => point.simulation_time <= maxTime);
}

/**
 * Get time scale label for chart title
 */
function getTimeScaleLabel(timeScale) {
    switch(timeScale) {
        case '1440': return 'Next 24 Hours';
        case '10080': return 'Next 7 Days';
        case '43200': return 'Next 30 Days';
        case 'all': return 'Full Duration';
        default: return 'Custom Range';
    }
}

/**
 * Update chart title with current metric and time scale
 */
function updateChartTitle(chart, baseTitle, metric, timeScale) {
    const metricLabel = getMetricLabel(metric);
    const timeLabel = getTimeScaleLabel(timeScale);
    
    if (chart && chart.options && chart.options.plugins && chart.options.plugins.title) {
        chart.options.plugins.title.text = `${baseTitle} - ${metricLabel} (${timeLabel})`;
        chart.update('none');
    }
}

/**
 * Update charts with current filters
 */
function updateChartsWithFilters() {
    if (!trajectoryData) return;
    
    console.log('Applying filters - Time range:', currentTimeRange, 'Metric:', currentMetric);
    
    // Apply filters to trajectory data
    const filteredTrajectories = trajectoryData.trajectories.map(traj => ({
        ...traj,
        data: getFilteredTrajectoryData(traj.data, currentTimeRange)
    }));
    
    // Update charts with filtered data
    updateEvolutionChart(filteredTrajectories);
    updateDistributionChart(filteredTrajectories);
    updateConfidenceChart(filteredTrajectories);
    
    console.log('Charts updated with filtered data');
}

/**
 * Filter trajectory data based on time range
 */
function getFilteredTrajectoryData(data, timeRange) {
    if (!data || timeRange === 'all') {
        return data;
    }
    
    let cutoffMinutes;
    
    switch (timeRange) {
        case '24h':
            cutoffMinutes = 24 * 60; // First 24 hours
            break;
        case '7d':
            cutoffMinutes = 7 * 24 * 60; // First 7 days
            break;
        case '30d':
            cutoffMinutes = 30 * 24 * 60; // First 30 days
            break;
        default:
            return data;
    }
    
    return data.filter(point => point.sim_time <= cutoffMinutes);
}

/**
 * Update chart types
 */
function updateChartTypes(newType) {
    console.log('Updating chart types to:', newType);
    
    if (trajectoryEvolutionChart) {
        trajectoryEvolutionChart.config.type = newType;
        trajectoryEvolutionChart.update();
    }
    
    if (confidenceChart) {
        confidenceChart.config.type = newType;
        confidenceChart.update();
    }
}