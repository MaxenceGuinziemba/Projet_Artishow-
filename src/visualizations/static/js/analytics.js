// Analytics page JavaScript
let analyticsData = null;
let charts = {};
let currentSimId = null;
let currentSpecialty = 'all';

function initializeAnalytics(simId) {
    currentSimId = simId;
    loadAnalyticsData();
    setupEventListeners();
}

async function loadAnalyticsData() {
    try {
        const response = await fetch(`/api/simulation/${currentSimId}/analytics`);
        const result = await response.json();
        
        if (result.success) {
            analyticsData = result.data;
            
            // Debug: Check the actual time intervals in the data
            if (analyticsData.hospital_states && analyticsData.hospital_states.length > 1) {
                const timeDiffs = [];
                for (let i = 1; i < Math.min(20, analyticsData.hospital_states.length); i++) {
                    const diff = analyticsData.hospital_states[i].sim_minutes - analyticsData.hospital_states[i-1].sim_minutes;
                    timeDiffs.push(diff);
                }
                console.log('Time intervals in hospital_states data (first 20):', timeDiffs);
                console.log('Min time interval:', Math.min(...timeDiffs), 'minutes');
                console.log('Max time interval:', Math.max(...timeDiffs), 'minutes');
                
                // Smart granularity selection based on data size for performance
                const dataPointCount = analyticsData.hospital_states.length;
                console.log('Total data points:', dataPointCount);
                
                if (dataPointCount > 5000) {
                    console.log('Large dataset detected, recommending day granularity for better performance');
                    document.getElementById('granularitySelect').value = 'day';
                } else if (dataPointCount > 1500) {
                    console.log('Medium dataset detected, using hour granularity');
                    document.getElementById('granularitySelect').value = 'hour';
                } else {
                    console.log('Small dataset, minute granularity available');
                }
            }
            
            createCharts();
            populateDoctorPerformance();
            populateSpecialtyDropdown(); // Populate specialties on load
        } else {
            showError('Failed to load analytics data: ' + result.error);
        }
    } catch (error) {
        showError('Error loading analytics data: ' + error.message);
    }
}

function setupEventListeners() {
    // Chart controls
    document.getElementById('timeRangeSelect').addEventListener('change', function() {
        console.log('Time range changed to:', this.value);
        updateChartsWithFilters();
    });
    
    document.getElementById('granularitySelect').addEventListener('change', function() {
        console.log('Granularity changed to:', this.value);
        updateChartsWithFilters();
    });
    
    // Specialty filter
    document.getElementById('specialtySelect').addEventListener('change', function() {
        currentSpecialty = this.value;
        console.log('Specialty filter changed to:', currentSpecialty);
        updateDoctorsChart();
    });
    
    // Show/hide data series
    document.getElementById('showTotal').addEventListener('change', updatePatientsChart);
    document.getElementById('showTreated').addEventListener('change', updatePatientsChart);
    document.getElementById('showWaiting').addEventListener('change', updatePatientsChart);
}

function updateChartsWithFilters() {
    if (!analyticsData) return;
    
    const timeRange = document.getElementById('timeRangeSelect').value;
    const granularity = document.getElementById('granularitySelect').value;
    
    console.log('Applying filters - Time range:', timeRange, 'Granularity:', granularity);
    
    // Filter hospital states data first
    let filteredStates = getFilteredData(analyticsData.hospital_states, timeRange);
    console.log('After time filtering:', filteredStates.length, 'data points');
    
    // Then aggregate the filtered data
    filteredStates = aggregateData(filteredStates, granularity);
    console.log('After aggregation:', filteredStates.length, 'data points');
    
    // Update patients chart
    if (charts.patients) {
        charts.patients.data.labels = filteredStates.map(state => formatTimeLabel(state.sim_minutes));
        charts.patients.data.datasets[0].data = filteredStates.map(state => state.patients_total);
        charts.patients.data.datasets[1].data = filteredStates.map(state => state.patients_treated);
        charts.patients.data.datasets[2].data = filteredStates.map(state => state.waiting_patients);
        charts.patients.update();
    }
    
    // Update doctors chart
    if (charts.doctors) {
        charts.doctors.data.labels = filteredStates.map(state => formatTimeLabel(state.sim_minutes));
        // For specialty filtering, we need to recalculate the doctor data
        let doctorData;
        if (currentSpecialty === 'all') {
            doctorData = filteredStates.map(state => state.busy_doctors);
        } else {
            // Calculate specialty-specific data for filtered timeframe
            const specialtyDoctors = analyticsData.doctor_performance.filter(
                doctor => doctor.doctor_specialty === currentSpecialty
            );
            const maxSpecialtyDoctors = specialtyDoctors.length;
            const totalDoctors = analyticsData.doctor_performance.length;
            const specialtyProportion = specialtyDoctors.length / totalDoctors;
            
            doctorData = filteredStates.map(state => 
                Math.min(maxSpecialtyDoctors, Math.round(state.busy_doctors * specialtyProportion))
            );
        }
        charts.doctors.data.datasets[0].data = doctorData;
        charts.doctors.update();
    }
    
    console.log('Charts updated with', filteredStates.length, 'data points');
}

function getFilteredData(data, timeRange) {
    if (!data || timeRange === 'all') {
        return data;
    }
    
    console.log('Filtering data with time range:', timeRange);
    
    // Get the maximum sim_minutes in the data
    const maxMinutes = Math.max(...data.map(item => item.sim_minutes || 0));
    let cutoffMinutes;
    
    switch (timeRange) {
        case '24h':
            cutoffMinutes = maxMinutes - (24 * 60); // Last 24 hours
            break;
        case '7d':
            cutoffMinutes = maxMinutes - (7 * 24 * 60); // Last 7 days
            break;
        case '30d':
            cutoffMinutes = maxMinutes - (30 * 24 * 60); // Last 30 days
            break;
        default:
            return data;
    }
    
    const filtered = data.filter(item => (item.sim_minutes || 0) >= Math.max(0, cutoffMinutes));
    console.log('Filtered from', data.length, 'to', filtered.length, 'data points');
    return filtered;
}

function aggregateData(data, granularity) {
    if (!data || data.length === 0) {
        return data;
    }
    
    // For minute granularity, return data as-is but potentially sampled for performance
    if (granularity === 'minute') {
        console.log('Using minute granularity - returning original data');
        // More aggressive sampling for better performance
        if (data.length > 3000) {
            const sampleRate = Math.ceil(data.length / 1000);
            console.log(`Large dataset: Sampling every ${sampleRate} points for performance (${data.length} -> ~${Math.ceil(data.length / sampleRate)} points)`);
            return data.filter((_, index) => index % sampleRate === 0);
        } else if (data.length > 1500) {
            const sampleRate = Math.ceil(data.length / 800);
            console.log(`Medium dataset: Light sampling every ${sampleRate} points for performance (${data.length} -> ~${Math.ceil(data.length / sampleRate)} points)`);
            return data.filter((_, index) => index % sampleRate === 0);
        }
        return data;
    }
    
    console.log('Aggregating data by:', granularity);
    
    const aggregated = {};
    let stepSize;
    
    switch (granularity) {
        case 'hour':
            stepSize = 60; // 60 minutes
            break;
        case 'day':
            stepSize = 1440; // 24 hours * 60 minutes
            break;
        default:
            console.log('Unknown granularity, returning original data');
            return data;
    }
    
    data.forEach(item => {
        const timeSlot = Math.floor((item.sim_minutes || 0) / stepSize) * stepSize;
        
        if (!aggregated[timeSlot]) {
            aggregated[timeSlot] = {
                sim_minutes: timeSlot,
                patients_total: [],
                patients_treated: [],
                busy_doctors: [],
                waiting_patients: []
            };
        }
        
        aggregated[timeSlot].patients_total.push(item.patients_total || 0);
        aggregated[timeSlot].patients_treated.push(item.patients_treated || 0);
        aggregated[timeSlot].busy_doctors.push(item.busy_doctors || 0);
        aggregated[timeSlot].waiting_patients.push(item.waiting_patients || 0);
    });
    
    // Convert to array and calculate averages (and max for busy_doctors)
    const result = Object.values(aggregated).map(item => ({
        sim_minutes: item.sim_minutes,
        patients_total: Math.round(item.patients_total.reduce((a, b) => a + b, 0) / item.patients_total.length),
        patients_treated: Math.round(item.patients_treated.reduce((a, b) => a + b, 0) / item.patients_treated.length),
        busy_doctors: Math.max(...item.busy_doctors), // Use max instead of average for busy doctors
        waiting_patients: Math.round(item.waiting_patients.reduce((a, b) => a + b, 0) / item.waiting_patients.length)
    })).sort((a, b) => a.sim_minutes - b.sim_minutes);
    
    console.log('Aggregated to', result.length, 'data points');
    return result;
}

function createCharts() {
    // Apply initial filtering and aggregation to avoid lag on first load
    const timeRange = document.getElementById('timeRangeSelect')?.value || 'all';
    const granularity = document.getElementById('granularitySelect')?.value || 'hour';
    
    // Filter and aggregate data for initial chart creation
    let initialData = getFilteredData(analyticsData.hospital_states, timeRange);
    initialData = aggregateData(initialData, granularity);
    
    console.log('Creating charts with', initialData.length, 'data points (aggregated from', analyticsData.hospital_states.length, 'original points)');
    
    createPatientsChart(initialData);
    createDoctorsChart(initialData);
    createHourlyChart();
    createDiseaseChart();
    createDailyChart();
    populateSpecialtyDropdown();
}

function createPatientsChart(processedData = null) {
    const ctx = document.getElementById('patientsChart').getContext('2d');
    
    // Use processed data if provided, otherwise fall back to raw data
    const dataToUse = processedData || analyticsData.hospital_states;
    
    const data = {
        labels: dataToUse.map(state => formatTimeLabel(state.sim_minutes)),
        datasets: [
            {
                label: 'Total Patients',
                data: dataToUse.map(state => state.patients_total),
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1
            },
            {
                label: 'Patients Treated',
                data: dataToUse.map(state => state.patients_treated),
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                tension: 0.1
            },
            {
                label: 'Waiting Patients',
                data: dataToUse.map(state => state.waiting_patients),
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                tension: 0.1
            }
        ]
    };
    
    charts.patients = new Chart(ctx, {
        type: 'line',
        data: data,
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
                },
                x: {
                    title: {
                        display: true,
                        text: 'Simulation Time'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Patient Flow Over Time'
                }
            }
        }
    });
}

function createDoctorsChart(processedData = null) {
    const ctx = document.getElementById('doctorsChart').getContext('2d');
    
    // Use processed data if provided, otherwise fall back to raw data
    const dataToUse = processedData || analyticsData.hospital_states;
    
    const data = {
        labels: dataToUse.map(state => formatTimeLabel(state.sim_minutes)),
        datasets: [{
            label: 'Peak Busy Doctors',
            data: dataToUse.map(state => state.busy_doctors), // Use the processed data directly
            borderColor: 'rgb(255, 159, 64)',
            backgroundColor: 'rgba(255, 159, 64, 0.2)',
            tension: 0.1,
            fill: true
        }]
    };
    
    charts.doctors = new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Doctors'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Simulation Time'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Peak Doctor Utilization Over Time - All Specialties'
                }
            }
        }
    });
}

function createHourlyChart() {
    const ctx = document.getElementById('hourlyChart').getContext('2d');
    
    const data = {
        labels: analyticsData.hourly_treatments.map(item => `${item.hour}:00`),
        datasets: [
            {
                label: 'Patients Treated',
                data: analyticsData.hourly_treatments.map(item => item.count),
                backgroundColor: 'rgba(54, 162, 235, 0.8)',
                yAxisID: 'y'
            },
            {
                label: 'Avg Wait Time (min)',
                data: analyticsData.hourly_treatments.map(item => item.avg_wait_time),
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                type: 'line',
                yAxisID: 'y1'
            }
        ]
    };
    
    charts.hourly = new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Number of Patients'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Wait Time (minutes)'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Hourly Treatment Patterns'
                }
            }
        }
    });
}

function createDiseaseChart() {
    const ctx = document.getElementById('diseaseChart').getContext('2d');
    
    const colors = [
        'rgba(255, 99, 132, 0.8)',
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 205, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)',
        'rgba(199, 199, 199, 0.8)',
        'rgba(83, 102, 255, 0.8)'
    ];
    
    const data = {
        labels: analyticsData.disease_distribution.map(item => item.disease),
        datasets: [{
            data: analyticsData.disease_distribution.map(item => item.count),
            backgroundColor: colors.slice(0, analyticsData.disease_distribution.length),
            borderWidth: 2,
            borderColor: '#fff'
        }]
    };
    
    charts.disease = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                title: {
                    display: true,
                    text: 'Disease Distribution'
                }
            }
        }
    });
}

function createDailyChart() {
    const ctx = document.getElementById('dailyChart').getContext('2d');
    
    const data = {
        labels: analyticsData.daily_patterns.map(item => item.date),
        datasets: [
            {
                label: 'Patients per Day',
                data: analyticsData.daily_patterns.map(item => item.patients),
                backgroundColor: 'rgba(75, 192, 192, 0.8)',
                yAxisID: 'y'
            },
            {
                label: 'Avg Wait Time (min)',
                data: analyticsData.daily_patterns.map(item => item.avg_wait_time),
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                type: 'line',
                yAxisID: 'y1'
            }
        ]
    };
    
    charts.daily = new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Number of Patients'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Wait Time (minutes)'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Daily Performance Metrics'
                }
            }
        }
    });
}

function populateDoctorPerformance() {
    const tbody = document.getElementById('doctorPerformanceBody');
    tbody.innerHTML = '';
    
    analyticsData.doctor_performance.forEach(doctor => {
        const efficiency = calculateEfficiencyScore(doctor);
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>Doctor ${doctor.doctor_id}</td>
            <td>${doctor.doctor_specialty}</td>
            <td>${doctor.patients_treated}</td>
            <td>${doctor.avg_treatment_time.toFixed(1)} min</td>
            <td>${doctor.avg_wait_time.toFixed(1)} min</td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="progress flex-grow-1 me-2" style="height: 20px;">
                        <div class="progress-bar ${getEfficiencyColor(efficiency)}" 
                             style="width: ${efficiency}%">${efficiency.toFixed(0)}%</div>
                    </div>
                </div>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function populateSpecialtyDropdown() {
    if (!analyticsData || !analyticsData.doctor_performance) return;
    
    const specialties = [...new Set(analyticsData.doctor_performance.map(doctor => doctor.doctor_specialty))];
    const specialtySelect = document.getElementById('specialtySelect');
    
    // Clear existing options except "All Specialties"
    specialtySelect.innerHTML = '<option value="all">All Specialties</option>';
    
    // Add each specialty
    specialties.forEach(specialty => {
        const option = document.createElement('option');
        option.value = specialty;
        option.textContent = specialty;
        specialtySelect.appendChild(option);
    });
    
    console.log('Available specialties:', specialties);
}

function calculateEfficiencyScore(doctor) {
    // Simple efficiency calculation - could be improved
    const avgTreatmentTime = doctor.avg_treatment_time;
    const avgWaitTime = doctor.avg_wait_time;
    const patientsHandled = doctor.patients_treated;
    
    // Lower treatment time and wait time = higher efficiency
    const timeScore = Math.max(0, 100 - (avgTreatmentTime + avgWaitTime) / 2);
    
    // More patients handled = higher efficiency (up to a point)
    const volumeScore = Math.min(100, patientsHandled * 2);
    
    return (timeScore + volumeScore) / 2;
}

function getEfficiencyColor(efficiency) {
    if (efficiency >= 80) return 'bg-success';
    if (efficiency >= 60) return 'bg-warning';
    return 'bg-danger';
}

function updateCharts() {
    // This function is now replaced by updateChartsWithFilters
    updateChartsWithFilters();
}

function updatePatientsChart() {
    const showTotal = document.getElementById('showTotal').checked;
    const showTreated = document.getElementById('showTreated').checked;
    const showWaiting = document.getElementById('showWaiting').checked;
    
    charts.patients.data.datasets[0].hidden = !showTotal;
    charts.patients.data.datasets[1].hidden = !showTreated;
    charts.patients.data.datasets[2].hidden = !showWaiting;
    
    charts.patients.update();
}

function formatTimeLabel(minutes) {
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    const mins = Math.floor(minutes % 60);
    
    // For minute-level granularity, show minutes when appropriate
    const granularity = document.getElementById('granularitySelect')?.value || 'hour';
    
    if (granularity === 'minute' && days === 0 && hours < 24) {
        // Show hours and minutes for minute-level data within first day
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    } else if (days > 0) {
        // Show days, hours and minutes for longer periods
        return `Day ${days}, ${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    } else {
        // Default format - hours and minutes
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    }
}

function showError(message) {
    console.error(message);
    alert(message);
}

function getSpecialtyFilteredDoctorData() {
    if (!analyticsData || currentSpecialty === 'all') {
        return analyticsData.hospital_states.map(state => state.busy_doctors);
    }
    
    // We need to calculate busy doctors by specialty from available data
    // Since we don't have specialty-specific busy doctor data in hospital_states,
    // we'll need to estimate based on doctor performance data
    const specialtyDoctors = analyticsData.doctor_performance.filter(
        doctor => doctor.doctor_specialty === currentSpecialty
    );
    
    if (specialtyDoctors.length === 0) {
        return analyticsData.hospital_states.map(() => 0);
    }
    
    // Calculate maximum possible doctors in this specialty
    const maxSpecialtyDoctors = specialtyDoctors.length;
    
    // Calculate proportion of doctors in this specialty
    const totalDoctors = analyticsData.doctor_performance.length;
    const specialtyProportion = specialtyDoctors.length / totalDoctors;
    
    // Estimate busy doctors for this specialty, ensuring we don't exceed the max
    return analyticsData.hospital_states.map(state => 
        Math.min(maxSpecialtyDoctors, Math.round(state.busy_doctors * specialtyProportion))
    );
}

function updateDoctorsChart() {
    if (!charts.doctors || !analyticsData) return;
    
    const timeRange = document.getElementById('timeRangeSelect').value;
    const granularity = document.getElementById('granularitySelect').value;
    
    // Filter and aggregate data
    let filteredStates = getFilteredData(analyticsData.hospital_states, timeRange);
    filteredStates = aggregateData(filteredStates, granularity);
    
    // Update chart data
    const labels = filteredStates.map(state => formatTimeLabel(state.sim_minutes));
    charts.doctors.data.labels = labels;
    
    // Apply specialty filter to doctor data
    let doctorData;
    if (currentSpecialty === 'all') {
        doctorData = filteredStates.map(state => state.busy_doctors);
    } else {
        // Calculate specialty-specific data for filtered timeframe
        const specialtyDoctors = analyticsData.doctor_performance.filter(
            doctor => doctor.doctor_specialty === currentSpecialty
        );
        const maxSpecialtyDoctors = specialtyDoctors.length;
        const totalDoctors = analyticsData.doctor_performance.length;
        const specialtyProportion = specialtyDoctors.length / totalDoctors;
        
        doctorData = filteredStates.map(state => 
            Math.min(maxSpecialtyDoctors, Math.round(state.busy_doctors * specialtyProportion))
        );
    }
    
    charts.doctors.data.datasets[0].data = doctorData;
    
    // Update chart title and label
    const specialtyLabel = currentSpecialty === 'all' ? 'All Specialties' : currentSpecialty;
    charts.doctors.options.plugins.title.text = `Peak Doctor Utilization Over Time - ${specialtyLabel}`;
    charts.doctors.data.datasets[0].label = currentSpecialty === 'all' ? 'Peak Busy Doctors' : `Peak Busy ${currentSpecialty} Doctors`;
    
    charts.doctors.update();
    
    console.log(`Updated doctors chart for specialty: ${currentSpecialty}`);
}