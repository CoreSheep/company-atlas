// Main JavaScript for Company Atlas website

// Use relative path for GitHub Pages (data files need to be in the website directory or accessible)
// For GitHub Pages, we'll need to either:
// 1. Copy data files to website directory, or
// 2. Use a CDN/API endpoint
const DATA_BASE_PATH = './data/marts';

// Initialize page
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    await loadStatistics();
    await loadCharts();
    await loadCompanyProfiles();
});

// Load data from local JSON files
async function loadData() {
    try {
        // Load companies data
        const companiesResponse = await fetch(`${DATA_BASE_PATH}/unified_companies.json`);
        window.companiesData = await companiesResponse.json();
        
        // Load statistics
        const statsResponse = await fetch(`${DATA_BASE_PATH}/statistics.json`);
        window.datasetStats = await statsResponse.json();
        
        console.log(`Loaded ${window.companiesData.length} companies`);
    } catch (error) {
        console.error('Error loading data:', error);
        // Fallback to API if local files not available
        try {
            const API_BASE_URL = 'http://localhost:8000/api/v1';
            const response = await fetch(`${API_BASE_URL}/statistics`);
            window.datasetStats = await response.json();
        } catch (apiError) {
            console.error('Error loading from API:', apiError);
        }
    }
}

// Load statistics
async function loadStatistics() {
    try {
        const stats = window.datasetStats;
        
        if (!stats) {
            await loadData();
            return;
        }
        
        // Update stat cards
        document.getElementById('total-companies').textContent = formatNumber(stats.total_companies || 0);
        document.getElementById('total-countries').textContent = formatNumber(stats.total_countries || 0);
        document.getElementById('total-industries').textContent = formatNumber(stats.total_industries || 0);
        document.getElementById('avg-employees').textContent = formatNumber(Math.round(stats.avg_employee_count || 0));
    } catch (error) {
        console.error('Error loading statistics:', error);
        // Show placeholder values on error
        document.getElementById('total-companies').textContent = 'Loading...';
    }
}

// Load charts
async function loadCharts() {
    try {
        const stats = window.datasetStats;
        
        if (!stats) {
            await loadData();
        }
        
        // Countries chart
        if (stats && stats.countries) {
            createCountriesChart(stats.countries);
        }
        
        // Industries chart
        if (stats && stats.industries) {
            createIndustriesChart(stats.industries);
        }
        
        // Revenue distribution chart
        if (window.companiesData && window.companiesData.length > 0) {
            createRevenueChart(window.companiesData);
        }
    } catch (error) {
        console.error('Error loading charts:', error);
    }
}

// Load and display company profiles
async function loadCompanyProfiles() {
    try {
        const companies = window.companiesData;
        
        if (!companies || companies.length === 0) {
            await loadData();
            return;
        }
        
        // Get top companies by revenue
        const topCompanies = companies
            .filter(c => c.revenue && c.revenue > 0)
            .sort((a, b) => (b.revenue || 0) - (a.revenue || 0))
            .slice(0, 12);
        
        // Display in a grid
        const profilesContainer = document.getElementById('company-profiles');
        if (profilesContainer) {
            profilesContainer.innerHTML = topCompanies.map(company => `
                <div class="company-card">
                    <div class="company-header">
                        <h3 class="company-name">${escapeHtml(company.company_name || 'Unknown')}</h3>
                        ${company.ticker ? `<span class="company-ticker">${escapeHtml(company.ticker)}</span>` : ''}
                    </div>
                    <div class="company-details">
                        ${company.fortune_rank ? `<div class="company-stat"><span class="stat-label">Fortune Rank:</span> <span class="stat-value">#${company.fortune_rank}</span></div>` : ''}
                        ${company.industry ? `<div class="company-stat"><span class="stat-label">Industry:</span> <span class="stat-value">${escapeHtml(company.industry)}</span></div>` : ''}
                        ${company.country ? `<div class="company-stat"><span class="stat-label">Country:</span> <span class="stat-value">${escapeHtml(company.country)}</span></div>` : ''}
                        ${company.founded_year ? `<div class="company-stat"><span class="stat-label">Founded:</span> <span class="stat-value">${company.founded_year}</span></div>` : ''}
                        ${company.employee_count ? `<div class="company-stat"><span class="stat-label">Employees:</span> <span class="stat-value">${formatNumber(company.employee_count)}</span></div>` : ''}
                        ${company.revenue ? `<div class="company-stat"><span class="stat-label">Revenue:</span> <span class="stat-value">$${formatCurrency(company.revenue)}</span></div>` : ''}
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading company profiles:', error);
    }
}

// Create countries chart
function createCountriesChart(countriesData) {
    const canvas = document.getElementById('countries-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const labels = Object.keys(countriesData).slice(0, 10);
    const data = labels.map(label => countriesData[label]);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Companies',
                data: data,
                backgroundColor: '#0071e3',
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// Create industries chart
function createIndustriesChart(industriesData) {
    const canvas = document.getElementById('industries-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const labels = Object.keys(industriesData).slice(0, 10);
    const data = labels.map(label => industriesData[label]);
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: 'Companies',
                data: data,
                backgroundColor: [
                    '#0071e3',
                    '#5ac8fa',
                    '#34c759',
                    '#ff9500',
                    '#ff3b30',
                    '#af52de',
                    '#ff2d55',
                    '#5856d6',
                    '#ffcc00',
                    '#8e8e93'
                ],
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

// Create revenue distribution chart
function createRevenueChart(companiesData) {
    const canvas = document.getElementById('revenue-chart');
    if (!canvas) return;
    
    // Filter companies with revenue and sort
    const companiesWithRevenue = companiesData
        .filter(c => c.revenue && c.revenue > 0)
        .sort((a, b) => (b.revenue || 0) - (a.revenue || 0))
        .slice(0, 20); // Top 20 by revenue
    
    const ctx = canvas.getContext('2d');
    const labels = companiesWithRevenue.map(c => c.company_name || 'Unknown');
    const data = companiesWithRevenue.map(c => (c.revenue || 0) / 1000000000); // Convert to billions
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue (Billions USD)',
                data: data,
                backgroundColor: '#0071e3',
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y', // Horizontal bars
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `$${context.parsed.x.toFixed(1)}B`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(1) + 'B';
                        }
                    }
                },
                y: {
                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                }
            }
        }
    });
}

// Format number with commas
function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '-';
    return num.toLocaleString();
}

// Format currency
function formatCurrency(num) {
    if (num === null || num === undefined || isNaN(num)) return '-';
    if (num >= 1000000000) {
        return (num / 1000000000).toFixed(1) + 'B';
    } else if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString();
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Smooth scroll for anchor links
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

