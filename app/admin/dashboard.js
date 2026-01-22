/**
 * Admin Dashboard JavaScript
 * Handles data fetching, chart rendering, and interactivity
 */

// =====================================================
// Configuration
// =====================================================

const API_BASE = '/api/admin';
let adminKey = localStorage.getItem('adminKey') || '';
let refreshInterval = null;

// =====================================================
// Authentication
// =====================================================

function showAuth() {
    document.getElementById('authSection').style.display = 'flex';
    document.getElementById('dashboardContent').classList.remove('active');
}

function showDashboard() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('dashboardContent').classList.add('active');
}

async function login() {
    const keyInput = document.getElementById('adminKeyInput');
    const errorEl = document.getElementById('authError');
    adminKey = keyInput.value.trim();

    if (!adminKey) {
        errorEl.textContent = 'Masukkan Admin Key';
        return;
    }

    try {
        // Test the key
        const response = await fetchAPI('/dashboard/stats');
        if (response) {
            localStorage.setItem('adminKey', adminKey);
            showDashboard();
            loadAllData();
            startAutoRefresh();
        }
    } catch (error) {
        errorEl.textContent = error.message || 'Admin Key tidak valid';
        adminKey = '';
    }
}

function logout() {
    adminKey = '';
    localStorage.removeItem('adminKey');
    stopAutoRefresh();
    showAuth();
}

// Check if already logged in
function checkAuth() {
    if (adminKey) {
        showDashboard();
        loadAllData();
        startAutoRefresh();
    } else {
        showAuth();
    }
}

// =====================================================
// API Helpers
// =====================================================

async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        'X-Admin-Key': adminKey
    };

    try {
        const response = await fetch(url, { ...options, headers });

        if (response.status === 401 || response.status === 403) {
            logout();
            throw new Error('Session expired');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail?.error || 'Request failed');
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

// =====================================================
// Data Loading
// =====================================================

async function loadAllData() {
    try {
        await Promise.all([
            loadStats(),
            loadRequestsChart(),
            loadAuditChart(),
            loadApiKeys(),
            loadAuditLogs()
        ]);
    } catch (error) {
        console.error('Failed to load data:', error);
    }
}

async function loadStats() {
    try {
        const stats = await fetchAPI('/dashboard/stats');

        // Update stat cards
        document.getElementById('totalRequests').textContent = formatNumber(stats.total_requests);
        document.getElementById('successRate').textContent = stats.success_rate.toFixed(1) + '%';
        document.getElementById('activeKeys').textContent = stats.active_keys;
        document.getElementById('avgProcessingTime').textContent = formatMs(stats.avg_processing_time_ms);
        document.getElementById('totalPages').textContent = formatNumber(stats.total_pages_processed);
        document.getElementById('auditEvents').textContent = formatNumber(stats.total_audit_events);

        // Update learning stats
        document.getElementById('totalTracked').textContent = stats.total_tracked_words;
        document.getElementById('approvedWords').textContent = stats.approved_words;
        document.getElementById('pendingWords').textContent = stats.pending_words;

        // Update progress bar
        const total = stats.total_tracked_words || 1;
        const progress = (stats.approved_words / total) * 100;
        document.getElementById('learningProgress').style.width = progress + '%';

        // Update progress percent text if element exists
        const progressPercent = document.getElementById('progressPercent');
        if (progressPercent) {
            progressPercent.textContent = progress.toFixed(0) + '%';
        }

    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function loadRequestsChart() {
    try {
        const data = await fetchAPI('/dashboard/requests-chart?days=7');
        renderRequestsChart(data);
    } catch (error) {
        console.error('Failed to load requests chart:', error);
    }
}

async function loadAuditChart() {
    try {
        const data = await fetchAPI('/dashboard/audit-summary');
        renderAuditChart(data);
    } catch (error) {
        console.error('Failed to load audit chart:', error);
    }
}

async function loadApiKeys() {
    try {
        const data = await fetchAPI('/keys');
        renderApiKeysTable(data.keys);
    } catch (error) {
        console.error('Failed to load API keys:', error);
    }
}

async function loadAuditLogs() {
    try {
        const data = await fetchAPI('/dashboard/audit-summary');
        renderAuditLogsTable(data.recent_events);
    } catch (error) {
        console.error('Failed to load audit logs:', error);
    }
}

// =====================================================
// Chart Rendering
// =====================================================

let requestsChart = null;
let auditChart = null;

function renderRequestsChart(data) {
    const ctx = document.getElementById('requestsChart').getContext('2d');

    // Format labels to show only day
    const labels = data.labels.map(date => {
        const d = new Date(date);
        return d.toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric' });
    });

    if (requestsChart) {
        requestsChart.data.labels = labels;
        requestsChart.data.datasets[0].data = data.successful;
        requestsChart.data.datasets[1].data = data.failed;
        requestsChart.update();
        return;
    }

    requestsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Sukses',
                    data: data.successful,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#10b981',
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Gagal',
                    data: data.failed,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#ef4444',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#a0a0b0',
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#a0a0b0',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#6c6c7c'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#6c6c7c',
                        precision: 0
                    }
                }
            }
        }
    });
}

function renderAuditChart(data) {
    const ctx = document.getElementById('auditChart').getContext('2d');

    const labels = data.events_by_type.map(e => formatEventType(e.event_type));
    const values = data.events_by_type.map(e => e.count);
    const colors = [
        '#6366f1', '#8b5cf6', '#10b981', '#f59e0b',
        '#ef4444', '#3b82f6', '#ec4899', '#14b8a6'
    ];

    if (auditChart) {
        auditChart.data.labels = labels;
        auditChart.data.datasets[0].data = values;
        auditChart.update();
        return;
    }

    auditChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: 'transparent',
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#a0a0b0',
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#a0a0b0',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            }
        }
    });
}

// =====================================================
// Table Rendering
// =====================================================

function renderApiKeysTable(keys) {
    const tbody = document.getElementById('apiKeysBody');

    if (!keys || keys.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted);">
                    Belum ada API Key
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = keys.map(key => `
        <tr>
            <td>
                <code style="color: var(--accent-primary);">${key.key_prefix}</code>
            </td>
            <td>${key.name}</td>
            <td>
                ${key.is_active
            ? '<span class="status-badge active">✓ Active</span>'
            : '<span class="status-badge inactive">✗ Revoked</span>'}
                ${key.is_admin
            ? '<span class="status-badge admin" style="margin-left: 4px;">👑 Admin</span>'
            : ''}
            </td>
            <td>${formatNumber(key.requests_count)}</td>
            <td>${key.last_used_at ? formatDate(key.last_used_at) : '-'}</td>
        </tr>
    `).join('');
}

function renderAuditLogsTable(logs) {
    const tbody = document.getElementById('auditLogsBody');

    if (!logs || logs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: var(--text-muted);">
                    Belum ada audit log
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${formatDate(log.created_at)}</td>
            <td><span class="status-badge">${formatEventType(log.event_type)}</span></td>
            <td>${log.actor || '-'}</td>
            <td style="color: var(--text-muted); font-size: 0.75rem;">${log.ip_address || '-'}</td>
        </tr>
    `).join('');
}

// =====================================================
// Utility Functions
// =====================================================

function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString('id-ID');
}

function formatMs(ms) {
    if (ms === null || ms === undefined) return '0ms';
    if (ms < 1000) return Math.round(ms) + 'ms';
    return (ms / 1000).toFixed(1) + 's';
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('id-ID', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatEventType(type) {
    if (!type) return '-';
    // Convert SNAKE_CASE to Title Case
    return type.toLowerCase()
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// =====================================================
// Auto Refresh
// =====================================================

function startAutoRefresh() {
    // Refresh every 30 seconds
    refreshInterval = setInterval(() => {
        loadAllData();
    }, 30000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

async function manualRefresh() {
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('spinning');

    await loadAllData();

    setTimeout(() => {
        btn.classList.remove('spinning');
    }, 500);
}

// =====================================================
// Initialize
// =====================================================

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();

    // Enter key to login
    document.getElementById('adminKeyInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') login();
    });
});
