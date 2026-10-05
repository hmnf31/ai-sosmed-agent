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

PRIVACY_LEVELS = ("PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY")
POST_MODES = ("DIRECT_POST", "MEDIA_UPLOAD")

MIN_CHUNK_BYTES = 5 * 1024 * 1024
MAX_CHUNK_BYTES = 64 * 1024 * 1024
MAX_CHUNKS = 1000


ERROR_HINTS = {
    "unaudited_client_can_only_post_to_private_accounts": (
        "Aplikasi belum lolos audit TikTok, jadi init unggah ditolak Apa pun privacy_level. "
        "Ajukan audit di developer.tiktok.com > Manage Apps > Audit, atau pakai draft lewat "
        "Tiktok UI sampai audit selesai."
    ),
    "scope_not_authorized": (
        "Scope akun ini belum memberi izin posting. Jalankan ulang scripts/tiktok_oauth.py "
        "setelah memberi izin video.publish atau video.upload."
    ),
    "spam_risk_too_many_posts": "Kuota harian posting API untuk akun ini sudah habis.",
    "spam_risk_user_banned_from_posting": "Akun TikTok dilarang melakukan posting.",
    "rate_limit_exceeded": "Terlalu banyak permintaan API. Tunggu sebentar sebelum mencoba lagi.",
    "invalid_publish_id": "publish_id tidak dikenal TikTok.",
    "url_ownership_unverified": (
        "PULL_FROM_URL butuh verifikasi kepemilikan domain di developer.tiktok.com. "
        "Gunakan source=FILE_UPLOAD yang tidak butuh verifikasi."
    ),
}


def _describe(response):
    """Ringkasan error TikTok: TikTok membungkus detail di objek 'error', bukan 'data'."""
    body = _payload(response)
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        parts = [f"HTTP {response.status_code}"]
        code = error.get("code")
        if code and code != "ok":
            parts.append(str(code))
        if error.get("message"):
            parts.append(str(error["message"]))
        if error.get("log_id"):
            parts.append(f"log_id {error['log_id']}")
        if code in ERROR_HINTS:
            parts.append(ERROR_HINTS[code])
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


def granted_scopes():
    """Scope yang benar-benar diberikan user, dibaca dari respons refresh token."""
    return (refresh_access_token().get("scope") or "").strip()


def require_scope(needed):
    """Memicat TikTokError bila scope yang dibutuhkan belum diberikan user."""
    have = {s for s in granted_scopes().split(",") if s}
    missing = [s for s in needed.split(",") if s and s not in have]
    if missing:
        raise TikTokError(
            f"scope belum diberikan: {', '.join(missing)} (sekarang: {', '.join(sorted(have)) or 'tidak ada'}). "
            "Jalankan ulang scripts/tiktok_oauth.py."
        )
    return True


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


def _chunk_size(size):
    """Ukuran chunk 5-64 MB sesuai aturan TikTok.

    Video di bawah 5 MB harus diunggah utuh, jadi chunk_size = ukuran file.
    """
    if size < MIN_CHUNK_BYTES:
        return size

    mb = int(os.getenv("TIKTOK_CHUNK_SIZE_MB") or 20)
    chunk = max(5, min(mb, 64)) * 1024 * 1024
    while size // chunk > MAX_CHUNKS:
        chunk = min(MAX_CHUNK_BYTES, chunk * 2)
    return min(chunk, MAX_CHUNK_BYTES)


def _plan_chunks(size, chunk_size):
    """TikTok mewajibkan total_chunk_count = video_size // chunk_size (pembagian bulat ke bawah).

    Sisa byte digabung ke chunk terakhir, yang boleh lebih besar dari chunk_size
    (maks 128 MB). File yang lebih kecil dari satu chunk diunggah utuh.
    """
    if size <= chunk_size:
        return 1, size

    total = max(1, size // chunk_size)
    return total, chunk_size


def _video_size(path):
    if not os.path.exists(path):
        raise TikTokError(f"File video tidak ditemukan: {path}")
    return os.path.getsize(path)


def _upload_binary(upload_url, path, chunk_size, total_chunks, max_retries=3):
    total = _video_size(path)
    print(f"[TIKTOK] Mengunggah {total / (1024 * 1024):.2f} MB dalam {total_chunks} chunk...")

    with open(path, "rb") as handle:
        start = 0
        for index in range(total_chunks):
            is_last = index == total_chunks - 1
            length = (total - start) if is_last else chunk_size
            data = handle.read(length)
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
                    if response.status_code in (200, 201, 204, 206):
                        last_error = None
                        break
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                except requests.RequestException as e:
                    last_error = str(e)
                if attempt < max_retries:
                    time.sleep(2 * attempt)
            if last_error:
                raise TikTokError(f"Upload chunk {index + 1}/{total_chunks} gagal: {last_error}")
            start = end + 1

    print("[TIKTOK] Seluruh chunk terunggah.")


def _fetch_status(publish_id, access_token):
    response = requests.post(
        STATUS_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={"publish_id": publish_id},
        timeout=TIMEOUT,
    )
    data = _payload(response)
    if response.status_code != 200:
        raise TikTokError(f"Gagal cek status: {_describe(response)}")
    return data


def publish_video(video_path, caption, access_token=None, privacy_level=None, wait=True, poll_seconds=90, post_mode=None):
    """Mengunggah video ke akun TikTok dan mengembalikan dict hasil publikasi.

    post_mode DIRECT_POST = langsung tayang di profil (butuh scope video.publish).
    post_mode MEDIA_UPLOAD = masuk draft, kreator menyelesaikan posting di aplikasi (butuh video.upload).
    """
    access_token = access_token or get_access_token()
    privacy_level = privacy_level or os.getenv("TIKTOK_PRIVACY_LEVEL") or "SELF_ONLY"
    if privacy_level not in PRIVACY_LEVELS:
        raise TikTokError(f"TIKTOK_PRIVACY_LEVEL tidak valid: {privacy_level}")

    post_mode = post_mode or os.getenv("TIKTOK_POST_MODE") or "DIRECT_POST"
    if post_mode not in POST_MODES:
        raise TikTokError(f"TIKTOK_POST_MODE tidak valid: {post_mode}")

    if post_mode == "DIRECT_POST":
        require_scope("video.publish")
    else:
        post_mode = "MEDIA_UPLOAD"
        require_scope("video.upload")

    post_info = {
        "title": (caption or "")[:2200],
        "disable_duet": False,
        "disable_comment": False,
        "disable_stitch": False,
    }
    if post_mode == "DIRECT_POST":
        post_info["privacy_level"] = privacy_level
    else:
        post_mode = "MEDIA_UPLOAD"

    size = _video_size(video_path)
    chunk_size = _chunk_size(size)
    total_chunks, chunk_size = _plan_chunks(size, chunk_size)

    init_response = requests.post(
        INIT_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "post_info": post_info,
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
                "video_width": 1080,
                "video_height": 1920,
            },
            "post_mode": post_mode,
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

    _upload_binary(upload_url, video_path, chunk_size, total_chunks)

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