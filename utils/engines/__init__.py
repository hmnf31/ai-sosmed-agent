"""Mesin konten per akun.

Tiap akun punya karakter berbeda, jadi tiap akun punya engine. Tujuannya bukan
menggandakan kode, melainkan memberi satu tempat untuk aturan khusus akun itu:
MLBB butuh disiplin fact-check, wedding butuh mengubah tren jadi ide, fashion
butuh paket affiliate, dan catur butuh materi yang bisa dipraktikkan.

Modul ini hanya menyusun brief untuk AI dan memeriksa hasilnya. Angka tetap
berasal dari sumber, bukan dari model.
"""
import re

ACCOUNT_ENGINES = {}


def engine_for(account_id):
    """Mengembalikan engine untuk satu akun, atau engine umum."""
    return ACCOUNT_ENGINES.get(account_id, GeneralEngine(account_id))


def register(account_id):
    """Decorator untuk mendaftarkan engine sebuah akun."""
    def wrapper(cls):
        ACCOUNT_ENGINES[account_id] = cls(account_id)
        return cls
    return wrapper


class GeneralEngine:
    """Engine bawaan: cocok untuk wedding dan akun tanpa aturan khusus."""

    #: Kata yang menandakan mode konten yang diminta.
    CATEGORY_WORDS = {
        "tren": ("tren", "trend"),
        "ide": ("ide", "ideas"),
        "caption": ("caption", "teks", "copywriting"),
        "carousel": ("carousel", "slide"),
        "reels": ("reels", "reel"),
        "checklist": ("checklist", "daftar"),
        "tips": ("tips", "trik", "cara"),
        "edukasi": ("edukasi", "belajar", "tutorial"),
    }

    def __init__(self, account_id):
        self.account_id = account_id

    def detect_category(self, text):
        """Menentukan kategori konten dari teks permintaan."""
        low = (text or "").lower()
        for category, words in self.CATEGORY_WORDS.items():
            if any(word in low for word in words):
                return category
        return None

    def build_brief(self, request, topic, account, category=None):
        """Menyusun brief yang diteruskan ke prompt builder.

        Kunci yang dipakai: request, topics, category, angle_hint, avoid_topics,
        dan extra_rules khusus akun.
        """
        return {
            "request": request,
            "topics": [topic],
            "category": category or self.detect_category(request),
            "angle_hint": "",
            "avoid_topics": [],
            "extra_rules": list(account.get("fact_check_rules") or []),
        }

    def extra_instructions(self, brief):
        """Instruksi tambahan per kategori yang digabung ke prompt."""
        category = (brief or {}).get("category")
        if category == "tren":
            return "Isi caption dengan nama tren dan satu sudut pandang yang masih baru."
        if category in ("carousel", "reels"):
            return "Buat poin-poin yang cocok untuk visual, bukan paragraf panjang."
        return ""


@register("wedding")
class WeddingEngine(GeneralEngine):
    """Wedding: tren diubah menjadi ide, bukan disalin mentah."""

    def build_brief(self, request, topic, account, category=None):
        brief = super().build_brief(request, topic, account, category)
        brief["extra_rules"] += [
            "jangan mengarang harga paket atau biaya dekorasi",
            "sebutkan tren sebagai referensi, bukan fakta yang bisa diverifikasi",
            "ubah tren menjadi ide yang bisa ditindaklanjuti pasangan",
        ]
        if (brief["category"] or "") == "tren":
            brief["angle_hint"] = (
                "Pakai satu sudut pandang yang jarang dipakai untuk tren ini, "
                "dan berikan tiga opsi angle singkat"
            )
        return brief


@register("mlbb")
class MlbbEngine(GeneralEngine):
    """MLBB: disiplin fact-check paling ketat karena data cepat basi."""

    CATEGORY_WORDS = dict(
        GeneralEngine.CATEGORY_WORDS,
        patch=("patch", "update", "nerf", "buff"),
        hero=("hero", "assassin"),
        counter=("counter", "matchup", "lawan"),
        meta=("meta", "meta game", "tier list"),
        mpl=("mpl", "mpl id", "mplid"),
        esports=("esport", "esports", "turnamen"),
        build=("build", "emblem", "item"),
    )

    def build_brief(self, request, topic, account, category=None):
        brief = super().build_brief(request, topic, account, category)
        brief["extra_rules"] = [
            "patch harus disebutkan versinya, dan hanya bila ada di sumber",
            "buff atau nerf harus berasal dari sumber patch, bukan dari ingatan",
            "hasil pertandingan dan klasemen harus berasal dari sumber",
            "statistik pemain tidak boleh dibuat sendiri",
            "bila data tidak ditemukan, tulis 'data tidak tersedia' di dalam caption",
        ]
        if (brief["category"] or "") in ("patch", "mpl", "esports"):
            brief["extra_rules"].append(
                "cantumkan sumber kalau ada; kalau tidak, tulis data tidak tersedia"
            )
        return brief


@register("fashion")
class FashionEngine(GeneralEngine):
    """Fashion: gaya umum plus mode affiliate."""

    CATEGORY_WORDS = dict(
        GeneralEngine.CATEGORY_WORDS,
        ootd=("ootd", "outfit"),
        styling=("styling", "mix and match", "mixmatch", "gaya"),
        affiliate=("affiliate", "produk", "link produk"),
    )

    def build_brief(self, request, topic, account, category=None):
        brief = super().build_brief(request, topic, account, category)
        brief["extra_rules"] += [
            "jangan mengarang nama brand atau harga produk",
            "jangan menjanjikan produk yang tidak disebutkan pengguna",
            "pisahkan opini styling dari fakta produk",
        ]
        if (brief["category"] or "") == "affiliate":
            brief["angle_hint"] = "fokus pada masalah nyata yang bisa diselesaikan produk"
        return brief


@register("chess")
class ChessEngine(GeneralEngine):
    """Catur: materi yang bisa langsung dipraktikkan pemain."""

    CATEGORY_WORDS = dict(
        GeneralEngine.CATEGORY_WORDS,
        tips=("tips", "cara", "trik"),
        opening=("opening", "bukaan"),
        endgame=("endgame", "akhir", "closing"),
        news=("berita", "news", "turnamen"),
    )

    def build_brief(self, request, topic, account, category=None):
        brief = super().build_brief(request, topic, account, category)
        brief["extra_rules"] += [
            "jangan mengarang hasil pertandingan, skor, atau Elo pemain",
            "nama opening dan konsep endgame harus benar secara catur",
        ]
        return brief


def category_words_for(account_id):
    """Exposed untuk pengujian."""
    return engine_for(account_id).CATEGORY_WORDS


_URL_RE = re.compile(r"https?://\S+")


def extract_links(text):
    """Mengambil semua URL polos dari teks, tanpa format markdown."""
    return [match.rstrip(".,);]}") for match in _URL_RE.findall(text or "")]