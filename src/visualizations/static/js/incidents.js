// Incidents page JavaScript
let incidentsData = null;
let currentSimId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Extract sim_id from URL
    const pathParts = window.location.pathname.split('/');
    currentSimId = parseInt(pathParts[pathParts.length - 1]);
    
    if (currentSimId) {
        loadIncidentsData();
    }
});

async function loadIncidentsData() {
    try {
        const response = await fetch(`/api/simulation/${currentSimId}/incidents`);
        const result = await response.json();
        
        if (result.success) {
            incidentsData = result.data;
            
            // Process incidents to group consecutive periods
            incidentsData.high_wait_incidents = groupConsecutiveIncidents(incidentsData.high_wait_incidents, 'waiting');
            incidentsData.high_occupancy_incidents = groupConsecutiveIncidents(incidentsData.high_occupancy_incidents, 'occupancy');
            
            displayIncidentsSummary();
            displayHighWaitIncidents();
            displayHighOccupancyIncidents();
            displayEventsTimeline();
            displayLongWaitPatients();
            createIncidentsCharts();
        } else {
            showError('Failed to load incidents data: ' + result.error);
        }
    } catch (error) {
        showError('Error loading incidents data: ' + error.message);
    }
}

function displayIncidentsSummary() {
    const stats = incidentsData.statistics;
    
    // Update to show grouped incident counts instead of individual time points
    document.getElementById('highWaitCount').textContent = incidentsData.high_wait_incidents.length;
    document.getElementById('highOccupancyCount').textContent = incidentsData.high_occupancy_incidents.length;
    document.getElementById('maxWaitingPatients').textContent = stats.max_waiting_patients;
    document.getElementById('activeEventsCount').textContent = incidentsData.active_events.length;
}

function displayHighWaitIncidents() {
    const container = document.getElementById('highWaitIncidents');
    container.innerHTML = '';
    
    if (incidentsData.high_wait_incidents.length === 0) {
        container.innerHTML = '<p class="text-muted">No high wait time incidents found.</p>';
        return;
    }
    
    // Sort incidents by start time (most recent first)
    const sortedWaitIncidents = [...incidentsData.high_wait_incidents].sort((a, b) => b.start_sim_minutes - a.start_sim_minutes);
    
    sortedWaitIncidents.forEach(incident => {
        const incidentEl = document.createElement('div');
        
        const severity = getSeverity(incident.max_waiting_patients, 'waiting');
        incidentEl.className = `incident-item ${severity}-severity`;
        
        const startTime = formatSimulationTime(incident.start_sim_minutes);
        const endTime = formatSimulationTime(incident.end_sim_minutes);
        const duration = incident.duration_minutes;
        
        incidentEl.innerHTML = `
            <div class="incident-header">
                <div class="incident-time">
                    ${startTime} - ${endTime}
                    <small class="text-muted d-block">Duration: ${formatDuration(duration)}</small>
                </div>
                <span class="incident-badge ${severity}">${severity.toUpperCase()}</span>
            </div>
            <h6><i class="fas fa-clock text-warning"></i> High Patient Wait Time Period</h6>
            <p><strong>Peak:</strong> ${incident.max_waiting_patients} patients waiting</p>
            <p><strong>Average:</strong> ${incident.avg_waiting_patients.toFixed(1)} patients waiting</p>
            <small class="text-muted">
                Max busy doctors: ${incident.max_busy_doctors} | 
                Patients affected: ${incident.total_patients_affected}
            </small>
        `;
        
        container.appendChild(incidentEl);
    });
}

function displayHighOccupancyIncidents() {
    const container = document.getElementById('highOccupancyIncidents');
    container.innerHTML = '';
    
    if (incidentsData.high_occupancy_incidents.length === 0) {
        container.innerHTML = '<p class="text-muted">No high occupancy incidents found.</p>';
        return;
    }
    
    // Sort incidents by start time (most recent first)
    const sortedOccupancyIncidents = [...incidentsData.high_occupancy_incidents].sort((a, b) => b.start_sim_minutes - a.start_sim_minutes);
    
    sortedOccupancyIncidents.forEach(incident => {
        const incidentEl = document.createElement('div');
        const maxOccupancyRate = (incident.max_occupancy_rate * 100).toFixed(1);
        const avgOccupancyRate = (incident.avg_occupancy_rate * 100).toFixed(1);
        const severity = getSeverity(incident.max_occupancy_rate, 'occupancy');
        
        incidentEl.className = `incident-item ${severity}-severity`;
        
        const startTime = formatSimulationTime(incident.start_sim_minutes);
        const endTime = formatSimulationTime(incident.end_sim_minutes);
        const duration = incident.duration_minutes;
        
        incidentEl.innerHTML = `
            <div class="incident-header">
                <div class="incident-time">
                    ${startTime} - ${endTime}
                    <small class="text-muted d-block">Duration: ${formatDuration(duration)}</small>
                </div>
                <span class="incident-badge ${severity}">${severity.toUpperCase()}</span>
            </div>
            <h6><i class="fas fa-users text-danger"></i> High Doctor Occupancy Period</h6>
            <p><strong>Peak:</strong> ${maxOccupancyRate}% occupancy</p>
            <p><strong>Average:</strong> ${avgOccupancyRate}% occupancy</p>
            <small class="text-muted">
                Max busy doctors: ${incident.max_busy_doctors} | 
                Patients affected: ${incident.total_patients_affected}
            </small>
        `;
        
        container.appendChild(incidentEl);
    });
}

function displayEventsTimeline() {
    const container = document.getElementById('eventsTimeline');
    container.innerHTML = '';
    
    if (incidentsData.active_events.length === 0) {
        container.innerHTML = '<p class="text-muted">No simulation events found.</p>';
        return;
    }
    
    incidentsData.active_events.forEach(event => {
        const eventEl = document.createElement('div');
        eventEl.className = 'incident-item low-severity';
        
        const duration = (event.end_sim_minutes - event.start_sim_minutes) / 60; // Convert to hours
        const params = JSON.parse(event.params || '{}');
        
        eventEl.innerHTML = `
            <div class="incident-header">
                <div class="incident-time">
                    ${formatSimulationTime(event.start_sim_minutes)} - 
                    ${formatSimulationTime(event.end_sim_minutes)}
                </div>
                <span class="incident-badge low">${event.event_type.toUpperCase()}</span>
            </div>
            <h6><i class="fas fa-bolt text-info"></i> ${capitalizeFirst(event.event_type)} Event</h6>
            <p>Duration: <strong>${duration.toFixed(1)} hours</strong></p>
            <small class="text-muted">${formatEventParams(params)}</small>
        `;
        
        container.appendChild(eventEl);
    });
}

function displayLongWaitPatients() {
    const tbody = document.getElementById('longWaitPatientsBody');
    tbody.innerHTML = '';
    
    // Group patients by patient_id and keep only the longest wait time for each patient
    const patientMap = new Map();
    
    incidentsData.long_wait_patients.forEach(patient => {
        const patientId = patient.patient_id;
        
        if (!patientMap.has(patientId) || patient.wait_time > patientMap.get(patientId).wait_time) {
            patientMap.set(patientId, patient);
        }
    });
    
    // Convert map to array and sort by wait time (longest first)
    const uniquePatients = Array.from(patientMap.values())
        .sort((a, b) => b.wait_time - a.wait_time);
    
    uniquePatients.forEach(patient => {
        const row = document.createElement('tr');
        const severity = getWaitTimeSeverity(patient.wait_time);
        
        row.innerHTML = `
            <td>Patient ${patient.patient_id}</td>
            <td>${patient.disease}</td>
            <td>
                <span class="badge ${severity === 'high' ? 'bg-danger' : severity === 'medium' ? 'bg-warning' : 'bg-primary'}">
                    ${patient.wait_time.toFixed(1)} min
                </span>
            </td>
            <td>${patient.start_treatment}</td>
            <td>${patient.doctor_specialty}</td>
            <td>
                <span class="badge ${severity === 'high' ? 'bg-danger' : severity === 'medium' ? 'bg-warning text-dark' : 'bg-success'}">
                    ${severity.toUpperCase()}
                </span>
            </td>
        `;
        
        tbody.appendChild(row);
    });
    
    console.log(`Displaying ${uniquePatients.length} unique patients (from ${incidentsData.long_wait_patients.length} total entries)`);
}

function createIncidentsCharts() {
    createIncidentsByHourChart();
    createIncidentTypesChart();
}

function createIncidentsByHourChart() {
    const ctx = document.getElementById('incidentsByHourChart').getContext('2d');
    
    // Process incidents by hour
    const hourlyIncidents = {};
    for (let i = 0; i < 24; i++) {
        hourlyIncidents[i] = { wait: 0, occupancy: 0 };
    }
    
    // For grouped incidents, we count each incident period once at its start hour
    incidentsData.high_wait_incidents.forEach(incident => {
        const hour = Math.floor((incident.start_sim_minutes % 1440) / 60);
        hourlyIncidents[hour].wait++;
    });
    
    incidentsData.high_occupancy_incidents.forEach(incident => {
        const hour = Math.floor((incident.start_sim_minutes % 1440) / 60);
        hourlyIncidents[hour].occupancy++;
    });
    
    const labels = Array.from({length: 24}, (_, i) => `${i}:00`);
    const waitData = labels.map((_, i) => hourlyIncidents[i].wait);
    const occupancyData = labels.map((_, i) => hourlyIncidents[i].occupancy);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'High Wait Periods',
                    data: waitData,
                    backgroundColor: 'rgba(255, 193, 7, 0.8)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 1
                },
                {
                    label: 'High Occupancy Periods',
                    data: occupancyData,
                    backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Incident Periods'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Hour of Day'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Incident Periods by Hour of Day'
                }
            }
        }
    });
}

function createIncidentTypesChart() {
    const ctx = document.getElementById('incidentTypesChart').getContext('2d');
    
    const incidentCounts = {
        'High Wait Time': incidentsData.high_wait_incidents.length,
        'High Occupancy': incidentsData.high_occupancy_incidents.length,
        'Long Patient Waits': incidentsData.long_wait_patients.length
    };
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(incidentCounts),
            datasets: [{
                data: Object.values(incidentCounts),
                backgroundColor: [
                    'rgba(255, 193, 7, 0.8)',
                    'rgba(220, 53, 69, 0.8)',
                    'rgba(255, 99, 132, 0.8)'
                ],
                borderColor: [
                    'rgba(255, 193, 7, 1)',
                    'rgba(220, 53, 69, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Incident Types Distribution'
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Verify both displays use formatDuration - this comment ensures the formatDuration function is applied to all duration displays
// in both displayHighWaitIncidents() and displayHighOccupancyIncidents() functions
/**
 * Group consecutive incidents into single incidents with duration
 */
function groupConsecutiveIncidents(incidents, type) {
    if (!incidents || incidents.length === 0) return [];
    
    // Sort incidents by simulation time
    const sortedIncidents = incidents.sort((a, b) => a.sim_minutes - b.sim_minutes);
    
    // First, let's analyze the time gaps to understand data granularity
    if (sortedIncidents.length > 1) {
        const timeGaps = [];
        for (let i = 1; i < Math.min(10, sortedIncidents.length); i++) {
            timeGaps.push(sortedIncidents[i].sim_minutes - sortedIncidents[i-1].sim_minutes);
        }
        console.log(`${type} incidents time gaps (first 10):`, timeGaps);
    }
    
    const groupedIncidents = [];
    let currentGroup = null;
    
    // Determine appropriate gap threshold based on data granularity
    // If data is recorded every minute, gap should be 1-2 minutes
    // If data is recorded every hour, gap should be 60-120 minutes
    const timeGap = sortedIncidents.length > 1 ? 
        sortedIncidents[1].sim_minutes - sortedIncidents[0].sim_minutes : 1;
    const gapThreshold = Math.max(timeGap, 2); // At least 2 minutes gap to separate incidents
    
    console.log(`Using gap threshold of ${gapThreshold} minutes for ${type} incidents`);
    
    for (let i = 0; i < sortedIncidents.length; i++) {
        const incident = sortedIncidents[i];
        
        // If this is the first incident or there's a significant gap in time
        if (!currentGroup || incident.sim_minutes - currentGroup.end_sim_minutes > gapThreshold) {
            // Finalize previous group if exists
            if (currentGroup) {
                groupedIncidents.push(currentGroup);
            }
            
            // Start new group
            currentGroup = {
                start_sim_minutes: incident.sim_minutes,
                end_sim_minutes: incident.sim_minutes,
                duration_minutes: timeGap, // Use actual data granularity
                max_waiting_patients: incident.waiting_patients,
                max_occupancy_rate: incident.occupancy_rate || 0,
                max_busy_doctors: incident.busy_doctors,
                avg_waiting_patients: incident.waiting_patients,
                avg_occupancy_rate: incident.occupancy_rate || 0,
                avg_busy_doctors: incident.busy_doctors,
                total_patients_affected: incident.patients_total,
                incident_count: 1,
                type: type
            };
        } else {
            // Extend current group
            currentGroup.end_sim_minutes = incident.sim_minutes;
            currentGroup.duration_minutes = currentGroup.end_sim_minutes - currentGroup.start_sim_minutes + timeGap;
            currentGroup.incident_count++;
            
            // Update maximums
            currentGroup.max_waiting_patients = Math.max(currentGroup.max_waiting_patients, incident.waiting_patients);
            currentGroup.max_occupancy_rate = Math.max(currentGroup.max_occupancy_rate, incident.occupancy_rate || 0);
            currentGroup.max_busy_doctors = Math.max(currentGroup.max_busy_doctors, incident.busy_doctors);
            
            // Update averages
            const count = currentGroup.incident_count;
            currentGroup.avg_waiting_patients = ((currentGroup.avg_waiting_patients * (count - 1)) + incident.waiting_patients) / count;
            currentGroup.avg_occupancy_rate = ((currentGroup.avg_occupancy_rate * (count - 1)) + (incident.occupancy_rate || 0)) / count;
            currentGroup.avg_busy_doctors = ((currentGroup.avg_busy_doctors * (count - 1)) + incident.busy_doctors) / count;
            currentGroup.total_patients_affected = Math.max(currentGroup.total_patients_affected, incident.patients_total);
        }
    }
    
    // Don't forget the last group
    if (currentGroup) {
        groupedIncidents.push(currentGroup);
    }
    
    console.log(`Grouped ${incidents.length} ${type} incidents into ${groupedIncidents.length} incident periods`);
    
    // Log duration distribution for analysis
    const durations = groupedIncidents.map(g => g.duration_minutes);
    const avgDuration = durations.reduce((a, b) => a + b, 0) / durations.length;
    const maxDuration = Math.max(...durations);
    console.log(`${type} incident durations - Average: ${avgDuration.toFixed(1)} min, Max: ${maxDuration} min`);
    
    return groupedIncidents;
}

// Utility functions
function getSeverity(value, type) {
    if (type === 'waiting') {
        if (value > 20) return 'high';
        if (value > 10) return 'medium';
        return 'low';
    } else if (type === 'occupancy') {
        if (value > 0.95) return 'high';
        if (value > 0.85) return 'medium';
        return 'low';
    }
    return 'low';
}

function getWaitTimeSeverity(waitTime) {
    if (waitTime > 120) return 'high';
    if (waitTime > 60) return 'medium';
    return 'low';
}

function formatSimulationTime(minutes) {
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    const mins = Math.floor(minutes % 60);
    
    if (days > 0) {
        return `Day ${days + 1}, ${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    } else {
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    }
}

function formatEventParams(params) {
    const formatted = [];
    for (const [key, value] of Object.entries(params)) {
        if (typeof value === 'number') {
            formatted.push(`${key}: ${value.toFixed(2)}`);
        } else {
            formatted.push(`${key}: ${value}`);
        }
    }
    return formatted.join(', ') || 'No parameters';
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function showError(message) {
    console.error(message);
    alert(message);
}

/**
 * Format duration in a human-readable way
 */
function formatDuration(minutes) {
    if (minutes < 60) {
        return `${minutes} minutes`;
    } else if (minutes < 1440) {
        const hours = Math.floor(minutes / 60);
        const remainingMins = minutes % 60;
        if (remainingMins === 0) {
            return `${hours} hour${hours > 1 ? 's' : ''}`;
        } else {
            return `${hours}h ${remainingMins}m`;
        }
    } else {
        const days = Math.floor(minutes / 1440);
        const remainingHours = Math.floor((minutes % 1440) / 60);
        if (remainingHours === 0) {
            return `${days} day${days > 1 ? 's' : ''}`;
        } else {
            return `${days}d ${remainingHours}h`;
        }
    }
}