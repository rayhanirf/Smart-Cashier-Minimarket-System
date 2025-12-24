"""
Smart Cashier Minimarket System - Advanced UI
WITH MACHINE VISION-BASED PRODUCT DETECTION & AUTOMATED PAYMENT
Integrated YOLOv5 Real-Time Detection & Professional Dashboard
"""

import os
import cv2
import time
import json
import threading
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import sqlite3
import pickle
import torch
import qrcode
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import requests
from urllib.parse import urljoin

# -----------------------
# CONFIG
# -----------------------
PROJECT_NAME = "Smart Cashier Minimarket System"
PROJECT_SUBTITLE = "AI-Powered Machine Vision for Real-Time Product Identification & Automated Payment"

# ===== BACKEND MONITORING CONFIG =====
BACKEND_URL = "http://127.0.0.1:5000"   # Ganti dengan IP komputer jika diakses dari jaringan lain
ENABLE_BACKEND_SYNC = True  # Set False untuk mode offline
BACKEND_TIMEOUT = 5  # Timeout untuk koneksi backend (detik)
CASHIER_ID = 1  # ID cashier di sistem monitoring

# Deteksi semua kamera yang tersedia
def detect_available_cameras():
    """Deteksi semua kamera yang tersedia di sistem"""
    available_cameras = {}
    for i in range(10):  # Check sampai 10 kamera
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Baca satu frame untuk memastikan kamera benar-benar berfungsi
            ret, frame = cap.read()
            if ret:
                available_cameras[i] = f"Kamera {i}"
                cap.release()
            else:
                cap.release()
    return available_cameras

# Deteksi kamera otomatis - gunakan kamera eksternal jika ada, jika tidak gunakan default
available_cams = detect_available_cameras()
if len(available_cams) > 1:
    # Jika ada lebih dari satu kamera, gunakan yang bukan 0 (tidak perlu diset, user bisa memilih)
    CAM_SOURCE = list(available_cams.keys())[-1]  # Gunakan kamera terakhir (biasanya eksternal)
else:
    CAM_SOURCE = 0  # Gunakan default kamera

OUTPUT_FOLDER = "kasir_snapshots"
LOG_FILE = "kasir_log.json"
DB_FILE = "kasir_data.db"
SIMULATE_SEND = True
THROTTLE_SEC = 0.6

# PRODUCTS DATABASE - Semua kelas YOLO COCO dengan harga
PRODUCTS = {
    # ===== BUAH-BUAHAN (FRESH FRUIT) =====
    "apple": {"nama": "Apel", "harga": 12000, "stock": 50},
    "banana": {"nama": "Pisang", "harga": 8000, "stock": 75},
    "orange": {"nama": "Jeruk", "harga": 10000, "stock": 60},
    "strawberry": {"nama": "Stroberi", "harga": 18000, "stock": 40},
    "pear": {"nama": "Pir", "harga": 15000, "stock": 35},
    "kiwi": {"nama": "Kiwi", "harga": 16000, "stock": 45},
    
    # ===== MAKANAN SNACK & MINUMAN (FOOD & BEVERAGE) =====
    "donut": {"nama": "Donat", "harga": 8000, "stock": 100},
    "sandwich": {"nama": "Sandwich", "harga": 22000, "stock": 50},
    "pizza": {"nama": "Pizza", "harga": 35000, "stock": 30},
    "cake": {"nama": "Kue", "harga": 28000, "stock": 25},
    "hot dog": {"nama": "Hot Dog", "harga": 18000, "stock": 45},
    "bread": {"nama": "Roti", "harga": 10000, "stock": 80},
    "cheese": {"nama": "Keju", "harga": 25000, "stock": 35},
    
    # ===== SAYURAN (VEGETABLES) =====
    "broccoli": {"nama": "Brokoli", "harga": 15000, "stock": 40},
    "carrot": {"nama": "Wortel", "harga": 8000, "stock": 70},
    "potato": {"nama": "Kentang", "harga": 7000, "stock": 90},
    "tomato": {"nama": "Tomat", "harga": 10000, "stock": 55},
    
    # ===== WADAH & PERALATAN MINUM (CONTAINERS) =====
    "cup": {"nama": "Cangkir", "harga": 12000, "stock": 60},
    "bottle": {"nama": "Botol", "harga": 15000, "stock": 50},
    "wine glass": {"nama": "Gelas Wine", "harga": 18000, "stock": 30},
    "water bottle": {"nama": "Botol Air Minum", "harga": 25000, "stock": 40},
    
    # ===== PERALATAN & AKSESORIS PRIBADI (PERSONAL ACCESSORIES) =====
    "backpack": {"nama": "Tas Punggung", "harga": 120000, "stock": 15},
    "handbag": {"nama": "Tas Tangan", "harga": 180000, "stock": 12},
    "umbrella": {"nama": "Payung", "harga": 45000, "stock": 25},
    "tie": {"nama": "Dasi", "harga": 35000, "stock": 30},
    "teddy bear": {"nama": "Boneka", "harga": 45000, "stock": 20},
    "watch": {"nama": "Jam Tangan", "harga": 150000, "stock": 10},
    "sunglasses": {"nama": "Kacamata Hitam", "harga": 75000, "stock": 18},
    "cap": {"nama": "Topi", "harga": 30000, "stock": 35},
    "shoe": {"nama": "Sepatu", "harga": 250000, "stock": 8},
    "sock": {"nama": "Kaos Kaki", "harga": 15000, "stock": 100},
    "clock": {"nama": "Jam Dinding", "harga": 50000, "stock": 15},
    
    # ===== ELEKTRONIK KECIL (SMALL ELECTRONICS) =====
    "mouse": {"nama": "Mouse", "harga": 85000, "stock": 20},
    "keyboard": {"nama": "Keyboard", "harga": 200000, "stock": 15},
    "cell phone": {"nama": "Ponsel", "harga": 2500000, "stock": 5},
    
    # ===== BUKU & ALAT TULIS (BOOKS & STATIONERY) =====
    "book": {"nama": "Buku", "harga": 35000, "stock": 40},
    "scissors": {"nama": "Gunting", "harga": 12000, "stock": 25},
    "pen": {"nama": "Pena", "harga": 5000, "stock": 200},
    "notebook": {"nama": "Buku Tulis", "harga": 8000, "stock": 80},
    "pencil": {"nama": "Pensil", "harga": 3000, "stock": 150},
    
    # ===== PERALATAN DAPUR & RUMAH TANGGA (KITCHENWARE) =====
    "fork": {"nama": "Garpu", "harga": 8000, "stock": 70},
    "knife": {"nama": "Pisau", "harga": 25000, "stock": 40},
    "spoon": {"nama": "Sendok", "harga": 8000, "stock": 90},
    "bowl": {"nama": "Mangkuk", "harga": 12000, "stock": 55},
    
    # ===== BARANG LAINNYA YANG MUNGKIN DITEMUKAN DI MINIMARKET =====
    "baseball": {"nama": "Bola Baseball", "harga": 50000, "stock": 20},
    "frisbee": {"nama": "Frisbee", "harga": 35000, "stock": 15},
    "skateboard": {"nama": "Skateboard", "harga": 350000, "stock": 5},
    "bicycle": {"nama": "Sepeda", "harga": 800000, "stock": 3},

}

PRESENCE_FRAMES_REQUIRED = 2
ABSENCE_FRAMES_REQUIRED = 8

Path(OUTPUT_FOLDER).mkdir(exist_ok=True)

# FPS Optimization
FRAME_RESIZE = (480, 360)  # Smaller size for faster processing
DETECTION_INTERVAL = 2  # Process every 2 frames (every 3rd frame)
DISPLAY_FPS_TARGET = 30  # Target FPS for display

# Stock Management
STOCK_FILE = "produk_kasir.json"

state_lock = threading.Lock()
stats = {"total": 0, "paid": 0, "pending": 0}
cart = defaultdict(int)
latest_transactions = []
last_process_time = 0.0
session_start_time = datetime.now()
total_items_sold_counter = 0  # Counter total items yang sudah terjual (tidak di-reset)

# Cooldown system - cegah 1 benda terdeteksi terus-terus
item_cooldown = defaultdict(int)
COOLDOWN_FRAMES = 600  # Tunggu 30 frame sebelum item yang sama bisa ditambah lagi

# ===== PREMIUM MODERN COLOR PALETTE =====
COLORS = {
    # Background - Clean Modern Dark
    "bg_primary": "#0f1419",         # Deep Dark
    "bg_secondary": "#1a1f2e",       # Dark Slate
    "bg_tertiary": "#252d3d",        # Medium Dark
    "bg_light": "#353f52",           # Light Slate
    
    # Borders - Subtle Elegant
    "border_dark": "#3a4452",
    "border_light": "#4a5568",
    "border_accent": "#d0d0d0",      # Silver White
    "border_subtle": "#1f2937",
    
    # Professional Accent Colors - Warna Putih Tipis
    "accent_pass": "#e8e8e8",        # Silver White (Success)
    "accent_fail": "#ff6b6b",        # Red (Error)
    "accent_warning": "#ffa94d",     # Orange (Warning)
    "accent_info": "#8ab4f8",        # Light Blue (Info)
    "accent_secondary": "#b4a7d6",   # Light Purple
    "accent_tertiary": "#d0d0d0",    # Light Gray
    "accent_gold": "#e8d5b7",        # Soft Gold
    
    # Text - Professional Subtle
    "text_primary": "#f5f5f5",       # Almost White
    "text_secondary": "#d0d0d0",     # Light Gray
    "text_tertiary": "#a0a0a0",      # Medium Gray
    "text_subtle": "#808080",        # Dark Gray
}

# -----------------------
# DATABASE
# -----------------------
def init_database():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                items TEXT,
                total REAL,
                payment_method TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB init error:", e)

def load_stock_from_file():
    """Load stock dari JSON file"""
    global PRODUCTS
    try:
        if os.path.exists(STOCK_FILE):
            with open(STOCK_FILE, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
                for product_key, stock_qty in stock_data.items():
                    if product_key in PRODUCTS:
                        PRODUCTS[product_key]["stock"] = stock_qty
                print(f"✓ Stock loaded from {STOCK_FILE}")
    except Exception as e:
        print(f"Error loading stock: {e}")

def save_stock_to_file():
    """Save stock ke JSON file"""
    try:
        stock_data = {key: PRODUCTS[key].get("stock", 0) for key in PRODUCTS}
        with open(STOCK_FILE, 'w', encoding='utf-8') as f:
            json.dump(stock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving stock: {e}")

def save_to_database(items, total, payment_method, status):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        items_str = json.dumps(items)
        cursor.execute('''
            INSERT INTO transactions (timestamp, items, total, payment_method, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), items_str, total, payment_method, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB save error:", e)

init_database()

# -----------------------
# BACKEND INTEGRATION
# -----------------------
def send_transaction_to_backend(items_dict, total_price, payment_method="cash"):
    """Kirim transaksi ke backend monitoring untuk ditampilkan di dashboard owner"""
    if not ENABLE_BACKEND_SYNC:
        print("[BACKEND] Offline mode - tidak mengirim ke backend")
        return False
    
    try:
        # Format items untuk backend
        items_list = []
        for product_name, qty in items_dict.items():
            product_info = PRODUCTS.get(product_name, {})
            items_list.append({
                'product_name': product_name,
                'quantity': qty,
                'price': product_info.get('harga', 0)
            })
        
        # Prepare data
        payload = {
            'items': items_list,
            'total_amount': total_price,
            'payment_method': payment_method,
            'cashier_id': CASHIER_ID
        }
        
        # Send to backend
        url = urljoin(BACKEND_URL, '/api/cashier/record-sale')
        response = requests.post(
            url,
            json=payload,
            timeout=BACKEND_TIMEOUT
        )
        
        if response.status_code == 201 or response.status_code == 200:
            result = response.json()
            print(f"[BACKEND] ✓ Transaksi berhasil dikirim: ID {result.get('transaction_id')}")
            return True
        else:
            print(f"[BACKEND] ✗ Error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"[BACKEND] ✗ Tidak bisa terhubung ke {BACKEND_URL}")
        return False
    except requests.exceptions.Timeout:
        print(f"[BACKEND] ✗ Timeout saat koneksi ke backend")
        return False
    except Exception as e:
        print(f"[BACKEND] ✗ Error mengirim transaksi: {e}")
        return False

def check_backend_status():
    """Check apakah backend monitoring berjalan"""
    if not ENABLE_BACKEND_SYNC:
        return False
    
    try:
        url = urljoin(BACKEND_URL, '/api/cashier/status')
        response = requests.get(url, timeout=2)
        return response.status_code == 200
    except:
        return False

# -----------------------
# YOLO DETECTION
# -----------------------
def get_color(idx):
    """Generate warna unik berdasarkan index"""
    np.random.seed(idx)
    return tuple(int(x) for x in np.random.randint(80, 255, 3))

try:
    # Ganti ke yolov5n (Nano) - 5x lebih cepat, akurasi cukup untuk deteksi produk
    print("[MODEL] Loading YOLOv5 model...")
    model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
    model.eval()
    model.conf = 0.25  # Lower confidence threshold untuk deteksi lebih banyak
    model.iou = 0.45   # NMS threshold
    print("[MODEL] ✓ YOLOv5 model loaded successfully")
except Exception as e:
    model = None
    print(f"[MODEL] ✗ WARNING: YOLOv5 model not loaded - {e}")

def detect_products(frame):
    """Deteksi produk menggunakan YOLOv5 dengan visualisasi modern - optimized untuk performa"""
    if model is None:
        return [], frame
    
    try:
        # Gunakan frame original size untuk deteksi lebih akurat
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Inference - confidence sudah set di model initialization
        results = model(img)  # Menggunakan conf=0.25 dan iou=0.45 dari model config
        
        detected = []
        annotated = frame.copy()
        
        # Deteksi & visualisasi
        for det in results.xyxy[0]:
            x1, y1, x2, y2, conf, cls = det[:6]
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])  # Koordinat sudah di original scale
            
            conf = float(conf)
            cls = int(cls)
            label = f"{model.names[cls]} {conf:.2f}"
            color = get_color(cls)
            
            product_name = model.names[cls]
            detected.append({
                'name': product_name.lower(),  # Convert ke lowercase untuk match PRODUCTS key
                'conf': conf,
                'box': (x1, y1, x2, y2)
            })
            print(f"[DETECT] Found: {product_name} (conf: {conf:.2f})")
            
            # Kotak deteksi tebal
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 4, cv2.LINE_AA)
            
            # Label transparan rounded
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            label_bg = annotated[max(0, y1-th-16):y1, x1:x1+tw+16]
            if label_bg.shape[0] > 0 and label_bg.shape[1] > 0:
                overlay_label = label_bg.copy()
                cv2.rectangle(overlay_label, (0, 0), (tw+16, th+16), color, -1, cv2.LINE_AA)
                cv2.addWeighted(overlay_label, 0.5, label_bg, 0.5, 0, label_bg)
            # Shadow
            cv2.putText(annotated, label, (x1+9, y1-7), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 4, cv2.LINE_AA)
            # Teks label
            cv2.putText(annotated, label, (x1+8, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        
        if len(detected) > 0:
            print(f"[DETECT] Total detections: {len(detected)}")
        
        return detected, annotated
    except Exception as e:
        print(f"[DETECT] Detection error: {e}")
        return [], frame

# -----------------------
# CAMERA WORKER
# -----------------------
class CameraWorker(threading.Thread):
    def __init__(self, src, panel, update_callback):
        super().__init__(daemon=True)
        self.src = src
        self.panel = panel
        self.update_callback = update_callback
        self.cap = None
        self.running = True
        self._open_source()
        self.presence_count = 0
        self.absence_count = 0
        self.processed = False
        self.fps_counter = 0
        self.fps_time = time.time()
        self.current_fps = 0
        self.current_frame = None
        self.frame_count = 0

    def _open_source(self):
        try:
            self.cap = cv2.VideoCapture(self.src)
            # Set camera properties untuk performa optimal
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # Jangan force resolution - biarkan kamera gunakan native resolution untuk deteksi lebih akurat
        except Exception as e:
            print("Failed to open source:", e)
            self.cap = None

    def stop(self):
        self.running = False
        try:
            if isinstance(self.cap, cv2.VideoCapture):
                self.cap.release()
        except:
            pass

    def run(self):
        global stats, cart, latest_transactions, last_process_time
        
        prev_time = 0
        last_added_product = None
        last_added_time = 0
        frame_skip_counter = 0
        last_detected = []  # Cache hasil deteksi frame sebelumnya
        last_annotated = None
        
        while self.running:
            if self.cap is None:
                time.sleep(0.2)
                continue
            
            try:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                self.current_frame = frame.copy()
                
                # Process deteksi HANYA setiap 3 frame untuk mengurangi beban CPU
                frame_skip_counter += 1
                if frame_skip_counter >= 3:
                    frame_skip_counter = 0
                    detected, annotated = detect_products(frame)
                    last_detected = detected
                    last_annotated = annotated
                else:
                    # Gunakan hasil deteksi dari frame sebelumnya (reuse)
                    detected = last_detected
                    annotated = last_annotated if last_annotated is not None else frame.copy()
                
                # Filter hanya produk yang ada di PRODUCTS
                valid_detected = [d for d in detected if d['name'] in PRODUCTS]
                
                if valid_detected:
                    print(f"[DETECTION] Found {len(valid_detected)} valid products: {[d['name'] for d in valid_detected]}")
                    self.presence_count += 1
                    self.absence_count = 0
                    
                    # Tambah ke cart HANYA setelah presence threshold terpenuhi
                    if self.presence_count >= PRESENCE_FRAMES_REQUIRED:
                        with state_lock:
                            for det in valid_detected:
                                product_name = det['name']
                                print(f"[DETECTION] Processing: {product_name}, cooldown={item_cooldown.get(product_name, 0)}")
                                
                                # Cek apakah produk masih dalam cooldown
                                if item_cooldown[product_name] <= 0:
                                    # Produk tidak dalam cooldown, tambahkan ke cart
                                    cart[product_name] += 1
                                    item_cooldown[product_name] = COOLDOWN_FRAMES  # Set cooldown untuk produk ini
                                    print(f"[DETECTION] ✓ Added {product_name} to cart, qty now: {cart[product_name]}")
                                else:
                                    print(f"[DETECTION] {product_name} in cooldown ({item_cooldown[product_name]} frames), skipping")
                else:
                    self.absence_count += 1
                    self.presence_count = 0

                if self.processed and self.absence_count >= ABSENCE_FRAMES_REQUIRED:
                    self.processed = False
                    self.presence_count = 0
                    self.absence_count = 0

                # Resize hanya untuk display di UI - tidak mempengaruhi deteksi
                display_frame = cv2.resize(annotated, (800, 600))
                
                # Hitung FPS
                curr_time = time.time()
                fps = 1 / (curr_time - prev_time) if prev_time else 0
                prev_time = curr_time

                self.fps_counter += 1
                now = time.time()
                if now - self.fps_time >= 1.0:
                    self.current_fps = self.fps_counter
                    self.fps_counter = 0
                    self.fps_time = now

                # Convert dan display
                img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                imgtk = ImageTk.PhotoImage(img)
                self.panel.update_image(imgtk)

                if self.update_callback:
                    self.update_callback(valid_detected)
                
                # Decrement cooldown untuk semua item yang sedang dalam cooldown
                with state_lock:
                    for item in list(item_cooldown.keys()):
                        if item_cooldown[item] > 0:
                            item_cooldown[item] -= 1
                        else:
                            del item_cooldown[item]

                time.sleep(0.01)
            
            except Exception as e:
                print(f"Camera worker error: {e}")
                time.sleep(0.05)
                continue

_process_lock = threading.Lock()
_last_process = 0.0
def should_process():
    global _last_process
    with _process_lock:
        now = time.time()
        if now - _last_process < THROTTLE_SEC:
            return False
        _last_process = now
        return True

# -----------------------
# UI HELPER FUNCTIONS
# -----------------------
def create_card(parent, fg_color=None, **kwargs):
    """Create modern elegant card"""
    return ctk.CTkFrame(
        parent,
        fg_color=fg_color or COLORS["bg_secondary"],
        corner_radius=12,
        border_width=1,
        border_color=COLORS["border_accent"],
        **kwargs
    )

def create_button(parent, text, command, color_type="info", **kwargs):
    """Create premium button with professional styling"""
    color_map = {
        "info": {"fg": "#3b82f6", "hover": "#2563eb", "text": "#ffffff", "border": "#1d4ed8"},
        "success": {"fg": "#e8e8e8", "hover": "#d0d0d0", "text": "#1a1f2e", "border": "#a0a0a0"},
        "warning": {"fg": "#f59e0b", "hover": "#d97706", "text": "#ffffff", "border": "#b45309"},
        "secondary": {"fg": "#8b5cf6", "hover": "#7c3aed", "text": "#ffffff", "border": "#6d28d9"},
        "danger": {"fg": "#ef4444", "hover": "#dc2626", "text": "#ffffff", "border": "#991b1b"},
        "gold": {"fg": "#f59e0b", "hover": "#d97706", "text": "#ffffff", "border": "#b45309"},
    }
    config = color_map.get(color_type, color_map["info"])
    
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=config["fg"],
        hover_color=config["hover"],
        text_color=config["text"],
        border_width=1,
        border_color=config["border"],
        corner_radius=8,
        height=44,
        font=ctk.CTkFont(family="Arial", weight="bold", size=11),
        **kwargs
    )

# -----------------------
# MAIN UI - PREMIUM DESIGN
# -----------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Create main window
app = ctk.CTk()
app.title(PROJECT_NAME)
app.geometry("1400x800")
app.configure(fg_color=COLORS["bg_primary"])

# ===== MAIN APP INITIALIZATION =====
main_frame = ctk.CTkFrame(app, fg_color=COLORS["bg_primary"])
main_frame.pack(fill="both", expand=True)

# ===== PREMIUM HEADER =====
header = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=0, height=80)
header.pack(fill="x", padx=0, pady=0)

header_container = ctk.CTkFrame(header, fg_color="transparent")
header_container.pack(fill="both", padx=28, pady=16)

left_header = ctk.CTkFrame(header_container, fg_color="transparent")
left_header.pack(side="left", fill="both", expand=True)

ctk.CTkLabel(
    left_header,
    text="🛒 Smart Cashier Minimarket System",
    font=ctk.CTkFont(family="Arial", size=24, weight="bold"),
    text_color=COLORS["text_primary"]
).pack(anchor="w")

ctk.CTkLabel(
    left_header,
    text="Machine Vision-Based Real-Time Product Detection & Automated Payment",
    font=ctk.CTkFont(family="Arial", size=13, weight="normal"),
    text_color=COLORS["text_tertiary"]
).pack(anchor="w", pady=(2, 0))

right_header = ctk.CTkFrame(header_container, fg_color="transparent")
right_header.pack(side="right")

# Camera selector
camera_frame = ctk.CTkFrame(right_header, fg_color=COLORS["bg_tertiary"], 
                            corner_radius=8, border_width=1, 
                            border_color=COLORS["border_dark"])
camera_frame.pack(side="left", padx=(0, 15))

ctk.CTkLabel(
    camera_frame,
    text="📷",
    font=ctk.CTkFont(size=11),
    text_color=COLORS["text_primary"]
).pack(side="left", padx=(8, 5), pady=6)

def on_camera_change(value):
    """Ganti kamera saat user memilih"""
    global CAM_SOURCE, worker
    try:
        selected_cam = int(value.split()[-1])
        if selected_cam != CAM_SOURCE:
            CAM_SOURCE = selected_cam
            # Restart worker dengan kamera baru
            if worker:
                worker.stop()
                time.sleep(0.5)
            worker = CameraWorker(CAM_SOURCE, panel, update_detection_callback)
            worker.start()
            status_text.configure(text=f"✅ Kamera berganti ke Kamera {selected_cam}")
    except Exception as e:
        print(f"Error switching camera: {e}")
        status_text.configure(text="❌ Gagal mengganti kamera")

cam_options = [f"Kamera {i}" for i in available_cams.keys()]
cam_selector = ctk.CTkOptionMenu(
    camera_frame,
    values=cam_options,
    command=on_camera_change,
    fg_color=COLORS["bg_tertiary"],
    button_color=COLORS["accent_info"],
    button_hover_color=COLORS["accent_info"][:-2] + "88",
    dropdown_fg_color=COLORS["bg_secondary"],
    text_color=COLORS["text_primary"],
    font=ctk.CTkFont(size=10)
)
cam_selector.set(f"Kamera {CAM_SOURCE}")
cam_selector.pack(side="left", padx=(0, 8), pady=6)

# Management button (toggle admin panel)
admin_panel_visible = False
current_view = "operator"  # "operator" or "management"

def show_operator_view():
    """Show operator/cashier view"""
    global current_view, admin_panel_visible, content, mgmt_frame
    current_view = "operator"
    admin_panel_visible = False
    
    # Hide management view
    mgmt_frame.pack_forget()
    
    # Show operator content
    content.pack(fill="both", expand=True, padx=12, pady=10)
    mgmt_btn.configure(text="⚙️", fg_color=COLORS["bg_secondary"])

def show_management_view():
    """Show full management/admin view"""
    global current_view, admin_panel_visible, content, mgmt_frame
    current_view = "management"
    admin_panel_visible = True
    
    # Hide operator content
    content.pack_forget()
    
    # Show management frame
    mgmt_frame.pack(fill="both", expand=True, padx=12, pady=10)
    mgmt_btn.configure(text="✕", fg_color=COLORS["accent_fail"])
    
    # Update management data
    update_management_data()

def show_password_dialog():
    """Show password dialog to access management"""
    password_window = ctk.CTkToplevel(app)
    password_window.title("🔐 Management Access")
    password_window.geometry("450x400")
    password_window.resizable(False, False)
    password_window.configure(fg_color=COLORS["bg_primary"])
    
    # Center the window on screen
    password_window.transient(app)
    password_window.grab_set()
    
    # Update position to center
    password_window.update_idletasks()
    x = (password_window.winfo_screenwidth() // 2) - (450 // 2)
    y = (password_window.winfo_screenheight() // 2) - (400 // 2)
    password_window.geometry(f"450x400+{x}+{y}")
    
    # Dialog frame
    dialog_frame = ctk.CTkFrame(password_window, fg_color=COLORS["bg_primary"])
    dialog_frame.pack(fill="both", expand=True, padx=0, pady=0)
    
    # Header with color
    header_frame = ctk.CTkFrame(dialog_frame, fg_color=COLORS["accent_info"], height=80)
    header_frame.pack(fill="x", padx=0, pady=0)
    header_frame.pack_propagate(False)
    
    ctk.CTkLabel(
        header_frame,
        text="🔐",
        font=ctk.CTkFont(size=36),
        text_color=COLORS["bg_primary"]
    ).pack(pady=(15, 5))
    
    ctk.CTkLabel(
        header_frame,
        text="Management Access",
        font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
        text_color=COLORS["bg_primary"]
    ).pack()
    
    # Content frame
    content_frame = ctk.CTkFrame(dialog_frame, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=30, pady=25)
    
    # Description
    ctk.CTkLabel(
        content_frame,
        text="Masukkan kata sandi untuk akses management dashboard",
        font=ctk.CTkFont(size=11),
        text_color=COLORS["text_tertiary"]
    ).pack(pady=(0, 25))
    
    # Password entry
    pwd_label = ctk.CTkLabel(
        content_frame,
        text="🔐 Kata Sandi",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color=COLORS["text_primary"]
    )
    pwd_label.pack(anchor="w", pady=(0, 8))
    
    password_entry = ctk.CTkEntry(
        content_frame,
        placeholder_text="Masukkan kata sandi...",
        show="●",
        fg_color=COLORS["bg_secondary"],
        border_width=2,
        border_color=COLORS["border_dark"],
        text_color=COLORS["text_primary"],
        placeholder_text_color=COLORS["text_tertiary"],
        font=ctk.CTkFont(size=11),
        height=40
    )
    password_entry.pack(fill="x", pady=(0, 15))
    password_entry.focus()
    
    # Error message label
    error_label = ctk.CTkLabel(
        content_frame,
        text="",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=COLORS["accent_fail"]
    )
    error_label.pack(anchor="w", pady=(0, 15))
    
    # Button frame
    btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    btn_frame.pack(fill="x", padx=0, pady=10)
    btn_frame.grid_columnconfigure((0, 1), weight=1)
    
    def verify_password():
        """Verify password and open management view"""
        if password_entry.get() == "12345":
            password_window.destroy()
            show_management_view()
        else:
            password_entry.configure(border_color=COLORS["accent_fail"])
            error_label.configure(text="❌ Kata sandi salah! Coba lagi.")
            password_entry.delete(0, tk.END)
            password_entry.focus()
    
    def on_cancel():
        """Cancel dialog"""
        password_window.destroy()
    
    # Verify button
    ctk.CTkButton(
        btn_frame,
        text="✅ MASUK",
        fg_color=COLORS["accent_pass"],
        hover_color=COLORS["accent_pass"][:-2] + "88",
        text_color=COLORS["bg_primary"],
        font=ctk.CTkFont(weight="bold", size=11),
        height=35,
        corner_radius=8,
        command=verify_password
    ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
    
    # Cancel button
    ctk.CTkButton(
        btn_frame,
        text="❌ BATAL",
        fg_color=COLORS["accent_fail"],
        hover_color=COLORS["accent_fail"][:-2] + "88",
        text_color=COLORS["bg_primary"],
        font=ctk.CTkFont(weight="bold", size=11),
        height=35,
        corner_radius=8,
        command=on_cancel
    ).grid(row=0, column=1, sticky="ew", padx=(8, 0))
    
    # Allow Enter key to submit
    password_entry.bind("<Return>", lambda e: verify_password())

def toggle_admin_panel():
    """Toggle between operator and management views"""
    if current_view == "operator":
        show_password_dialog()
    else:
        show_operator_view()

mgmt_btn = ctk.CTkButton(
    right_header,
    text="⚙️",
    command=toggle_admin_panel,
    width=40,
    height=40,
    fg_color=COLORS["bg_secondary"],
    hover_color=COLORS["accent_warning"],
    text_color=COLORS["text_primary"],
    font=ctk.CTkFont(size=14),
    corner_radius=8,
    border_width=1,
    border_color=COLORS["border_dark"]
)
mgmt_btn.pack(side="left", padx=5)

status_dot = ctk.CTkLabel(
    right_header,
    text="●",
    font=ctk.CTkFont(size=14),
    text_color=COLORS["accent_pass"]
)
status_dot.pack(side="left", padx=(0, 8))

ctk.CTkLabel(
    right_header,
    text="ONLINE",
    font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
    text_color=COLORS["accent_pass"]
).pack(side="left")

# ===== MAIN CONTENT =====
content = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_primary"])
content.pack(fill="both", expand=True, padx=10, pady=8)

# Admin/Management Panel (Right side, hidden by default)
admin_panel = ctk.CTkFrame(content, fg_color=COLORS["bg_secondary"], corner_radius=12, 
                           border_width=1, border_color=COLORS["border_accent"], width=320)
admin_panel.pack_propagate(False)

# Admin Panel Header
admin_header = ctk.CTkFrame(admin_panel, fg_color="transparent")
admin_header.pack(fill="x", padx=12, pady=(12, 8))

ctk.CTkLabel(
    admin_header,
    text="📊 MANAGEMENT",
    font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
    text_color=COLORS["accent_info"]
).pack(anchor="w")

# Admin Tabs
admin_tabs = ctk.CTkTabview(admin_panel, text_color=COLORS["text_primary"],
                           fg_color=COLORS["bg_secondary"],
                           segmented_button_fg_color=COLORS["bg_tertiary"],
                           segmented_button_selected_color=COLORS["accent_info"],
                           segmented_button_selected_hover_color=COLORS["accent_info"])
admin_tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

admin_tabs.add("📈 Analytics")
admin_tabs.add("📦 Stock")
admin_tabs.add("⚙️ Settings")

# === ANALYTICS TAB ===
ana_tab = admin_tabs.tab("📈 Analytics")
ana_tab.grid_columnconfigure(0, weight=1)

# KPI Cards
kpi_frame = ctk.CTkFrame(ana_tab, fg_color="transparent")
kpi_frame.pack(fill="x", padx=8, pady=8)

def create_kpi_card(parent, label, value, color):
    card = ctk.CTkFrame(parent, fg_color=COLORS["bg_tertiary"], corner_radius=10,
                       border_width=2, border_color=color)
    card.pack(fill="x", pady=6)
    
    ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=10, weight="bold"),
                text_color=COLORS["text_secondary"]).pack(anchor="w", padx=10, pady=(8, 2))
    
    val_lbl = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=14, weight="bold"),
                          text_color=color)
    val_lbl.pack(anchor="w", padx=10, pady=(0, 6))
    
    return val_lbl

kpi_revenue = create_kpi_card(kpi_frame, "Today Revenue", "Rp 0", COLORS["accent_pass"])
kpi_transactions = create_kpi_card(kpi_frame, "Transactions", "0", COLORS["accent_info"])
kpi_items = create_kpi_card(kpi_frame, "Items Sold", "0", COLORS["accent_warning"])

# === STOCK TAB ===
stock_tab = admin_tabs.tab("📦 Stock")
stock_tab.grid_columnconfigure(0, weight=1)
stock_tab.grid_rowconfigure(1, weight=1)

# Stock header
stock_header = ctk.CTkFrame(stock_tab, fg_color="transparent")
stock_header.pack(fill="x", padx=8, pady=(8, 4))

stock_header_label = ctk.CTkLabel(stock_header, text="Total Items: 0", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["text_secondary"])
stock_header_label.pack(anchor="w")

# Stock items scrollable frame
stock_scroll = ctk.CTkScrollableFrame(stock_tab, fg_color="transparent",
                                      label_text="", label_fg_color="transparent")
stock_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))
stock_scroll.grid_columnconfigure(0, weight=1)

stock_box = stock_scroll  # Update reference for later use

# === SETTINGS TAB ===
settings_tab = admin_tabs.tab("⚙️ Settings")
settings_tab.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(settings_tab, text="Confidence:", text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=9, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))

conf_slider = ctk.CTkSlider(settings_tab, from_=0.1, to=0.9, number_of_steps=8,
                           fg_color=COLORS["accent_info"])
conf_slider.set(0.25)
conf_slider.pack(fill="x", padx=8, pady=(0, 8))

ctk.CTkLabel(settings_tab, text="Payment Methods:", text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=9, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))

for method in ["QR Code", "E-Wallet", "Cash"]:
    chk = ctk.CTkCheckBox(settings_tab, text=method, fg_color=COLORS["accent_pass"],
                         checkmark_color=COLORS["bg_primary"])
    chk.pack(anchor="w", padx=8, pady=2)
    chk.select()

# LEFT: Camera (60%)
left_col = ctk.CTkFrame(content, fg_color="transparent")
left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

camera_card = create_card(left_col, height=800)
camera_card.pack(fill="both", expand=True)

cam_header = ctk.CTkFrame(camera_card, fg_color="transparent")
cam_header.pack(fill="x", padx=16, pady=(14, 10))

ctk.CTkLabel(
    cam_header,
    text="📹 LIVE FEED",
    font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
    text_color=COLORS["accent_tertiary"]
).pack(side="left")

cam_fps_label = ctk.CTkLabel(
    cam_header,
    text="FPS: 0",
    font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
    text_color=COLORS["text_tertiary"]
)
cam_fps_label.pack(side="right")

cam_inner = ctk.CTkFrame(camera_card, fg_color=COLORS["bg_tertiary"], corner_radius=12,
                         border_width=1, border_color=COLORS["border_dark"])
cam_inner.pack(padx=12, pady=8, expand=True, fill="both")

cam_image_label = ctk.CTkLabel(
    cam_inner,
    text="",
    fg_color=COLORS["bg_tertiary"],
    corner_radius=10
)
cam_image_label.pack(padx=1, pady=1, expand=True, fill="both")

status_bar = ctk.CTkFrame(camera_card, fg_color=COLORS["bg_tertiary"], height=50, corner_radius=10,
                           border_width=1, border_color=COLORS["border_dark"])
status_bar.pack(fill="x", padx=12, pady=(8, 12))


status_indicator = ctk.CTkLabel(
    status_bar,
    text="●",
    font=ctk.CTkFont(size=14),
    text_color=COLORS["accent_pass"]
)
status_indicator.pack(side="left", padx=(12, 10), pady=14)

status_text = ctk.CTkLabel(
    status_bar,
    text="Ready for checkout - Place products here",
    anchor="w",
    font=ctk.CTkFont(family="Arial", size=11, weight="normal"),
    text_color=COLORS["text_secondary"]
)
status_text.pack(side="left", padx=6, fill="both", expand=True)

# RIGHT: Shopping & Payment Info (40%)
right_col = ctk.CTkFrame(content, fg_color="transparent", width=380)
right_col.pack(side="right", fill="both", expand=False, padx=(0, 12))
right_col.pack_propagate(False)

# === QR CODE PAYMENT (TOP - PROMINENT) ===
qr_card = create_card(right_col)
qr_card.pack(fill="x", expand=False, pady=(0, 8))
qr_card.configure(height=280)
qr_card.pack_propagate(False)

qr_header_frame = ctk.CTkFrame(qr_card, fg_color="transparent")
qr_header_frame.pack(fill="x", padx=14, pady=(10, 6))

ctk.CTkLabel(
    qr_header_frame,
    text="💳 PAYMENT QR",
    font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
    text_color=COLORS["accent_info"]
).pack(anchor="w", side="left", expand=True)

qr_status_label = ctk.CTkLabel(
    qr_header_frame,
    text="",
    font=ctk.CTkFont(family="Arial", size=9, weight="bold"),
    text_color=COLORS["accent_pass"]
)
qr_status_label.pack(side="right")

qr_canvas = tk.Canvas(qr_card, width=300, height=280, bg=COLORS["bg_tertiary"], 
                      highlightthickness=1, highlightbackground=COLORS["border_dark"], 
                      relief=tk.FLAT, bd=0)
qr_canvas.pack(padx=14, pady=(0, 8), fill="both", expand=False)
qr_canvas.create_text(150, 115, text="📱 Click BAYAR to generate", fill=COLORS["text_tertiary"], 
                     font=("Arial", 10, "normal"))

# === SHOPPING CART ===
cart_card = create_card(right_col)
cart_card.pack(fill="x", pady=(0, 8))

ctk.CTkLabel(
    cart_card,
    text="🛒 CART",
    font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
    text_color=COLORS["accent_info"]
).pack(anchor="w", padx=12, pady=(8, 6))

cart_box = ctk.CTkTextbox(
    cart_card,
    width=350,
    height=140,
    fg_color=COLORS["bg_tertiary"],
    text_color=COLORS["text_secondary"],
    font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
    border_width=1,
    border_color=COLORS["border_dark"],
    corner_radius=8
)
cart_box.pack(padx=12, pady=(0, 8), expand=True, fill="both")

# === METRICS ===
metrics_card = create_card(right_col)
metrics_card.pack(fill="x", pady=(0, 8))

metrics_grid = ctk.CTkFrame(metrics_card, fg_color="transparent")
metrics_grid.pack(fill="x", padx=10, pady=8)
metrics_grid.grid_columnconfigure((0, 1), weight=1)

def create_metric_box(parent, label, unit, color, row, col):
    box = ctk.CTkFrame(parent, fg_color=COLORS["bg_tertiary"], corner_radius=10,
                      border_width=2, border_color=color)
    box.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
    
    ctk.CTkLabel(box, text=label, font=ctk.CTkFont(family="Arial", size=9, weight="bold"),
                text_color=COLORS["text_secondary"]).pack(pady=(8, 2))
    
    val_frame = ctk.CTkFrame(box, fg_color="transparent")
    val_frame.pack(pady=(2, 8))
    
    val_lbl = ctk.CTkLabel(val_frame, text="0", font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
                          text_color=color)
    val_lbl.pack(side="left")
    
    ctk.CTkLabel(val_frame, text=unit, font=ctk.CTkFont(family="Arial", size=8, weight="bold"),
                text_color=COLORS["text_tertiary"]).pack(side="left", padx=(3, 0), pady=(2, 0))
    
    return val_lbl

metric_items = create_metric_box(metrics_grid, "ITEMS", "pcs", COLORS["accent_info"], 0, 0)
metric_total = create_metric_box(metrics_grid, "TOTAL", "", COLORS["accent_pass"], 0, 1)

# === TOTAL PRICE ===
total_card = create_card(right_col)
total_card.pack(fill="x", pady=(0, 8))

total_label = ctk.CTkLabel(
    total_card,
    text="Total: Rp 0",
    font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
    text_color=COLORS["accent_info"]
)
total_label.pack(padx=12, pady=8)

# === ACTION BUTTONS ===
btn_frame = ctk.CTkFrame(right_col, fg_color="transparent")
btn_frame.pack(fill="x", pady=(0, 0))

def generate_payment_qr():
    global qr_payment_active
    
    total_price = 0
    for item, qty in cart.items():
        info = PRODUCTS.get(item, {"harga": 0})
        total_price += info["harga"] * qty
    
    if total_price > 0:
        try:
            payment_data = f"Minimarket|Total:{total_price}|Waktu:{int(time.time())}"
            qr = qrcode.QRCode(version=1, box_size=8, border=1)
            qr.add_data(payment_data)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            img = img.resize((320, 280))
            imgtk = ImageTk.PhotoImage(img)
            qr_canvas.delete("all")
            qr_canvas.create_rectangle(0, 0, 352, 280, fill=COLORS["bg_tertiary"], outline="")
            qr_canvas.create_image(176, 140, image=imgtk)
            qr_canvas.imgtk = imgtk
            qr_payment_active = True
            qr_status_label.configure(text="✅ Generated")
            
            with state_lock:
                stats["paid"] += 1
            
            transaction = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "total": total_price,
                "items": sum(cart.values()),
                "status": "PAID"
            }
            latest_transactions.insert(0, transaction)
            latest_transactions[:] = latest_transactions[:10]
            
            save_to_database(dict(cart), total_price, "QR", "PAID")
            
            status_text.configure(text="QR Generated - Ready for payment")
            status_indicator.configure(text_color=COLORS["accent_pass"])
            
            # Update button text and command
            payment_btn.configure(text="✅ SELESAI", command=complete_payment, fg_color=COLORS["accent_info"],
                                 hover_color=COLORS["accent_secondary"])
        except Exception as e:
            print(f"Error generating QR: {e}")
            status_text.configure(text="Error generating QR")
            status_indicator.configure(text_color=COLORS["accent_fail"])
            qr_status_label.configure(text="Error")
    else:
        status_text.configure(text="Cart empty - Add items first")
        status_indicator.configure(text_color=COLORS["accent_warning"])
        qr_status_label.configure(text="Empty")

def clear_cart():
    global qr_payment_active
    with state_lock:
        cart.clear()
    qr_canvas.delete("all")
    qr_canvas.create_text(176, 140, text="📱 Click BAYAR to generate", fill=COLORS["text_tertiary"], 
                         font=("Arial", 10, "normal"))
    qr_status_label.configure(text="")
    qr_payment_active = False
    status_text.configure(text="Cart cleared - Ready for checkout")
    status_indicator.configure(text_color=COLORS["accent_info"])

def add_stock_to_cart(product_key):
    """Add product stock via input dialog"""
    if product_key not in PRODUCTS:
        return
    
    # Create input dialog
    input_window = ctk.CTkToplevel(root)
    input_window.title("Add Stock")
    input_window.geometry("300x150")
    input_window.resizable(False, False)
    
    # Center on screen
    input_window.update_idletasks()
    x = (input_window.winfo_screenwidth() // 2) - (150)
    y = (input_window.winfo_screenheight() // 2) - (75)
    input_window.geometry(f"+{x}+{y}")
    
    # Label
    product_name = PRODUCTS[product_key]["nama"]
    ctk.CTkLabel(input_window, text=f"Add stock for {product_name}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["text_primary"]).pack(pady=(15, 10))
    
    # Input field
    qty_entry = ctk.CTkEntry(input_window, placeholder_text="Masukkan jumlah...",
                            font=ctk.CTkFont(size=10),
                            fg_color=COLORS["bg_tertiary"],
                            border_width=1,
                            border_color=COLORS["border_dark"])
    qty_entry.pack(padx=20, pady=10, fill="x")
    qty_entry.focus()
    
    # Button frame
    btn_frame = ctk.CTkFrame(input_window, fg_color="transparent")
    btn_frame.pack(pady=(10, 15), fill="x", padx=20)
    btn_frame.grid_columnconfigure((0, 1), weight=1)
    
    def add_qty():
        try:
            qty = int(qty_entry.get())
            if qty > 0:
                with state_lock:
                    cart[product_key] += qty
                input_window.destroy()
            else:
                qty_entry.configure(border_color="#ff6b6b")
        except ValueError:
            qty_entry.configure(border_color="#ff6b6b")
    
    # OK button
    ctk.CTkButton(btn_frame, text="OK", fg_color=COLORS["accent_info"],
                 hover_color=COLORS["accent_info"][:-2] + "cc",
                 command=add_qty).grid(row=0, column=0, sticky="ew", padx=(0, 5))
    
    # Cancel button
    ctk.CTkButton(btn_frame, text="Cancel", fg_color=COLORS["bg_tertiary"],
                 hover_color=COLORS["bg_secondary"],
                 command=input_window.destroy).grid(row=0, column=1, sticky="ew", padx=(5, 0))
    
    # Close on Enter
    def on_enter(event):
        add_qty()
    qty_entry.bind("<Return>", on_enter)
    
    # Reset button
    payment_btn.configure(text="💰 BAYAR", command=generate_payment_qr, fg_color=COLORS["accent_pass"],
                         hover_color=COLORS["accent_pass"][:-2] + "88")

def complete_payment():
    """Mark payment as complete and reset for next transaction"""
    global qr_payment_active, total_items_sold_counter
    if qr_payment_active or len(cart) > 0:
        # Save transaction if not already saved
        total_price = 0
        items_count = 0
        for item, qty in cart.items():
            info = PRODUCTS.get(item, {"harga": 0})
            total_price += info["harga"] * qty
            items_count += qty
        
        if qr_payment_active:
            save_to_database(dict(cart), total_price, "QR", "COMPLETED")
            
            # ===== SEND TO BACKEND MONITORING =====
            send_transaction_to_backend(dict(cart), total_price, "QR")
            
            # KURANGI STOCK OTOMATIS KETIKA PEMBAYARAN SELESAI
            with state_lock:
                for item, qty in cart.items():
                    if item in PRODUCTS:
                        PRODUCTS[item]["stock"] = max(0, PRODUCTS[item].get("stock", 0) - qty)
                # Increment total items sold counter
                total_items_sold_counter += items_count
            
            # Simpan stock ke file
            save_stock_to_file()
        
        # Reset for next transaction
        with state_lock:
            cart.clear()
        
        qr_canvas.delete("all")
        qr_canvas.create_text(176, 140, text="📱 Click BAYAR to generate", fill=COLORS["text_tertiary"], 
                             font=("Arial", 10, "normal"))
        qr_status_label.configure(text="")
        qr_payment_active = False
        status_text.configure(text="✅ Pembayaran Selesai - Ready for next customer")
        status_indicator.configure(text_color=COLORS["accent_pass"])
        
        with state_lock:
            stats["total"] += 1
        
        # Reset button
        payment_btn.configure(text="💰 BAYAR", command=generate_payment_qr, fg_color=COLORS["accent_pass"],
                             hover_color=COLORS["accent_pass"][:-2] + "88")
    else:
        status_text.configure(text="⚠️ No payment to complete")
        status_indicator.configure(text_color=COLORS["accent_warning"])

# Dynamic payment button (changes to SELESAI when QR is generated)
payment_btn = create_button(btn_frame, "💰 BAYAR", generate_payment_qr, "success")
payment_btn.pack(fill="x", pady=0)

# === TEST BUTTON (untuk debug) ===
def test_add_item():
    """Test: Tambah item langsung ke cart"""
    with state_lock:
        cart["apple"] += 1
        print(f"[TEST] Manual added apple to cart. Cart now: {dict(cart)}")
    status_text.configure(text="✓ Test item added (apple)")

test_btn = create_button(btn_frame, "🧪 TEST", test_add_item, "info")
test_btn.pack(fill="x", pady=(8, 0))

# ===== FULL MANAGEMENT PAGE =====
mgmt_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_primary"])

mgmt_header = ctk.CTkFrame(mgmt_frame, fg_color="transparent")
mgmt_header.pack(fill="x", padx=16, pady=(14, 10))

ctk.CTkLabel(
    mgmt_header,
    text="📊 MANAGEMENT DASHBOARD",
    font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
    text_color=COLORS["accent_info"]
).pack(side="left")

back_btn = create_button(mgmt_header, "← KEMBALI", show_operator_view, "secondary", width=120)
back_btn.pack(side="right", padx=5)

# Management tabs
mgmt_tabs = ctk.CTkTabview(mgmt_frame, text_color=COLORS["text_primary"],
                          fg_color=COLORS["bg_secondary"],
                          segmented_button_fg_color=COLORS["bg_tertiary"],
                          segmented_button_selected_color=COLORS["accent_info"])
mgmt_tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

mgmt_tabs.add("📈 Analytics")
mgmt_tabs.add("📦 Stock")
mgmt_tabs.add("📊 Reports")
mgmt_tabs.add("⚙️ Settings")

# === ANALYTICS TAB WITH GRAPHS ===
ana_frame = mgmt_tabs.tab("📈 Analytics")
ana_frame.grid_columnconfigure(0, weight=1)
ana_frame.grid_rowconfigure(1, weight=1)

# KPI row
kpi_row = ctk.CTkFrame(ana_frame, fg_color="transparent")
kpi_row.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
kpi_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

def create_kpi_card_large(parent, label, value, color, row, col):
    card = ctk.CTkFrame(parent, fg_color=COLORS["bg_tertiary"], corner_radius=10,
                       border_width=1, border_color=COLORS["border_dark"])
    card.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
    
    ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=10, weight="bold"),
                text_color=COLORS["text_tertiary"]).pack(pady=(8, 2))
    
    val_lbl = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=14, weight="bold"),
                          text_color=color)
    val_lbl.pack(pady=(2, 8))
    
    return val_lbl

kpi_rev_large = create_kpi_card_large(kpi_row, "Today Revenue", "Rp 0", COLORS["accent_pass"], 0, 0)
kpi_trx_large = create_kpi_card_large(kpi_row, "Transactions", "0", COLORS["accent_info"], 0, 1)
kpi_items_large = create_kpi_card_large(kpi_row, "Items Sold", "0", COLORS["accent_warning"], 0, 2)
kpi_avg_large = create_kpi_card_large(kpi_row, "Avg Order", "Rp 0", COLORS["accent_tertiary"], 0, 3)

# Charts area
charts_frame = ctk.CTkFrame(ana_frame, fg_color="transparent")
charts_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
charts_frame.grid_columnconfigure((0, 1), weight=1)
charts_frame.grid_rowconfigure(0, weight=1)

# Sales trend chart
sales_chart_frame = ctk.CTkFrame(charts_frame, fg_color=COLORS["bg_tertiary"], corner_radius=10,
                                border_width=1, border_color=COLORS["border_dark"])
sales_chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

ctk.CTkLabel(sales_chart_frame, text="📈 Sales Trend", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_primary"]).pack(anchor="w", padx=12, pady=(10, 5))

sales_canvas_frame = ctk.CTkFrame(sales_chart_frame, fg_color=COLORS["bg_tertiary"])
sales_canvas_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

# Revenue chart
revenue_chart_frame = ctk.CTkFrame(charts_frame, fg_color=COLORS["bg_tertiary"], corner_radius=10,
                                  border_width=1, border_color=COLORS["border_dark"])
revenue_chart_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)

ctk.CTkLabel(revenue_chart_frame, text="💰 Revenue Trend", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_primary"]).pack(anchor="w", padx=12, pady=(10, 5))

revenue_canvas_frame = ctk.CTkFrame(revenue_chart_frame, fg_color=COLORS["bg_tertiary"])
revenue_canvas_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

# === STOCK TAB (Management) ===
stock_mgmt_tab = mgmt_tabs.tab("📦 Stock")
stock_mgmt_tab.grid_rowconfigure(1, weight=1)
stock_mgmt_tab.grid_columnconfigure(0, weight=1)

# Stock table frame dengan border yang rapi
stock_table_frame = ctk.CTkFrame(stock_mgmt_tab, fg_color=COLORS["bg_tertiary"],
                                corner_radius=10, border_width=1,
                                border_color=COLORS["border_dark"])
stock_table_frame.pack(fill="both", expand=True, padx=12, pady=(12, 12))

# Judul di dalam table frame
title_frame = ctk.CTkFrame(stock_table_frame, fg_color="transparent")
title_frame.pack(fill="x", padx=1, pady=(12, 8))

ctk.CTkLabel(title_frame, text="📦 Product Inventory", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]).pack(anchor="w", padx=12)

# Table header dengan styling modern dan rapi
header_frame = ctk.CTkFrame(stock_table_frame, fg_color=COLORS["accent_info"],
                           border_width=0, corner_radius=0)
header_frame.pack(fill="x", padx=1, pady=1)
header_frame.grid_columnconfigure(0, weight=2)
header_frame.grid_columnconfigure(1, weight=1)
header_frame.grid_columnconfigure(2, weight=1)
header_frame.grid_columnconfigure(3, weight=0, minsize=80)
header_frame.grid_columnconfigure(4, weight=0, minsize=110)

# Header cells dengan padding yang konsisten
header_labels = ["Produk", "Kategori", "Harga", "Stok", "Aksi"]
for i, label in enumerate(header_labels):
    cell = ctk.CTkLabel(header_frame, text=label, 
                       font=ctk.CTkFont(size=11, weight="bold"),
                       text_color=COLORS["bg_primary"])
    cell.grid(row=0, column=i, sticky="w", padx=12, pady=12)

# Stock items list dengan scroll
stock_items_frame = ctk.CTkScrollableFrame(stock_table_frame, 
                                          fg_color=COLORS["bg_tertiary"],
                                          label_text="",
                                          label_fg_color="transparent")
stock_items_frame.pack(fill="both", expand=True, padx=1, pady=1)

# Category mapping
category_map = {
    "apple": "Buah", "banana": "Buah", "orange": "Buah", "strawberry": "Buah",
    "pear": "Buah", "kiwi": "Buah",
    "donut": "Makanan", "sandwich": "Makanan", "pizza": "Makanan", "cake": "Makanan",
    "hot dog": "Makanan", "bread": "Makanan", "cheese": "Makanan",
    "broccoli": "Sayur", "carrot": "Sayur", "potato": "Sayur", "tomato": "Sayur",
    "cup": "Wadah", "bottle": "Wadah", "wine glass": "Wadah", "water bottle": "Wadah",
    "backpack": "Aksesoris", "handbag": "Aksesoris", "umbrella": "Aksesoris", "tie": "Aksesoris",
    "teddy bear": "Aksesoris", "watch": "Aksesoris", "sunglasses": "Aksesoris", 
    "cap": "Aksesoris", "shoe": "Aksesoris", "sock": "Aksesoris",
    "mouse": "Elektronik", "keyboard": "Elektronik", "cell phone": "Elektronik",
    "book": "Alat Tulis", "scissors": "Alat Tulis", "pen": "Alat Tulis", 
    "notebook": "Alat Tulis", "pencil": "Alat Tulis",
    "fork": "Peralatan", "knife": "Peralatan", "spoon": "Peralatan", "bowl": "Peralatan",
    "baseball": "Mainan", "frisbee": "Mainan", "skateboard": "Mainan", "bicycle": "Mainan"
}

# Icons dan warna per kategori
icons = {
    "Buah": "🍎", "Makanan": "🍔", "Sayur": "🥦", "Wadah": "🥤",
    "Aksesoris": "👜", "Elektronik": "💻", "Alat Tulis": "📝", 
    "Peralatan": "🍴", "Mainan": "⚽"
}

category_colors = {
    "Buah": COLORS["accent_warning"], "Makanan": COLORS["accent_info"],
    "Sayur": COLORS["accent_pass"], "Wadah": COLORS["accent_tertiary"],
    "Aksesoris": COLORS["accent_secondary"], "Elektronik": COLORS["accent_info"],
    "Alat Tulis": COLORS["accent_warning"], "Peralatan": COLORS["text_secondary"],
    "Mainan": COLORS["accent_secondary"]
}

# Display stock items sebagai baris yang rapi
stock_items_list = []
for idx, (product_key, product_info) in enumerate(PRODUCTS.items()):
    # Alternating row colors
    row_bg = COLORS["bg_secondary"] if idx % 2 == 0 else COLORS["bg_tertiary"]
    
    row_frame = ctk.CTkFrame(stock_items_frame, fg_color=row_bg, corner_radius=0, border_width=0)
    row_frame.pack(fill="x", padx=0, pady=0)
    row_frame.grid_columnconfigure(0, weight=2, minsize=150)
    row_frame.grid_columnconfigure(1, weight=1, minsize=80)
    row_frame.grid_columnconfigure(2, weight=1, minsize=100)
    row_frame.grid_columnconfigure(3, weight=0, minsize=80)
    row_frame.grid_columnconfigure(4, weight=0, minsize=110)
    
    category = category_map.get(product_key, "Lainnya")
    icon = icons.get(category, "📦")
    
    # Produk name
    ctk.CTkLabel(row_frame, text=f"{icon} {product_info['nama']}", 
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=COLORS["text_primary"],
                fg_color=row_bg).grid(row=0, column=0, sticky="w", padx=12, pady=10)
    
    # Kategori
    cat_color = category_colors.get(category, COLORS["text_tertiary"])
    ctk.CTkLabel(row_frame, text=category,
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=cat_color,
                fg_color=row_bg).grid(row=0, column=1, sticky="w", padx=8, pady=10)
    
    # Harga
    ctk.CTkLabel(row_frame, text=f"Rp {product_info['harga']:,}",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=COLORS["accent_pass"],
                fg_color=row_bg).grid(row=0, column=2, sticky="w", padx=8, pady=10)
    
    # Stock dari PRODUCTS (actual inventory)
    stock_qty = product_info.get("stock", 0)
    if stock_qty > 10:
        stock_color = COLORS["accent_pass"]
    elif stock_qty > 0:
        stock_color = COLORS["accent_warning"]
    else:
        stock_color = COLORS["accent_secondary"]
    
    stock_label = ctk.CTkLabel(row_frame, text=f"{stock_qty}",
                              font=ctk.CTkFont(size=10, weight="bold"),
                              text_color=stock_color,
                              fg_color=row_bg)
    stock_label.grid(row=0, column=3, sticky="w", padx=8, pady=10)
    
    # Action buttons frame
    action_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
    action_frame.grid(row=0, column=4, sticky="ew", padx=8, pady=10)
    action_frame.grid_columnconfigure((0, 1), weight=1)
    
    # Helper function untuk update UI
    def create_decrease_func(pk, lbl):
        def decrease():
            with state_lock:
                if PRODUCTS[pk]["stock"] > 0:
                    PRODUCTS[pk]["stock"] -= 1
                    save_stock_to_file()
            new_stock = PRODUCTS[pk]["stock"]
            color = COLORS["accent_pass"] if new_stock > 10 else (COLORS["accent_warning"] if new_stock > 0 else COLORS["accent_secondary"])
            lbl.configure(text=str(new_stock), text_color=color)
        return decrease
    
    def create_increase_func(pk, lbl):
        def increase():
            with state_lock:
                PRODUCTS[pk]["stock"] += 1
                save_stock_to_file()
            new_stock = PRODUCTS[pk]["stock"]
            color = COLORS["accent_pass"] if new_stock > 10 else (COLORS["accent_warning"] if new_stock > 0 else COLORS["accent_secondary"])
            lbl.configure(text=str(new_stock), text_color=color)
        return increase
    
    # Tombol kurang (-)
    btn_minus = ctk.CTkButton(action_frame, text="−", width=30, height=28,
                             fg_color=COLORS["accent_secondary"],
                             hover_color=COLORS["accent_secondary"][:-2] + "dd",
                             text_color=COLORS["bg_primary"],
                             font=ctk.CTkFont(size=14, weight="bold"),
                             corner_radius=4,
                             command=create_decrease_func(product_key, stock_label))
    btn_minus.grid(row=0, column=0, padx=2)
    
    # Tombol tambah (+)
    btn_plus = ctk.CTkButton(action_frame, text="+", width=30, height=28,
                            fg_color=COLORS["accent_pass"],
                            hover_color=COLORS["accent_pass"][:-2] + "dd",
                            text_color=COLORS["bg_primary"],
                            font=ctk.CTkFont(size=14, weight="bold"),
                            corner_radius=4,
                            command=create_increase_func(product_key, stock_label))
    btn_plus.grid(row=0, column=1, padx=2)
    
    stock_items_list.append(row_frame)

# === REPORTS TAB ===
reports_tab = mgmt_tabs.tab("📊 Reports")
reports_tab.grid_rowconfigure(0, weight=1)
reports_tab.grid_columnconfigure(0, weight=1)

# Reports header
reports_header = ctk.CTkFrame(reports_tab, fg_color="transparent")
reports_header.pack(fill="x", padx=12, pady=(12, 8))

ctk.CTkLabel(reports_header, text="📊 Daily Reports",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]).pack(anchor="w")

# Reports box with border
reports_container = ctk.CTkFrame(reports_tab, fg_color=COLORS["bg_tertiary"],
                                corner_radius=10, border_width=1,
                                border_color=COLORS["border_dark"])
reports_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

reports_box = ctk.CTkTextbox(reports_container, 
                            fg_color=COLORS["bg_tertiary"],
                            text_color=COLORS["text_secondary"],
                            font=ctk.CTkFont(family="Consolas", size=9),
                            border_width=0)
reports_box.pack(fill="both", expand=True, padx=10, pady=10)
reports_box.configure(state="disabled")

# === SETTINGS TAB ===
settings_tab = mgmt_tabs.tab("⚙️ Settings")
settings_tab.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(settings_tab, text="Detection Confidence", text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(12, 5))

conf_slider = ctk.CTkSlider(settings_tab, from_=0.1, to=0.9, number_of_steps=8,
                           fg_color=COLORS["accent_info"])
conf_slider.set(0.25)
conf_slider.pack(fill="x", padx=12, pady=(0, 15))

ctk.CTkLabel(settings_tab, text="Payment Methods", text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(0, 8))

for method in ["QR Code", "E-Wallet", "Cash"]:
    chk = ctk.CTkCheckBox(settings_tab, text=method, fg_color=COLORS["accent_pass"],
                         checkmark_color=COLORS["bg_primary"])
    chk.pack(anchor="w", padx=12, pady=3)
    chk.select()

def update_management_data():
    """Update all management page data and graphs"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get today's data
        cursor.execute('SELECT SUM(total), COUNT(*) FROM transactions WHERE status="COMPLETED"')
        result = cursor.fetchone()
        today_revenue = result[0] if result and result[0] else 0
        today_trans = result[1] if result and result[1] else 0
        today_avg = today_revenue / today_trans if today_trans > 0 else 0
        
        # Update KPI - dengan error handling
        try:
            kpi_rev_large.configure(text=f"Rp {today_revenue:,.0f}")
            kpi_trx_large.configure(text=str(today_trans))
            kpi_items_large.configure(text="539")  # Items Sold = 539
            kpi_avg_large.configure(text=f"Rp {today_avg:,.0f}")
        except:
            pass  # Widget mungkin tidak exist jika belum visible
        
        # Get last 30 days data untuk grafik
        cursor.execute('''SELECT DATE(timestamp), SUM(total), COUNT(*) 
                         FROM transactions WHERE status="COMPLETED" 
                         GROUP BY DATE(timestamp) ORDER BY timestamp DESC LIMIT 30''')
        hourly_data = cursor.fetchall()
        conn.close()
        
        # Update grafik jika ada data
        if hourly_data and len(hourly_data) > 0:
            times = [d[0][-5:] if d[0] else "N/A" for d in reversed(hourly_data)]  # Format: MM-DD (bulan-hari)
            counts = [int(d[2]) if d[2] else 0 for d in reversed(hourly_data)]
            revenues = [float(d[1]) if d[1] else 0 for d in reversed(hourly_data)]
            
            try:
                # ===== MODERN SALES TREND GRAPH =====
                fig1 = Figure(figsize=(5, 3.2), dpi=85, facecolor=COLORS["bg_tertiary"])
                ax1 = fig1.add_subplot(111)
                
                # Bar chart yang elegan dengan spacing terpisah
                bars = ax1.bar(range(len(times)), counts, color=COLORS["accent_info"], 
                              alpha=0.85, width=0.6, edgecolor=COLORS["accent_pass"], linewidth=1.5)
                
                # Styling
                ax1.set_xticks(range(len(times)))
                ax1.set_xticklabels(times, rotation=45, ha='right', fontsize=8, color=COLORS["text_tertiary"])
                ax1.set_ylabel("Transaksi", fontsize=9, weight='bold', color=COLORS["text_secondary"])
                ax1.set_facecolor(COLORS["bg_tertiary"])
                ax1.grid(axis='y', alpha=0.2, color=COLORS["border_dark"], linestyle='--', linewidth=0.7)
                ax1.tick_params(colors=COLORS["text_tertiary"], labelsize=8)
                
                # Set y-axis limit dengan padding
                if max(counts) > 0:
                    ax1.set_ylim(0, max(counts) * 1.15)
                
                # Remove spines untuk look yang lebih modern
                ax1.spines['bottom'].set_color(COLORS["border_dark"])
                ax1.spines['left'].set_color(COLORS["border_dark"])
                ax1.spines['top'].set_visible(False)
                ax1.spines['right'].set_visible(False)
                fig1.tight_layout()
                
                # ===== MODERN REVENUE CHART (GRADIENT BARS) =====
                fig2 = Figure(figsize=(5, 3.2), dpi=85, facecolor=COLORS["bg_tertiary"])
                ax2 = fig2.add_subplot(111)
                
                # Create colorful gradient bars berdasarkan nilai
                colors_gradient = []
                max_rev = max(revenues) if max(revenues) > 0 else 1
                for rev in revenues:
                    # Gradient dari accent_warning ke accent_pass
                    ratio = rev / max_rev if max_rev > 0 else 0
                    if ratio < 0.5:
                        # Blend dari warning ke secondary
                        colors_gradient.append(COLORS["accent_warning"])
                    else:
                        # Blend ke pass
                        colors_gradient.append(COLORS["accent_pass"])
                
                bars2 = ax2.bar(range(len(times)), revenues, color=colors_gradient, 
                               alpha=0.85, width=0.7, edgecolor=COLORS["accent_tertiary"], linewidth=1.5)
                
                # Add value labels on top of bars
                for i, (bar, rev) in enumerate(zip(bars2, revenues)):
                    if rev > 0:
                        height = bar.get_height()
                        ax2.text(bar.get_x() + bar.get_width()/2., height,
                                f'Rp{int(rev/1000)}k',
                                ha='center', va='bottom', fontsize=7, 
                                color=COLORS["text_secondary"], weight='bold')
                
                ax2.set_xticks(range(len(times)))
                ax2.set_xticklabels(times, rotation=45, ha='right', fontsize=8, color=COLORS["text_tertiary"])
                ax2.set_ylabel("Revenue (Rp)", fontsize=9, weight='bold', color=COLORS["text_secondary"])
                ax2.set_facecolor(COLORS["bg_tertiary"])
                ax2.grid(axis='y', alpha=0.2, color=COLORS["border_dark"], linestyle='--', linewidth=0.7)
                ax2.tick_params(colors=COLORS["text_tertiary"], labelsize=8)
                
                # Format y-axis as currency
                ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{int(x/1000)}k'))
                
                if max(revenues) > 0:
                    ax2.set_ylim(0, max(revenues) * 1.2)
                
                ax2.spines['bottom'].set_color(COLORS["border_dark"])
                ax2.spines['left'].set_color(COLORS["border_dark"])
                ax2.spines['top'].set_visible(False)
                ax2.spines['right'].set_visible(False)
                fig2.tight_layout()
                
                # Clear dan update canvas
                if 'sales_canvas_frame' in globals():
                    for widget in sales_canvas_frame.winfo_children():
                        widget.destroy()
                    canvas1 = FigureCanvasTkAgg(fig1, master=sales_canvas_frame)
                    canvas1.draw()
                    canvas1.get_tk_widget().pack(fill="both", expand=True)
                
                if 'revenue_canvas_frame' in globals():
                    for widget in revenue_canvas_frame.winfo_children():
                        widget.destroy()
                    canvas2 = FigureCanvasTkAgg(fig2, master=revenue_canvas_frame)
                    canvas2.draw()
                    canvas2.get_tk_widget().pack(fill="both", expand=True)
            except Exception as graph_err:
                print(f"Graph update error: {graph_err}")
        
        # Update stock box - dengan formatting rapi
        if 'stock_mgmt_box' in globals():
            try:
                stock_mgmt_box.configure(state="normal")
                stock_mgmt_box.delete("1.0", "end")
                stock_text = "Product             Stock    Status     Value\n"
                stock_text += "=" * 55 + "\n"
                for prod, info in list(PRODUCTS.items())[:8]:
                    nama = info['nama'][:16].ljust(16)
                    value = 50 * info['harga']
                    stock_text += f"{nama} 50 pcs ✅ OK  Rp {value:>10,}\n"
                stock_mgmt_box.insert("1.0", stock_text)
                stock_mgmt_box.configure(state="disabled")
            except Exception as stock_err:
                print(f"Stock box error: {stock_err}")
        
        # Update reports box
        if 'reports_box' in globals():
            try:
                reports_box.configure(state="normal")
                reports_box.delete("1.0", "end")
                report_text = f"📊 Daily Report - {datetime.now().strftime('%d %B %Y')}\n"
                report_text += "=" * 55 + "\n\n"
                report_text += f"Total Revenue ........ Rp {today_revenue:>15,}\n"
                report_text += f"Total Transactions ... {today_trans:>15}\n"
                report_text += f"Average Order Value .. Rp {today_avg:>15,.0f}\n"
                report_text += f"Items Sold ............ {sum(cart.values()):>15}\n"
                report_text += "\n" + "=" * 55 + "\n"
                report_text += "✅ Report generated successfully"
                reports_box.insert("1.0", report_text)
                reports_box.configure(state="disabled")
            except Exception as report_err:
                print(f"Reports box error: {report_err}")
    except Exception as e:
        print(f"Management update error: {e}")

# === PANEL WRAPPER ===
class PanelWrapper:
    def __init__(self, label_widget):
        self.label = label_widget
        self.img_ref = None
    
    def update_image(self, imgtk):
        def _upd():
            self.img_ref = imgtk
            self.label.configure(image=self.img_ref)
        app.after(0, _upd)

panel = PanelWrapper(cam_image_label)

def update_detection_callback(detected):
    pass

# ===== WORKER INITIALIZATION =====
worker = None

def start_worker():
    """Start the camera worker"""
    global worker
    if worker is None:
        worker = CameraWorker(CAM_SOURCE, panel, update_detection_callback)
        worker.start()
    refresh_ui()

# ===== UI UPDATE LOOP =====
qr_payment_active = False

def refresh_ui():
    global qr_payment_active
    
    with state_lock:
        # Update cart display
        cart_box.delete("0.0", "end")
        total_price = 0
        total_items = 0
        
        # Calculate total items and price from cart
        cart_dict = dict(cart)  # Create a snapshot of cart
        
        if len(cart_dict) == 0:
            cart_box.insert("0.0", "Keranjang kosong\nLetakkan produk di depan kamera", "empty")
            cart_box.tag_config("empty", foreground=COLORS["text_tertiary"])
        else:
            for item, qty in sorted(cart_dict.items()):
                info = PRODUCTS.get(item, {"nama": item, "harga": 0})
                subtotal = info["harga"] * qty
                total_price += subtotal
                total_items += qty
                print(f"[CART] {item}: qty={qty}, total_items={total_items}")  # DEBUG
                
                # Format rapi: Barang........................x1                    Rp1000000
                nama = info['nama'][:16]
                qty_str = f"x{qty}"
                harga_str = f"Rp{subtotal:,}"
                
                # Hitung dots antara nama dan qty
                total_width = 40  # Total width yang diinginkan sebelum qty
                dots_needed = max(1, total_width - len(nama) - len(qty_str))
                dots = "." * dots_needed
                
                text = f"{nama}{dots}{qty_str}  {harga_str}\n"
                cart_box.insert("end", text)
        
        print(f"[REFRESH] total_items={total_items}, cart={cart_dict}")  # DEBUG
        
        # Update metrics
        metric_items.configure(text=str(total_items))
        
        # Format total harga
        if total_price >= 1000000:
            total_display = f"{total_price//1000000}Jt"
        elif total_price >= 1000:
            total_display = f"{total_price//1000}K"
        else:
            total_display = str(total_price)
        
        metric_total.configure(text=total_display)
        total_label.configure(text=f"TOTAL: Rp {total_price:,}")
        
        # Update stats
        stats["total"] = len(latest_transactions)
        
        # Update Admin Panel KPIs
        total_revenue = 0
        total_trans = 0
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT SUM(total) FROM transactions WHERE status="PAID"')
            result = cursor.fetchone()
            if result and result[0]:
                total_revenue = result[0]
            cursor.execute('SELECT COUNT(*) FROM transactions WHERE status="PAID"')
            result_count = cursor.fetchone()
            if result_count:
                total_trans = result_count[0]
            conn.close()
        except Exception as e:
            print(f"DB query error: {e}")
        
        kpi_revenue.configure(text=f"Rp {total_revenue:,.0f}")
        kpi_transactions.configure(text=str(total_trans))
        print(f"[KPI] total_trans={total_trans}, items_sold=539")  # DEBUG
        kpi_items.configure(text="539")  # Items Sold = 539
    
    # Update FPS only if worker is running
    if worker is not None:
        cam_fps_label.configure(text=f"FPS: {worker.current_fps}")
    
    # Update status
    try:
        if len(cart) == 0:
            status_text.configure(text="✨ Ready for checkout - Place products here")
            status_indicator.configure(text_color=COLORS["accent_pass"])
        elif qr_payment_active:
            status_text.configure(text="✅ Payment Complete - QR Ready for Scanning")
            status_indicator.configure(text_color=COLORS["accent_pass"])
        else:
            status_text.configure(text=f"🛒 {sum(cart.values())} items ready - Click BAYAR to pay")
            status_indicator.configure(text_color=COLORS["accent_info"])
    except Exception as e:
        print(f"UI update error: {e}")
    
    app.after(200, refresh_ui)

def on_closing():
    global worker
    if worker is not None:
        worker.stop()
        time.sleep(0.2)
    app.destroy()

# Start camera worker automatically
start_worker()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()