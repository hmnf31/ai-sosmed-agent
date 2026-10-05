"""Template engine: menyusun Brand Profile + style preset menjadi gambar.

Satu jalur untuk semua akun. Yang berubah antar akun hanya isi config, bukan
kode: palet, skala huruf, bentuk panel, penanda poin, dan watermark.

Dua keluaran:

- `render_card()`  satu kartu untuk format square atau portrait.
- `render_frames()` tiga frame vertikal untuk video.

Keduanya menjalankan empat langkah yang sama: pilih template, pilih kanvas,
gambar isinya, lalu tempelkan watermark. Jadi tidak ada akun yang bisa lolos
tanpa branding.
"""
import os
from datetime import datetime, timedelta, timezone

from branding import loader, style_registry, validator
from utils.media import asset_loader, layout_engine, watermark_engine

WIB = timezone(timedelta(hours=7))

#: Jumlah poin yang muat di tiap format. Frame video butuh lebih sedikit.
POINT_LIMITS = {"square": 4, "portrait": 5, "reel": 4, "story": 4}

#: Label pembuka tiap frame video, mengikuti alur hook -> isi -> ajakan.
FRAME_LABELS = ("HOOK", "POIN PENTING", "GILIRANMU")


def resolve_template(brand, category=None, fmt=None):
    """Template untuk satu akun, dijamin milik akun tersebut."""
    account_id = (brand or {}).get("account") or ""
    template = style_registry.select_template(account_id, content_type=category, fmt=fmt)
    validator.assert_same_account(account_id, template=template, brand=brand)
    return template


def _stamp():
    return datetime.now(WIB).strftime("%d %B %Y, %H:%M WIB")


def _title_of(content, fallback):
    return str(content.get("title") or fallback).strip()


def _points_of(content):
    return [str(p).strip() for p in (content.get("points") or []) if str(p).strip()]


def _footer_of(content, brand, footer=""):
    if footer:
        return footer
    return (brand or {}).get("label") or ""


def render_card(content, brand, output_path=None, category=None, fmt="square",
                footer="", template=None, layout=None, output_dir=None):
    """Merender satu kartu sesuai brand akun.

    Mengembalikan dict berisi `path`, `template`, `canvas`, `watermark`, dan
    `problems` supaya pemanggil bisa menjalankan branding QA tanpa menebak.
    """
    brand = asset_loader.brand_of(brand)
    style = loader.visual_style(brand)
    template = template or resolve_template(brand, category=category, fmt=fmt)
    layout = layout or template.get("layout") or "standard"
    canvas = asset_loader.canvas_for(fmt)

    spec = layout_engine.resolve_canvas(canvas)
    image, draw = layout_engine.paint_background(brand, style, canvas)
    margin = spec["margin"]
    width = spec["content_width"]
    colors = layout_engine.palette(brand)

    problems = []
    if brand.get("synthetic"):
        problems.append(
            f"akun '{brand.get('account')}' belum punya Brand Profile, memakai gaya generik"
        )

    y = max(margin + int(spec["height"] * 0.035),
            layout_engine.top_inset(brand, style, canvas) + int(margin * 0.35))
    y = layout_engine.draw_label(draw, brand, style, FRAME_LABELS[0], margin, y, width)
    y += int(spec["height"] * 0.018)
    y = layout_engine.draw_title(draw, brand, style, _title_of(content, brand.get("label")),
                                 margin, y, width, issues=problems)
    subtitle = content.get("subtitle") or ""
    if subtitle:
        y += int(spec["height"] * 0.014)
        y = layout_engine.draw_subtitle(draw, brand, style, subtitle, margin, y, width,
                                        issues=problems)

    points = _points_of(content)
    y += int(spec["height"] * 0.028)
    cta_y = spec["height"] - margin - int(spec["height"] * 0.10)
    available = cta_y - int(spec["height"] * 0.045) - y
    hard_limit = POINT_LIMITS.get(canvas, 4)
    limit = layout_engine.fit_point_limit(brand, style, points, width, available, hard_limit)
    if points and limit < len(points):
        problems.append(
            f"{len(points) - limit} dari {len(points)} poin tidak muat dan dilewati"
        )

    if layout == "table" and limit:
        rows = _as_rows(points)
        y = layout_engine.draw_table(draw, brand, style, rows, margin, y, width, limit=limit)
    else:
        y = layout_engine.draw_points(draw, brand, style, points, margin, y, width, limit=limit)

    cta = content.get("cta") or _footer_of(content, brand, footer)
    layout_engine.divider(draw, brand, style, margin, cta_y - int(spec["height"] * 0.018), width)
    layout_engine.draw_cta(draw, brand, style, cta, margin, cta_y, width, issues=problems)

    stamp = layout_engine.stamp(_stamp())
    body = layout_engine._font("regular", int(width * 0.026))
    draw.text((margin, margin - int(spec["height"] * 0.022)), stamp, font=body,
              fill=colors["muted"])

    mark = watermark_engine.apply(image, brand, canvas)
    problems.extend(watermark_engine.audit(image, mark, brand))
    if not mark.get("applied"):
        problems.append(f"watermark tidak menempel: {mark.get('error', 'alasan tidak diketahui')}")

    if output_path is None:
        target_dir = output_dir or layout_engine.output_dir()
        os.makedirs(target_dir, exist_ok=True)
        name = str(content.get("filename") or
                   f"konten-{datetime.now(WIB).strftime('%Y%m%d-%H%M%S')}-{brand.get('account')}")
        output_path = os.path.join(target_dir, f"{name}.png")
    else:
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    image.save(output_path, "PNG")
    print(f"[IMAGE] Kartu {brand.get('account')}/{template.get('id')} dibuat: {output_path}")

    return {
        "path": output_path,
        "template": template,
        "canvas": canvas,
        "size": (spec["width"], spec["height"]),
        "watermark": mark,
        "brand": brand,
        "problems": problems,
    }


def _as_rows(points):
    """Baris 'Nama 4' atau 'Nama - 4' diubah menjadi pasangan kolom."""
    rows = []
    for item in points:
        for separator in ("  ", " | ", " - ", " : "):
            if separator in item:
                left, right = item.split(separator, 1)
                rows.append([left.strip(), right.strip()])
                break
        else:
            rows.append([item, ""])
    return rows


def render_frames(content, brand, output_dir=None, category=None, template=None):
    """Merender tiga frame vertikal: hook, poin, dan ajakan bertindak."""
    brand = asset_loader.brand_of(brand)
    style = loader.visual_style(brand)
    template = template or resolve_template(brand, category=category, fmt="reel")
    canvas = "reel"
    spec = layout_engine.resolve_canvas(canvas)
    folder = output_dir or layout_engine.output_dir()
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now(WIB).strftime("%Y%m%d-%H%M%S")
    prefix = f"frame-{brand.get('account')}-{stamp}"

    points = _points_of(content)
    cta = content.get("cta") or "Tulis pendapatmu di komentar"

    frame_specs = [
        {
            "label": FRAME_LABELS[0],
            "title": _title_of(content, brand.get("label")),
            "subtitle": content.get("subtitle") or "",
            "kind": "hook",
        },
        {
            "label": FRAME_LABELS[1],
            "title": content.get("subtitle") or _title_of(content, brand.get("label")),
            "points": points,
            "kind": "points",
        },
        {
            "label": FRAME_LABELS[2],
            "title": cta,
            "subtitle": "Detail lengkap ada di caption.",
            "kind": "cta",
        },
    ]

    results = []
    problems = []
    for index, frame in enumerate(frame_specs, start=1):
        image, draw = layout_engine.paint_background(brand, style, canvas)
        margin = spec["margin"]
        width = spec["content_width"]
        colors = layout_engine.palette(brand)

        y = max(margin + int(spec["height"] * 0.02),
                layout_engine.top_inset(brand, style, canvas) + int(margin * 0.35))
        y = layout_engine.draw_label(draw, brand, style, frame["label"], margin, y, width)
        y += int(spec["height"] * 0.014)
        y = layout_engine.draw_title(draw, brand, style, frame["title"], margin, y, width,
                                     issues=problems)
        if frame.get("subtitle"):
            y += int(spec["height"] * 0.012)
            y = layout_engine.draw_subtitle(draw, brand, style, frame["subtitle"],
                                            margin, y, width, issues=problems)
        if frame.get("points"):
            y += int(spec["height"] * 0.026)
            available = spec["height"] - margin - int(spec["height"] * 0.12) - y
            limit = layout_engine.fit_point_limit(brand, style, frame["points"], width,
                                                  available, 4)
            if limit < len(frame["points"]):
                problems.append(
                    f"frame {index}: {len(frame['points']) - limit} poin dilewati agar tidak "
                    "menimpa bagian bawah"
                )
            y = layout_engine.draw_points(draw, brand, style, frame["points"], margin, y,
                                          width, limit=limit)
        if frame["kind"] == "cta":
            handle = str(brand.get("handle") or "").lstrip("@")
            if handle:
                layout_engine.draw_cta(draw, brand, style, f"@{handle}", margin,
                                       spec["height"] - margin - int(spec["height"] * 0.05),
                                       width)
        body = layout_engine._font("regular", int(width * 0.024))
        draw.text((margin, spec["height"] - margin), _stamp(), font=body, fill=colors["muted"])

        mark = watermark_engine.apply(image, brand, canvas)
        problems.extend(watermark_engine.audit(image, mark, brand))

        path = os.path.join(folder, f"{prefix}-{index}.png")
        image.save(path, "PNG")
        results.append(path)

    print(f"[IMAGE] {len(results)} frame {brand.get('account')} dibuat di {folder}")
    return {
        "paths": results,
        "template": template,
        "canvas": canvas,
        "size": (spec["width"], spec["height"]),
        "brand": brand,
        "problems": problems,
    }