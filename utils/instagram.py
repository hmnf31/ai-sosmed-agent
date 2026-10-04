import os
import requests


def publish_to_instagram(image_url, caption):
    """Mengunggah gambar dan caption ke Instagram Bisnis via Meta Graph API."""
    ig_user_id = os.getenv("IG_USER_ID")
    access_token = os.getenv("IG_ACCESS_TOKEN")

    if not ig_user_id or not access_token:
        raise ValueError("IG_USER_ID atau IG_ACCESS_TOKEN belum diset!")

    # Step 1: Buat Media Container
    container_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
    container_payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    }

    print("[INSTAGRAM] Membuat container media...")
    r_container = requests.post(container_url, data=container_payload)
    res_container = r_container.json()

    if "id" not in res_container:
        raise Exception(f"Gagal membuat container media IG: {res_container}")

    creation_id = res_container["id"]

    # Step 2: Publish Container
    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": access_token,
    }

    print("[INSTAGRAM] Mengunggah postingan ke Instagram...")
    r_publish = requests.post(publish_url, data=publish_payload)
    res_publish = r_publish.json()

    if "id" not in res_publish:
        raise Exception(f"Gagal publish postingan IG: {res_publish}")

    print(f"[INSTAGRAM] Postingan berhasil dipublikasikan! Post ID: {res_publish['id']}")
    return res_publish["id"]