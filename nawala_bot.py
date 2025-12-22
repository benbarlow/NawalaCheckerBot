from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update, error
import logging
import requests
from bs4 import BeautifulSoup
import datetime
import time

# --- Konfigurasi Log ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION (DATA ANDA) ---
TOKEN = "8312452980:AAHjQa_m6HPT5-MtLUxkxlivUh7ZxeGOubg"  
TARGET_CHAT_ID = "7038651668"  

# DATA PROXY PRIBADI ANDA (Sesuai gambar detail pesanan)
# Format: socks5://username:password@ip:port
PROXY_URL = "socks5://bernardabraham90:bky7zsB5tA@193.5.64.78:50101" 

# Daftar Domain Pantauan
DOMAINS_TO_MONITOR = [
    "aksesbatikslot.vip",  
    "aksesbatikslot.com",  
    "batikslot-win.fashion",
    "aksesbatikslot.org",  
    "batikslot.space",
]

# Keyword pemblokiran yang sering muncul di ISP Indonesia
BLOCKING_KEYWORDS = [
    "internet positif",    
    "internet sehat",
    "access denied",
    "dialihkan",
    "blokir",
    "kominfo",
    "trust-positive",
]

def check_blocking_status(domain):
    """Mengecek status domain menggunakan Proxy Indonesia Anda."""
    url = f"http://{domain}"
    
    proxies = {
        'http': PROXY_URL,
        'https': PROXY_URL,
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    try:
        # Melakukan request melalui Proxy Indonesia
        # allow_redirects=True sangat penting untuk mendeteksi pengalihan ke Nawala
        response = requests.get(url, headers=headers, proxies=proxies, timeout=20, allow_redirects=True)
        
        # 1. Cek jika URL akhir mengandung kata kunci blokir (Nawala Redirect)
        final_url = response.url.lower()
        if any(kw in final_url for kw in ["internet-positif", "trust-positive", "block-page"]):
            return "❌ DIBLOKIR! (Redirect Nawala)", "N/A", "Situs dialihkan ke halaman Internet Positif oleh ISP."

        # 2. Cek konten halaman (Web Scraping)
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text().lower()

        for keyword in BLOCKING_KEYWORDS:
            if keyword in page_text:
                return "❌ DIBLOKIR! (Konten Terdeteksi)", "N/A", f"Ditemukan kata kunci blokir: '{keyword}'"
        
        # 3. Cek Status Code HTTP
        if response.status_code >= 400:
            return f"⚠️ PERINGATAN (HTTP {response.status_code})", "N/A", "Situs memberikan respon error, kemungkinan diblokir atau server down."

        return "✅ AMAN (Konten Bersih)", "N/A", "Berhasil diakses melalui Proxy Indonesia tanpa hambatan."

    except requests.exceptions.ProxyError:
        return "🚨 PROXY ERROR", "N/A", "Gagal konek ke Proxy. Pastikan IP bot sudah di-whitelist di Proxy-Seller."
    except requests.exceptions.Timeout:
        return "❓ GAGAL (Timeout)", "N/A", "Koneksi lambat, biasanya indikasi blokir keras."
    except requests.exceptions.ConnectionError:
        return "❌ DIBLOKIR! (Connection Refused)", "N/A", "Koneksi ditolak oleh ISP Indonesia (Blokir Port/IP)."
    except Exception as e:
        return "🚨 ERROR", "N/A", f"Kendala teknis: {e}"

# --- Fungsi Handler Telegram ---

async def dom_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_domain = context.args[0].lower().strip() if context.args else None
    if not new_domain:
        await update.message.reply_text("Contoh: `/dom_add contoh.com`", parse_mode='Markdown')
        return
    if new_domain not in DOMAINS_TO_MONITOR:
        DOMAINS_TO_MONITOR.append(new_domain)
        await update.message.reply_text(f"✅ `{new_domain}` ditambahkan.", parse_mode='Markdown')

async def dom_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    list_items = '\n'.join([f"• `{d}`" for d in sorted(DOMAINS_TO_MONITOR)])
    await update.message.reply_text(f"*** [DAFTAR MONITORING] ***\n\n{list_items}", parse_mode='Markdown')

async def echo_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domain = update.message.text.lower().strip()
    if '.' in domain and ' ' not in domain:
        await update.message.reply_text(f"🔎 Mengecek `{domain}` via Proxy Indo...", parse_mode='Markdown')
        status, _, detail = check_blocking_status(domain)
        res = f"*** [HASIL CEK] ***\nDomain: `{domain}`\nSTATUS: **{status}**\nDetail: {detail}"
        await update.message.reply_text(res, parse_mode='Markdown')

async def send_interval_info(context: ContextTypes.DEFAULT_TYPE):
    application = context.application
    blocked = []
    safe = []
    
    for domain in DOMAINS_TO_MONITOR:
        status, _, _ = check_blocking_status(domain)
        if "❌" in status:
            blocked.append(f"• 🚨 `{domain}`")
        else:
            safe.append(f"• ✅ `{domain}`")
            
    msg = f"*** [LAPORAN OTOMATIS] ***\n\n❌ **BLOKIR ({len(blocked)}):**\n" + "\n".join(blocked) + \
          f"\n\n✅ **AMAN ({len(safe)}):**\n" + "\n".join(safe)
    
    await application.bot.send_message(chat_id=TARGET_CHAT_ID, text=msg, parse_mode='Markdown')

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("dom_add", dom_add))
    app.add_handler(CommandHandler("dom_list", dom_list))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_domain))
    
    # Menjalankan laporan otomatis setiap 2 jam (7200 detik)
    app.job_queue.run_repeating(send_interval_info, interval=7200, first=10)
    
    print("Bot Monitoring Aktif dengan Proxy Indonesia...")
    app.run_polling()

if __name__ == "__main__":
    main()
