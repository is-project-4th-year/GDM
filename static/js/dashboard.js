// Dashboard JavaScript - Charts and Interactions
document.addEventListener('DOMContentLoaded', function() {
    // Get chart data from the hidden script tag
    const chartDataElement = document.getElementById('chartData');
    if (!chartDataElement) {
        console.error('Chart data not found');
        return;
    }
    
    let chartData;
    try {
        chartData = JSON.parse(chartDataElement.textContent);
    } catch (e) {
        console.error('Error parsing chart data:', e);
        return;
    }
    
    // Initialize charts
    initializeRiskDistributionChart(chartData.riskDistribution);
    initializeAssessmentTrendsChart(chartData.assessmentTrends);
    
    // Add interactive features
    addInteractiveFeatures();
});

// Risk Distribution Doughnut Chart
function initializeRiskDistributionChart(data) {
    const ctx = document.getElementById('riskDistributionChart');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Low Risk', 'Moderate Risk', 'High Risk'],
            datasets: [{
                data: [
                    data.low_risk || 0,
                    data.moderate_risk || 0,
                    data.high_risk || 0
                ],
                backgroundColor: [
                    '#198754', // Green for low risk
                    '#ffc107', // Yellow for moderate risk
                    '#dc3545'  // Red for high risk
                ],
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}: ${value} patients (${percentage}%)`;
                        }
                    },
                    backgroundColor: '#fff',
                    titleColor: '#2c3e50',
                    bodyColor: '#495057',
                    borderColor: '#e9ecef',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true
                }
            },
            cutout: '65%',
            animation: {
                animateRotate: true,
                duration: 1000
            }
        }
    });
}

// Assessment Trends Line Chart
function initializeAssessmentTrendsChart(data) {
    const ctx = document.getElementById('assessmentTrendsChart');
    if (!ctx) return;
    
    // Prepare data for the last 7 days or weeks
    const labels = data.labels || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const assessmentCounts = data.counts || [0, 0, 0, 0, 0, 0, 0];
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Risk Assessments',
                data: assessmentCounts,
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#0d6efd',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: '#fff',
                    titleColor: '#2c3e50',
                    bodyColor: '#495057',
                    borderColor: '#e9ecef',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        title: function(tooltipItems) {
                            return tooltipItems[0].label;
                        },
                        label: function(context) {
                            return `Assessments: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        color: '#6c757d'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        stepSize: 1,
                        font: {
                            size: 12
                        },
                        color: '#6c757d',
                        callback: function(value) {
                            return Number.isInteger(value) ? value : '';
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
}

// Add interactive features
function addInteractiveFeatures() {
    // Auto-refresh data every 5 minutes
    setInterval(refreshDashboardData, 5 * 60 * 1000);
    
    // Add click handlers for KPI cards
    addKPICardInteractions();
    
    // Add search functionality if needed
    addSearchFunctionality();
    
    // Initialize tooltips
    initializeTooltips();
}

// Refresh dashboard data
async function refreshDashboardData() {
    try {
        const response = await fetch('/api/dashboard-data', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateKPICards(data.stats);
            // Note: Chart updates would require re-initializing charts
            console.log('Dashboard data refreshed');
        }
    } catch (error) {
        console.log('Dashboard refresh failed (this is normal if API endpoint not implemented):', error);
    }
}

// Update KPI card values
function updateKPICards(stats) {
    const kpiElements = {
        totalPatients: document.querySelector('.kpi-card:nth-child(1) h3'),
        totalAssessments: document.querySelector('.kpi-card:nth-child(2) h3'),
        highRiskCount: document.querySelector('.kpi-card:nth-child(3) h3'),
        assessmentsThisWeek: document.querySelector('.kpi-card:nth-child(4) h3')
    };
    
    Object.keys(kpiElements).forEach(key => {
        const element = kpiElements[key];
        if (element && stats[key]) {
            // Add a subtle animation when updating
            element.style.transform = 'scale(1.1)';
            element.textContent = stats[key];
            setTimeout(() => {
                element.style.transform = 'scale(1)';
            }, 150);
        }
    });
}

// KPI Card interactions
function addKPICardInteractions() {
    const kpiCards = document.querySelectorAll('.kpi-card');
    
    kpiCards.forEach((card, index) => {
        card.addEventListener('click', function() {
            // Add click effect
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 100);
            
            // Navigate based on card type
            switch(index) {
                case 0: // Total Patients
                    window.location.href = '/patients';
                    break;
                case 1: // Total Assessments
                    window.location.href = '/patients';
                    break;
                case 2: // High Risk
                    window.location.href = '/patients?filter=high_risk';
                    break;
                case 3: // This Week
                    window.location.href = '/patients?filter=recent';
                    break;
            }
        });
        
        // Add cursor pointer
        card.style.cursor = 'pointer';
    });
}

// Search functionality
function addSearchFunctionality() {
    const searchInputs = document.querySelectorAll('[data-search]');
    
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const targetSelector = e.target.getAttribute('data-search');
            const items = document.querySelectorAll(targetSelector);
            
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        }, 300));
    });
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(tooltipTriggerEl => {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Utility function: debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeRiskDistributionChart,
        initializeAssessmentTrendsChart,
        refreshDashboardData
    };