"""Klien TikTok Content Posting API.

Alur unggah resmi TikTok:
  1. tukar refresh token -> access token  (POST /v2/oauth/token/)
  2. cek akun tujuan       (GET  /v2/user/info/)
  3. inisialisasi unggahan (POST /v2/post/publish/video/init/)
  4. upload binary per chunk ke upload_url (PUT)
  5. poll status           (POST /v2/post/publish/status/fetch/)
"""
import os
import time

import requests

API_BASE = "https://open.tiktokapis.com/v2"
TOKEN_URL = f"{API_BASE}/oauth/token/"
USER_INFO_URL = f"{API_BASE}/user/info/"
INIT_URL = f"{API_BASE}/post/publish/video/init/"
STATUS_URL = f"{API_BASE}/post/publish/status/fetch/"
TIMEOUT = 60

PRIVACY_LEVELS = ("PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY")


def _describe(response):
    """Ringkasan error TikTok: TikTok membungkus detail di objek 'error', bukan 'data'."""
    body = _payload(response)
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        parts = [f"HTTP {response.status_code}"]
        if error.get("code") and error["code"] != "ok":
            parts.append(str(error["code"]))
        if error.get("message"):
            parts.append(str(error["message"]))
        if error.get("log_id"):
            parts.append(f"log_id {error['log_id']}")
        return " | ".join(parts)
    if body:
        return f"HTTP {response.status_code}: {body}"
    raw = (response.text or "").strip()
    return f"HTTP {response.status_code}: {raw[:200]}" if raw else f"HTTP {response.status_code} (respons kosong)"


def _payload(response):
    """TikTok mengembalikan payload datar; sebagian endpoint membungkusnya di 'data'."""
    try:
        body = response.json()
    except ValueError:
        return {}
    if isinstance(body, dict):
        inner = body.get("data")
        if isinstance(inner, dict):
            return inner
    return body if isinstance(body, dict) else {}


class TikTokError(Exception):
    pass


def is_enabled():
    return os.getenv("TIKTOK_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


def _required(name, value):
    if not value:
        raise TikTokError(f"{name} belum diisi di .env")
    return value


def build_authorize_url(client_key=None, redirect_uri=None, scope=None, state="ai-sosmed-agent"):
    client_key = _required("TIKTOK_CLIENT_KEY", client_key or os.getenv("TIKTOK_CLIENT_KEY"))
    redirect_uri = _required("TIKTOK_REDIRECT_URI", redirect_uri or os.getenv("TIKTOK_REDIRECT_URI"))
    scope = scope or os.getenv("TIKTOK_SCOPE") or "video.publish,user.info.basic"
    return (
        "https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={client_key}&response_type=code"
        f"&scope={scope}&redirect_uri={redirect_uri}&state={state}"
    )


def exchange_authorization_code(code, client_key=None, client_secret=None, redirect_uri=None):
    """Menukar authorization code jadi access_token + refresh_token."""
    client_key = _required("TIKTOK_CLIENT_KEY", client_key or os.getenv("TIKTOK_CLIENT_KEY"))
    client_secret = _required("TIKTOK_CLIENT_SECRET", client_secret or os.getenv("TIKTOK_CLIENT_SECRET"))
    redirect_uri = _required("TIKTOK_REDIRECT_URI", redirect_uri or os.getenv("TIKTOK_REDIRECT_URI"))

    response = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=TIMEOUT,
    )
    data = _payload(response)
    if response.status_code != 200 or not data.get("access_token"):
        raise TikTokError(f"Tukar kode gagal: {_describe(response)}")
    return data


def refresh_access_token(refresh_token=None):
    """Mengambil access token baru dari refresh token (ber umur panjang)."""
    refresh_token = _required("TIKTOK_REFRESH_TOKEN", refresh_token or os.getenv("TIKTOK_REFRESH_TOKEN"))
    client_key = _required("TIKTOK_CLIENT_KEY", os.getenv("TIKTOK_CLIENT_KEY"))
    client_secret = _required("TIKTOK_CLIENT_SECRET", os.getenv("TIKTOK_CLIENT_SECRET"))

    response = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    data = _payload(response)
    if response.status_code != 200 or not data.get("access_token"):
        raise TikTokError(f"Refresh token gagal: {_describe(response)}")
    return data


def get_access_token():
    """Access token dari env bila tersedia, hasil refresh bila tidak."""
    cached = (os.getenv("TIKTOK_ACCESS_TOKEN") or "").strip()
    if cached and not cached.lower().startswith("sk-"):
        return cached
    tokens = refresh_access_token()
    print(f"[TIKTOK] Access token diperbarui, berlaku {tokens.get('expires_in')} detik.")
    return tokens["access_token"]


def get_user_info(access_token=None):
    access_token = access_token or get_access_token()
    response = requests.get(
        USER_INFO_URL,
        params={"fields": "open_id,union_id,avatar_url,display_name"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT,
    )
    data = _payload(response)
    if response.status_code != 200:
        raise TikTokError(f"Gagal ambil info akun: {_describe(response)}")
    user = data.get("user")
    return user if isinstance(user, dict) else data


def _chunk_size():
    mb = int(os.getenv("TIKTOK_CHUNK_SIZE_MB") or 10)
    return max(5, min(100, mb)) * 1024 * 1024


def _video_size(path):
    if not os.path.exists(path):
        raise TikTokError(f"File video tidak ditemukan: {path}")
    return os.path.getsize(path)


def _upload_binary(upload_url, path, chunk_size, max_retries=3):
    total = _video_size(path)
    total_chunks = max(1, (total + chunk_size - 1) // chunk_size)
    print(f"[TIKTOK] Mengunggah {total / (1024 * 1024):.2f} MB dalam {total_chunks} chunk...")

    with open(path, "rb") as handle:
        for index in range(total_chunks):
            data = handle.read(chunk_size)
            start = index * chunk_size
            end = start + len(data) - 1
            headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{end}/{total}",
            }
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    response = requests.put(upload_url, data=data, headers=headers, timeout=300)
                    if response.status_code in (200, 201, 204):
                        last_error = None
                        break
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                except requests.RequestException as e:
                    last_error = str(e)
                if attempt < max_retries:
                    time.sleep(2 * attempt)
            if last_error:
                raise TikTokError(f"Upload chunk {index + 1}/{total_chunks} gagal: {last_error}")

    print("[TIKTOK] Seluruh chunk terunggah.")


def _fetch_status(publish_id, access_token):
    response = requests.post(
        STATUS_URL,
        json={"publish_id": publish_id, "access_token": access_token},
        timeout=TIMEOUT,
    )
    data = _payload(response)
    if response.status_code != 200:
        raise TikTokError(f"Gagal cek status: {_describe(response)}")
    return data


def publish_video(video_path, caption, access_token=None, privacy_level=None, wait=True, poll_seconds=90):
    """Mengunggah video ke akun TikTok dan mengembalikan dict hasil publikasi."""
    access_token = access_token or get_access_token()
    privacy_level = privacy_level or os.getenv("TIKTOK_PRIVACY_LEVEL") or "PUBLIC_TO_EVERYONE"
    if privacy_level not in PRIVACY_LEVELS:
        raise TikTokError(f"TIKTOK_PRIVACY_LEVEL tidak valid: {privacy_level}")

    size = _video_size(video_path)
    chunk_size = _chunk_size()
    total_chunks = max(1, (size + chunk_size - 1) // chunk_size)

    init_response = requests.post(
        INIT_URL,
        json={
            "post_info": {
                "title": (caption or "")[:2200],
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "UPLOAD",
                "video_size": size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
                "video_width": 1080,
                "video_height": 1920,
            },
            "access_token": access_token,
        },
        timeout=TIMEOUT,
    )
    if init_response.status_code != 200:
        raise TikTokError(f"Inisialisasi unggah gagal: {_describe(init_response)}")

    payload = _payload(init_response)
    publish_id = payload.get("publish_id")
    upload_url = payload.get("upload_url")
    if not publish_id or not upload_url:
        raise TikTokError(f"Respons init tidak lengkap: {payload}")

    _upload_binary(upload_url, video_path, chunk_size)

    if not wait:
        return {"publish_id": publish_id, "status": "UPLOADED"}

    deadline = time.time() + poll_seconds
    status = "PROCESSING"
    while time.time() < deadline:
        info = _fetch_status(publish_id, access_token)
        status = info.get("status", "UNKNOWN")
        print(f"[TIKTOK] Status: {status}")
        if status == "PUBLISH_COMPLETE":
            return {"publish_id": publish_id, "status": status, "detail": info}
        if status == "FAILED":
            raise TikTokError(f"Unggahan ditolak TikTok: {info.get('fail_reason') or info}")
        time.sleep(10)

    return {"publish_id": publish_id, "status": status}