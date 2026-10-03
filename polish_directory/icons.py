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
    border_hex: str = "#888888"
) -> Image.Image:
    img, draw, w, h = _create_supersampled_canvas(size, size)
    cx, cy, r = w / 2, h / 2, (w * 0.40)
    
    clean_hex = str(hex_code or "").strip().upper()
    if clean_hex and not clean_hex.startswith("#"):
        clean_hex = f"#{clean_hex}"
        
    has_color = False
    fill_color = "#EAEAEA"
    
    if clean_hex and len(clean_hex) in [4, 7]:
        try:
            Image.new("RGBA", (1, 1), clean_hex)
            fill_color = clean_hex
            has_color = True
        except Exception:
            has_color = False

    if has_color:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill_color)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=border_hex, width=max(1, int(1.2 * SS)))
    else:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#CCCCCC", width=max(1, int(1.0 * SS)))
        draw.line([cx - r * 0.4, cy, cx + r * 0.4, cy], fill="#CCCCCC", width=max(1, int(1.0 * SS)))

    return _finalize_image(img, size, size)


@lru_cache(maxsize=128)
def generate_star_rating_image(
    rating_5: float,
    width: int = 90,
    height: int = 18,
    fill_hex: str = "#FBC02D",   # Rich warm gold stars
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
    fill_hex: str = "#1E88E5",   # Clean cobalt blue opacity pips
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
    # Classic polish bottle: dark cap with crimson lacquer base and white gloss highlight
    draw.rectangle([w * 0.42, h * 0.12, w * 0.58, h * 0.42], fill="#37474F")
    draw.rectangle([w * 0.24, h * 0.44, w * 0.76, h * 0.88], fill="#C2185B")
    draw.line([(w * 0.32, h * 0.50), (w * 0.32, h * 0.80)], fill="#FFFFFF", width=max(1, int(1.2 * SS)))


def _draw_type_uv_gel(draw, w, h):
    # UV LED Lamp: Curved royal-blue hood over radiant violet/cyan UV rays
    draw.arc([w * 0.15, h * 0.18, w * 0.85, h * 0.72], 180, 360, fill="#283593", width=int(w * 0.12))
    draw.line([(w * 0.15, h * 0.85), (w * 0.85, h * 0.85)], fill="#283593", width=int(w * 0.09))
    cx, cy = w / 2, h * 0.45
    for dx, color in [(-w * 0.22, "#7E57C2"), (0, "#00E5FF"), (w * 0.22, "#7E57C2")]:
        draw.line([(cx + dx * 0.3, cy), (cx + dx, h * 0.78)], fill=color, width=int(w * 0.08))


def _draw_type_top_coat(draw, w, h):
    # Glossy shield with brilliant cyan/white diamond flash
    cx, cy, s = w / 2, h / 2, w * 0.38
    draw.polygon([(cx, cy - s), (cx + s * 0.85, cy), (cx, cy + s), (cx - s * 0.85, cy)], fill="#00ACC1")
    draw.line([(cx - s * 0.35, cy - s * 0.35), (cx + s * 0.35, cy + s * 0.35)], fill="#FFFFFF", width=int(w * 0.10))


def _draw_type_base_coat(draw, w, h):
    # Foundation base plate: golden anchor bar and terracotta foundation layer
    draw.rectangle([w * 0.18, h * 0.54, w * 0.82, h * 0.84], fill="#D84315")
    draw.line([(w * 0.18, h * 0.38), (w * 0.82, h * 0.38)], fill="#FFA000", width=int(w * 0.10))


def _draw_type_cuticle_oil(draw, w, h):
    # Pipette dropper with amber/golden oil bead
    draw.polygon([(w * 0.44, h * 0.12), (w * 0.56, h * 0.12), (w * 0.52, h * 0.55), (w * 0.48, h * 0.55)], fill="#546E7A")
    cx, cy, r = w / 2, h * 0.74, w * 0.16
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FFB300")


def _draw_type_treatment(draw, w, h):
    # Healing jade green droplet containing a crisp white medical plus (+)
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#2E7D32")
    p = w * 0.16
    draw.line([(cx - p, cy), (cx + p, cy)], fill="#FFFFFF", width=int(w * 0.10))
    draw.line([(cx, cy - p), (cx, cy + p)], fill="#FFFFFF", width=int(w * 0.10))


def _draw_type_latex(draw, w, h):
    # Barrier ribbon peel: vibrant coral shield
    pts = [(w * 0.20, h * 0.30), (w * 0.50, h * 0.20), (w * 0.80, h * 0.50), (w * 0.50, h * 0.80), (w * 0.20, h * 0.70)]
    draw.polygon(pts, fill="#FF5252")
    draw.line([(w * 0.35, h * 0.25), (w * 0.65, h * 0.75)], fill="#FFFFFF", width=int(w * 0.08))


def _draw_type_drying_drops(draw, w, h):
    # Fast-dry droplet: sky blue drop with horizontal speed lines
    cx, cy, r = w * 0.62, h / 2, w * 0.26
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#0288D1")
    draw.line([(w * 0.10, cy - r * 0.5), (w * 0.32, cy - r * 0.5)], fill="#0288D1", width=int(w * 0.08))
    draw.line([(w * 0.06, cy), (w * 0.28, cy)], fill="#0288D1", width=int(w * 0.09))
    draw.line([(w * 0.14, cy + r * 0.5), (w * 0.34, cy + r * 0.5)], fill="#0288D1", width=int(w * 0.08))


def _draw_type_stamping(draw, w, h):
    # Stamping stamper: dark handle with soft squishy silicone pad
    draw.rectangle([w * 0.40, h * 0.15, w * 0.60, h * 0.52], fill="#455A64")
    cx, cy, r = w / 2, h * 0.68, w * 0.30
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], 0, 180, fill="#AB47BC")


def _draw_type_glue(draw, w, h):
    # Adhesive tube nozzle: orange applicator with white tube
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
    # Smooth glossy crimson drop with sleek white reflection crescent
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#C2185B")
    draw.arc([cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], 190, 260, fill="#FFFFFF", width=int(w * 0.08))


def _draw_confetti(draw, w, h):
    # Festive party confetti: vibrant matte sequins and angled streamer ribbons
    cx, cy = w / 2, h / 2

    # Angled ticker-tape streamers (Neon Magenta and Lime)
    draw.line([(w * 0.18, h * 0.28), (w * 0.46, h * 0.14)], fill="#E040FB", width=int(w * 0.09))
    draw.line([(w * 0.54, h * 0.74), (w * 0.84, h * 0.54)], fill="#00E676", width=int(w * 0.08))

    # Floating round matte confetti sequins
    dots = [
        (w * 0.28, h * 0.65, w * 0.13, "#FF1744"),  # Coral Red dot
        (w * 0.74, h * 0.28, w * 0.11, "#00E5FF"),  # Bright Cyan dot
        (w * 0.68, h * 0.82, w * 0.09, "#FFD600"),  # Sunny Yellow dot
        (w * 0.16, h * 0.44, w * 0.08, "#FF9100"),  # Tangerine dot
    ]
    for dx, dy, r, color in dots:
        draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=color)

    # Center diamond sequin (Electric Blue)
    s = w * 0.11
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill="#2979FF")


def _draw_shimmer(draw, w, h):
    # Midnight blue diamond with 4 golden sparkle glints
    cx, cy, s = w / 2, h / 2, w * 0.32
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill="#311B92")
    d = s * 0.35
    for ox, oy in [(-s * 0.75, -s * 0.75), (s * 0.75, -s * 0.75), (-s * 0.75, s * 0.75), (s * 0.75, s * 0.75)]:
        draw.ellipse([cx + ox - d, cy + oy - d, cx + ox + d, cy + oy + d], fill="#FFD54F")


def _draw_glitter(draw, w, h):
    # Multi-colored geometric sequins: Magenta, Cyan, Gold
    cx, cy = w / 2, h / 2
    for ox, oy, r, color in [
        (0, 0, w * 0.28, "#FFD700"), 
        (-w * 0.25, -h * 0.22, w * 0.16, "#00E5FF"), 
        (w * 0.25, h * 0.22, w * 0.18, "#FF1744")
    ]:
        pts = _get_star_points(cx + ox, cy + oy, r, r * 0.45, points=6)
        draw.polygon(pts, fill=color)


def _draw_holo(draw, w, h):
    # Radiant 8-pointed prismatic rainbow diffraction star
    cx, cy = w / 2, h / 2
    pts = _get_star_points(cx, cy, w * 0.42, w * 0.16, points=8)
    draw.polygon(pts, fill="#7C4DFF")
    # Multi-colored rainbow center core
    draw.ellipse([cx - w * 0.12, cy - h * 0.12, cx + w * 0.12, cy + h * 0.12], fill="#00E5FF")
    draw.ellipse([cx - w * 0.06, cy - h * 0.06, cx + w * 0.06, cy + h * 0.06], fill="#FFEB3B")


def _draw_flake(draw, w, h):
    # 3 floating angular iridescent leaf shards (Teal, Gold, Coral)
    draw.polygon([(w * 0.18, h * 0.18), (w * 0.52, h * 0.14), (w * 0.42, h * 0.50), (w * 0.14, h * 0.40)], fill="#00BFA5")
    draw.polygon([(w * 0.54, h * 0.35), (w * 0.86, h * 0.24), (w * 0.76, h * 0.66), (w * 0.50, h * 0.60)], fill="#FFAB00")
    draw.polygon([(w * 0.28, h * 0.64), (w * 0.62, h * 0.70), (w * 0.46, h * 0.90), (w * 0.24, h * 0.84)], fill="#FF5252")


def _draw_metallic(draw, w, h):
    # Reflective silver/steel chrome bars
    line_w = int(w * 0.14)
    draw.line([(w * 0.15, h * 0.85), (w * 0.85, h * 0.15)], fill="#37474F", width=line_w)
    draw.line([(w * 0.15, h * 0.55), (w * 0.55, h * 0.15)], fill="#78909C", width=int(line_w * 0.75))
    draw.line([(w * 0.45, h * 0.85), (w * 0.85, h * 0.45)], fill="#CFD8DC", width=int(line_w * 0.75))


def _draw_pearl(draw, w, h):
    # Concentric iridescent rings with soft pearl luster
    cx, cy = w / 2, h / 2
    draw.ellipse([cx - w * 0.36, cy - h * 0.36, cx + w * 0.36, cy + h * 0.36], outline="#80DEEA", width=int(w * 0.08))
    draw.ellipse([cx - w * 0.26, cy - h * 0.26, cx + w * 0.26, cy + h * 0.26], outline="#F48FB1", width=int(w * 0.07))
    draw.ellipse([cx - w * 0.14, cy - h * 0.14, cx + w * 0.14, cy + h * 0.14], fill="#ECEFF1")


def _draw_matte(draw, w, h):
    # Frosted matte square badge with clean diagonal sash
    margin = w * 0.18
    draw.rectangle([margin, margin, w - margin, h - margin], fill="#607D8B")
    draw.line([(margin, h - margin), (w - margin, margin)], fill="#ECEFF1", width=int(w * 0.09))


def _draw_jelly(draw, w, h):
    # Translucent ruby glass-tint drop with inner luminous void
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#E53935")
    draw.ellipse([cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45], fill="#FFCDD2")


def _draw_thermal(draw, w, h):
    # Universal thermal shift: Warm Coral left, Cold Cobalt right
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], 90, 270, fill="#FF5722")
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], 270, 90, fill="#1976D2")
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#263238", width=max(1, int(1.2 * SS)))


def _draw_magnetic(draw, w, h):
    # Horseshoe magnet: red body, silver poles, blue magnetic field arcs
    draw.arc([w * 0.20, h * 0.15, w * 0.80, h * 0.75], 180, 0, fill="#D32F2F", width=int(w * 0.14))
    draw.line([(w * 0.20, h * 0.45), (w * 0.20, h * 0.70)], fill="#D32F2F", width=int(w * 0.14))
    draw.line([(w * 0.80, h * 0.45), (w * 0.80, h * 0.70)], fill="#D32F2F", width=int(w * 0.14))
    # Silver pole tips
    draw.rectangle([w * 0.13, h * 0.70, w * 0.27, h * 0.84], fill="#CFD8DC")
    draw.rectangle([w * 0.73, h * 0.70, w * 0.87, h * 0.84], fill="#CFD8DC")
    # Magnetic force wave
    draw.arc([w * 0.30, h * 0.65, w * 0.70, h * 0.90], 0, 180, fill="#1E88E5", width=int(w * 0.07))


def _draw_solar(draw, w, h):
    # Sunburst with UV Flares: Golden core with violet UV ray spikes
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
    # High-voltage neon-lime lightning bolt with dark contour
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
    # Multi-faceted gold leaf jewel polygon
    cx, cy, s = w / 2, h / 2, w * 0.38
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill="#FFB300")
    draw.line([(cx, cy - s), (cx, cy + s)], fill="#FFE082", width=int(w * 0.07))
    draw.line([(cx - s, cy), (cx + s, cy)], fill="#FF8F00", width=int(w * 0.07))
    draw.polygon([(cx, cy - s * 0.4), (cx + s * 0.4, cy), (cx, cy + s * 0.4), (cx - s * 0.4, cy)], fill="#FFF8E1")


def _draw_satin(draw, w, h):
    # Dual flowing silk ribbon wave in amber and terracotta
    pts1 = [(w * 0.15, h * 0.65), (w * 0.40, h * 0.25), (w * 0.60, h * 0.75), (w * 0.85, h * 0.35)]
    pts2 = [(w * 0.15, h * 0.75), (w * 0.40, h * 0.35), (w * 0.60, h * 0.85), (w * 0.85, h * 0.45)]
    draw.line(pts1, fill="#D84315", width=int(w * 0.10), joint="curve")
    draw.line(pts2, fill="#FF8A65", width=int(w * 0.07), joint="curve")


def _draw_iridescent(draw, w, h):
    # Translucent soap-bubble double arc in pastel lavender and aqua
    draw.arc([w * 0.15, h * 0.15, w * 0.75, h * 0.75], 0, 360, fill="#AB47BC", width=int(w * 0.09))
    draw.arc([w * 0.25, h * 0.25, w * 0.85, h * 0.85], 0, 360, fill="#26C6DA", width=int(w * 0.09))


def _draw_sheer(draw, w, h):
    # Translucent tinted droplet with dotted boundary veil
    cx, cy, r = w / 2, h / 2, w * 0.36
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#F3E5F5")
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#8E24AA", width=max(1, int(1.2 * SS)))
    for ox, oy in [(-r * 0.4, 0), (r * 0.4, 0), (0, -r * 0.4), (0, r * 0.4)]:
        draw.ellipse([cx + ox - 2 * SS, cy + oy - 2 * SS, cx + ox + 2 * SS, cy + oy + 2 * SS], fill="#BA68C8")


def _draw_glow(draw, w, h):
    # Phosphorescent green crescent moon radiating light
    cx, cy = w / 2, h / 2
    moon_img = Image.new("L", (w, h), 0)
    m_draw = ImageDraw.Draw(moon_img)
    m_draw.ellipse([cx - w * 0.36, cy - h * 0.36, cx + w * 0.36, cy + h * 0.36], fill=255)
    m_draw.ellipse([cx - w * 0.18, cy - h * 0.46, cx + w * 0.46, cy + h * 0.26], fill=0)
    glow_color = Image.new("RGBA", (w, h), "#00E676")
    draw._image.paste(glow_color, (0, 0), moon_img)
    draw.ellipse([cx + w * 0.18, cy - h * 0.24, cx + w * 0.28, cy - h * 0.14], fill="#B9F6CA")


def _draw_glass_fleck(draw, w, h):
    # Radiant 4-point crystal star with bright cyan/aquamarine mica flecks
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
    # Dual shifting chromatic diamonds: Emerald Green overlapping Royal Purple
    cx, cy, s = w / 2, h / 2, w * 0.26
    draw.polygon([(cx - s * 0.6, cy - s), (cx + s * 0.4, cy), (cx - s * 0.6, cy + s), (cx - s * 1.6, cy)], fill="#AA00FF")
    draw.polygon([(cx + s * 0.6, cy - s), (cx + s * 1.6, cy), (cx + s * 0.6, cy + s), (cx - s * 0.4, cy)], fill="#00E676")


def _draw_crackle(draw, w, h):
    # Shattered ceramic tile: crimson background fractured by dark slate spiderweb fissures
    margin = w * 0.16
    draw.rectangle([margin, margin, w - margin, h - margin], fill="#D32F2F")
    draw.line([(w * 0.16, h * 0.35), (w * 0.48, h * 0.52)], fill="#212121", width=int(w * 0.08))
    draw.line([(w * 0.48, h * 0.52), (w * 0.84, h * 0.28)], fill="#212121", width=int(w * 0.08))
    draw.line([(w * 0.48, h * 0.52), (w * 0.38, h * 0.84)], fill="#212121", width=int(w * 0.08))
    draw.line([(w * 0.48, h * 0.52), (w * 0.78, h * 0.78)], fill="#212121", width=int(w * 0.08))


def _draw_textured(draw, w, h):
    # Stippled granite/sand pebble badge with dual-tone sand grit
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