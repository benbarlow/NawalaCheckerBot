from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes # Import ContextTypes
import logging
import socket
import requests
from bs4 import BeautifulSoup
import datetime
from telegram import Update # Import Update

# --- Konfigurasi ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# NILAI KONFIGURASI ANDA (SUDAH DIMASUKKAN)
TOKEN = "8312452980:AAG4od8CYHuUgvs6M7UryWx8gCkXTcDsXMk"  
TARGET_CHAT_ID = "7038651668"  

# Target Domain untuk dipantau (UBAH JIKA PERLU)
# Catatan: Variabel ini akan dimodifikasi saat runtime oleh command /dom_add dan /dom_del
DOMAINS_TO_MONITOR = [
    "aksesbatikslot.vip",  
    "aksesbatikslot.com",  
    "batikslot-win.fashion",
    "aksesbatikslot.org",  
    "batikslot.space",
]

# Kata kunci yang menandakan pemblokiran (Web Scraping)
BLOCKING_KEYWORDS = [
    "internet positif",  
    "situs diblokir",  
    "nawala unblocker",  
    "pemblokiran",
    "trustpositif",
    "kementerian komunikasi",    
    "konten negatif",            
    "blocked due to content",    
    "akun anda ditangguhkan"    
]

# IP Pemblokiran Umum di Indonesia (Deteksi Akurat)
BLOCKING_IPS = [
    '103.1.208.57', 
    '104.244.48.91', 
    '15.197.225.128', 
    '104.21.67.48',  
    '172.67.213.207',  
]


# --- Fungsi Pengecekan Akurat (Deteksi IP & Web Scraping) ---
# ... (Fungsi check_blocking_status tetap sama) ...
def check_blocking_status(domain):
    """Mengecek status domain dengan Deteksi IP (lebih akurat) dan Web Scraping."""
    url = f"http://{domain}"  
    ip_address = "N/A"

    # --- 1. DETEKSI DNS/IP ---
    try:
        ip_address = socket.gethostbyname(domain)
        if ip_address in BLOCKING_IPS:
            return "❌ DIBLOKIR! (IP Blokir Ditemukan)", ip_address, "Domain dialihkan ke IP Pemblokiran Umum."
            
    except socket.gaierror:
        return "❓ INVALID", "Domain tidak ditemukan (DNS Error)", "N/A"
    except Exception as e:
        logger.warning(f"Error DNS Lookup untuk {domain}: {e}")
        pass

    # --- 2. WEB SCRAPING ---
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)  
        status_code_info = f"HTTP Status {response.status_code}. " if response.status_code >= 400 else ""
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text().lower()  

        for keyword in BLOCKING_KEYWORDS:
            if keyword in page_text:
                return "❌ DIBLOKIR! (Konten Blokir Ditemukan)", ip_address, f"{status_code_info}Keyword '{keyword}' ditemukan di halaman."
        
        return "✅ AMAN (IP & Konten Bersih)", ip_address, f"{status_code_info}Akses berhasil. Konten bersih."

    except requests.exceptions.Timeout:
        return "❓ GAGAL (Timeout)", ip_address, "Akses melebihi batas waktu (sering terjadi jika diblokir keras)"
    except requests.exceptions.ConnectionError:
        return "❓ GAGAL (Koneksi Error)", ip_address, "Gagal tersambung (sering terjadi jika diblokir)"
    except Exception as e:
        return "🚨 ERROR", ip_address, f"Terjadi Error: {e}"


# --- FUNGSI BARU UNTUK MANAJEMEN DOMAIN ---

async def dom_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menambahkan domain ke daftar pemantauan."""
    try:
        if not context.args:
            await update.message.reply_text("❌ **Gagal:** Mohon berikan nama domain. Contoh: `/dom_add contohdomain.com`", parse_mode='Markdown')
            return

        new_domain = context.args[0].lower().strip()
        
        if new_domain not in DOMAINS_TO_MONITOR:
            DOMAINS_TO_MONITOR.append(new_domain)
            await update.message.reply_text(
                f"✅ **Berhasil:** Domain `{new_domain}` telah ditambahkan ke daftar pemantauan.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"⚠️ **Peringatan:** Domain `{new_domain}` sudah ada di daftar.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error di dom_add: {e}")
        await update.message.reply_text("🚨 Terjadi error saat memproses permintaan.")


async def dom_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menghapus domain dari daftar pemantauan."""
    try:
        if not context.args:
            await update.message.reply_text("❌ **Gagal:** Mohon berikan nama domain yang akan dihapus. Contoh: `/dom_del contohdomain.com`", parse_mode='Markdown')
            return

        domain_to_delete = context.args[0].lower().strip()
        
        if domain_to_delete in DOMAINS_TO_MONITOR:
            DOMAINS_TO_MONITOR.remove(domain_to_delete)
            await update.message.reply_text(
                f"✅ **Berhasil:** Domain `{domain_to_delete}` telah dihapus dari daftar.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"⚠️ **Peringatan:** Domain `{domain_to_delete}` tidak ditemukan di daftar.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error di dom_del: {e}")
        await update.message.reply_text("🚨 Terjadi error saat memproses permintaan.")


async def dom_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan daftar domain yang saat ini dipantau."""
    if DOMAINS_TO_MONITOR:
        list_items = '\n'.join([f"• `{d}`" for d in sorted(DOMAINS_TO_MONITOR)])
        response_text = (
            f"*** [DAFTAR DOMAIN AKTIF DIPANTAU ({len(DOMAINS_TO_MONITOR)})] ***\n\n"
            f"{list_items}"
        )
    else:
        response_text = "Daftar pemantauan kosong. Tambahkan domain dengan /dom_add."
        
    await update.message.reply_text(response_text, parse_mode='Markdown')


# --- FUNGSI LAMA UNTUK CHAT INSTAN ---
# ... (check_domain_command dan echo_domain tetap sama) ...
async def check_domain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim daftar domain yang dipantau saat user mengetik /list_domain (alias /dom_list)"""
    # Fungsi ini sekarang dialihkan ke dom_list
    await dom_list(update, context) 

async def echo_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Merespons pesan chat yang berisi nama domain (tanpa http/s)"""
    domain = update.message.text.lower().strip()
    
    if '.' in domain and len(domain) > 5 and ' ' not in domain:
        if domain.startswith(('http://', 'https://')):
            domain = domain.split('//')[-1]
            
        await update.message.reply_text(f"Mengecek status domain: `{domain}`...", parse_mode='Markdown')
        
        status, ip, detail = check_blocking_status(domain)
        
        result_text = (
            f"*** [HASIL CEK DOMAIN] ***\n"
            f"Domain: `{domain}`\n"
            f"STATUS: **{status}**\n\n"
            f"Detail Teknis:\n"
            f"IP Asli: `{ip}`\n"
            f"Keterangan: {detail}"
        )
        
        await update.message.reply_text(result_text, parse_mode='Markdown')

# --- Fungsi Penjadwalan (Alerting) ---
# ... (send_interval_info tetap sama) ...
async def send_interval_info(application: Application):
    """Fungsi yang dipanggil oleh Job Queue: Mengirim laporan AMAN dan DIBLOKIR."""
    logger.info("Menjalankan tugas cek domain 2 jam (V3.2 - Cron Optimized)...")
    
    blocked_results = []
    safe_results = []
    total_monitored = len(DOMAINS_TO_MONITOR)

    for domain in DOMAINS_TO_MONITOR:
        status, ip, detail = check_blocking_status(domain)
        
        if "❌ DIBLOKIR!" in status:
            blocked_results.append(f"• 🚨 `{domain}`: **{status}** (IP: `{ip}`)")
        else:
            safe_results.append(f"• ✅ `{domain}`: **{status}**")
            
    header_
