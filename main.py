import os

from dotenv import load_dotenv

from utils.scraper import get_google_trends
from utils.ai_generator import generate_caption
from utils.instagram import publish_to_instagram
from utils.notifier import send_telegram_notification

# Load variabel lingkungan untuk pengembangan lokal
load_dotenv()


def run_agent():
    print("=== [MULAI SIKLUS AI SOSMED AGENT] ===")

    try:
        # 1. Riset Tren
        trends = get_google_trends()

        # 2. Generasi Caption via AI
        caption = generate_caption(trends)

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