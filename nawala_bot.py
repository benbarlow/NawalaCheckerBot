from telegram.ext import Application
import logging
import socket
import requests
from bs4 import BeautifulSoup
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
    "konten negatif",           # Frasa umum yang digunakan operator ISP
    "blocked due to content",   # Teks umum jika diblokir oleh CDN
    "akun anda ditangguhkan"    # Frasa di halaman blokir tertentu
]

# IP Pemblokiran Umum di Indonesia (Deteksi Akurat)
# CATATAN: PENGHAPUSAN IP BLOKIR TIDAK DISARANKAN. Bot ini menggunakan IP di bawah ini
# untuk deteksi yang akurat. Jika ada perubahan IP Blokir di masa depan, sebaiknya IP lama dihapus
# dan IP baru ditambahkan.
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


# --- Fungsi Penjadwalan (Alerting) yang Dioptimalkan untuk Cron Job ---

async def send_interval_info(application: Application):
    """Fungsi yang dipanggil oleh Cron Job: Mengirim laporan AMAN dan DIBLOKIR."""
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
            
    # KODE PESAN LAPORAN LENGKAP (AMAN dan DIBLOKIR)
    header_text = f"*** [LAPORAN OTOMATIS DOMAIN] ***\n"
    timestamp = f"Waktu Cek: {datetime.datetime.now().strftime('%d %b %Y, %H:%M:%S WIB')}\n"
    
    # 1. Bagian yang DIBLOKIR (ALERT)
    if blocked_results:
        blocked_section = (
            f"\n--- ❌ ALERT BLOKIR DITEMUKAN ({len(blocked_results)} Domain) ---\n"
            f"{'\n'.join(blocked_results)}\n"
            f"Tindakan: Segera ganti DNS domain-domain ini!"
        )
    else:
        blocked_section = "\n--- ❌ ALERT BLOKIR: TIDAK ADA (Semua OK) ---"

    # 2. Bagian yang AMAN (Laporan Rutin)
    safe_section = (
        f"\n--- ✅ STATUS AMAN ({len(safe_results)} Domain) ---\n"
        f"{'\n'.join(safe_results)}"
    )
    
    message_text = header_text + timestamp + blocked_section + safe_section

    try:
        await application.bot.send_message(
            chat_id=TARGET_CHAT_ID, 
            text=message_text, 
            parse_mode='Markdown'
        )
        logger.info(f"Laporan berhasil dikirim (Total: {total_monitored} domain) ke chat ID {TARGET_CHAT_ID}")
    except Exception as e:
        logger.error(f"Gagal mengirim Laporan Otomatis. Error: {e}")

# --- Fungsi Utama (Dioptimalkan untuk Cron Job) ---

def main():
    """Fungsi utama yang hanya akan memicu pengecekan sekali untuk Cron Job."""
    application = Application.builder().token(TOKEN).build()
    
    # Karena kita menggunakan Cron Job, kita hanya perlu menjalankan fungsi async sekali
    # tanpa perlu 'run_polling'. Cron yang akan mengulang eksekusi setiap 2 jam.
    
    # Jalankan fungsi send_interval_info secara langsung
    import asyncio
    asyncio.run(send_interval_info(application))
    
    # CATATAN: application.job_queue dan handler (start_command, check_domain)
    # dihapus karena bot dijalankan setiap 2 jam oleh Cron, bukan 24/7 oleh run_polling.

if __name__ == '__main__':
    main()
