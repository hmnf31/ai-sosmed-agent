import os

from dotenv import load_dotenv

from utils.scraper import get_trends
from utils.ai_generator import generate_caption
from utils.instagram import publish_to_instagram
from utils.image_maker import render_trend_image
from utils.video_maker import render_trend_video
from utils.notifier import send_telegram_notification, send_telegram_photo, send_telegram_video
from utils import tiktok

# Load variabel lingkungan untuk pengembangan lokal
load_dotenv()


def dry_run_enabled():
    if os.getenv("DRY_RUN", "false").strip().lower() in ("1", "true", "yes", "on"):
        return True
    return not tiktok.is_enabled()


def preview_format():
    return os.getenv("PREVIEW_FORMAT", "video").strip().lower()


def current_niche():
    return os.getenv("CONTENT_NICHE", "general").strip().lower()


def run_agent():
    niche = current_niche()
    print("=== [MULAI SIKLUS AI SOSMED AGENT] ===")

    if tiktok.is_enabled():
        mode = "PUBLISH ke TikTok (niche: mlbb)"
    elif dry_run_enabled():
        mode = f"PREVIEW ke Telegram (niche: {niche})"
    else:
        mode = "PUBLISH ke Instagram"
    print(f"[MAIN] Mode: {mode}")

    try:
        # 1. Riset Tren
        trends = get_trends(niche=niche)

        # 2. Generasi Caption via AI
        caption = generate_caption(trends, niche=niche)

        # 3. Render media
        if preview_format() == "image":
            media_path = render_trend_image(trends)
        else:
            media_path = render_trend_video(trends)

        # 4. Publikasi
        if tiktok.is_enabled():
            account = tiktok.get_user_info()
            handle = account.get("display_name", "tidak diketahui")
            result = tiktok.publish_video(media_path, caption)
            message = (
                f"🎮 *AI Agent TikTok: Sukses!*\n\n"
                f"*Niche:* {niche}\n"
                f"*Akun:* {handle} (`{account.get('open_id', '?')}`)\n"
                f"*Topik:* {', '.join(trends)}\n"
                f"*Publish ID:* `{result.get('publish_id')}`\n"
                f"*Status:* {result.get('status')}\n"
                f"*Video:* `{media_path}`"
            )
            send_telegram_notification(message)
            print(f"\n--- CAPTION ---\n{caption}\n")
        elif dry_run_enabled():
            if preview_format() == "image":
                media_ok = send_telegram_photo(media_path, caption)
            else:
                media_ok = send_telegram_video(media_path, caption)

            message = (
                f"🆗 *Preview AI Agent (siap posting manual)*\n\n"
                f"*Niche:* {niche}\n"
                f"*Topik Tren:* {', '.join(trends)}\n"
                f"*Media:* `{media_path}`\n"
                f"*Terkirim ke Telegram:* {'ya' if media_ok else 'tidak'}"
            )
            send_telegram_notification(message)
            print(f"\n--- CAPTION (siap disalin ke media sosial) ---\n{caption}\n")
        else:
            sample_image_url = "https://picsum.photos/1080/1080"
            post_id = publish_to_instagram(sample_image_url, caption)

            success_msg = (
                f"✅ *AI Agent Report: Sukses Posting!*\n\n"
                f"*Niche:* {niche}\n"
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