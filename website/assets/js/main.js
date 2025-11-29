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
    initCarousel();
    initSearch();
    initLogoRefresh();
    initMobileMenu();
});

/**
 * Loads company data and statistics from local JSON files.
 * Falls back to API endpoint if local files are not available.
 * Stores data in window.companiesData and window.datasetStats.
 * 
 * @async
 * @function loadData
 * @returns {Promise<void>} Resolves when data is loaded or fails silently
 */
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

/**
 * Loads and displays statistics on the dashboard.
 * Updates stat cards with total companies, revenue, industries, and average employees.
 * 
 * @async
 * @function loadStatistics
 * @returns {Promise<void>} Resolves when statistics are loaded and displayed
 */
async function loadStatistics() {
    try {
        const stats = window.datasetStats;
        
        if (!stats) {
            await loadData();
            return;
        }
        
        // Update stat cards
        document.getElementById('total-companies').textContent = formatNumber(stats.total_companies || 0);
        // Calculate total revenue from companies data
        const totalRevenue = (window.companiesData || []).reduce((sum, c) => {
            return sum + (c.revenue || 0);
        }, 0);
        document.getElementById('total-revenue').textContent = '$' + formatCurrency(totalRevenue);
        document.getElementById('total-industries').textContent = formatNumber(stats.total_industries || 0);
        document.getElementById('avg-employees').textContent = formatNumber(Math.round(stats.avg_employee_count || 0));
    } catch (error) {
        console.error('Error loading statistics:', error);
        // Show placeholder values on error
        document.getElementById('total-companies').textContent = 'Loading...';
    }
}

/**
 * Initializes and renders all dashboard charts.
 * Creates industries, revenue, cities, employees, revenue change, and profitability charts.
 * 
 * @async
 * @function loadCharts
 * @returns {Promise<void>} Resolves when all charts are created
 */
async function loadCharts() {
    try {
        const stats = window.datasetStats;
        
        if (!stats) {
            await loadData();
        }
        
        // Industries chart
        if (stats && stats.industries) {
            createIndustriesChart(stats.industries);
        }
        
        // Revenue distribution chart
        if (window.companiesData && window.companiesData.length > 0) {
            createRevenueChart(window.companiesData);
            createCitiesChart(window.companiesData);
            createEmployeesChart(window.companiesData);
            createRevenueChangeChart(window.companiesData);
            createProfitabilityCharts(window.companiesData);
        }
    } catch (error) {
        console.error('Error loading charts:', error);
    }
}

/**
 * Extracts the domain name from a website URL.
 * Removes protocol, www prefix, path, query strings, and port numbers.
 * 
 * @function extractDomain
 * @param {string|null|undefined} websiteUrl - The full website URL
 * @returns {string|null} The extracted domain name, or null if invalid
 * @example
 * extractDomain('https://www.example.com:8080/path?query=1') // Returns 'example.com'
 */
function extractDomain(websiteUrl) {
    if (!websiteUrl) return null;
    try {
        // Remove protocol (http://, https://)
        let domain = websiteUrl.replace(/^https?:\/\//, '');
        // Remove www.
        domain = domain.replace(/^www\./, '');
        // Remove path and query string
        domain = domain.split('/')[0];
        // Remove port if present
        domain = domain.split(':')[0];
        return domain;
    } catch (e) {
        return null;
    }
}

/**
 * Maps company names to their corresponding logo filenames.
 * Returns the logo filename if found in the predefined mapping, otherwise returns null.
 * 
 * @function getCompanyLogo
 * @param {string|null|undefined} companyName - The company name to look up
 * @returns {string|null} The logo filename (e.g., 'apple.svg') or null if not found
 */
function getCompanyLogo(companyName) {
    const logoMap = {
        'APPLE': 'apple.svg',
        'MICROSOFT': 'microsoft.png',
        'NVIDIA': 'nvidia.svg',
        'ALPHABET': 'alphabet.svg',
        'AMAZON': 'amazon.png',
        'META PLATFORMS': 'meta_platforms.svg'
    };
    const normalizedName = (companyName || '').toUpperCase();
    return logoMap[normalizedName] || null;
}

/**
 * Loads and displays the top 6 companies by market cap as profile cards.
 * Each card shows company logo, name, ticker, market cap, fortune rank, domain,
 * revenue, employee count, and founded year.
 * 
 * @async
 * @function loadCompanyProfiles
 * @returns {Promise<void>} Resolves when company profiles are loaded and displayed
 */
async function loadCompanyProfiles() {
    try {
        const companies = window.companiesData;
        
        if (!companies || companies.length === 0) {
            await loadData();
            return;
        }
        
        // Get top 6 companies by market cap
        const topCompanies = companies
            .filter(c => c.market_cap_updated_m && c.market_cap_updated_m > 0)
            .sort((a, b) => (b.market_cap_updated_m || 0) - (a.market_cap_updated_m || 0))
            .slice(0, 6);
        
        // Display in a grid
        const profilesContainer = document.getElementById('company-profiles');
        if (profilesContainer) {
            profilesContainer.innerHTML = topCompanies.map(company => {
                const logoFile = getCompanyLogo(company.company_name);
                const logoPath = logoFile ? `assets/logos/${logoFile}` : null;
                
                const displayName = capitalizeCompanyName(company.company_name || 'Unknown');
                return `
                <div class="company-card">
                    <div class="company-logo-section">
                        ${logoPath ? `<img src="${logoPath}" alt="${escapeHtml(displayName)} logo" class="company-logo" onerror="this.style.display='none'">` : ''}
                        <div class="company-header-info">
                            <div class="company-name-row">
                                <h3 class="company-name">${escapeHtml(displayName)}</h3>
                                ${company.ticker ? `<span class="company-ticker">${escapeHtml(company.ticker)}</span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="company-details">
                        ${company.market_cap_updated_m ? `<div class="company-stat">
                            <span class="company-stat-label">Market Cap</span>
                            <span class="company-stat-value">$${formatCurrency(company.market_cap_updated_m * 1000000)}</span>
                        </div>` : ''}
                        ${company.fortune_rank ? `<div class="company-stat">
                            <span class="company-stat-label">Fortune Rank</span>
                            <span class="company-stat-value">#${company.fortune_rank}</span>
                        </div>` : ''}
                        ${company.domain ? `<div class="company-stat">
                            <span class="company-stat-label">Domain</span>
                            <span class="company-stat-value">${escapeHtml(company.domain)}</span>
                        </div>` : ''}
                        ${company.revenue ? `<div class="company-stat">
                            <span class="company-stat-label">Revenue</span>
                            <span class="company-stat-value">$${formatCurrency(company.revenue)}</span>
                        </div>` : ''}
                        ${company.employee_count ? `<div class="company-stat">
                            <span class="company-stat-label">Employees</span>
                            <span class="company-stat-value">${formatNumber(company.employee_count)}</span>
                        </div>` : ''}
                        ${company.founded_year ? `<div class="company-stat">
                            <span class="company-stat-label">Founded</span>
                            <span class="company-stat-value">${company.founded_year}</span>
                        </div>` : ''}
                    </div>
                </div>`;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading company profiles:', error);
    }
}

// OpenAI-style color palette - Same color family with different intensities
// Using green/teal family (OpenAI's signature colors) with varying intensities
const CHART_COLORS = {
    primary: '#10a37f',       // OpenAI green
    primaryLight: '#19c37d',  // Lighter green
    primaryDark: '#0d8c6f',   // Darker green
    secondary: '#ab68ff',     // Purple accent
    secondaryLight: '#c084fc', // Light purple
    secondaryDark: '#9333ea', // Dark purple
    accent: '#8b5cf6',        // Violet
    accentLight: '#a78bfa',   // Light violet
    accentDark: '#7c3aed',    // Dark violet
    neutral: '#94a3b8',       // Slate-400
    neutralLight: '#cbd5e1',  // Slate-300
    neutralDark: '#64748b'    // Slate-500
};

/**
 * Generates a color palette array by cycling through predefined base colors.
 * Uses OpenAI-style color scheme with green/teal, purple, and violet families.
 * 
 * @function getColorPalette
 * @param {number} count - The number of colors needed
 * @returns {string[]} Array of hex color codes
 */
function getColorPalette(count) {
    const baseColors = [
        CHART_COLORS.primary,
        CHART_COLORS.primaryLight,
        CHART_COLORS.primaryDark,
        CHART_COLORS.secondary,
        CHART_COLORS.secondaryLight,
        CHART_COLORS.secondaryDark,
        CHART_COLORS.accent,
        CHART_COLORS.accentLight,
        CHART_COLORS.accentDark,
        CHART_COLORS.neutral
    ];
    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}

// Removed createCountriesChart - no longer needed

/**
 * Creates a bar chart displaying the top 10 industries by company count.
 * Uses Chart.js to render a vertical bar chart with custom styling.
 * 
 * @function createIndustriesChart
 * @param {Object<string, number>} industriesData - Object mapping industry names to company counts
 * @returns {void}
 */
function createIndustriesChart(industriesData) {
    const canvas = document.getElementById('industries-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const labels = Object.keys(industriesData).slice(0, 10);
    const data = labels.map(label => industriesData[label]);
    const colors = getColorPalette(labels.length);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Companies',
                data: data,
                backgroundColor: colors,
                borderRadius: 6,
                barThickness: 40,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            aspectRatio: 1.8,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 10,
                    titleFont: { family: 'Quicksand', size: 12 },
                    bodyFont: { family: 'Quicksand', size: 11 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        font: { family: 'Quicksand', size: 11 },
                        color: '#1a1a1a'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    ticks: {
                        font: { family: 'Quicksand', size: 10 },
                        color: '#1a1a1a'
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

/**
 * Creates a horizontal bar chart showing the top 15 companies by revenue.
 * Displays revenue in billions of USD with formatted tooltips and labels.
 * 
 * @function createRevenueChart
 * @param {Array<Object>} companiesData - Array of company objects with revenue data
 * @returns {void}
 */
function createRevenueChart(companiesData) {
    const canvas = document.getElementById('revenue-chart');
    if (!canvas) return;
    
    // Filter companies with revenue and sort
    const companiesWithRevenue = companiesData
        .filter(c => c.revenue && c.revenue > 0)
        .sort((a, b) => (b.revenue || 0) - (a.revenue || 0))
        .slice(0, 15); // Top 15 by revenue
    
    const ctx = canvas.getContext('2d');
    const labels = companiesWithRevenue.map(c => (c.company_name || 'Unknown').substring(0, 20));
    const data = companiesWithRevenue.map(c => (c.revenue || 0) / 1000000000); // Convert to billions
    const colors = getColorPalette(labels.length);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue (Billions USD)',
                data: data,
                backgroundColor: colors,
                borderRadius: 6,
                barThickness: 35,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            aspectRatio: 1.8,
            indexAxis: 'y', // Horizontal bars
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 10,
                    titleFont: { family: 'Quicksand', size: 12 },
                    bodyFont: { family: 'Quicksand', size: 11 },
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
                        },
                        font: { family: 'Quicksand', size: 10 },
                        color: '#1a1a1a'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    ticks: {
                        font: { family: 'Quicksand', size: 9 },
                        color: '#1a1a1a'
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

/**
 * Formats a number with locale-specific thousand separators.
 * Returns '-' for null, undefined, or NaN values.
 * 
 * @function formatNumber
 * @param {number|null|undefined} num - The number to format
 * @returns {string} Formatted number string with commas, or '-' for invalid values
 * @example
 * formatNumber(1234567) // Returns '1,234,567'
 */
function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '-';
    return num.toLocaleString();
}

/**
 * Formats a number as currency with appropriate suffix (K, M, B).
 * Automatically scales large numbers to thousands, millions, or billions.
 * Returns '-' for null, undefined, or NaN values.
 * 
 * @function formatCurrency
 * @param {number|null|undefined} num - The currency amount to format
 * @returns {string} Formatted currency string (e.g., '1.5B', '250.3M', '45.2K'), or '-' for invalid values
 * @example
 * formatCurrency(1500000000) // Returns '1.5B'
 * formatCurrency(250000) // Returns '250.0K'
 */
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

/**
 * Escapes HTML special characters to prevent XSS attacks.
 * Converts potentially dangerous characters to their HTML entity equivalents.
 * 
 * @function escapeHtml
 * @param {string|null|undefined} text - The text to escape
 * @returns {string} Escaped HTML string, or empty string if input is falsy
 * @example
 * escapeHtml('<script>alert("xss")</script>') // Returns '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Converts a company name to title case.
 * Capitalizes the first letter of each word and lowercases the rest.
 * 
 * @function capitalizeCompanyName
 * @param {string|null|undefined} name - The company name to capitalize
 * @returns {string} Title-cased company name, or empty string if input is falsy
 * @example
 * capitalizeCompanyName('APPLE INC') // Returns 'Apple Inc'
 */
function capitalizeCompanyName(name) {
    if (!name) return '';
    // Convert to title case: first letter of each word capitalized, rest lowercase
    return name.toLowerCase()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Dashboard Carousel
let currentDashboard = 0;
const totalDashboards = 6; // Combined revenue growth and decline into one chart

/**
 * Initializes the dashboard carousel navigation.
 * Creates indicator dots and sets up previous/next button event listeners.
 * Allows users to navigate between different dashboard views.
 * 
 * @function initCarousel
 * @returns {void}
 */
function initCarousel() {
    const prevBtn = document.getElementById('prev-dashboard');
    const nextBtn = document.getElementById('next-dashboard');
    const indicators = document.getElementById('dashboard-indicators');
    
    // Create indicators
    for (let i = 0; i < totalDashboards; i++) {
        const indicator = document.createElement('div');
        indicator.className = 'dashboard-indicator' + (i === 0 ? ' active' : '');
        indicator.addEventListener('click', () => goToDashboard(i));
        indicators.appendChild(indicator);
    }
    
    prevBtn.addEventListener('click', () => {
        currentDashboard = (currentDashboard - 1 + totalDashboards) % totalDashboards;
        goToDashboard(currentDashboard);
    });
    
    nextBtn.addEventListener('click', () => {
        currentDashboard = (currentDashboard + 1) % totalDashboards;
        goToDashboard(currentDashboard);
    });
}

/**
 * Navigates to a specific dashboard slide by index.
 * Updates the active state of slides and indicators.
 * 
 * @function goToDashboard
 * @param {number} index - The zero-based index of the dashboard to display
 * @returns {void}
 */
function goToDashboard(index) {
    const slides = document.querySelectorAll('.dashboard-slide');
    const indicators = document.querySelectorAll('.dashboard-indicator');
    
    slides.forEach((slide, i) => {
        slide.classList.toggle('active', i === index);
    });
    
    indicators.forEach((indicator, i) => {
        indicator.classList.toggle('active', i === index);
    });
    
    currentDashboard = index;
}

/**
 * Creates a bar chart displaying the top 12 cities by company headquarters count.
 * Counts companies per city and displays them in descending order.
 * 
 * @function createCitiesChart
 * @param {Array<Object>} companiesData - Array of company objects with headquarters_city data
 * @returns {void}
 */
function createCitiesChart(companiesData) {
    const canvas = document.getElementById('cities-chart');
    if (!canvas) return;
    
    const cityCounts = {};
    companiesData.forEach(c => {
        if (c.headquarters_city) {
            cityCounts[c.headquarters_city] = (cityCounts[c.headquarters_city] || 0) + 1;
        }
    });
    
    const sortedCities = Object.entries(cityCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 12);
    
    const ctx = canvas.getContext('2d');
    const colors = getColorPalette(sortedCities.length);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedCities.map(c => c[0]),
            datasets: [{
                label: 'Companies',
                data: sortedCities.map(c => c[1]),
                backgroundColor: colors,
                borderRadius: 6,
                barThickness: 40,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            aspectRatio: 1.8,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 10,
                    titleFont: { family: 'Quicksand', size: 12 },
                    bodyFont: { family: 'Quicksand', size: 11 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { 
                        precision: 0,
                        font: { family: 'Quicksand', size: 11 },
                        color: '#1a1a1a'
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' }
                },
                x: {
                    ticks: { font: { family: 'Quicksand', size: 10 }, color: '#1a1a1a' },
                    grid: { display: false }
                }
            }
        }
    });
}

/**
 * Creates a doughnut chart showing employee count distribution across ranges.
 * Groups companies into ranges: 0-10K, 10K-50K, 50K-100K, 100K-200K, and 200K+.
 * 
 * @function createEmployeesChart
 * @param {Array<Object>} companiesData - Array of company objects with employee_count data
 * @returns {void}
 */
function createEmployeesChart(companiesData) {
    const canvas = document.getElementById('employees-chart');
    if (!canvas) return;
    
    const ranges = [
        { label: '0-10K', min: 0, max: 10000 },
        { label: '10K-50K', min: 10000, max: 50000 },
        { label: '50K-100K', min: 50000, max: 100000 },
        { label: '100K-200K', min: 100000, max: 200000 },
        { label: '200K+', min: 200000, max: Infinity }
    ];
    
    const counts = ranges.map(range => 
        companiesData.filter(c => c.employee_count >= range.min && c.employee_count < range.max).length
    );
    
    const ctx = canvas.getContext('2d');
    const colors = getColorPalette(ranges.length);
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ranges.map(r => r.label),
            datasets: [{
                data: counts,
                backgroundColor: colors,
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            aspectRatio: 1.5,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { font: { family: 'Quicksand', size: 10 }, padding: 8, usePointStyle: true, color: '#1a1a1a' }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 10,
                    titleFont: { family: 'Quicksand', size: 12 },
                    bodyFont: { family: 'Quicksand', size: 11 }
                }
            }
        }
    });
}

/**
 * Creates a horizontal bar chart showing the top 15 companies by revenue percentage change.
 * Displays companies with the highest revenue growth or decline.
 * 
 * @function createRevenueChangeChart
 * @param {Array<Object>} companiesData - Array of company objects with revenue_percent_change data
 * @returns {void}
 */
function createRevenueChangeChart(companiesData) {
    const canvas = document.getElementById('revenue-change-chart');
    if (!canvas) return;
    
    const companiesWithChange = companiesData
        .filter(c => c.revenue_percent_change !== null && c.revenue_percent_change !== undefined)
        .sort((a, b) => (b.revenue_percent_change || 0) - (a.revenue_percent_change || 0))
        .slice(0, 15);
    
    const ctx = canvas.getContext('2d');
    const colors = getColorPalette(companiesWithChange.length);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: companiesWithChange.map(c => (c.company_name || 'Unknown').substring(0, 18)),
            datasets: [{
                label: 'Revenue % Change',
                data: companiesWithChange.map(c => c.revenue_percent_change),
                backgroundColor: colors,
                borderRadius: 6,
                barThickness: 35,
            }]
        },
            options: {
            responsive: true,
            maintainAspectRatio: false,
            aspectRatio: 1.8,
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            return context.parsed.x.toFixed(1) + '%';
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(1) + '%';
                        },
                        font: { family: 'Quicksand', size: 10 },
                        color: '#1a1a1a'
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' }
                },
                y: {
                    ticks: { font: { family: 'Quicksand', size: 9 }, color: '#1a1a1a' },
                    grid: { display: false }
                }
            }
        }
    });
}

/**
 * Creates a combined bar chart showing revenue growth and decline.
 * Displays top 20 companies with the highest absolute revenue change.
 * Uses green colors for growth and red colors for decline.
 * Excludes the top growth company to better compare others.
 * 
 * @function createProfitabilityCharts
 * @param {Array<Object>} companiesData - Array of company objects with revenue_percent_change data
 * @returns {void}
 */
function createProfitabilityCharts(companiesData) {
    // Get top growth companies (excluding #1 to better compare others)
    const allGrowthCompanies = companiesData
        .filter(c => c.revenue_percent_change !== null && c.revenue_percent_change !== undefined && c.revenue_percent_change > 0)
        .sort((a, b) => (b.revenue_percent_change || 0) - (a.revenue_percent_change || 0));
    
    // Remove top 1 and take next 10
    const topRevenueGrowth = allGrowthCompanies.slice(1, 11);
    
    // Get top decline companies
    const topRevenueDecline = companiesData
        .filter(c => c.revenue_percent_change !== null && c.revenue_percent_change !== undefined && c.revenue_percent_change < 0)
        .sort((a, b) => (a.revenue_percent_change || 0) - (b.revenue_percent_change || 0))
        .slice(0, 10);
    
    // Combine and sort all companies by absolute value of change
    const allCompanies = [...topRevenueGrowth, ...topRevenueDecline]
        .sort((a, b) => Math.abs(b.revenue_percent_change || 0) - Math.abs(a.revenue_percent_change || 0))
        .slice(0, 20);
    
    const canvas = document.getElementById('revenue-growth-decline-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Create gradient colors for growth (green shades) and decline (red shades)
    const growthColors = [
        '#10a37f', '#19c37d', '#0d8c6f', '#14b87a', '#0ea572',
        '#1dd98a', '#0fb875', '#16a67f', '#1bc580', '#12b06d'
    ];
    const declineColors = [
        '#ef4444', '#f87171', '#dc2626', '#fca5a5', '#b91c1c',
        '#fee2e2', '#991b1b', '#fecaca', '#7f1d1d', '#ef4444'
    ];
    
    // Assign colors based on growth/decline with variety
    const colors = allCompanies.map((c, index) => {
        if (c.revenue_percent_change > 0) {
            return growthColors[index % growthColors.length];
        } else {
            return declineColors[index % declineColors.length];
        }
    });
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: allCompanies.map(c => (c.company_name || 'Unknown').substring(0, 15)),
            datasets: [{
                label: 'Revenue % Change',
                data: allCompanies.map(c => c.revenue_percent_change),
                backgroundColor: colors,
                borderRadius: 8,
                barThickness: 40,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            aspectRatio: 2,
            plugins: {
                legend: { 
                    display: true,
                    position: 'top',
                    labels: {
                        font: { family: 'Quicksand', size: 12 },
                        color: '#1a1a1a',
                        padding: 15,
                        usePointStyle: true,
                        generateLabels: function(chart) {
                            return [
                                {
                                    text: 'Growth',
                                    fillStyle: '#10a37f',
                                    strokeStyle: '#10a37f',
                                    lineWidth: 0,
                                    hidden: false,
                                    index: 0
                                },
                                {
                                    text: 'Decline',
                                    fillStyle: '#ef4444',
                                    strokeStyle: '#ef4444',
                                    lineWidth: 0,
                                    hidden: false,
                                    index: 1
                                }
                            ];
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.85)',
                    padding: 12,
                    titleFont: { family: 'Quicksand', size: 13, weight: '600' },
                    bodyFont: { family: 'Quicksand', size: 12 },
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.y;
                            const sign = value >= 0 ? '+' : '';
                            return `${sign}${value.toFixed(1)}%`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            const sign = value >= 0 ? '+' : '';
                            return sign + value.toFixed(1) + '%';
                        },
                        font: { family: 'Quicksand', size: 11 },
                        color: '#1a1a1a'
                    },
                    grid: { 
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    title: {
                        display: true,
                        text: 'Revenue % Change',
                        font: { family: 'Quicksand', size: 12, weight: '600' },
                        color: '#1a1a1a',
                        padding: { top: 10, bottom: 10 }
                    }
                },
                x: {
                    ticks: { 
                        font: { family: 'Quicksand', size: 9 }, 
                        color: '#1a1a1a',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: { display: false }
                }
            }
        }
    });
}

/**
 * Initializes the company search functionality.
 * Sets up event listeners for search input and button.
 * Searches companies by name or CEO, displaying up to 20 results.
 * 
 * @function initSearch
 * @returns {void}
 */
function initSearch() {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsTable = document.getElementById('search-results');
    
    const performSearch = () => {
        const query = searchInput.value.trim().toLowerCase();
        if (!query) {
            resultsTable.classList.remove('active');
            return;
        }
        
        const companies = window.companiesData || [];
        const results = companies.filter(c => 
            (c.company_name && c.company_name.toLowerCase().includes(query)) ||
            (c.ceo && c.ceo.toLowerCase().includes(query))
        ).slice(0, 20);
        
        if (results.length > 0) {
            displaySearchResults(results);
        } else {
            resultsTable.innerHTML = '<p style="text-align: center; padding: 2rem; color: var(--color-text-secondary);">No results found</p>';
            resultsTable.classList.add('active');
        }
    };
    
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
}

/**
 * Displays search results in a table format.
 * Shows company details including name, ticker, CEO, founded year, domain,
 * industry, headquarters, market cap, revenue, and employee count.
 * 
 * @function displaySearchResults
 * @param {Array<Object>} results - Array of company objects matching the search query
 * @returns {void}
 */
function displaySearchResults(results) {
    const resultsTable = document.getElementById('search-results');
    resultsTable.innerHTML = `
        <table class="results-table">
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Ticker</th>
                    <th>CEO</th>
                    <th>Founded</th>
                    <th>Domain</th>
                    <th>Industry</th>
                    <th>Headquarters</th>
                    <th>Market Cap</th>
                    <th>Revenue</th>
                    <th>Employees</th>
                </tr>
            </thead>
            <tbody>
                ${results.map(c => `
                    <tr>
                        <td><strong>${escapeHtml(c.company_name || 'N/A')}</strong></td>
                        <td>${escapeHtml(c.ticker || 'N/A')}</td>
                        <td>${escapeHtml(c.ceo || 'N/A')}</td>
                        <td>${c.founded_year || 'N/A'}</td>
                        <td>${escapeHtml(c.domain || 'N/A')}</td>
                        <td>${escapeHtml(c.industry || 'N/A')}</td>
                        <td>${escapeHtml(c.headquarters_city || 'N/A')}</td>
                        <td>${c.market_cap_updated_m ? '$' + formatCurrency(c.market_cap_updated_m * 1000000) : 'N/A'}</td>
                        <td>${c.revenue ? '$' + formatCurrency(c.revenue) : 'N/A'}</td>
                        <td>${c.employee_count ? formatNumber(c.employee_count) : 'N/A'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    resultsTable.classList.add('active');
}

/**
 * Initializes the logo click handler to scroll to the top of the page.
 * Provides smooth scrolling behavior when the logo is clicked.
 * 
 * @function initLogoRefresh
 * @returns {void}
 */
function initLogoRefresh() {
    const logo = document.getElementById('logo-refresh');
    if (logo) {
        logo.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
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

/**
 * Initializes the mobile menu toggle functionality.
 * Handles hamburger menu click, link clicks, outside clicks, and Escape key.
 * Manages ARIA attributes for accessibility.
 * 
 * @function initMobileMenu
 * @returns {void}
 */
function initMobileMenu() {
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('nav-menu');
    
    if (!hamburger || !navMenu) return;
    
    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
        hamburger.setAttribute('aria-expanded', hamburger.classList.contains('active'));
    });
    
    // Close menu when clicking on a link
    const navLinks = navMenu.querySelectorAll('a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
            hamburger.setAttribute('aria-expanded', 'false');
        });
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (navMenu.classList.contains('active') && 
            !navMenu.contains(e.target) && 
            !hamburger.contains(e.target)) {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
            hamburger.setAttribute('aria-expanded', 'false');
        }
    });
    
    // Close menu on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && navMenu.classList.contains('active')) {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
            hamburger.setAttribute('aria-expanded', 'false');
        }
    });
}

