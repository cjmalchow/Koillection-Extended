import math
import colorsys
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


def _parse_hex_color(hex_str: str):
    if not hex_str:
        return None
    clean = str(hex_str).strip().upper()
    if not clean.startswith("#"):
        clean = f"#{clean}"
    if len(clean) in [4, 7]:
        try:
            Image.new("RGBA", (1, 1), clean)
            return clean
        except Exception:
            pass
    return None


def compute_effective_secondary_hex(primary_hex: str, secondary_hex: str = "", finish_str: str = "") -> str:
    # 1. DATABASE EXPLICIT SECONDARY HEX ALWAYS TAKES PRECEDENCE
    if secondary_hex:
        clean_sec = _parse_hex_color(secondary_hex)
        if clean_sec:
            return clean_sec

    clean_pri = _parse_hex_color(primary_hex)
    if not clean_pri or len(clean_pri.lstrip("#")) != 6:
        return ""

    f_lower = str(finish_str or "").lower()
    is_multi = any(k in f_lower for k in ["multichrome", "duochrome"])
    is_thermal = "thermal" in f_lower
    is_solar = any(k in f_lower for k in ["solar", "photochromic"])

    # Only synthesize if finish explicitly demands multi-tone and user left it blank
    if not (is_multi or is_thermal or is_solar):
        return ""

    try:
        hex_body = clean_pri.lstrip("#")
        r = int(hex_body[0:2], 16) / 255.0
        g = int(hex_body[2:4], 16) / 255.0
        b = int(hex_body[4:6], 16) / 255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        if is_multi:
            if v < 0.25 or s < 0.20:
                shift_h, shift_s, shift_v = 0.04, 0.85, 0.75
            else:
                shift_h = (h + 0.24) % 1.0
                shift_s = min(1.0, s * 1.05)
                shift_v = max(0.40, min(0.95, v * 1.10))
        elif is_thermal:
            shift_h = (h + 0.12) % 1.0
            shift_s = max(0.20, s * 0.55)
            shift_v = min(0.95, v * 1.35 + 0.15)
        elif is_solar:
            shift_h, shift_s, shift_v = 0.80, 0.85, 0.65
        else:
            return ""

        sr, sg, sb = colorsys.hsv_to_rgb(shift_h, shift_s, shift_v)
        return f"#{int(round(sr * 255)):02X}{int(round(sg * 255)):02X}{int(round(sb * 255)):02X}"
    except Exception:
        return ""


@lru_cache(maxsize=1024)
def generate_color_swatch_image(
    hex_code: str,
    secondary_hex: str = "",
    width: int = 44,
    height: int = 30,
    border_hex: str = "#9E9E9E",
    radius: int = 5,
    finish: str = "",
    size: int = None
) -> Image.Image:
    if isinstance(secondary_hex, (int, float)):
        width = int(secondary_hex)
        height = int(secondary_hex)
        secondary_hex = ""
    elif size is not None:
        width = int(size)
        height = int(size)

    w, h = width * SS, height * SS
    r = int(radius * SS)

    primary_clean = _parse_hex_color(hex_code)
    resolved_sec = compute_effective_secondary_hex(primary_clean, secondary_hex, finish)
    secondary_clean = _parse_hex_color(resolved_sec)

    img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    if not primary_clean:
        draw.rounded_rectangle(
            [0, 0, w - 1, h - 1],
            radius=r,
            fill="#F5F5F5",
            outline="#CFD8DC",
            width=max(1, int(1.2 * SS))
        )
        draw.line(
            [(w * 0.25, h * 0.5), (w * 0.75, h * 0.5)],
            fill="#B0BEC5",
            width=max(1, int(1.5 * SS))
        )
        return _finalize_image(img, width, height)

    mask = Image.new("L", (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)

    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas_draw = ImageDraw.Draw(canvas)

    if secondary_clean and secondary_clean != primary_clean:
        canvas_draw.rectangle([0, 0, w, h], fill=primary_clean)
        canvas_draw.polygon([(0, h), (w, 0), (w, h)], fill=secondary_clean)
        canvas_draw.line([(0, h), (w, 0)], fill="#FFFFFF", width=max(1, int(0.8 * SS)))
    else:
        canvas_draw.rectangle([0, 0, w, h], fill=primary_clean)

    img.paste(canvas, (0, 0), mask=mask)

    draw.rounded_rectangle(
        [0, 0, w - 1, h - 1],
        radius=r,
        outline=border_hex,
        width=max(1, int(1.2 * SS))
    )

    return _finalize_image(img, width, height)


@lru_cache(maxsize=128)
def generate_star_rating_image(
    rating_5: float,
    width: int = 65,
    height: int = 12,
    fill_hex: str = "#FBC02D",
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
    width: int = 36,
    height: int = 12,
    fill_hex: str = "#1E88E5",
    empty_hex: str = "#B0BEC5"
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
            draw.ellipse(bbox, outline=empty_hex, width=max(2, int(1.5 * SS)))
            
    return _finalize_image(img, width, height)


# -------------------------------------------------------------------------
# FORMULATION TYPE VECTOR GLYPHS
# -------------------------------------------------------------------------

def _draw_type_regular_lacquer(draw, w, h):
    draw.rectangle([w * 0.42, h * 0.12, w * 0.58, h * 0.42], fill="#37474F")
    draw.rectangle([w * 0.24, h * 0.44, w * 0.76, h * 0.88], fill="#C2185B")
    draw.line([(w * 0.32, h * 0.50), (w * 0.32, h * 0.80)], fill="#FFFFFF", width=max(1, int(1.2 * SS)))


def _draw_type_uv_gel(draw, w, h):
    draw.arc([w * 0.15, h * 0.18, w * 0.85, h * 0.72], 180, 360, fill="#283593", width=int(w * 0.12))
    draw.line([(w * 0.15, h * 0.85), (w * 0.85, h * 0.85)], fill="#283593", width=int(w * 0.09))
    cx, cy = w / 2, h * 0.45
    for dx, color in [(-w * 0.22, "#7E57C2"), (0, "#00E5FF"), (w * 0.22, "#7E57C2")]:
        draw.line([(cx + dx * 0.3, cy), (cx + dx, h * 0.78)], fill=color, width=int(w * 0.08))


def _draw_type_top_coat(draw, w, h):
    cx, cy, s = w / 2, h / 2, w * 0.38
    draw.polygon([(cx, cy - s), (cx + s * 0.85, cy), (cx, cy + s), (cx - s * 0.85, cy)], fill="#00ACC1")
    draw.line([(cx - s * 0.35, cy - s * 0.35), (cx + s * 0.35, cy + s * 0.35)], fill="#FFFFFF", width=int(w * 0.10))


def _draw_type_base_coat(draw, w, h):
    draw.rectangle([w * 0.18, h * 0.54, w * 0.82, h * 0.84], fill="#D84315")
    draw.line([(w * 0.18, h * 0.38), (w * 0.82, h * 0.38)], fill="#FFA000", width=int(w * 0.10))


def _draw_type_cuticle_oil(draw, w, h):
    draw.polygon([(w * 0.44, h * 0.12), (w * 0.56, h * 0.12), (w * 0.52, h * 0.55), (w * 0.48, h * 0.55)], fill="#546E7A")
    cx, cy, r = w / 2, h * 0.74, w * 0.16
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FFB300")


def _draw_type_treatment(draw, w, h):
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#2E7D32")
    p = w * 0.16
    draw.line([(cx - p, cy), (cx + p, cy)], fill="#FFFFFF", width=int(w * 0.10))
    draw.line([(cx, cy - p), (cx, cy + p)], fill="#FFFFFF", width=int(w * 0.10))


def _draw_type_latex(draw, w, h):
    pts = [(w * 0.20, h * 0.30), (w * 0.50, h * 0.20), (w * 0.80, h * 0.50), (w * 0.50, h * 0.80), (w * 0.20, h * 0.70)]
    draw.polygon(pts, fill="#FF5252")
    draw.line([(w * 0.35, h * 0.25), (w * 0.65, h * 0.75)], fill="#FFFFFF", width=int(w * 0.08))


def _draw_type_drying_drops(draw, w, h):
    cx, cy, r = w * 0.62, h / 2, w * 0.26
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#0288D1")
    draw.line([(w * 0.10, cy - r * 0.5), (w * 0.32, cy - r * 0.5)], fill="#0288D1", width=int(w * 0.08))
    draw.line([(w * 0.06, cy), (w * 0.28, cy)], fill="#0288D1", width=int(w * 0.09))
    draw.line([(w * 0.14, cy + r * 0.5), (w * 0.34, cy + r * 0.5)], fill="#0288D1", width=int(w * 0.08))


def _draw_type_stamping(draw, w, h):
    draw.rectangle([w * 0.40, h * 0.15, w * 0.60, h * 0.52], fill="#455A64")
    cx, cy, r = w / 2, h * 0.68, w * 0.30
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], 0, 180, fill="#AB47BC")


def _draw_type_glue(draw, w, h):
    draw.polygon([(w * 0.45, h * 0.12), (w * 0.55, h * 0.12), (w * 0.68, h * 0.65), (w * 0.32, h * 0.65)], fill="#FF6D00")
    draw.rectangle([w * 0.28, h * 0.65, w * 0.72, h * 0.88], fill="#37474F")


TYPE_RENDERERS = {
    "regular nail lacquer": _draw_type_regular_lacquer,
    "regular": _draw_type_regular_lacquer,
    "stamping air dry lacquer": _draw_type_stamping,
    "stamping": _draw_type_stamping,
    "uv gel nail lacquer": _draw_type_uv_gel,
    "uv gel": _draw_type_uv_gel,
    "gel": _draw_type_uv_gel,
    "top coat": _draw_type_top_coat,
    "topcoat": _draw_type_top_coat,
    "base coat": _draw_type_base_coat,
    "baee coat": _draw_type_base_coat,
    "basecoat": _draw_type_base_coat,
    "cuticle oil": _draw_type_cuticle_oil,
    "oil": _draw_type_cuticle_oil,
    "nail treatment": _draw_type_treatment,
    "treatment": _draw_type_treatment,
    "liquid latex": _draw_type_latex,
    "latex tape": _draw_type_latex,
    "latex": _draw_type_latex,
    "drying drops": _draw_type_drying_drops,
    "press on glue/releaser": _draw_type_glue,
    "press on glue": _draw_type_glue,
    "glue": _draw_type_glue,
}


@lru_cache(maxsize=64)
def get_type_icon_image(type_name: str, size: int = 24) -> Image.Image:
    img, draw, w, h = _create_supersampled_canvas(size, size)
    clean_name = str(type_name or "").lower().strip()
    
    matched_fn = None
    for key, fn in TYPE_RENDERERS.items():
        if key in clean_name:
            matched_fn = fn
            break
            
    if not matched_fn:
        matched_fn = _draw_type_regular_lacquer
        
    matched_fn(draw, w, h)
    return _finalize_image(img, size, size)


# -------------------------------------------------------------------------
# AESTHETIC FINISH VECTOR GLYPHS
# -------------------------------------------------------------------------

def _draw_creme(draw, w, h):
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#C2185B")
    draw.arc([cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], 190, 260, fill="#FFFFFF", width=int(w * 0.08))


def _draw_confetti(draw, w, h):
    cx, cy = w / 2, h / 2
    draw.line([(w * 0.18, h * 0.28), (w * 0.46, h * 0.14)], fill="#E040FB", width=int(w * 0.09))
    draw.line([(w * 0.54, h * 0.74), (w * 0.84, h * 0.54)], fill="#00E676", width=int(w * 0.08))

    dots = [
        (w * 0.28, h * 0.65, w * 0.13, "#FF1744"),
        (w * 0.74, h * 0.28, w * 0.11, "#00E5FF"),
        (w * 0.68, h * 0.82, w * 0.09, "#FFD600"),
        (w * 0.16, h * 0.44, w * 0.08, "#FF9100"),
    ]
    for dx, dy, r, color in dots:
        draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=color)

    s = w * 0.11
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill="#2979FF")


def _draw_shimmer(draw, w, h):
    cx, cy, s = w / 2, h / 2, w * 0.32
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill="#311B92")
    d = s * 0.35
    for ox, oy in [(-s * 0.75, -s * 0.75), (s * 0.75, -s * 0.75), (-s * 0.75, s * 0.75), (s * 0.75, s * 0.75)]:
        draw.ellipse([cx + ox - d, cy + oy - d, cx + ox + d, cy + oy + d], fill="#FFD54F")


def _draw_glitter(draw, w, h):
    cx, cy = w / 2, h / 2
    for ox, oy, r, color in [
        (0, 0, w * 0.28, "#FFD700"), 
        (-w * 0.25, -h * 0.22, w * 0.16, "#00E5FF"), 
        (w * 0.25, h * 0.22, w * 0.18, "#FF1744")
    ]:
        pts = _get_star_points(cx + ox, cy + oy, r, r * 0.45, points=6)
        draw.polygon(pts, fill=color)


def _draw_holo(draw, w, h):
    cx, cy = w / 2, h / 2
    pts = _get_star_points(cx, cy, w * 0.42, w * 0.16, points=8)
    draw.polygon(pts, fill="#7C4DFF")
    draw.ellipse([cx - w * 0.12, cy - h * 0.12, cx + w * 0.12, cy + h * 0.12], fill="#00E5FF")
    draw.ellipse([cx - w * 0.06, cy - h * 0.06, cx + w * 0.06, cy + h * 0.06], fill="#FFEB3B")


def _draw_flake(draw, w, h):
    draw.polygon([(w * 0.18, h * 0.18), (w * 0.52, h * 0.14), (w * 0.42, h * 0.50), (w * 0.14, h * 0.40)], fill="#00BFA5")
    draw.polygon([(w * 0.54, h * 0.35), (w * 0.86, h * 0.24), (w * 0.76, h * 0.66), (w * 0.50, h * 0.60)], fill="#FFAB00")
    draw.polygon([(w * 0.28, h * 0.64), (w * 0.62, h * 0.70), (w * 0.46, h * 0.90), (w * 0.24, h * 0.84)], fill="#FF5252")


def _draw_metallic(draw, w, h):
    line_w = int(w * 0.14)
    draw.line([(w * 0.15, h * 0.85), (w * 0.85, h * 0.15)], fill="#37474F", width=line_w)
    draw.line([(w * 0.15, h * 0.55), (w * 0.55, h * 0.15)], fill="#78909C", width=int(line_w * 0.75))
    draw.line([(w * 0.45, h * 0.85), (w * 0.85, h * 0.45)], fill="#CFD8DC", width=int(line_w * 0.75))


def _draw_pearl(draw, w, h):
    cx, cy = w / 2, h / 2
    draw.ellipse([cx - w * 0.36, cy - h * 0.36, cx + w * 0.36, cy + h * 0.36], outline="#80DEEA", width=int(w * 0.08))
    draw.ellipse([cx - w * 0.26, cy - h * 0.26, cx + w * 0.26, cy + h * 0.26], outline="#F48FB1", width=int(w * 0.07))
    draw.ellipse([cx - w * 0.14, cy - h * 0.14, cx + w * 0.14, cy + h * 0.14], fill="#ECEFF1")


def _draw_matte(draw, w, h):
    margin = w * 0.18
    draw.rectangle([margin, margin, w - margin, h - margin], fill="#607D8B")
    draw.line([(margin, h - margin), (w - margin, margin)], fill="#ECEFF1", width=int(w * 0.09))


def _draw_jelly(draw, w, h):
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#E53935")
    draw.ellipse([cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45], fill="#FFCDD2")


def _draw_thermal(draw, w, h):
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], 90, 270, fill="#FF5722")
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], 270, 90, fill="#1976D2")
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#263238", width=max(1, int(1.2 * SS)))


def _draw_magnetic(draw, w, h):
    draw.arc([w * 0.20, h * 0.15, w * 0.80, h * 0.75], 180, 0, fill="#D32F2F", width=int(w * 0.14))
    draw.line([(w * 0.20, h * 0.45), (w * 0.20, h * 0.70)], fill="#D32F2F", width=int(w * 0.14))
    draw.line([(w * 0.80, h * 0.45), (w * 0.80, h * 0.70)], fill="#D32F2F", width=int(w * 0.14))
    draw.rectangle([w * 0.13, h * 0.70, w * 0.27, h * 0.84], fill="#CFD8DC")
    draw.rectangle([w * 0.73, h * 0.70, w * 0.87, h * 0.84], fill="#CFD8DC")
    draw.arc([w * 0.30, h * 0.65, w * 0.70, h * 0.90], 0, 180, fill="#1E88E5", width=int(w * 0.07))


def _draw_solar(draw, w, h):
    cx, cy = w / 2, h / 2
    for i in range(8):
        angle = i * (math.pi / 4)
        x1 = cx + (w * 0.22) * math.cos(angle)
        y1 = cy + (h * 0.22) * math.sin(angle)
        x2 = cx + (w * 0.44) * math.cos(angle)
        y2 = cy + (h * 0.44) * math.sin(angle)
        draw.line([(x1, y1), (x2, y2)], fill="#7B1FA2", width=int(w * 0.08))
    draw.ellipse([cx - w * 0.20, cy - h * 0.20, cx + w * 0.20, cy + h * 0.20], fill="#FBC02D")


def _draw_neon(draw, w, h):
    pts = [
        (w * 0.55, h * 0.10),
        (w * 0.22, h * 0.52),
        (w * 0.48, h * 0.52),
        (w * 0.36, h * 0.90),
        (w * 0.82, h * 0.42),
        (w * 0.56, h * 0.42)
    ]
    draw.polygon(pts, fill="#00E676")
    draw.polygon(pts, outline="#1B5E20", width=max(1, int(1.2 * SS)))


def _draw_foil(draw, w, h):
    cx, cy, s = w / 2, h / 2, w * 0.38
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill="#FFB300")
    draw.line([(cx, cy - s), (cx + s, cy)], fill="#FFE082", width=int(w * 0.07))
    draw.line([(cx - s, cy), (cx + s, cy)], fill="#FF8F00", width=int(w * 0.07))
    draw.polygon([(cx, cy - s * 0.4), (cx + s * 0.4, cy), (cx, cy + s * 0.4), (cx - s * 0.4, cy)], fill="#FFF8E1")


def _draw_satin(draw, w, h):
    pts1 = [(w * 0.15, h * 0.65), (w * 0.40, h * 0.25), (w * 0.60, h * 0.75), (w * 0.85, h * 0.35)]
    pts2 = [(w * 0.15, h * 0.75), (w * 0.40, h * 0.35), (w * 0.60, h * 0.85), (w * 0.85, h * 0.45)]
    draw.line(pts1, fill="#D84315", width=int(w * 0.10), joint="curve")
    draw.line(pts2, fill="#FF8A65", width=int(w * 0.07), joint="curve")


def _draw_iridescent(draw, w, h):
    draw.arc([w * 0.15, h * 0.15, w * 0.75, h * 0.75], 0, 360, fill="#AB47BC", width=int(w * 0.09))
    draw.arc([w * 0.25, h * 0.25, w * 0.85, h * 0.85], 0, 360, fill="#26C6DA", width=int(w * 0.09))


def _draw_sheer(draw, w, h):
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#F3E5F5")
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#8E24AA", width=max(1, int(1.2 * SS)))
    for ox, oy in [(-r * 0.4, 0), (r * 0.4, 0), (0, -r * 0.4), (0, r * 0.4)]:
        draw.ellipse([cx + ox - 2 * SS, cy + oy - 2 * SS, cx + ox + 2 * SS, cy + oy + 2 * SS], fill="#BA68C8")


def _draw_glow(draw, w, h):
    cx, cy = w / 2, h / 2
    moon_img = Image.new("L", (w, h), 0)
    m_draw = ImageDraw.Draw(moon_img)
    m_draw.ellipse([cx - w * 0.36, cy - h * 0.36, cx + w * 0.36, cy + h * 0.36], fill=255)
    m_draw.ellipse([cx - w * 0.18, cy - h * 0.46, cx + w * 0.46, cy + h * 0.26], fill=0)
    glow_color = Image.new("RGBA", (w, h), "#00E676")
    draw._image.paste(glow_color, (0, 0), moon_img)
    draw.ellipse([cx + w * 0.18, cy - h * 0.24, cx + w * 0.28, cy - h * 0.14], fill="#B9F6CA")


def _draw_glass_fleck(draw, w, h):
    cx, cy = w / 2, h / 2
    for angle_deg in [0, 45, 90, 135]:
        rad = math.radians(angle_deg)
        x1 = cx + (w * 0.40) * math.cos(rad)
        y1 = cy + (h * 0.40) * math.sin(rad)
        x2 = cx - (w * 0.40) * math.cos(rad)
        y2 = cy - (h * 0.40) * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill="#00E5FF", width=int(w * 0.08))
    draw.ellipse([cx - w * 0.12, cy - h * 0.12, cx + w * 0.12, cy + h * 0.12], fill="#FFFFFF")


def _draw_multichrome(draw, w, h):
    cx, cy, s = w / 2, h / 2, w * 0.26
    draw.polygon([(cx - s * 0.6, cy - s), (cx + s * 0.4, cy), (cx - s * 0.6, cy + s), (cx - s * 1.6, cy)], fill="#AA00FF")
    draw.polygon([(cx + s * 0.6, cy - s), (cx + s * 1.6, cy), (cx + s * 0.6, cy + s), (cx - s * 0.4, cy)], fill="#00E676")


def _draw_crackle(draw, w, h):
    margin = w * 0.16
    draw.rectangle([margin, margin, w - margin, h - margin], fill="#D32F2F")
    draw.line([(w * 0.16, h * 0.35), (w * 0.48, h * 0.52)], fill="#212121", width=int(w * 0.08))
    draw.line([(w * 0.48, h * 0.52), (w * 0.84, h * 0.28)], fill="#212121", width=int(w * 0.08))
    draw.line([(w * 0.48, h * 0.52), (w * 0.38, h * 0.84)], fill="#212121", width=int(w * 0.08))
    draw.line([(w * 0.48, h * 0.52), (w * 0.78, h * 0.78)], fill="#212121", width=int(w * 0.08))


def _draw_textured(draw, w, h):
    margin = w * 0.16
    draw.rectangle([margin, margin, w - margin, h - margin], fill="#6D4C41")
    cx, cy = w / 2, h / 2
    r_dot = w * 0.05
    coords = [
        (-0.18, -0.18), (0.05, -0.22), (0.20, -0.12),
        (-0.22, 0.05), (0.02, 0.02), (0.22, 0.08),
        (-0.15, 0.20), (0.08, 0.22), (0.22, 0.22)
    ]
    for ox, oy in coords:
        px = cx + ox * w
        py = cy + oy * h
        draw.ellipse([px - r_dot, py - r_dot, px + r_dot, py + r_dot], fill="#FFE082")


FINISH_RENDERERS = {
    "creme": _draw_creme,
    "cream": _draw_creme,
    "confetti": _draw_confetti,
    "party": _draw_confetti,
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
    "solar": _draw_solar,
    "photochromic": _draw_solar,
    "neon": _draw_neon,
    "foil": _draw_foil,
    "satin": _draw_satin,
    "iridescent": _draw_iridescent,
    "sheer": _draw_sheer,
    "glow": _draw_glow,
    "glass fleck": _draw_glass_fleck,
    "multichrome": _draw_multichrome,
    "duochrome": _draw_multichrome,
    "crackle": _draw_crackle,
    "textured": _draw_textured,
    "sand": _draw_textured,
}


@lru_cache(maxsize=128)
def get_finish_icon_image(finish_name: str, size: int = 24) -> Image.Image:
    img, draw, w, h = _create_supersampled_canvas(size, size)
    clean_name = str(finish_name or "").lower().strip()
    
    matched_fn = None
    for key, fn in FINISH_RENDERERS.items():
        if key in clean_name:
            matched_fn = fn
            break
            
    if not matched_fn:
        matched_fn = _draw_creme
        
    matched_fn(draw, w, h)
    return _finalize_image(img, size, size)