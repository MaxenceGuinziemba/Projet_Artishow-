// Real-time simulation playback JavaScript
let realtimeData = null;
let currentSimId = null;
let playbackState = {
    isPlaying: false,
    currentTime: 0,
    maxTime: 0,
    speed: 'normal',
    intervalId: null
};

let liveChart = null;
let currentDiseasesChart = null;
let previousState = null;
let chartTimeScale = '1w'; // Default to 1 week (7 days)

document.addEventListener('DOMContentLoaded', function() {
    // Extract sim_id from URL
    const pathParts = window.location.pathname.split('/');
    currentSimId = parseInt(pathParts[pathParts.length - 1]);
    
    if (currentSimId) {
        initializeRealtime();
    }
});

async function initializeRealtime() {
    try {
        // Get simulation time range
        const response = await fetch(`/api/simulation/${currentSimId}/timerange`);
        const result = await response.json();
        
        if (result.success) {
            const timeRange = result.data;
            playbackState.maxTime = timeRange.max_time;
            playbackState.currentTime = timeRange.min_time;
            
            setupControls();
            setupCharts();
            await loadCurrentData();
        } else {
            showError('Failed to get simulation time range: ' + result.error);
        }
    } catch (error) {
        showError('Error initializing real-time view: ' + error.message);
    }
}

function setupControls() {
    const slider = document.getElementById('timeSlider');
    slider.min = playbackState.currentTime;
    slider.max = playbackState.maxTime;
    slider.value = playbackState.currentTime;
    
    // Control event listeners
    document.getElementById('playBtn').addEventListener('click', startPlayback);
    document.getElementById('pauseBtn').addEventListener('click', pausePlayback);
    document.getElementById('stopBtn').addEventListener('click', stopPlayback);
    document.getElementById('speedSelect').addEventListener('change', changeSpeed);
    document.getElementById('timeSlider').addEventListener('input', seekToTime);
    
    // Chart visibility toggles
    document.getElementById('showCurrentPatients').addEventListener('change', updateChartVisibility);
    document.getElementById('showWaitingPatients').addEventListener('change', updateChartVisibility);
    document.getElementById('showBusyDoctors').addEventListener('change', updateChartVisibility);
    
    // Add time scale selector event listener
    const timeScaleSelect = document.getElementById('timeScaleSelect');
    if (timeScaleSelect) {
        timeScaleSelect.addEventListener('change', changeTimeScale);
    }
    
    updateTimeDisplay();
}

function setupCharts() {
    // Live activity chart
    const liveCtx = document.getElementById('liveChart').getContext('2d');
    liveChart = new Chart(liveCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Current Patients in Hospital',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                },
                {
                    label: 'Waiting Patients',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1
                },
                {
                    label: 'Busy Doctors',
                    data: [],
                    borderColor: 'rgb(255, 159, 64)',
                    backgroundColor: 'rgba(255, 159, 64, 0.2)',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Live Hospital Activity (Last Week)'
                }
            }
        }
    });
    
    // Current diseases chart
    const diseasesCtx = document.getElementById('currentDiseasesChart').getContext('2d');
    currentDiseasesChart = new Chart(diseasesCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 205, 86, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(153, 102, 255, 0.8)',
                    'rgba(255, 159, 64, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Current Disease Types'
                }
            }
        }
    });
}

async function loadCurrentData() {
    try {
        // Get window size based on chart time scale
        const windowSize = getTimeScaleMinutes(chartTimeScale);
        const startTime = Math.max(playbackState.currentTime - windowSize, 0);
        const endTime = playbackState.currentTime;
        
        const response = await fetch(`/api/simulation/${currentSimId}/realtime?start_time=${startTime}&end_time=${endTime}`);
        const result = await response.json();
        
        if (result.success) {
            realtimeData = result.data;
            updateDisplay();
        } else {
            showError('Failed to load real-time data: ' + result.error);
        }
    } catch (error) {
        showError('Error loading real-time data: ' + error.message);
    }
}

function updateDisplay() {
    updateStatCards();
    updateLiveChart();
    updateCurrentDiseasesChart();
    updateRecentEvents();
    updateDoctorStatus();
    updateActiveAlerts();
    updateTimeDisplay();
}

function updateStatCards() {
    if (!realtimeData.hospital_states.length) return;
    
    // Get current state (latest in the time window)
    const currentState = realtimeData.hospital_states[realtimeData.hospital_states.length - 1];
    
    // Calculate current patients in hospital (waiting + being treated)
    const currentInHospital = (currentState.waiting_patients || 0) + (currentState.busy_doctors || 0);
    const waitingPatients = currentState.waiting_patients || 0;
    const busyDoctors = currentState.busy_doctors || 0;
    const treatedTotal = currentState.patients_treated || 0;
    
    // Calculate changes from previous state
    let changes = { patients: 0, doctors: 0, waiting: 0, treated: 0 };
    if (previousState) {
        const prevInHospital = (previousState.waiting_patients || 0) + (previousState.busy_doctors || 0);
        changes.patients = currentInHospital - prevInHospital;
        changes.doctors = busyDoctors - (previousState.busy_doctors || 0);
        changes.waiting = waitingPatients - (previousState.waiting_patients || 0);
        changes.treated = treatedTotal - (previousState.patients_treated || 0);
    }
    
    // Update displays - current patients shows patients currently in hospital
    document.getElementById('currentPatients').textContent = currentInHospital;
    document.getElementById('busyDoctors').textContent = busyDoctors;
    document.getElementById('waitingPatients').textContent = waitingPatients;
    document.getElementById('treatedPatients').textContent = treatedTotal;
    
    // Update change indicators
    updateChangeIndicator('patientsChange', changes.patients);
    updateChangeIndicator('doctorsChange', changes.doctors);
    updateChangeIndicator('waitingChange', changes.waiting);
    updateChangeIndicator('treatedChange', changes.treated);
    
    previousState = {
        waiting_patients: waitingPatients,
        busy_doctors: busyDoctors,
        patients_treated: treatedTotal
    };
}

function updateChangeIndicator(elementId, change) {
    const element = document.getElementById(elementId);
    const changeClass = change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral';
    const changeSymbol = change > 0 ? '+' : '';
    
    element.textContent = `${changeSymbol}${change}`;
    element.className = `change ${changeClass}`;
}

function updateLiveChart() {
    // Adjust the number of points based on time scale for better visibility
    let maxPoints;
    switch (chartTimeScale) {
        case '30m': maxPoints = 30; break;
        case '2h': maxPoints = 60; break;
        case '1d': maxPoints = 144; break;  // Every 10 minutes for 24 hours
        case '1w': maxPoints = 168; break; // Every hour for 7 days
        default: maxPoints = 30;
    }
    
    const states = realtimeData.hospital_states.slice(-maxPoints);
    
    liveChart.data.labels = states.map(state => formatTimeLabel(state.sim_minutes));
    // Update the chart to show current patients in hospital (waiting + being treated)
    liveChart.data.datasets[0].data = states.map(state => 
        (state.waiting_patients || 0) + (state.busy_doctors || 0)
    );
    liveChart.data.datasets[1].data = states.map(state => state.waiting_patients);
    liveChart.data.datasets[2].data = states.map(state => state.busy_doctors);
    
    liveChart.update('none'); // No animation for real-time updates
}

function updateCurrentDiseasesChart() {
    // Count diseases in recent treatments (last hour)
    const recentTreatments = realtimeData.patient_treatments.filter(treatment => 
        treatment.sim_minutes >= playbackState.currentTime - 60
    );
    
    const diseaseCounts = {};
    recentTreatments.forEach(treatment => {
        diseaseCounts[treatment.disease] = (diseaseCounts[treatment.disease] || 0) + 1;
    });
    
    const sortedDiseases = Object.entries(diseaseCounts)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 6); // Top 6 diseases
    
    currentDiseasesChart.data.labels = sortedDiseases.map(([disease]) => disease);
    currentDiseasesChart.data.datasets[0].data = sortedDiseases.map(([,count]) => count);
    
    currentDiseasesChart.update('none');
}

function updateRecentEvents() {
    const container = document.getElementById('recentEvents');
    container.innerHTML = '';
    
    // Get recent events (last 30 minutes)
    const recentEvents = realtimeData.detailed_events
        .filter(event => event.sim_minutes >= playbackState.currentTime - 30)
        .sort((a, b) => b.sim_minutes - a.sim_minutes)
        .slice(0, 10);
    
    recentEvents.forEach(event => {
        const eventEl = document.createElement('div');
        eventEl.className = `event-item ${getEventClass(event.event_type)}`;
        
        eventEl.innerHTML = `
            <div class="event-time">${formatTimeLabel(event.sim_minutes)}</div>
            <div class="event-description">${formatEventDescription(event)}</div>
        `;
        
        container.appendChild(eventEl);
    });
    
    if (recentEvents.length === 0) {
        container.innerHTML = '<p class="text-muted">No recent events</p>';
    }
}

function updateDoctorStatus() {
    const container = document.getElementById('doctorStatus');
    container.innerHTML = '';
    
    // Use doctors data from API if available, otherwise derive from treatments
    let doctors = [];
    
    if (realtimeData.doctors && realtimeData.doctors.length > 0) {
        // Use the doctor data with specialties from the API
        doctors = realtimeData.doctors;
    } else {
        // Fallback: get doctor info from patient treatments
        const doctorMap = new Map();
        const totalDoctors = realtimeData.total_doctors || 25;
        
        // Initialize all doctors as available
        for (let i = 1; i <= totalDoctors; i++) {
            doctorMap.set(i, { 
                id: i, 
                specialty: 'generalist', // Default specialty
                status: 'available', 
                last_activity: null 
            });
        }
        
        // Update with actual specialties from treatments
        realtimeData.patient_treatments
            .filter(treatment => treatment.sim_minutes <= playbackState.currentTime)
            .forEach(treatment => {
                if (treatment.doctor_id && doctorMap.has(treatment.doctor_id)) {
                    const doctor = doctorMap.get(treatment.doctor_id);
                    doctor.specialty = treatment.doctor_specialty || 'generalist';
                    doctor.last_activity = treatment.sim_minutes;
                    
                    // Check if doctor is currently busy
                    const timeSinceLastActivity = playbackState.currentTime - treatment.sim_minutes;
                    if (timeSinceLastActivity < 30) { // Last 30 minutes
                        doctor.status = 'busy';
                        doctor.current_patient = treatment.patient_id;
                    }
                }
            });
        
        doctors = Array.from(doctorMap.values());
    }
    
    // Sort doctors by ID for consistent display
    doctors.sort((a, b) => a.id - b.id);
    
    // Display doctor cards with actual specialties
    doctors.forEach(doctor => {
        const doctorEl = document.createElement('div');
        doctorEl.className = `doctor-card ${doctor.status}`;
        
        const specialtyDisplay = formatSpecialty(doctor.specialty);
        
        doctorEl.innerHTML = `
            <div class="doctor-info">
                <h6>Dr. ${doctor.id}</h6>
                <small>${specialtyDisplay}</small>
            </div>
            <div class="doctor-status ${doctor.status}">
                ${doctor.status === 'busy' ? 
                    `Treating ${doctor.current_patient || 'Patient'}` : 
                    'Available'}
            </div>
        `;
        
        container.appendChild(doctorEl);
    });
}

function formatSpecialty(specialty) {
    // Format specialty names to be more readable
    const specialtyMap = {
        'generalist': 'General',
        'emergency': 'Emergency',
        'cardiologist': 'Cardiology',
        'neurologist': 'Neurology', 
        'gynecologist': 'Gynecology',
        'pulmonologist': 'Pulmonology'
    };
    
    return specialtyMap[specialty] || specialty.charAt(0).toUpperCase() + specialty.slice(1);
}

function updateActiveAlerts() {
    const alertsRow = document.getElementById('alertsRow');
    const alertsContainer = document.getElementById('activeAlerts');
    
    const alerts = [];
    const totalDoctors = realtimeData.total_doctors || 25;
    
    // Check for current alerts
    if (realtimeData.hospital_states.length > 0) {
        const currentState = realtimeData.hospital_states[realtimeData.hospital_states.length - 1];
        
        if (currentState.waiting_patients > 15) {
            alerts.push({
                type: 'High Wait Queue',
                message: `${currentState.waiting_patients} patients waiting for treatment`,
                severity: 'warning'
            });
        }
        
        // Use dynamic doctor count for utilization alert
        const utilizationThreshold = Math.floor(totalDoctors * 0.85); // 85% utilization
        if (currentState.busy_doctors > utilizationThreshold) {
            alerts.push({
                type: 'High Doctor Utilization',
                message: `${currentState.busy_doctors} out of ${totalDoctors} doctors are busy`,
                severity: 'danger'
            });
        }
    }
    
    if (alerts.length > 0) {
        alertsContainer.innerHTML = '';
        alerts.forEach(alert => {
            const alertEl = document.createElement('div');
            alertEl.className = 'alert-item';
            alertEl.innerHTML = `
                <h6><i class="fas fa-exclamation-triangle"></i> ${alert.type}</h6>
                <p>${alert.message}</p>
            `;
            alertsContainer.appendChild(alertEl);
        });
        alertsRow.style.display = 'block';
    } else {
        alertsRow.style.display = 'none';
    }
}

function updateTimeDisplay() {
    const slider = document.getElementById('timeSlider');
    slider.value = playbackState.currentTime;
    
    document.getElementById('currentTime').textContent = formatTimeLabel(playbackState.currentTime);
    
    // Calculate simulation date
    const startDate = new Date('2024-01-01'); // Assuming simulation starts on this date
    const simDate = new Date(startDate.getTime() + playbackState.currentTime * 60 * 1000);
    document.getElementById('simulationDate').textContent = simDate.toLocaleDateString();
}

// Playback control functions
function startPlayback() {
    if (playbackState.isPlaying) return;
    
    playbackState.isPlaying = true;
    document.getElementById('playBtn').style.display = 'none';
    document.getElementById('pauseBtn').style.display = 'inline-block';
    
    const speed = getSpeedMultiplier();
    // For realtime, update every minute (60000ms), otherwise every second (1000ms)
    const updateInterval = playbackState.speed === 'realtime' ? 60000 : 1000;
    
    playbackState.intervalId = setInterval(async () => {
        playbackState.currentTime += speed;
        
        if (playbackState.currentTime >= playbackState.maxTime) {
            stopPlayback();
            return;
        }
        
        await loadCurrentData();
    }, updateInterval);
}

function pausePlayback() {
    playbackState.isPlaying = false;
    document.getElementById('playBtn').style.display = 'inline-block';
    document.getElementById('pauseBtn').style.display = 'none';
    
    if (playbackState.intervalId) {
        clearInterval(playbackState.intervalId);
        playbackState.intervalId = null;
    }
}

function stopPlayback() {
    pausePlayback();
    playbackState.currentTime = 0;
    loadCurrentData();
}

function changeSpeed() {
    playbackState.speed = document.getElementById('speedSelect').value;
    
    if (playbackState.isPlaying) {
        pausePlayback();
        startPlayback();
    }
}

function seekToTime() {
    const slider = document.getElementById('timeSlider');
    playbackState.currentTime = parseFloat(slider.value);
    loadCurrentData();
}

function getSpeedMultiplier() {
    switch (playbackState.speed) {
        case 'realtime': return 1; // 1 minute per minute (real time) - updates every 60 seconds
        case 'normal': return 1; // 1 minute per second - advances 1 sim minutes per second
        case 'fast': return 60; // 1 hour per second - advances 60 sim minutes per second
        case 'very-fast': return 720; // 12 hours per second - advances 720 sim minutes per second
        case 'day': return 1440; // 1 day per second - advances 1440 sim minutes per second
        default: return 60;
    }
}

// Time scale management functions
function changeTimeScale() {
    const timeScaleSelect = document.getElementById('timeScaleSelect');
    chartTimeScale = timeScaleSelect.value;
    
    // Update chart title
    updateChartTitle();
    
    // Reload data with new time scale
    loadCurrentData();
}

function getTimeScaleMinutes(scale) {
    switch (scale) {
        case '30m': return 30;
        case '2h': return 120;
        case '1d': return 1440;
        case '1w': return 10080;
        default: return 120;
    }
}

function getTimeScaleLabel(scale) {
    switch (scale) {
        case '30m': return 'Last 30 Minutes';
        case '2h': return 'Last 2 Hours';
        case '1d': return 'Last Day';
        case '1w': return 'Last Week';
        default: return 'Last 2 Hours';
    }
}

function updateChartTitle() {
    if (liveChart) {
        liveChart.options.plugins.title.text = `Live Hospital Activity (${getTimeScaleLabel(chartTimeScale)})`;
        liveChart.update();
    }
}

// Utility functions
function getEventClass(eventType) {
    switch (eventType) {
        case 'patient_arrival': return 'patient-arrival';
        case 'treatment_start': return 'patient-treatment';
        case 'treatment_end': return 'patient-discharge';
        default: return '';
    }
}

function formatEventDescription(event) {
    switch (event.event_type) {
        case 'patient_arrival':
            return `Patient ${event.patient_id} arrived with ${event.disease}`;
        case 'treatment_start':
            return `Dr. ${event.doctor_id} started treating Patient ${event.patient_id}`;
        case 'treatment_end':
            return `Patient ${event.patient_id} treatment completed`;
        default:
            return `${event.event_type}: ${event.description || 'No description'}`;
    }
}

function formatTimeLabel(minutes) {
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    const mins = Math.floor(minutes % 60);
    
    if (days > 0) {
        return `Day ${days + 1}, ${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    } else {
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    }
}

function showError(message) {
    console.error(message);
    alert(message);
}

function updateChartVisibility() {
    if (!liveChart) return;
    
    const showCurrentPatients = document.getElementById('showCurrentPatients').checked;
    const showWaitingPatients = document.getElementById('showWaitingPatients').checked;
    const showBusyDoctors = document.getElementById('showBusyDoctors').checked;
    
    // Update dataset visibility
    liveChart.data.datasets[0].hidden = !showCurrentPatients;
    liveChart.data.datasets[1].hidden = !showWaitingPatients;
    liveChart.data.datasets[2].hidden = !showBusyDoctors;
    
    liveChart.update();
}