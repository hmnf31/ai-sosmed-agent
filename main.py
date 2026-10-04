import os

from dotenv import load_dotenv

from utils.scraper import get_google_trends
from utils.ai_generator import generate_caption
from utils.instagram import publish_to_instagram
from utils.image_maker import render_trend_image
from utils.notifier import send_telegram_notification, send_telegram_photo

# Load variabel lingkungan untuk pengembangan lokal
load_dotenv()


def dry_run_enabled():
    return os.getenv("DRY_RUN", "false").strip().lower() in ("1", "true", "yes", "on")


def run_agent():
    print("=== [MULAI SIKLUS AI SOSMED AGENT] ===")
    mode = "PREVIEW (kirim ke Telegram)" if dry_run_enabled() else "PUBLISH (Instagram Graph API)"
    print(f"[MAIN] Mode: {mode}")

    try:
        # 1. Riset Tren
        trends = get_google_trends()

        # 2. Generasi Caption via AI
        caption = generate_caption(trends)

        if dry_run_enabled():
            # 3. Render kartu tren + kirim ke Telegram untuk diposting manual
            image_path = render_trend_image(trends)
            photo_ok = send_telegram_photo(image_path, caption)

            message = (
                f"🆗 *Preview AI Agent (siap posting manual)*\n\n"
                f"*Topik Tren:* {', '.join(trends)}\n"
                f"*Gambar:* `{image_path}`\n"
                f"*Foto terkirim ke Telegram:* {'ya' if photo_ok else 'tidak'}"
            )
            send_telegram_notification(message)
            print(f"\n--- CAPTION (siap disalin ke Instagram) ---\n{caption}\n")
        else:
            # 3. Tentukan URL Gambar (Gambar sampel high quality atau image generator)
            sample_image_url = "https://picsum.photos/1080/1080"

            # 4. Upload ke Instagram
            post_id = publish_to_instagram(sample_image_url, caption)

            # 5. Kirim Notifikasi Sukses
            success_msg = (
                f"✅ *AI Agent Report: Sukses Posting!*\n\n"
                f"*Topik Tren:* {', '.join(trends)}\n"
                f"*Post ID IG:* `{post_id}`"
            )
            send_telegram_notification(success_msg)

    except Exception as e:
        error_msg = f"❌ *AI Agent Report: Gagal!*\n\n*Error Detail:* `{str(e)}`"
        print(f"[MAIN ERROR] {e}")
        send_telegram_notification(error_msg)

    print("=== [SIKLUS SELESAI] ===")


if __name__ == "__main__":
    run_agent()