"""
OWNER MONITORING SYSTEM - INTEGRATED WITH KASIR
Dashboard untuk monitoring penjualan real-time dari kasir_ui_advanced.py
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime, timedelta, date
import logging
import os

# Inisialisasi Flask
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['JSON_AS_ASCII'] = False

# CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database
DB_PATH = 'kasir_data.db'

# ========================
# HELPER FUNCTIONS
# ========================

def get_db_connection():
    """Koneksi ke database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_items_from_json(items_json):
    """Parse items dari JSON string"""
    try:
        return json.loads(items_json) if items_json else {}
    except:
        return {}

# ========================
# ROUTES
# ========================

@app.route('/')
def index():
    """Halaman utama dashboard"""
    return render_template('index.html')

# ========================
# API ENDPOINTS
# ========================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok'}), 200

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    """Dashboard ringkasan"""
    try:
        today = date.today().isoformat()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hitung hari ini
        cursor.execute('''
            SELECT 
                COUNT(*) as trans_count,
                SUM(total) as total_sales,
                COUNT(DISTINCT DATE(timestamp)) as days_active
            FROM transactions
            WHERE DATE(timestamp) = ?
        ''', (today,))
        
        row = cursor.fetchone()
        total_trans = row['trans_count'] or 0
        total_sales = row['total_sales'] or 0
        
        # Hitung jumlah items
        cursor.execute('''
            SELECT items FROM transactions WHERE DATE(timestamp) = ?
        ''', (today,))
        
        total_items = 0
        for row in cursor.fetchall():
            items = parse_items_from_json(row['items'])
            for item_name, item_data in items.items():
                total_items += item_data.get('qty', 1)
        
        # Hitung 7 hari
        start_date = (date.today() - timedelta(days=6)).isoformat()
        cursor.execute('''
            SELECT SUM(total) as total FROM transactions
            WHERE DATE(timestamp) BETWEEN ? AND ?
        ''', (start_date, today))
        
        sales_7days = cursor.fetchone()['total'] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'date': today,
                'transactions_today': total_trans,
                'sales_today': float(total_sales),
                'items_today': total_items,
                'sales_7days': float(sales_7days),
                'avg_transaction': float(total_sales / total_trans) if total_trans > 0 else 0
            }
        }), 200
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/today', methods=['GET'])
def get_today_sales():
    """Transaksi hari ini"""
    try:
        today = date.today().isoformat()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, items, total, payment_method
            FROM transactions
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp DESC
        ''', (today,))
        
        transactions = []
        for row in cursor.fetchall():
            items = parse_items_from_json(row['items'])
            num_items = len(items)
            
            transactions.append({
                'id': row['id'],
                'time': row['timestamp'][11:16],
                'items_count': num_items,
                'total': float(row['total']),
                'payment': row['payment_method'],
                'items': items
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': transactions
        }), 200
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/chart-7days', methods=['GET'])
def chart_7days():
    """Grafik penjualan 7 hari"""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Data untuk setiap hari
        chart_data = []
        for i in range(7):
            current_date = end_date - timedelta(days=6-i)
            date_str = current_date.isoformat()
            
            cursor.execute('''
                SELECT COALESCE(SUM(total), 0) as daily_total, COUNT(*) as trans_count
                FROM transactions
                WHERE DATE(timestamp) = ?
            ''', (date_str,))
            
            row = cursor.fetchone()
            chart_data.append({
                'date': date_str,
                'sales': float(row['daily_total']),
                'transactions': row['trans_count']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': chart_data
        }), 200
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/payment-method', methods=['GET'])
def payment_method():
    """Breakdown metode pembayaran"""
    try:
        today = date.today().isoformat()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                payment_method,
                COUNT(*) as count,
                SUM(total) as total
            FROM transactions
            WHERE DATE(timestamp) = ?
            GROUP BY payment_method
        ''', (today,))
        
        methods = []
        for row in cursor.fetchall():
            methods.append({
                'method': row['payment_method'] or 'Unknown',
                'count': row['count'],
                'total': float(row['total'])
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': methods
        }), 200
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/top-products', methods=['GET'])
def top_products():
    """Produk terlaris hari ini"""
    try:
        today = date.today().isoformat()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT items FROM transactions
            WHERE DATE(timestamp) = ?
        ''', (today,))
        
        product_sales = {}
        for row in cursor.fetchall():
            items = parse_items_from_json(row['items'])
            for item_name, item_data in items.items():
                qty = item_data.get('qty', 1)
                price = item_data.get('price', 0)
                if item_name not in product_sales:
                    product_sales[item_name] = {'qty': 0, 'total': 0}
                product_sales[item_name]['qty'] += qty
                product_sales[item_name]['total'] += qty * price
        
        # Sort by qty
        sorted_products = sorted(
            product_sales.items(),
            key=lambda x: x[1]['qty'],
            reverse=True
        )[:10]
        
        data = [
            {
                'name': name,
                'qty': info['qty'],
                'total': float(info['total'])
            }
            for name, info in sorted_products
        ]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/add-transaction', methods=['POST'])
def add_transaction():
    """Tambah transaksi manual"""
    try:
        data = request.json
        
        items = data.get('items', {})
        total = data.get('total', 0)
        payment = data.get('payment_method', 'QRIS')
        
        if not items or total <= 0:
            return jsonify({'success': False, 'message': 'Data tidak valid'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        items_json = json.dumps(items)
        
        cursor.execute('''
            INSERT INTO transactions 
            (timestamp, items, total, payment_method, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, items_json, total, payment, 'COMPLETED'))
        
        conn.commit()
        trans_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"Transaksi #{trans_id} ditambahkan: Rp {total:,}")
        
        return jsonify({
            'success': True,
            'message': 'Transaksi berhasil ditambahkan',
            'transaction_id': trans_id
        }), 201
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

# ========================
# RUN
# ========================

if __name__ == '__main__':
    import socket
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("\n" + "="*70)
    print("🎯 OWNER MONITORING SYSTEM - INTEGRATED WITH KASIR")
    print("="*70)
    print(f"\n📊 Dashboard tersedia di:")
    print(f"   • http://localhost:5000")
    print(f"   • http://{local_ip}:5000")
    print(f"\n📡 API Endpoints:")
    print(f"   GET  /api/health - Status server")
    print(f"   GET  /api/dashboard - Ringkasan dashboard")
    print(f"   GET  /api/today - Transaksi hari ini")
    print(f"   GET  /api/chart-7days - Grafik 7 hari")
    print(f"   GET  /api/payment-method - Metode pembayaran")
    print(f"   GET  /api/top-products - Produk terlaris")
    print(f"   POST /api/add-transaction - Tambah transaksi")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
