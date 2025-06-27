// Main dashboard JavaScript
let selectedSimulationId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadSimulations();
});

async function loadSimulations() {
    try {
        const response = await fetch('/api/simulations');
        const result = await response.json();
        
        if (result.success) {
            displaySimulations(result.data);
        } else {
            showError('Failed to load simulations: ' + result.error);
        }
    } catch (error) {
        showError('Error loading simulations: ' + error.message);
    }
}

function displaySimulations(simulations) {
    const loadingEl = document.getElementById('loading');
    const listEl = document.getElementById('simulationsList');
    const noSimEl = document.getElementById('noSimulations');
    const tableBody = document.getElementById('simulationsTableBody');
    
    loadingEl.style.display = 'none';
    
    if (simulations.length === 0) {
        noSimEl.style.display = 'block';
        return;
    }
    
    listEl.style.display = 'block';
    tableBody.innerHTML = '';
    
    simulations.forEach(sim => {
        const row = document.createElement('tr');
        row.className = 'simulation-row';
        row.style.cursor = 'pointer';
        
        const startDate = new Date(sim.start_time);
        const statusBadge = getStatusBadge(sim);
        
        // Ensure we have the dynamic values, with fallbacks
        const numDoctors = sim.num_doctors || 'Unknown';
        const arrivalRate = sim.arrival_rate ? sim.arrival_rate.toFixed(1) : 'Unknown';
        
        row.innerHTML = `
            <td><strong>#${sim.id}</strong></td>
            <td>${startDate.toLocaleString()}</td>
            <td>${numDoctors}</td>
            <td>${arrivalRate}/hr</td>
            <td>${sim.description || 'Hospital Simulation'}</td>
            <td>${statusBadge}</td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-primary" onclick="selectSimulation(${sim.id})">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="btn btn-success" onclick="goToAnalytics(${sim.id})">
                        <i class="fas fa-chart-line"></i>
                    </button>
                    <button class="btn btn-warning" onclick="goToIncidents(${sim.id})">
                        <i class="fas fa-exclamation-triangle"></i>
                    </button>
                    <button class="btn btn-info" onclick="goToRealtime(${sim.id})">
                        <i class="fas fa-play"></i>
                    </button>
                </div>
            </td>
        `;
        
        row.addEventListener('click', (e) => {
            if (!e.target.closest('.btn-group')) {
                selectSimulation(sim.id);
            }
        });
        
        tableBody.appendChild(row);
    });
}

function getStatusBadge(sim) {
    // Simple status logic - could be enhanced
    const now = new Date();
    const simDate = new Date(sim.start_time);
    const daysDiff = (now - simDate) / (1000 * 60 * 60 * 24);
    
    if (daysDiff < 1) {
        return '<span class="badge bg-success">Recent</span>';
    } else if (daysDiff < 7) {
        return '<span class="badge bg-primary">Active</span>';
    } else {
        return '<span class="badge bg-secondary">Archived</span>';
    }
}

async function selectSimulation(simId) {
    selectedSimulationId = simId;
    
    // Update navigation links
    updateNavigationLinks(simId);
    
    // Highlight selected row
    document.querySelectorAll('.simulation-row').forEach(row => {
        row.classList.remove('table-active');
    });
    event.target.closest('tr').classList.add('table-active');
    
    // Load and display simulation details
    await loadSimulationDetails(simId);
}

function updateNavigationLinks(simId) {
    const analyticsLink = document.getElementById('analyticsLink');
    const incidentsLink = document.getElementById('incidentsLink');
    const realtimeLink = document.getElementById('realtimeLink');
    const navEl = document.getElementById('simulationNav');
    
    analyticsLink.href = `/analytics/${simId}`;
    incidentsLink.href = `/incidents/${simId}`;
    realtimeLink.href = `/realtime/${simId}`;
    
    navEl.style.display = 'flex';
}

async function loadSimulationDetails(simId) {
    try {
        const response = await fetch(`/api/simulation/${simId}/info`);
        const result = await response.json();
        
        if (result.success) {
            displaySimulationDetails(result.data);
        } else {
            showError('Failed to load simulation details: ' + result.error);
        }
    } catch (error) {
        showError('Error loading simulation details: ' + error.message);
    }
}

function displaySimulationDetails(data) {
    const infoEl = document.getElementById('selectedSimulationInfo');
    
    document.getElementById('totalPatients').textContent = 
        data.patients_total ? data.patients_total.toLocaleString() : '-';
    document.getElementById('totalDoctors').textContent = data.num_doctors || '-';
    document.getElementById('simulationDuration').textContent = 
        data.time_range ? ((data.time_range.max - data.time_range.min) / 1440).toFixed(1) : '-';
    document.getElementById('eventsCount').textContent = 
        data.events_count ? data.events_count.toLocaleString() : '-';
    
    infoEl.style.display = 'block';
}

function goToAnalytics(simId) {
    window.location.href = `/analytics/${simId}`;
}

function goToIncidents(simId) {
    window.location.href = `/incidents/${simId}`;
}

function goToRealtime(simId) {
    window.location.href = `/realtime/${simId}`;
}

function showError(message) {
    console.error(message);
    // You could add a toast notification here
    alert(message);
}

// Utility functions
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

function formatTime(minutes) {
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    const mins = Math.floor(minutes % 60);
    
    if (days > 0) {
        return `${days}d ${hours}h ${mins}m`;
    } else if (hours > 0) {
        return `${hours}h ${mins}m`;
    } else {
        return `${mins}m`;
    }
}