# nawala_bot.py (Versi 3.0 - Web Scraping untuk Akurasi)

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
import logging
import socket
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# --- Konfigurasi ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# TOKEN BOT ANDA
TOKEN = "8312452980:AAG4od8CYHuUgvs6M7UryWx8gCkXTcDsXMk" 

# Target Chat ID dan Domain Monitor
# GANTI INI dengan ID Group/Channel Anda (contoh: -1001234567890)
TARGET_CHAT_ID = "GANTI_DENGAN_ID_CHAT_ANDA" 
DOMAINS_TO_MONITOR = [
    "aksesbatikslot.vip",  # Ganti dengan domain yang ingin dipantau
    "aksesbatikslot.com", 
    "batikslot-win.fashion", 
    "aksesbatikslot.org", 
    "aksesbatikslot.info",
]

# Kata kunci yang menandakan pemblokiran (Kasus-kasus umum di Indonesia)
BLOCKING_KEYWORDS = [
    "internet positif", 
    "situs diblokir", 
    "nawala unblocker", 
    "pemblokiran",
    "trustpositif"
]

# --- Fungsi Pengecekan Akurat (Web Scraping) ---

def check_blocking_status(domain):
    """Mengecek status domain dengan mencoba mengakses dan menganalisis konten halaman."""
    # Selalu coba akses menggunakan HTTP
    url = f"http://{domain}" 
    
    # 1. Cek IP Asli (untuk info teknis)
    try:
        ip_address = socket.gethostbyname(domain)
    except socket.gaierror:
        return "❓ INVALID", "Domain tidak ditemukan (DNS Error)"
    except Exception:
        ip_address = "N/A"

    # 2. Web Scraping
    try:
        # Lakukan request dengan User-Agent agar terlihat seperti browser normal
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        # Tambahkan Timeout untuk menghindari hang jika diblokir
        response = requests.get(url, headers=headers, timeout=15) 
        
        # Periksa Status Code HTTP
        status_code_info = ""
        if response.status_code >= 400:
            status_code_info = f"HTTP Status {response.status_code}. "

        # Analisis Konten Halaman (Mencari Keyword Blokir)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Ambil semua teks dan ubah ke huruf kecil untuk pengecekan keyword yang sensitif
        page_text = soup.get_text().lower() 

        for keyword in BLOCKING_KEYWORDS:
            if keyword in page_text:
                return "❌ DIBLOKIR! (Konten Blokir Ditemukan)", ip_address, f"{status_code_info}Keyword '{keyword}' ditemukan."
        
        # Jika tidak ada kata kunci blokir
        return "✅ AMAN (Konten Bersih)", ip_address, f"{status_code_info}Akses berhasil. Konten bersih."

    except requests.exceptions.Timeout:
        return "❓ GAGAL (Timeout)", ip_address, "Akses melebihi batas waktu (sering terjadi jika diblokir keras)"
    except requests.exceptions.ConnectionError:
        return "❓ GAGAL (Koneksi Error)", ip_address, "Gagal tersambung (sering terjadi jika diblokir)"
    except Exception as e:
        return "🚨 ERROR", ip_address, f"Terjadi Error: {e}"


# --- Fungsi Handler dan Penjadwalan ---

async def start_command(update, context):
    """Mengirim pesan selamat datang ketika perintah /start diterima."""
    await update.message.reply_text("Halo! Bot Pengecek Domain Anti Nawala (v3.0 - Akurat) sudah aktif. 🛡️\n\nSilakan kirimkan nama domain yang ingin Anda cek (contoh: google.com).")

async def check_domain(update, context):
    """Merespons pesan teks (domain) dengan hasil pengecekan Web Scraping."""
    domain = update.message.text.strip().lower().replace("http://", "").replace("https://", "").split("/")[0]

    await update.message.reply_text(f"Mengecek status domain: `{domain}`...", parse_mode='Markdown')
    
    # Panggil fungsi pengecekan akurat
    status, ip, detail = check_blocking_status(domain)
    
    response_text = (
        f"**[ HASIL CEK DOMAIN ]**\n"
        f"Domain: `{domain}`\n\n"
        f"**STATUS: {status}**\n\n"
        f"Detail Teknis:\nIP Asli: `{ip}`\nKeterangan: {detail}"
    )
    
    await update.message.reply_text(response_text, parse_mode='Markdown')

# --- Fungsi Penjadwalan Baru (Hanya Lapor Jika Diblokir - Versi 3.1) ---

async def send_interval_info(application: Application):
    """Tugas yang dijadwalkan: Mengirim laporan hanya jika ada domain yang diblokir."""
    logger.info("Menjalankan tugas interval 3 jam (V3.1 - Alerting)...")
    
    # List untuk menampung HANYA domain yang diblokir
    blocked_results = []
    total_monitored = len(DOMAINS_TO_MONITOR)

    for domain in DOMAINS_TO_MONITOR:
        status, ip, detail = check_blocking_status(domain)
        
        # Periksa apakah status menunjukkan pemblokiran
        if "❌ DIBLOKIR!" in status:
            blocked_results.append(f"• 🚨 `{domain}`: **{status}**")
        
    # LOGIKA BARU: HANYA KIRIM PESAN JIKA ADA DOMAIN YANG DIBLOKIR
    if not blocked_results:
        # Jika list kosong, tidak ada domain yang diblokir. Tidak perlu kirim notifikasi.
        logger.info(f"Semua {total_monitored} domain AMAN. Tidak ada notifikasi dikirim.")
        return

    # Jika ada domain yang diblokir, buat laporan peringatan
    # Jika ada domain yang diblokir, buat laporan peringatan
message_text = f"""*** [ALERT NAWALA DITEMUKAN!] ***\n\nDitemukan **{len(blocked_results)}** domain diblokir dari {total_monitored} domain yang dipantau per {datetime.now().strftime('%d %b %Y %H:%M:%S')}:\n\n- {'\n- '.join(blocked_results)}\n\nSegera ganti DNS domain-domain ini!"""
    try:
        # Mengirim pesan peringatan
        await application.bot.send_message(
            chat_id=TARGET_CHAT_ID, 
            text=message_text, 
            parse_mode='Markdown'
        )
        logger.warning(f"ALERT NAWALA berhasil dikirim untuk {len(blocked_results)} domain ke chat ID {TARGET_CHAT_ID}")
    except Exception as e:
        logger.error(f"Gagal mengirim ALERT otomatis. Error: {e}")

# --- END Fungsi Penjadwalan Baru ---
