import math
from functools import lru_cache
from PIL import Image, ImageDraw

SS = 4


def _create_supersampled_canvas(width: int, height: int, bg_color=None):
    w, h = width * SS, height * SS
    img = Image.new("RGBA", (w, h), bg_color or (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    return img, draw, w, h


def _finalize_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)


def _get_star_points(cx: float, cy: float, r_outer: float, r_inner: float, points: int = 5):
    coords = []
    angle_offset = -math.pi / 2
    for i in range(points * 2):
        r = r_outer if i % 2 == 0 else r_inner
        angle = angle_offset + (i * math.pi / points)
        coords.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return coords


@lru_cache(maxsize=512)
def generate_color_swatch_image(
    hex_code: str,
    size: int = 24,
    border_hex: str = "#AAAAAA"
) -> Image.Image:
    """Renders a circular color swatch pip with an archival boundary ring."""
    img, draw, w, h = _create_supersampled_canvas(size, size)
    cx, cy, r = w / 2, h / 2, (w * 0.40)
    
    clean_hex = str(hex_code or "").strip()
    if clean_hex and not clean_hex.startswith("#"):
        clean_hex = f"#{clean_hex}"
        
    has_color = False
    fill_color = "#EAEAEA"
    if clean_hex and len(clean_hex) in [4, 7, 9]:
        try:
            Image.new("RGBA", (1, 1), clean_hex)
            fill_color = clean_hex
            has_color = True
        except Exception:
            pass

    if has_color:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill_color)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=border_hex, width=max(1, int(1.2 * SS)))
    else:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#CCCCCC", width=max(1, int(1.0 * SS)))
        draw.line([cx - r * 0.5, cy, cx + r * 0.5, cy], fill="#CCCCCC", width=max(1, int(1.0 * SS)))

    return _finalize_image(img, size, size)


@lru_cache(maxsize=128)
def generate_star_rating_image(
    rating_5: float,
    width: int = 90,
    height: int = 18,
    fill_hex: str = "#222222",
    empty_hex: str = "#D0D0D0"
) -> Image.Image:
    img, draw, w, h = _create_supersampled_canvas(width, height)
    star_spacing = w / 5.0
    star_radius_outer = (h * 0.45)
    star_radius_inner = star_radius_outer * 0.42
    val = max(0.0, min(5.0, float(rating_5 or 0.0)))
    
    for i in range(5):
        cx = (i + 0.5) * star_spacing
        cy = h / 2.0
        star_pts = _get_star_points(cx, cy, star_radius_outer, star_radius_inner)
        star_val = val - i
        if star_val >= 0.75:
            draw.polygon(star_pts, fill=fill_hex)
        elif star_val >= 0.25:
            draw.polygon(star_pts, fill=empty_hex)
            half_mask = Image.new("L", (w, h), 0)
            mask_draw = ImageDraw.Draw(half_mask)
            mask_draw.polygon(star_pts, fill=255)
            mask_draw.rectangle([cx, 0, w, h], fill=0)
            half_star_layer = Image.new("RGBA", (w, h), fill_hex)
            img.paste(half_star_layer, (0, 0), half_mask)
        else:
            draw.polygon(star_pts, fill=empty_hex)
            
    return _finalize_image(img, width, height)


@lru_cache(maxsize=64)
def generate_opacity_dots_image(
    coats: str = "2",
    max_coats: int = 3,
    width: int = 44,
    height: int = 14,
    fill_hex: str = "#222222",
    empty_hex: str = "#CCCCCC"
) -> Image.Image:
    img, draw, w, h = _create_supersampled_canvas(width, height)
    try:
        c_count = int(str(coats).strip()[:1])
    except Exception:
        c_count = 2
    c_count = max(1, min(max_coats, c_count))
    dot_radius = h * 0.32
    spacing = w / max_coats
    
    for i in range(max_coats):
        cx = (i + 0.5) * spacing
        cy = h / 2.0
        bbox = [cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius]
        if i < c_count:
            draw.ellipse(bbox, fill=fill_hex)
        else:
            draw.ellipse(bbox, outline=empty_hex, width=max(2, int(2 * SS)))
            
    return _finalize_image(img, width, height)


# -------------------------------------------------------------------------
# Distinct Finish Vector Glyphs
# -------------------------------------------------------------------------

def _draw_top_coat(draw, w, h, color):
    cx, cy, s = w / 2, h / 2, w * 0.38
    draw.polygon([(cx, cy - s), (cx + s * 0.85, cy), (cx, cy + s), (cx - s * 0.85, cy)], outline=color, width=int(w * 0.08))
    draw.line([(cx - s * 0.3, cy - s * 0.3), (cx + s * 0.3, cy + s * 0.3)], fill=color, width=int(w * 0.08))


def _draw_base_coat(draw, w, h, color):
    draw.rectangle([w * 0.2, h * 0.55, w * 0.8, h * 0.82], fill=color)
    draw.line([(w * 0.2, h * 0.4), (w * 0.8, h * 0.4)], fill=color, width=int(w * 0.08))


def _draw_regular_lacquer(draw, w, h, color):
    # Cap
    draw.rectangle([w * 0.4, h * 0.15, w * 0.6, h * 0.42], fill=color)
    # Bottle
    draw.rectangle([w * 0.25, h * 0.45, w * 0.75, h * 0.85], fill=color)


def _draw_gel(draw, w, h, color):
    cx, cy, s = w / 2, h / 2, w * 0.35
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=color)
    for ox, oy in [(-w * 0.3, 0), (w * 0.3, 0), (0, -h * 0.3), (0, h * 0.3)]:
        draw.line([(cx, cy), (cx + ox, cy + oy)], fill=color, width=int(w * 0.06))


def _draw_creme(draw, w, h, color):
    cx, cy, r = w / 2, h / 2, w * 0.35
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)


def _draw_shimmer(draw, w, h, color):
    cx, cy, s = w / 2, h / 2, w * 0.30
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=color)
    d = s * 0.35
    for ox, oy in [(-s * 0.7, -s * 0.7), (s * 0.7, -s * 0.7), (-s * 0.7, s * 0.7), (s * 0.7, s * 0.7)]:
        draw.ellipse([cx + ox - d, cy + oy - d, cx + ox + d, cy + oy + d], fill=color)


def _draw_glitter(draw, w, h, color):
    cx, cy = w / 2, h / 2
    for ox, oy, r in [(0, 0, w * 0.26), (-w * 0.25, -h * 0.2, w * 0.15), (w * 0.25, h * 0.2, w * 0.16)]:
        pts = _get_star_points(cx + ox, cy + oy, r, r * 0.45, points=6)
        draw.polygon(pts, fill=color)


def _draw_holo(draw, w, h, color):
    cx, cy = w / 2, h / 2
    pts = _get_star_points(cx, cy, w * 0.42, w * 0.16, points=8)
    draw.polygon(pts, fill=color)
    draw.ellipse([cx - w * 0.1, cy - h * 0.1, cx + w * 0.1, cy + h * 0.1], fill="#FFFFFF")


def _draw_flake(draw, w, h, color):
    draw.polygon([(w * 0.2, h * 0.2), (w * 0.5, h * 0.15), (w * 0.4, h * 0.5), (w * 0.15, h * 0.4)], fill=color)
    draw.polygon([(w * 0.55, h * 0.35), (w * 0.85, h * 0.25), (w * 0.75, h * 0.65), (w * 0.5, h * 0.6)], fill=color)
    draw.polygon([(w * 0.3, h * 0.65), (w * 0.6, h * 0.7), (w * 0.45, h * 0.9), (w * 0.25, h * 0.85)], fill=color)


def _draw_metallic(draw, w, h, color):
    line_w = int(w * 0.13)
    draw.line([(w * 0.15, h * 0.85), (w * 0.85, h * 0.15)], fill=color, width=line_w)
    draw.line([(w * 0.15, h * 0.55), (w * 0.55, h * 0.15)], fill=color, width=int(line_w * 0.7))
    draw.line([(w * 0.45, h * 0.85), (w * 0.85, h * 0.45)], fill=color, width=int(line_w * 0.7))


def _draw_pearl(draw, w, h, color):
    cx, cy = w / 2, h / 2
    draw.ellipse([cx - w * 0.36, cy - h * 0.36, cx + w * 0.36, cy + h * 0.36], outline=color, width=int(w * 0.08))
    draw.ellipse([cx - w * 0.18, cy - h * 0.18, cx + w * 0.18, cy + h * 0.18], fill=color)


def _draw_matte(draw, w, h, color):
    margin = w * 0.18
    draw.rectangle([margin, margin, w - margin, h - margin], outline=color, width=int(w * 0.09))
    draw.line([(margin * 1.5, margin * 1.5), (w - margin * 1.5, h - margin * 1.5)], fill=color, width=int(w * 0.06))


def _draw_jelly(draw, w, h, color):
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=int(w * 0.1))
    draw.ellipse([cx - r * 0.4, cy - r * 0.4, cx + r * 0.4, cy + r * 0.4], fill=color)


def _draw_thermal(draw, w, h, color):
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], 90, 270, fill=color)
    draw.arc([cx - r, cy - r, cx + r, cy + r], 270, 90, fill=color, width=int(w * 0.09))


def _draw_magnetic(draw, w, h, color):
    draw.arc([w * 0.2, h * 0.15, w * 0.8, h * 0.75], 180, 0, fill=color, width=int(w * 0.13))
    draw.line([(w * 0.2, h * 0.45), (w * 0.2, h * 0.8)], fill=color, width=int(w * 0.13))
    draw.line([(w * 0.8, h * 0.45), (w * 0.8, h * 0.8)], fill=color, width=int(w * 0.13))


FINISH_RENDERERS = {
    "top coat": _draw_top_coat,
    "topcoat": _draw_top_coat,
    "rapiddry": _draw_top_coat,
    "base coat": _draw_base_coat,
    "basecoat": _draw_base_coat,
    "regular nail la": _draw_regular_lacquer,
    "regular": _draw_regular_lacquer,
    "lacquer": _draw_regular_lacquer,
    "nail lacquer": _draw_regular_lacquer,
    "uv gel": _draw_gel,
    "gelement": _draw_gel,
    "gel": _draw_gel,
    "creme": _draw_creme,
    "cream": _draw_creme,
    "shimmer": _draw_shimmer,
    "glitter": _draw_glitter,
    "holo": _draw_holo,
    "holographic": _draw_holo,
    "flake": _draw_flake,
    "flakies": _draw_flake,
    "metallic": _draw_metallic,
    "chrome": _draw_metallic,
    "pearl": _draw_pearl,
    "matte": _draw_matte,
    "jelly": _draw_jelly,
    "thermal": _draw_thermal,
    "magnetic": _draw_magnetic,
}


@lru_cache(maxsize=128)
def get_finish_icon_image(
    finish_name: str,
    size: int = 24,
    fill_hex: str = "#222222"
) -> Image.Image:
    img, draw, w, h = _create_supersampled_canvas(size, size)
    clean_name = str(finish_name or "").lower().strip()
    
    matched_fn = None
    for key, fn in FINISH_RENDERERS.items():
        if key in clean_name:
            matched_fn = fn
            break
            
    if not matched_fn:
        matched_fn = _draw_creme
        
    matched_fn(draw, w, h, fill_hex)
    return _finalize_image(img, size, size)