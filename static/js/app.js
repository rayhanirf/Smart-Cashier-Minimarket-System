/* ============================================
   OWNER MONITORING SYSTEM - MAIN APP JS
   ============================================ */

// Configuration
const API_BASE = '/api';
let currentChart = {};
let authToken = null;

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', () => {
    checkAuthentication();
    initializeApp();
    registerServiceWorker();
    setInterval(updateDateTime, 1000);
});

function checkAuthentication() {
    const isLoggedIn = localStorage.getItem('auth_token');
    if (!isLoggedIn) {
        window.location.href = '/login-page';
    }
}

function initializeApp() {
    // Load dashboard data
    loadDashboardData();
    loadSalesData();
    loadInventoryData();
    
    // Set current date for report
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('reportDate').value = today;
    
    // Auto refresh setiap 30 detik
    setInterval(() => {
        const activeTab = document.querySelector('.tab-content.active').id;
        if (activeTab === 'dashboard') {
            loadDashboardData();
        } else if (activeTab === 'sales') {
            loadSalesData();
        } else if (activeTab === 'inventory') {
            loadInventoryData();
        }
    }, 30000);
}

function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/sw.js').catch(() => {
            console.log('Service Worker registration failed');
        });
    }
}

// ============ UI FUNCTIONS ============
function updateDateTime() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    document.getElementById('dateTime').textContent = now.toLocaleDateString('id-ID', options);
}

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Deactivate all buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    
    // Activate button
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Load data for selected tab
    if (tabName === 'dashboard') {
        loadDashboardData();
    } else if (tabName === 'sales') {
        loadSalesData();
    } else if (tabName === 'inventory') {
        loadInventoryData();
    }
}

function showLoading(show = true) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.add('active');
    } else {
        overlay.classList.remove('active');
    }
}

function formatCurrency(value) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(value);
}

function formatNumber(value) {
    return new Intl.NumberFormat('id-ID').format(value);
}

async function logout() {
    if (confirm('Apakah Anda yakin ingin logout?')) {
        try {
            await fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        } catch (error) {
            console.log('Logout error:', error);
        } finally {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('username');
            window.location.href = '/login-page';
        }
    }
}

// ============ API FUNCTIONS ============
async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        showLoading(true);
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`${API_BASE}${endpoint}`, options);
        
        if (response.status === 401) {
            // Unauthorized - redirect to login
            localStorage.removeItem('auth_token');
            window.location.href = '/login-page';
            return null;
        }

        const jsonData = await response.json();
        
        if (!response.ok) {
            console.error('API Error:', jsonData.message);
            return null;
        }

        return jsonData;
    } catch (error) {
        console.error('API Call Error:', error);
        alert('Error: ' + error.message);
        return null;
    } finally {
        showLoading(false);
    }
}

// ============ DASHBOARD TAB ============
async function loadDashboardData() {
    const data = await apiCall('/dashboard/summary');
    
    if (!data || !data.success) {
        console.error('Failed to load dashboard summary');
        return;
    }

    const summary = data.data;

    // Update summary cards
    document.getElementById('totalSales').textContent = formatCurrency(summary.total_sales);
    document.getElementById('totalTransactions').textContent = formatNumber(summary.total_transactions);
    document.getElementById('totalItems').textContent = formatNumber(summary.total_items_sold);
    document.getElementById('lowStock').textContent = summary.low_stock_products;

    // Load charts
    loadSalesChart();
    loadPaymentChart();
    loadLowStockProducts();
}

async function loadSalesChart() {
    const data = await apiCall('/sales/chart?days=7');
    
    if (!data || !data.success) return;

    const chartData = data.data;
    const ctx = document.getElementById('salesChart');
    
    if (!ctx) return;

    if (currentChart.sales) {
        currentChart.sales.destroy();
    }

    currentChart.sales = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.map(d => {
                const date = new Date(d.date);
                return date.toLocaleDateString('id-ID', { day: 'short', month: 'short' });
            }),
            datasets: [{
                label: 'Penjualan (Rp)',
                data: chartData.map(d => d.sales),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#667eea'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        font: { size: 12 }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return 'Rp ' + (value / 1000000).toFixed(1) + 'M';
                        }
                    }
                }
            }
        }
    });
}

async function loadPaymentChart() {
    const data = await apiCall('/payment/breakdown?days=7');
    
    if (!data || !data.success) return;

    const paymentData = data.data;
    const ctx = document.getElementById('paymentChart');
    
    if (!ctx) return;

    if (currentChart.payment) {
        currentChart.payment.destroy();
    }

    const colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b'];

    currentChart.payment = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: paymentData.map(p => p.method),
            datasets: [{
                data: paymentData.map(p => p.total),
                backgroundColor: colors.slice(0, paymentData.length),
                borderColor: 'white',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { size: 12 },
                        padding: 15
                    }
                }
            }
        }
    });
}

async function loadLowStockProducts() {
    const data = await apiCall('/products/low-stock?threshold=5');
    
    if (!data || !data.success) return;

    const products = data.data;
    const container = document.getElementById('lowStockList');

    if (products.length === 0) {
        container.innerHTML = '<p style="padding: 20px; text-align: center; color: #27ae60;">✅ Semua produk stok aman</p>';
        return;
    }

    let html = '<table><thead><tr><th>Produk</th><th>Kategori</th><th>Stok</th><th>Harga</th></tr></thead><tbody>';
    
    products.forEach(product => {
        const stockClass = product.stock === 0 ? 'badge-danger' : 'badge-warning';
        html += `
            <tr>
                <td><strong>${product.name}</strong></td>
                <td>${product.category || '-'}</td>
                <td><span class="badge ${stockClass}">${product.stock}</span></td>
                <td>${formatCurrency(product.price)}</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// ============ SALES TAB ============
async function loadSalesData() {
    const data = await apiCall('/sales/today');
    
    if (!data || !data.success) return;

    const transactions = data.data;
    const container = document.getElementById('salesList');

    if (transactions.length === 0) {
        container.innerHTML = '<p style="padding: 20px; text-align: center; color: #7f8c8d;">Belum ada transaksi hari ini</p>';
    } else {
        let html = '<table><thead><tr><th>Waktu</th><th>Jumlah</th><th>Item</th><th>Metode</th></tr></thead><tbody>';
        
        transactions.forEach(tx => {
            html += `
                <tr>
                    <td>${tx.time}</td>
                    <td><strong>${formatCurrency(tx.amount)}</strong></td>
                    <td>${tx.items} item</td>
                    <td>${tx.payment_method || '-'}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    }

    // Load top selling products
    loadTopSellingProducts();
}

async function loadTopSellingProducts() {
    const data = await apiCall('/products/top-selling?limit=10&days=7');
    
    if (!data || !data.success) return;

    const products = data.data;
    const container = document.getElementById('topProducts');

    if (products.length === 0) {
        container.innerHTML = '<p>Belum ada data penjualan</p>';
        return;
    }

    let html = '<table><thead><tr><th>Produk</th><th>Kategori</th><th>Terjual</th></tr></thead><tbody>';
    
    products.forEach((product, index) => {
        html += `
            <tr>
                <td><strong>${index + 1}. ${product.name}</strong></td>
                <td>${product.category || '-'}</td>
                <td>${formatNumber(product.sold)} pcs</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// ============ INVENTORY TAB ============
async function loadInventoryData() {
    const data = await apiCall('/inventory/summary');
    
    if (!data || !data.success) return;

    const inventory = data.data;

    // Load inventory chart
    loadInventoryChart(inventory);

    // Load inventory table
    const container = document.getElementById('inventoryList');
    let html = '<table><thead><tr><th>Kategori</th><th>Jumlah Produk</th><th>Total Stok</th></tr></thead><tbody>';
    
    inventory.forEach(item => {
        html += `
            <tr>
                <td><strong>${item.category}</strong></td>
                <td>${formatNumber(item.product_count)} produk</td>
                <td><strong>${formatNumber(item.total_stock)}</strong> unit</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function loadInventoryChart(inventoryData) {
    const ctx = document.getElementById('inventoryChart');
    
    if (!ctx) return;

    if (currentChart.inventory) {
        currentChart.inventory.destroy();
    }

    const colors = [
        '#667eea', '#764ba2', '#f093fb', '#4facfe', 
        '#43e97b', '#fa709a', '#fee140', '#30b0fe'
    ];

    currentChart.inventory = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: inventoryData.map(i => i.category),
            datasets: [{
                label: 'Total Stok',
                data: inventoryData.map(i => i.total_stock),
                backgroundColor: colors.slice(0, inventoryData.length),
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        font: { size: 12 }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

// ============ REPORTS TAB ============
async function loadDailyReport() {
    const dateInput = document.getElementById('reportDate').value;
    
    if (!dateInput) {
        alert('Pilih tanggal terlebih dahulu');
        return;
    }

    const data = await apiCall(`/reports/daily/${dateInput}`);
    
    if (!data || !data.success) {
        alert('Gagal memuat laporan');
        return;
    }

    const report = data.data;
    const reportContent = document.getElementById('reportContent');

    const paymentBreakdown = report.payment_breakdown.map(p => `
        <tr>
            <td>${p.method}</td>
            <td>${p.count} transaksi</td>
            <td>${formatCurrency(p.total)}</td>
        </tr>
    `).join('');

    const html = `
        <div class="section">
            <h3>Ringkasan Laporan - ${new Date(report.date).toLocaleDateString('id-ID')}</h3>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px;">
                <div style="background: #f0f4ff; padding: 15px; border-radius: 8px; text-align: center;">
                    <p style="color: #7f8c8d; font-size: 12px;">Total Penjualan</p>
                    <h3 style="color: #2c3e50; margin: 5px 0;">${formatCurrency(report.total_sales)}</h3>
                </div>
                <div style="background: #f0f4ff; padding: 15px; border-radius: 8px; text-align: center;">
                    <p style="color: #7f8c8d; font-size: 12px;">Transaksi</p>
                    <h3 style="color: #2c3e50; margin: 5px 0;">${report.total_transactions}</h3>
                </div>
                <div style="background: #f0f4ff; padding: 15px; border-radius: 8px; text-align: center;">
                    <p style="color: #7f8c8d; font-size: 12px;">Item Terjual</p>
                    <h3 style="color: #2c3e50; margin: 5px 0;">${report.total_items}</h3>
                </div>
            </div>

            <h4 style="margin-top: 20px; margin-bottom: 10px;">Breakdown Metode Pembayaran</h4>
            <table>
                <thead>
                    <tr>
                        <th>Metode</th>
                        <th>Jumlah</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${paymentBreakdown}
                </tbody>
            </table>
        </div>
    `;

    reportContent.innerHTML = html;
}

// ============ UTILITY FUNCTIONS ============
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

// ============ NETWORK STATUS ============
window.addEventListener('online', () => {
    console.log('Back online');
    loadDashboardData();
});

window.addEventListener('offline', () => {
    console.log('Offline mode');
});
