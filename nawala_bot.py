from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
import logging
import socket
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime

# --- Konfigurasi ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# NILAI KONFIGURASI ANDA (SUDAH DIMASUKKAN)
TOKEN = "8312452980:AAG4od8CYHuUgvs6M7UryWx8gCkXTcDsXMk" 
TARGET_CHAT_ID = "7038651668" 

# Target Domain untuk dipantau (UBAH JIKA PERLU)
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
    "kementerian komunikasi",   # Umumnya ada di header halaman blokir
    "konten negatif",            # Frasa umum yang digunakan operator ISP
    "blocked due to content",    # Teks umum jika diblokir oleh CDN
    "akun anda ditangguhkan"    # Frasa di halaman blokir tertentu
]

# IP Pemblokiran Umum di Indonesia (Deteksi Akurat)
BLOCKING_IPS = [
    '103.1.208.57',  # IP Nawala / TrustPositif lama
    '104.244.48.91', # Salah satu IP umum TrustPositif
    '15.197.225.128', # IP dari kasus batikslot.work
    '104.21.67.48',  # IP dari kasus infortpbatik99.vip sebelumnya
    '172.67.213.207',  # <--- IP BARU DITEMUKAN
]


# --- Fungsi Pengecekan Akurat (Deteksi IP & Web Scraping) ---

def check_blocking_status(domain):
    """Mengecek status domain dengan Deteksi IP (lebih akurat) dan Web Scraping."""
    url = f"http://{domain}" 
    
    ip_address = "N/A"

    # --- 1. DETEKSI DNS/IP (Tingkat Paling Akurat) ---
    try:
        # Lakukan DNS Lookup untuk mendapatkan IP asli
        ip_address = socket.gethostbyname(domain)
        
        # Cek apakah IP yang didapat adalah IP Pemblokiran
        if ip_address in BLOCKING_IPS:
            return "❌ DIBLOKIR! (IP Blokir Ditemukan)", ip_address, "Domain dialihkan ke IP Pemblokiran Umum."
            
    except socket.gaierror:
        # Jika Domain tidak ditemukan, catat error dan keluar.
        return "❓ INVALID", "Domain tidak ditemukan (DNS Error)", "N/A"
    except Exception as e:
        # Jika terjadi error lain, catat dan lanjutkan ke Web Scraping
        logger.warning(f"Error DNS Lookup untuk {domain}: {e}")
        pass

    # --- 2. WEB SCRAPING (Jika IP Asli Ditemukan atau DNS Error) ---
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15) 
        
        status_code_info = f"HTTP Status {response.status_code}. " if response.status_code >= 400 else ""

        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text().lower() 

        # Cek Kata Kunci Pemblokiran
        for keyword in BLOCKING_KEYWORDS:
            if keyword in page_text:
                return "❌ DIBLOKIR! (Konten Blokir Ditemukan)", ip_address, f"{status_code_info}Keyword '{keyword}' ditemukan di halaman."
        
        # Jika lolos kedua tes (IP bersih & konten bersih)
        return "✅ AMAN (IP & Konten Bersih)", ip_address, f"{status_code_info}Akses berhasil. Konten bersih."

    except requests.exceptions.Timeout:
        return "❓ GAGAL (Timeout)", ip_address, "Akses melebihi batas waktu (sering terjadi jika diblokir keras)"
    except requests.exceptions.ConnectionError:
        return "❓ GAGAL (Koneksi Error)", ip_address, "Gagal tersambung (sering terjadi jika diblokir)"
    except Exception as e:
        return "🚨 ERROR", ip_address, f"Terjadi Error: {e}"


# --- Fungsi Handler dan Penjadwalan ---

async def start_command(update: Update, context):
    """Mengirim pesan selamat datang ketika perintah /start diterima."""
    await update.message.reply_text("Halo! Bot Pengecek Domain Anti Nawala (v3.2 - Akurat) sudah aktif. 🛡️\n\nSilakan kirimkan nama domain yang ingin Anda cek (contoh: google.com).")

async def check_domain(update: Update, context):
    """Merespons pesan teks (domain) dengan hasil pengecekan Akurat."""
    domain = update.message.text.strip().lower().replace("http://", "").replace("https://", "").split("/")[0]

    await update.message.reply_text(f"Mengecek status domain: `{domain}`...", parse_mode='Markdown')
    
    status, ip, detail = check_blocking_status(domain)
    
    response_text = (
        f"**[ HASIL CEK DOMAIN ]**\n"
        f"Domain: `{domain}`\n\n"
        f"**STATUS: {status}**\n\n"
        f"Detail Teknis:\nIP Asli: `{ip}`\nKeterangan: {detail}"
    )
    
    await update.message.reply_text(response_text, parse_mode='Markdown')

# --- Fungsi Penjadwalan (Alerting) ---

async def send_interval_info(application: Application):
    """Tugas yang dijadwalkan: Mengirim laporan hanya jika ada domain yang diblokir."""
    logger.info("Menjalankan tugas interval 3 jam (V3.2 - Alerting)...")
    
    blocked_results = []
    total_monitored = len(DOMAINS_TO_MONITOR)

    for domain in DOMAINS_TO_MONITOR:
        status, ip, detail = check_blocking_status(domain)
        
        if "❌ DIBLOKIR!" in status:
            blocked_results.append(f"• 🚨 `{domain}`: **{status}**")
        
    if not blocked_results:
        logger.info(f"Semua {total_monitored} domain AMAN. Tidak ada notifikasi dikirim.")
        return

    # KODE PESAN PERINGATAN (Menggunakan format yang kuat untuk menghindari error copy-paste)
    message_text = (
        f"*** [ALERT NAWALA DITEMUKAN!] ***\n\n"
        f"Ditemukan **{len(blocked_results)}** domain diblokir dari {total_monitored} domain yang dipantau per {datetime.datetime.now().strftime('%d %b %Y %H:%M:%S')}:\n\n"
        f"{''.join(blocked_results)}\n\n"
        f"Segera ganti DNS domain-domain ini!"
    )
    
    try:
        await application.bot.send_message(
            chat_id=TARGET_CHAT_ID, 
            text=message_text, 
            parse_mode='Markdown'
        )
        logger.warning(f"ALERT NAWALA berhasil dikirim untuk {len(blocked_results)} domain ke chat ID {TARGET_CHAT_ID}")
    except Exception as e:
        logger.error(f"Gagal mengirim ALERT otomatis. Error: {e}")

# --- Fungsi Utama ---

def main():
    # 1. Buat aplikasi bot
    application = Application.builder().token(TOKEN).build()
    
    # 2. Tambahkan handler
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_domain))
    
    # 3. Tambahkan pekerjaan berulang (Penjadwalan)
    # Jalankan cek setiap 3 jam
    application.job_queue.run_repeating(
        send_interval_info, 
        interval=datetime.timedelta(hours=3), 
        first=0
    )

    # 4. Mulai bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
