from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update, error
import logging
import socket
import requests
from bs4 import BeautifulSoup
import datetime
import asyncio
import time # Tambah import time

# --- Konfigurasi ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# NILAI KONFIGURASI ANDA (SUDAH DIMASUKKAN)
TOKEN = "8312452980:AAG4od8CYHuUgvs6M7UryWx8gCkXTcDsXMk"  
TARGET_CHAT_ID = "7038651668"  

# --- KONFIGURASI PROXY BARU ---
# Status saat ini: NON-AKTIF untuk menghindari crash.
PROXY_URL = 'http://16.78.93.162:761' # <<< JANGAN UBAH INI DULU

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
def check_blocking_status(domain):
    """Mengecek status domain dengan Deteksi IP (lebih akurat) dan Web Scraping melalui Proxy."""
    url = f"http://{domain}"  
    ip_address = "N/A"
    
    # KONFIGURASI PROXY
    proxies = {}
    if PROXY_URL:
        proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL,
        }

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

    # --- 2. WEB SCRAPING (MEMAKAI PROXY INDONESIA) ---
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        # Requests menggunakan proxy yang dikonfigurasi di atas
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)  
        
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
        # Jika proxy gagal atau koneksi domain gagal, asumsikan itu diblokir
        if proxies:
            return "❓ GAGAL (Koneksi Error melalui Proxy)", ip_address, "Proxy gagal terhubung ke domain (kemungkinan diblokir keras)"
        else:
             return "❓ GAGAL (Koneksi Error)", ip_address, "Gagal tersambung (sering terjadi jika diblokir)"
    except Exception as e:
        return "🚨 ERROR", ip_address, f"Terjadi Error: {e}"


# --- FUNGSI DOMAIN MANAGEMENT & CHAT INSTAN ---
# (Semua fungsi ini tetap sama, hanya kode di main yang diubah)

async def dom_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    if DOMAINS_TO_MONITOR:
        list_items = '\n'.join([f"• `{d}`" for d in sorted(DOMAINS_TO_MONITOR)])
        response_text = (
            f"*** [DAFTAR DOMAIN AKTIF DIPANTAU ({len(DOMAINS_TO_MONITOR)})] ***\n\n"
            f"{list_items}"
        )
    else:
        response_text = "Daftar pemantauan kosong. Tambahkan domain dengan /dom_add."
        
    await update.message.reply_text(response_text, parse_mode='Markdown')


async def check_domain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await dom_list(update, context)  

async def echo_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
async def send_interval_info(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Menjalankan tugas cek domain 2 jam (V3.2 - Cron Optimized Job Queue)...")
    
    application = context.application  
    
    blocked_results = []
    safe_results = []
    total_monitored = len(DOMAINS_TO_MONITOR)

    for domain in DOMAINS_TO_MONITOR:
        status, ip, detail = check_blocking_status(domain)
        
        if "❌ DIBLOKIR!" in status:
            blocked_results.append(f"• 🚨 `{domain}`: **{status}** (IP: `{ip}`)")
        else:
            safe_results.append(f"• ✅ `{domain}`: **{status}**")
            
    header_text = f"*** [LAPORAN OTOMATIS DOMAIN] ***\n"
    timestamp = f"Waktu Cek: {datetime.datetime.now().strftime('%d %b %Y, %H:%M:%S WIB')}\n"
    
    if blocked_results:
        blocked_section = (
            f"\n--- ❌ ALERT BLOKIR DITEMUKAN ({len(blocked_results)} Domain) ---\n"
            f"{'\n'.join(blocked_results)}\n"
            f"Tindakan: Segera ganti DNS domain-domain ini!"
        )
    else:
        blocked_section = "\n--- ❌ ALERT BLOKIR: TIDAK ADA (Semua OK) ---"

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
    except error.BadRequest:
        logger.error("Gagal mengirim pesan: Chat ID tidak valid atau bot tidak diizinkan.")
    except Exception as e:
        logger.error(f"Gagal mengirim Laporan Otomatis. Error: {e}")


# --- Fungsi Utama (FINAL: Polling 24/7) ---

def main():
    logger.info("Bot Starting...")
    application = Application.builder().token(TOKEN).build()
    job_queue = application.job_queue # <<< DEKLARASI job_queue DI SINI
    
    # 1. MENAMBAH HANDLER CHAT (RESPONS INSTAN)
    application.add_handler(CommandHandler("list_domain", check_domain_command))
    application.add_handler(CommandHandler("dom_add", dom_add))
    application.add_handler(CommandHandler("dom_del", dom_del))
    application.add_handler(CommandHandler("dom_list", dom_list))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_domain))
    
    # 2. MENAMBAH PENJADWALAN OTOMATIS (LAPORAN 2 JAM)
    # Jadwal diatur untuk berjalan setiap 7200 detik (2 jam)
    # Gunakan first=None agar job langsung dijalankan saat bot start
    job_queue.run_repeating(send_interval_info, interval=7200, first=time.time()) 
    
    # 3. MEMULAI POLLING BOT (WAJIB!)
    logger.info("Bot Started! Polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES) # <<< MENJALANKAN BOT
    
if __name__ == "__main__":
    main()
