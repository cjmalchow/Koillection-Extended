import os
import json
import math
import socket
from io import BytesIO
import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import qrcode

# ==============================================================================
# 1. GOLDEN RULES: TOP-OF-FILE SESSION STATE & VAULT
# ==============================================================================
if "vault" not in st.session_state:
    st.session_state.vault = {}

st.set_page_config(
    page_title="Bottle Label Maker",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Large Red Centered "EXPERIMENTAL" Header
st.markdown(
    """
    <div style="text-align: center; margin-top: -5px; margin-bottom: 8px;">
        <span style="color: #D32F2F; font-size: 2.3rem; font-weight: 900; letter-spacing: 4px; text-transform: uppercase; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">
            ⚠️ EXPERIMENTAL ⚠️
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. DATABASE & NETWORK CONFIGURATION
# ==============================================================================
DB_USER = os.getenv("DB_USER", "koillection_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "local_polish_vault_2026")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "koillection")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.1.100"

DEFAULT_LAN_IP = get_lan_ip()

# ==============================================================================
# 3. ROBUST DATA CLEANERS
# ==============================================================================
def clean_datum_value(val):
    if not val:
        return []
    val_str = str(val).strip()
    if val_str.startswith("[") and val_str.endswith("]"):
        try:
            parsed = json.loads(val_str)
            if isinstance(parsed, list):
                return [str(p).strip().strip('"').strip("'") for p in parsed if str(p).strip()]
        except Exception:
            pass
        cleaned = val_str.strip("[]").replace('"', '').replace("'", "")
        return [c.strip() for c in cleaned.split(",") if c.strip()]
    return [val_str.strip('"').strip("'")]

def clean_single_str(val):
    items = clean_datum_value(val)
    return items[0] if items else ""

def normalize_rating(rating_val):
    try:
        score = float(clean_single_str(rating_val))
        if score > 5.0:
            score = score / 2.0
        return round(score, 1)
    except (ValueError, TypeError):
        return None

def clean_shade_name(shade_name, brand_name):
    s = str(shade_name or "").strip()
    b = str(brand_name or "").strip()
    if b and s.lower().startswith(b.lower()):
        s = s[len(b):].lstrip(" -:—")
    return s.strip()

# ==============================================================================
# 4. ROBUST FONT LOADER & AUTO-SCALER
# ==============================================================================
def get_font(size=12, bold=False):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def fit_text(text_str, max_pt=18, min_pt=10, max_w=118):
    """Dynamically scales font size to fill horizontal width without clipping."""
    # Single-line check
    for pt in range(max_pt, min_pt - 1, -1):
        f = get_font(size=pt, bold=True)
        w = f.getbbox(text_str)[2] - f.getbbox(text_str)[0]
        if w <= max_w:
            return f, pt, [text_str]
    
    # 2-line wrap check if multi-word
    words = text_str.split(" ")
    if len(words) > 1:
        mid = len(words) // 2
        l1 = " ".join(words[:mid])
        l2 = " ".join(words[mid:])
        for pt in range(max_pt - 2, min_pt - 1, -1):
            f = get_font(size=pt, bold=True)
            w1 = f.getbbox(l1)[2] - f.getbbox(l1)[0]
            w2 = f.getbbox(l2)[2] - f.getbbox(l2)[0]
            if max(w1, w2) <= max_w:
                return f, pt, [l1, l2]

    return get_font(size=min_pt, bold=True), min_pt, [text_str]

# ==============================================================================
# 5. DATABASE QUERIES (Golden Rule: CAST(:id AS text) & ttl=0)
# ==============================================================================
@st.cache_data(ttl=0)
def fetch_collections():
    with engine.connect() as conn:
        df = pd.read_sql_query(text("""
            SELECT CAST(id AS text) AS id, title 
            FROM koi_collection 
            ORDER BY title ASC
        """), conn)
    return df

@st.cache_data(ttl=0)
def fetch_polish_catalog(collection_id=None):
    query = text("""
        SELECT 
            CAST(i.id AS text) AS item_id,
            i.name AS shade_name,
            c.title AS collection_name,
            MAX(CASE WHEN d.label = 'Brand' THEN d.value END) AS brand,
            MAX(CASE WHEN d.label = 'Finish' THEN d.value END) AS finish,
            MAX(CASE WHEN d.label = 'Coats' THEN d.value END) AS coats,
            MAX(CASE WHEN d.label = 'Size (oz)' THEN d.value END) AS size_oz,
            MAX(CASE WHEN d.label = 'Purchase Date' THEN d.value END) AS purchase_date,
            MAX(CASE WHEN d.label = 'Location' THEN d.value END) AS location_id,
            MAX(CASE WHEN d.label = 'Overall Rating' THEN d.value END) AS rating
        FROM koi_item i
        JOIN koi_collection c ON i.collection_id = c.id
        LEFT JOIN koi_datum d ON d.item_id = i.id
        WHERE (:collection_id IS NULL OR CAST(c.id AS text) = CAST(:collection_id AS text))
        GROUP BY i.id, i.name, c.title
        ORDER BY brand ASC, i.name ASC;
    """)
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={"collection_id": collection_id})
    return df

@st.cache_data(ttl=0)
def fetch_single_polish(item_id):
    query = text("""
        SELECT 
            CAST(i.id AS text) AS item_id,
            i.name AS shade_name,
            c.title AS collection_name,
            MAX(CASE WHEN d.label = 'Brand' THEN d.value END) AS brand,
            MAX(CASE WHEN d.label = 'Finish' THEN d.value END) AS finish,
            MAX(CASE WHEN d.label = 'Coats' THEN d.value END) AS coats,
            MAX(CASE WHEN d.label = 'Size (oz)' THEN d.value END) AS size_oz,
            MAX(CASE WHEN d.label = 'Purchase Date' THEN d.value END) AS purchase_date,
            MAX(CASE WHEN d.label = 'Location' THEN d.value END) AS location_id,
            MAX(CASE WHEN d.label = 'Overall Rating' THEN d.value END) AS rating
        FROM koi_item i
        JOIN koi_collection c ON i.collection_id = c.id
        LEFT JOIN koi_datum d ON d.item_id = i.id
        WHERE CAST(i.id AS text) = CAST(:item_id AS text)
        GROUP BY i.id, i.name, c.title;
    """)
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={"item_id": item_id})
    return df.iloc[0].to_dict() if not df.empty else None

# ==============================================================================
# 6. PURE VECTOR FINISH ICONS
# ==============================================================================
FINISH_CATALOG = [
    ("Cream", "Smooth, opaque high-gloss solid color"),
    ("Shimmer", "Fine reflective micro-sparkle particles"),
    ("Holo", "Prismatic rainbow light refraction"),
    ("Glitter", "Suspended geometric hexagonal particles"),
    ("Magnetic", "Reactive particles shifting with a magnet"),
    ("Foil", "Crinkled metallic gold/silver leaf shards"),
    ("Top Coat", "Protective high-gloss or effect seal"),
    ("Base Coat", "Adhesion & nail protection foundation"),
    ("Thermal", "Color-shifting with temperature changes"),
    ("Solar", "Color-shifting under UV / sunlight"),
    ("Pearl", "Soft lustrous iridescent sheen"),
    ("Confetti", "Multi-shape mixed geometric particles"),
    ("Metallic", "Heavy liquid metal / brushed sheen"),
    ("Jelly", "Translucent tinted squishy gloss"),
    ("Satin", "Semi-matte low-sheen silk finish"),
    ("Micro-Glitter", "Dense field of microscopic glitter specks"),
    ("Flake", "Irregular iridescent / multichrome shards"),
    ("Multichrome", "Shifts through multiple colors with angle"),
    ("Matte", "Non-reflective flat velvety finish"),
    ("Chrome", "Mirror-like high-specular reflective sheen"),
    ("Topper", "Layering effect designed over a base"),
    ("Glow In The Dark", "Luminescent glow after light exposure")
]

ALL_FINISH_NAMES = [name for name, _ in FINISH_CATALOG]

def draw_vector_icon(draw, cx, cy, size, finish_name):
    fn = str(finish_name).strip().upper()
    r = size // 2
    x0, y0 = cx - r, cy - r
    x1, y1 = cx + r, cy + r

    if "MAG" in fn:
        draw.arc([x0 + int(size*0.12), y0 + int(size*0.08), x1 - int(size*0.12), y1 + int(size*0.16)], start=180, end=0, fill=0, width=max(2, int(size*0.16)))
        draw.line([x0 + int(size*0.2), cy, x0 + int(size*0.2), y1 - int(size*0.08)], fill=0, width=max(2, int(size*0.16)))
        draw.line([x1 - int(size*0.2), cy, x1 - int(size*0.2), y1 - int(size*0.08)], fill=0, width=max(2, int(size*0.16)))
        draw.line([x0 + int(size*0.12), y1 - int(size*0.08), x0 + int(size*0.28), y1 - int(size*0.08)], fill=0, width=max(1, int(size*0.04)))
        draw.line([x1 - int(size*0.28), y1 - int(size*0.08), x1 - int(size*0.12), y1 - int(size*0.08)], fill=0, width=max(1, int(size*0.04)))
    elif "FLAK" in fn:
        draw.polygon([(cx - int(size*0.3), cy - int(size*0.16)), (cx - int(size*0.08), cy - int(size*0.35)), (cx - int(size*0.16), cy + int(size*0.04))], fill=0)
        draw.polygon([(cx + int(size*0.04), cy - int(size*0.25)), (cx + int(size*0.35), cy - int(size*0.12)), (cx + int(size*0.2), cy + int(size*0.12)), (cx + int(size*0.04), cy - int(size*0.04))], fill=0)
        draw.polygon([(cx - int(size*0.2), cy + int(size*0.12)), (cx + int(size*0.04), cy + int(size*0.35)), (cx - int(size*0.08), cy + int(size*0.2))], fill=0)
    elif "HOLO" in fn:
        draw.polygon([(cx - int(size*0.3), cy + int(size*0.25)), (cx, cy - int(size*0.3)), (cx + int(size*0.3), cy + int(size*0.25))], outline=0, width=max(1, int(size*0.05)))
        draw.line([cx - int(size*0.04), cy + int(size*0.04), cx + int(size*0.38), cy - int(size*0.08)], fill=0, width=max(1, int(size*0.05)))
        draw.line([cx, cy + int(size*0.12), cx + int(size*0.38), cy + int(size*0.12)], fill=0, width=max(1, int(size*0.05)))
        draw.line([cx, cy + int(size*0.2), cx + int(size*0.38), cy + int(size*0.28)], fill=0, width=max(1, int(size*0.05)))
    elif "GLIT" in fn and "MICRO" not in fn:
        def hex_pts(hcx, hcy, hr):
            return [(hcx + hr * math.cos(math.radians(a)), hcy + hr * math.sin(math.radians(a))) for a in range(0, 360, 60)]
        draw.polygon(hex_pts(cx - int(size*0.12), cy - int(size*0.08), int(size*0.22)), outline=0, width=max(1, int(size*0.05)))
        draw.polygon(hex_pts(cx + int(size*0.16), cy + int(size*0.12), int(size*0.22)), fill=0)
    elif "MICRO" in fn:
        step = int(size*0.22)
        for dx in [-step, 0, step]:
            for dy in [-step, 0, step]:
                draw.rectangle([cx + dx - max(1, int(size*0.04)), cy + dy - max(1, int(size*0.04)), 
                                cx + dx + max(1, int(size*0.04)), cy + dy + max(1, int(size*0.04))], fill=0)
    elif "SHIM" in fn:
        pts = [(cx, cy - r + 2), (cx + int(size*0.12), cy - int(size*0.12)), (cx + r - 2, cy), (cx + int(size*0.12), cy + int(size*0.12)),
               (cx, cy + r - 2), (cx - int(size*0.12), cy + int(size*0.12)), (cx - r + 2, cy), (cx - int(size*0.12), cy - int(size*0.12))]
        draw.polygon(pts, fill=0)
    elif "CREAM" in fn or "CREME" in fn:
        draw.polygon([(cx, cy - int(size*0.35)), (cx - int(size*0.3), cy + int(size*0.12)), (cx + int(size*0.3), cy + int(size*0.12))], fill=0)
        draw.ellipse([cx - int(size*0.3), cy - int(size*0.12), cx + int(size*0.3), cy + int(size*0.3)], fill=0)
        draw.arc([cx - int(size*0.16), cy - int(size*0.04), cx + int(size*0.08), cy + int(size*0.2)], start=180, end=270, fill=1, width=max(1, int(size*0.08)))
    elif "JELLY" in fn:
        draw.polygon([(cx, cy - int(size*0.35)), (cx - int(size*0.3), cy + int(size*0.12)), (cx + int(size*0.3), cy + int(size*0.12))], outline=0, width=max(1, int(size*0.05)))
        draw.ellipse([cx - int(size*0.3), cy - int(size*0.12), cx + int(size*0.3), cy + int(size*0.3)], outline=0, width=max(1, int(size*0.05)))
        draw.chord([cx - int(size*0.25), cy + int(size*0.04), cx + int(size*0.25), cy + int(size*0.25)], start=0, end=180, fill=0)
    elif "THERM" in fn:
        draw.ellipse([cx - int(size*0.16), cy + int(size*0.08), cx + int(size*0.16), cy + int(size*0.32)], fill=0)
        draw.rectangle([cx - int(size*0.08), cy - int(size*0.3), cx + int(size*0.08), cy + int(size*0.12)], fill=0)
        draw.rectangle([cx - int(size*0.12), cy - int(size*0.32), cx + int(size*0.12), cy + int(size*0.16)], outline=0, width=max(1, int(size*0.05)))
        draw.line([cx + int(size*0.12), cy - int(size*0.2), cx + int(size*0.25), cy - int(size*0.2)], fill=0, width=max(1, int(size*0.05)))
        draw.line([cx + int(size*0.12), cy - int(size*0.04), cx + int(size*0.25), cy - int(size*0.04)], fill=0, width=max(1, int(size*0.05)))
    elif "SOLAR" in fn:
        draw.ellipse([cx - int(size*0.16), cy - int(size*0.16), cx + int(size*0.16), cy + int(size*0.16)], fill=0)
        for a in range(0, 360, 45):
            rad = math.radians(a)
            draw.line([cx + int(size*0.25) * math.cos(rad), cy + int(size*0.25) * math.sin(rad),
                       cx + int(size*0.38) * math.cos(rad), cy + int(size*0.38) * math.sin(rad)], fill=0, width=max(1, int(size*0.05)))
    elif "GLOW" in fn:
        draw.ellipse([cx - int(size*0.32), cy - int(size*0.28), cx + int(size*0.16), cy + int(size*0.28)], fill=0)
        draw.ellipse([cx - int(size*0.2), cy - int(size*0.36), cx + int(size*0.24), cy + int(size*0.24)], fill=1)
        draw.point((cx + int(size*0.2), cy - int(size*0.16)), fill=0)
        draw.point((cx + int(size*0.28), cy + int(size*0.08)), fill=0)
    elif "CHROME" in fn:
        draw.ellipse([x0 + int(size*0.08), y0 + int(size*0.08), x1 - int(size*0.08), y1 - int(size*0.08)], fill=0)
        draw.line([x0 + int(size*0.16), y1 - int(size*0.16), x1 - int(size*0.16), y0 + int(size*0.16)], fill=1, width=max(2, int(size*0.12)))
    elif "METALLIC" in fn:
        draw.polygon([(x0 + int(size*0.2), y0 + int(size*0.16)), (x1 - int(size*0.2), y0 + int(size*0.16)), 
                      (x1 - int(size*0.08), y0 + int(size*0.32)), (x1 - int(size*0.08), y1 - int(size*0.2)), 
                      (x0 + int(size*0.08), y1 - int(size*0.2)), (x0 + int(size*0.08), y0 + int(size*0.32))], outline=0, width=max(1, int(size*0.05)))
        draw.line([x0 + int(size*0.2), y0 + int(size*0.16), x0 + int(size*0.08), y0 + int(size*0.32)], fill=0, width=max(1, int(size*0.05)))
        draw.line([x1 - int(size*0.2), y0 + int(size*0.16), x1 - int(size*0.08), y0 + int(size*0.32)], fill=0, width=max(1, int(size*0.05)))
        draw.line([x0 + int(size*0.16), cy + int(size*0.04), x1 - int(size*0.16), cy + int(size*0.04)], fill=0, width=max(1, int(size*0.08)))
    elif "MULTI" in fn:
        draw.arc([x0 + int(size*0.08), y0 + int(size*0.08), cx + int(size*0.08), cy + int(size*0.08)], start=180, end=360, fill=0, width=max(1, int(size*0.08)))
        draw.arc([cx - int(size*0.08), cy - int(size*0.08), x1 - int(size*0.08), y1 - int(size*0.08)], start=0, end=180, fill=0, width=max(1, int(size*0.08)))
        draw.arc([x0 + int(size*0.16), cy - int(size*0.04), x1 - int(size*0.16), y1 + int(size*0.12)], start=180, end=360, fill=0, width=max(1, int(size*0.08)))
    elif "MATTE" in fn:
        draw.rectangle([x0 + int(size*0.12), y0 + int(size*0.12), x1 - int(size*0.12), y1 - int(size*0.12)], outline=0, width=max(1, int(size*0.05)))
        for o in range(int(-size*0.25), int(size*0.5), max(3, int(size*0.15))):
            draw.line([x0 + int(size*0.2) + o, y1 - int(size*0.2), x0 + int(size*0.4) + o, y0 + int(size*0.2)], fill=0, width=max(1, int(size*0.04)))
    elif "PEARL" in fn:
        draw.ellipse([x0 + int(size*0.12), y0 + int(size*0.12), x1 - int(size*0.12), y1 - int(size*0.12)], outline=0, width=max(1, int(size*0.05)))
        draw.arc([x0 + int(size*0.2), y0 + int(size*0.2), x1 - int(size*0.2), y1 - int(size*0.2)], start=120, end=240, fill=0, width=max(1, int(size*0.08)))
        draw.point((cx + int(size*0.08), cy - int(size*0.08)), fill=0)
    elif "CONFETTI" in fn:
        draw.rectangle([cx - int(size*0.3), cy - int(size*0.25), cx - int(size*0.12), cy - int(size*0.08)], fill=0)
        draw.ellipse([cx + int(size*0.08), cy - int(size*0.2), cx + int(size*0.25), cy - int(size*0.04)], fill=0)
        draw.polygon([(cx - int(size*0.12), cy + int(size*0.08)), (cx + int(size*0.04), cy + int(size*0.32)), (cx - int(size*0.2), cy + int(size*0.28))], fill=0)
        draw.line([cx + int(size*0.12), cy + int(size*0.12), cx + int(size*0.3), cy + int(size*0.3)], fill=0, width=max(1, int(size*0.08)))
    elif "SATIN" in fn:
        draw.arc([x0 + int(size*0.12), cy - int(size*0.16), cx, cy + int(size*0.16)], start=180, end=0, fill=0, width=max(1, int(size*0.08)))
        draw.arc([cx, cy - int(size*0.16), x1 - int(size*0.12), cy + int(size*0.16)], start=0, end=180, fill=0, width=max(1, int(size*0.08)))
    elif "TOP" in fn:
        draw.polygon([(cx, y0 + int(size*0.08)), (x1 - int(size*0.16), y0 + int(size*0.16)), (x1 - int(size*0.16), cy + int(size*0.08)), 
                      (cx, y1 - int(size*0.08)), (x0 + int(size*0.16), cy + int(size*0.08)), (x0 + int(size*0.16), y0 + int(size*0.16))], outline=0, width=max(1, int(size*0.05)))
        draw.polygon([(cx, y0 + int(size*0.2)), (x1 - int(size*0.28), y0 + int(size*0.28)), (x1 - int(size*0.28), cy + int(size*0.04)), 
                      (cx, y1 - int(size*0.2)), (x0 + int(size*0.28), cy + int(size*0.04)), (x0 + int(size*0.28), y0 + int(size*0.28))], fill=0)
    elif "BASE" in fn:
        draw.rectangle([x0 + int(size*0.12), y1 - int(size*0.2), x1 - int(size*0.12), y1 - int(size*0.08)], fill=0)
        draw.line([cx, y0 + int(size*0.16), cx, y1 - int(size*0.24)], fill=0, width=max(1, int(size*0.08)))
        draw.polygon([(cx - int(size*0.16), y0 + int(size*0.28)), (cx, y0 + int(size*0.12)), (cx + int(size*0.16), y0 + int(size*0.28))], fill=0)
    elif "TOPPER" in fn:
        draw.rounded_rectangle([x0 + int(size*0.12), y0 + int(size*0.2), cx + int(size*0.08), y1 - int(size*0.08)], radius=2, outline=0, width=max(1, int(size*0.05)))
        draw.line([x1 - int(size*0.28), cy - int(size*0.08), x1 - int(size*0.04), cy - int(size*0.08)], fill=0, width=max(1, int(size*0.08)))
        draw.line([x1 - int(size*0.16), cy - int(size*0.2), x1 - int(size*0.16), cy + int(size*0.04)], fill=0, width=max(1, int(size*0.08)))
    elif "FOIL" in fn:
        draw.polygon([(cx, y0 + int(size*0.12)), (x1 - int(size*0.12), cy - int(size*0.08)), (cx + int(size*0.12), y1 - int(size*0.12)), (x0 + int(size*0.12), cy + int(size*0.08))], outline=0, width=max(1, int(size*0.05)))
        draw.line([cx, y0 + int(size*0.12), cx + int(size*0.12), y1 - int(size*0.12)], fill=0, width=max(1, int(size*0.04)))
        draw.line([x0 + int(size*0.12), cy + int(size*0.08), x1 - int(size*0.12), cy - int(size*0.08)], fill=0, width=max(1, int(size*0.04)))
    else:
        draw.rectangle([x0 + int(size*0.16), y0 + int(size*0.16), x1 - int(size*0.16), y1 - int(size*0.16)], outline=0, width=max(1, int(size*0.05)))
        draw.point((cx, cy), fill=0)

# ==============================================================================
# 7. PROPORTIONAL VECTOR STARS & OPACITY
# ==============================================================================
def draw_vector_star(draw, cx, cy, radius, fill_type="full"):
    points = []
    inner_radius = radius * 0.4
    for i in range(10):
        r = radius if i % 2 == 0 else inner_radius
        angle = i * (math.pi / 5) - (math.pi / 2)
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    if fill_type == "full":
        draw.polygon(points, fill=0)
    elif fill_type == "empty":
        draw.polygon(points, outline=0, width=1)
    elif fill_type == "half":
        draw.polygon(points, outline=0, width=1)
        min_y = cy - radius
        max_y = cy + radius
        for px in range(int(cx - radius), int(cx) + 1):
            for py in range(int(min_y), int(max_y) + 1):
                if is_inside_polygon(px, py, points):
                    draw.point((px, py), fill=0)

def is_inside_polygon(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def draw_star_row(draw, center_x, y, rating_val, max_stars=5, radius=8):
    score = normalize_rating(rating_val) or 0.0
    spacing = radius * 2.35
    total_w = (max_stars - 1) * spacing
    start_x = center_x - (total_w / 2)

    for i in range(max_stars):
        cx = start_x + (i * spacing)
        diff = score - i
        if diff >= 0.75:
            draw_vector_star(draw, cx, y, radius, fill_type="full")
        elif 0.25 <= diff < 0.75:
            draw_vector_star(draw, cx, y, radius, fill_type="half")
        else:
            draw_vector_star(draw, cx, y, radius, fill_type="empty")

def draw_opacity_dots(draw, center_x, y, coats_str):
    coats_num = 2
    raw = clean_single_str(coats_str)
    if raw:
        digits = [int(s) for s in raw if s.isdigit()]
        if digits:
            coats_num = digits[0]
    coats_num = max(1, min(3, coats_num))

    font_sub = get_font(size=11, bold=True)
    label = f"{coats_num} Coats"
    
    r = 4.0
    spacing = 13
    total_w = (2 * spacing) + 10 + (font_sub.getbbox(label)[2] - font_sub.getbbox(label)[0])
    start_x = center_x - (total_w / 2)

    for i in range(3):
        dx = start_x + (i * spacing)
        if i < coats_num:
            draw.ellipse([dx - r, y - r, dx + r, y + r], fill=0)
        else:
            draw.ellipse([dx - r, y - r, dx + r, y + r], outline=0, width=1)

    text_x = start_x + (3 * spacing)
    draw.text((text_x, y - 6), label, fill=0, font=font_sub)

# ==============================================================================
# 8. MASTER LABEL COMPOSER (Brother 24mm @ 180 DPI)
# ==============================================================================
def render_bottle_label(polish, height_mm, base_url):
    DPI = 180
    WIDTH_PX = 128
    HEIGHT_PX = int(round(height_mm * DPI / 25.4))

    img = Image.new("1", (WIDTH_PX, HEIGHT_PX), 1)
    draw = ImageDraw.Draw(img)

    brand_clean = clean_single_str(polish.get("brand")).upper()
    shade_clean = clean_shade_name(polish.get("shade_name"), brand_clean).upper()
    rating_norm = normalize_rating(polish.get("rating"))
    coats_clean = clean_single_str(polish.get("coats"))
    location_clean = clean_single_str(polish.get("location_id")) or "NONE"
    finishes_list = clean_datum_value(polish.get("finish"))
    size_clean = clean_single_str(polish.get("size_oz"))
    pdate_clean = clean_single_str(polish.get("purchase_date"))

    show_p6 = height_mm >= 48.0
    show_p5 = height_mm >= 40.0
    show_p4 = height_mm >= 34.0
    is_truncated = not (show_p6 and show_p5 and show_p4)

    meta_parts = []
    if size_clean:
        meta_parts.append(f"{size_clean}oz")
    if pdate_clean:
        if len(pdate_clean) >= 7 and "-" in pdate_clean:
            meta_parts.append(f"{pdate_clean[5:7]}/{pdate_clean[2:4]}")
        else:
            meta_parts.append(pdate_clean[:5])
    specs_str = " · ".join(meta_parts) if meta_parts else ""

    rating_str = f"{rating_norm}/5" if rating_norm is not None else "Unrated"
    finish_summary = ", ".join(finishes_list) if finishes_list else "Standard"

    qr_payload = (
        f"💅 {brand_clean or 'POLISH'}: {shade_clean}\n"
        f"⭐ {rating_str} | 🧥 {coats_clean or '2'} Coats\n"
        f"✨ {finish_summary}\n"
        f"📍 LOC: {location_clean}\n"
        f"🧴 {specs_str or 'N/A'}\n"
        f"🔗 {base_url}/items/{polish['item_id']}"
    )

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=2, border=1)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")
    qr_w, qr_h = qr_img.size

    # --- DYNAMIC TYPOGRAPHY SCALING ---
    # 1. Brand: Scaled up to 13pt
    brand_font, brand_pt, brand_lines = fit_text(brand_clean, max_pt=14, min_pt=10, max_w=116)
    
    # 2. Shade: Scaled up to 18-20pt (Hero element)
    shade_max = 20 if height_mm >= 50 else (17 if height_mm >= 40 else 15)
    shade_font, shade_pt, shade_lines = fit_text(shade_clean, max_pt=shade_max, min_pt=11, max_w=118)
    shade_block_h = (len(shade_lines) * (shade_pt + 3))

    # 3. Stars: Scaled up to 8px radius
    star_radius = 8 if height_mm >= 50 else 7

    # 4. Location: Scaled up to 13pt bold inside badge
    loc_font = get_font(size=13, bold=True)
    loc_text = f"LOC: {location_clean}"
    lw = loc_font.getbbox(loc_text)[2] - loc_font.getbbox(loc_text)[0]
    loc_badge_w = min(120, lw + 16)
    loc_badge_h = 22

    # Assemble Vertical Blocks
    blocks = []
    if show_p4 and brand_clean:
        blocks.append(("brand", brand_pt + 4))

    blocks.append(("shade", shade_block_h))

    if show_p5 and rating_norm is not None:
        blocks.append(("stars", (star_radius * 2) + 2))

    if show_p4 and coats_clean:
        blocks.append(("opacity", 16))

    if show_p6 and finishes_list:
        blocks.append(("finish_icons", 28))

    if show_p6 and specs_str:
        blocks.append(("meta", 12))

    blocks.append(("location", loc_badge_h))
    blocks.append(("qr", qr_h))

    total_blocks_h = sum([h for _, h in blocks])
    avail_gap = max(4, (HEIGHT_PX - total_blocks_h - 12) // len(blocks))

    # Render Progressively
    curr_y = 6
    for b_type, b_h in blocks:
        if b_type == "brand":
            bw = brand_font.getbbox(brand_clean)[2] - brand_font.getbbox(brand_clean)[0]
            draw.text(((WIDTH_PX - bw) / 2, curr_y), brand_clean, fill=0, font=brand_font)
            curr_y += b_h + avail_gap
            draw.line([16, curr_y - (avail_gap // 2), WIDTH_PX - 16, curr_y - (avail_gap // 2)], fill=0, width=1)

        elif b_type == "shade":
            for line in shade_lines:
                lw_line = shade_font.getbbox(line)[2] - shade_font.getbbox(line)[0]
                draw.text(((WIDTH_PX - lw_line) / 2, curr_y), line, fill=0, font=shade_font)
                curr_y += shade_pt + 3
            curr_y += avail_gap

        elif b_type == "stars":
            draw_star_row(draw, WIDTH_PX // 2, curr_y + star_radius, rating_norm, max_stars=5, radius=star_radius)
            curr_y += b_h + avail_gap

        elif b_type == "opacity":
            draw_opacity_dots(draw, WIDTH_PX // 2, curr_y + 8, coats_clean)
            curr_y += b_h + avail_gap

        elif b_type == "finish_icons":
            active_finishes = finishes_list[:3]
            n_icons = len(active_finishes)
            icon_box_size = 26
            box_spacing = 6
            total_icon_w = (n_icons * icon_box_size) + ((n_icons - 1) * box_spacing)
            start_x = (WIDTH_PX - total_icon_w) // 2

            for idx, f_name in enumerate(active_finishes):
                ix = start_x + (idx * (icon_box_size + box_spacing)) + (icon_box_size // 2)
                iy = curr_y + (icon_box_size // 2)
                draw.rounded_rectangle([ix - 13, iy - 13, ix + 13, iy + 13], radius=4, outline=0, width=1)
                draw_vector_icon(draw, ix, iy, 20, f_name)

            curr_y += b_h + avail_gap

        elif b_type == "meta":
            m_font = get_font(size=9, bold=False)
            mw = m_font.getbbox(specs_str)[2] - m_font.getbbox(specs_str)[0]
            draw.text(((WIDTH_PX - mw) / 2, curr_y), specs_str, fill=0, font=m_font)
            curr_y += b_h + avail_gap

        elif b_type == "location":
            # Prominent Rounded Location Badge
            badge_x = (WIDTH_PX - loc_badge_w) // 2
            draw.rounded_rectangle([badge_x, curr_y, badge_x + loc_badge_w, curr_y + loc_badge_h], radius=4, outline=0, width=1)
            draw.text(((WIDTH_PX - lw) / 2, curr_y + 3), loc_text, fill=0, font=loc_font)
            curr_y += b_h + (avail_gap // 2)

        elif b_type == "qr":
            qr_x = (WIDTH_PX - qr_w) // 2
            img.paste(qr_img, (qr_x, curr_y))

    return img, is_truncated, qr_payload

# ==============================================================================
# 9. DIRECTORY GENERATORS (24mm Continuous Tape & 8.5" x 11" Letter PDF)
# ==============================================================================
def render_tape_icon_directory():
    DPI = 180
    WIDTH_PX = 128
    ROW_H = 34
    TOTAL_H = len(ALL_FINISH_NAMES) * ROW_H + 40
    
    img = Image.new("1", (WIDTH_PX, TOTAL_H), 1)
    draw = ImageDraw.Draw(img)

    title_font = get_font(size=10, bold=True)
    draw.text((12, 10), "FINISH DIRECTORY", fill=0, font=title_font)
    draw.line([10, 26, WIDTH_PX - 10, 26], fill=0, width=1)

    y = 34
    lbl_font = get_font(size=9, bold=True)
    for fn in ALL_FINISH_NAMES:
        draw.rounded_rectangle([12, y, 36, y + 24], radius=3, outline=0, width=1)
        draw_vector_icon(draw, 24, y + 12, 18, fn)
        draw.text((44, y + 6), fn[:11], fill=0, font=lbl_font)
        y += ROW_H

    return img

@st.cache_data(ttl=0)
def render_letter_sheet_directory():
    WIDTH_PX = 2550
    HEIGHT_PX = 3300

    img = Image.new("RGB", (WIDTH_PX, HEIGHT_PX), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = get_font(size=64, bold=True)
    sub_font = get_font(size=26, bold=False)
    name_font = get_font(size=32, bold=True)
    desc_font = get_font(size=20, bold=False)

    title_text = "LACQUER FINISH DIRECTORY"
    sub_text = "Visual Icon Reference Key for Nail Polish Vault & Bottle Labels"
    draw.text((150, 140), title_text, fill=(20, 20, 20), font=title_font)
    draw.text((150, 225), sub_text, fill=(100, 100, 100), font=sub_font)
    draw.line([150, 280, WIDTH_PX - 150, 280], fill=(180, 180, 180), width=3)

    margin_x = 150
    margin_y = 340
    n_cols = 3
    col_w = (WIDTH_PX - (2 * margin_x) - ((n_cols - 1) * 45)) // n_cols
    row_h = 320
    box_gap_y = 35

    for idx, (fn, desc) in enumerate(FINISH_CATALOG):
        c = idx % n_cols
        r = idx // n_cols
        x = margin_x + c * (col_w + 45)
        y = margin_y + r * (row_h + box_gap_y)

        draw.rounded_rectangle([x, y, x + col_w, y + row_h], radius=16, outline=(210, 210, 210), width=2)

        icon_box_size = 110
        icon_box_x = x + 30
        icon_box_y = y + (row_h - icon_box_size) // 2
        draw.rounded_rectangle([icon_box_x, icon_box_y, icon_box_x + icon_box_size, icon_box_y + icon_box_size], 
                               radius=14, outline=(0, 0, 0), width=3)

        draw_vector_icon(draw, icon_box_x + (icon_box_size // 2), icon_box_y + (icon_box_size // 2), 80, fn)

        text_x = icon_box_x + icon_box_size + 28
        text_w = col_w - (icon_box_size + 85)

        draw.text((text_x, y + 55), fn.upper(), fill=(10, 10, 10), font=name_font)

        desc_words = desc.split(" ")
        lines = []
        cur_line = []
        for word in desc_words:
            test_line = " ".join(cur_line + [word])
            if desc_font.getbbox(test_line)[2] < text_w:
                cur_line.append(word)
            else:
                lines.append(" ".join(cur_line))
                cur_line = [word]
        if cur_line:
            lines.append(" ".join(cur_line))

        line_y = y + 115
        for line in lines[:3]:
            draw.text((text_x, line_y), line, fill=(90, 90, 90), font=desc_font)
            line_y += 32

    footer_text = "Generated by Koillection Bottle Label Maker • Standard 8.5\" × 11\" Letter"
    draw.line([150, HEIGHT_PX - 140, WIDTH_PX - 150, HEIGHT_PX - 140], fill=(220, 220, 220), width=2)
    draw.text((150, HEIGHT_PX - 110), footer_text, fill=(140, 140, 140), font=get_font(size=22, bold=False))

    return img

# ==============================================================================
# 10. ROUTING: DUAL-MODE (Mobile Card vs. Studio)
# ==============================================================================
query_card_id = st.query_params.get("card")

if query_card_id:
    polish = fetch_single_polish(query_card_id)
    if not polish:
        st.error("Polish specimen not found in database.")
        st.stop()

    b_clean = clean_single_str(polish.get('brand'))
    s_clean = clean_shade_name(polish.get('shade_name'), b_clean)
    r_norm = normalize_rating(polish.get('rating'))
    f_list = clean_datum_value(polish.get('finish'))

    st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>💅 Specimen Card</h2>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; color: #888;'>{b_clean or 'Unknown Brand'}</h4>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; margin-top: 0;'>{s_clean}</h1>", unsafe_allow_html=True)
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Storage Location", clean_single_str(polish.get("location_id")) or "Unassigned")
        st.metric("Finishes", ", ".join(f_list) if f_list else "Standard")
        st.metric("Rating", f"★ {r_norm}/5" if r_norm is not None else "N/A")
    with c2:
        st.metric("Suggested Coats", f"{clean_single_str(polish.get('coats')) or '2'} Coats")
        st.metric("Bottle Size", f"{clean_single_str(polish.get('size_oz'))} oz" if clean_single_str(polish.get('size_oz')) else "N/A")
        st.metric("Acquisition", str(clean_single_str(polish.get('purchase_date')))[:7] if clean_single_str(polish.get('purchase_date')) else "N/A")

    st.divider()
    koillection_url = f"http://{DEFAULT_LAN_IP}:8081/items/{polish['item_id']}"
    st.link_button("🚀 Open in Koillection Vault", koillection_url, use_container_width=True)
    st.stop()

# ==============================================================================
# 11. MAIN APP: TABS FOR LABEL STUDIO & ICON DIRECTORY
# ==============================================================================
tab_studio, tab_directory = st.tabs(["🏷️ Label Creator Studio", "📖 Finish Icon Directory"])

with tab_directory:
    st.header("📖 Lacquer Finish Icon Directory")
    st.caption("Export reference keys for your nail room, swatch albums, or polish drawers.")

    d_col1, d_col2 = st.columns([1, 2])
    
    with d_col1:
        st.subheader("Brother 24mm Tape Strip")
        st.write("A continuous vertical reference tape to stick inside Helmer drawers or on swatch album spines.")
        dir_tape_img = render_tape_icon_directory()
        st.image(dir_tape_img, caption="Continuous Tape Strip Preview", width=160)

        buf_dir = BytesIO()
        dir_tape_img.save(buf_dir, format="PNG")
        st.download_button(
            label="💾 Download Tape Strip (.png)",
            data=buf_dir.getvalue(),
            file_name="brother_24mm_finish_directory.png",
            mime="image/png",
            use_container_width=True
        )

    with d_col2:
        st.subheader("8.5\" × 11\" Letter Sheet Legend")
        st.write("A publication-grade 300 DPI reference sheet with icons, names, and descriptions formatted for standard home printers.")
        
        letter_img = render_letter_sheet_directory()
        
        st.image(letter_img, caption="8.5\" × 11\" Letter Preview (300 DPI)", width=480)

        pdf_buf = BytesIO()
        letter_img.save(pdf_buf, format="PDF", resolution=300.0)
        
        png_buf = BytesIO()
        letter_img.save(png_buf, format="PNG")

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            st.download_button(
                label="📄 Download Letter Sheet (.pdf)",
                data=pdf_buf.getvalue(),
                file_name="lacquer_finish_directory_letter.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        with btn_c2:
            st.download_button(
                label="🖼️ Download High-Res Sheet (.png)",
                data=png_buf.getvalue(),
                file_name="lacquer_finish_directory_letter.png",
                mime="image/png",
                use_container_width=True
            )

with tab_studio:
    st.sidebar.title("⚙️ Label Settings")

    lan_ip = st.sidebar.text_input("Host LAN IP (for Phone QR):", value=DEFAULT_LAN_IP)
    koillection_base_url = f"http://{lan_ip}:8081"

    st.sidebar.subheader("📏 Tape Length Presets")
    preset = st.sidebar.radio(
        "Quick Bottle Presets:",
        ["Mooncat / Holo Taco (55mm)", "ILNP / Cracked (48mm)", "Londontown Mini (34mm)", "Custom Slider"],
        index=0
    )

    if preset == "Mooncat / Holo Taco (55mm)":
        height_mm = 55.0
    elif preset == "ILNP / Cracked (48mm)":
        height_mm = 48.0
    elif preset == "Londontown Mini (34mm)":
        height_mm = 34.0
    else:
        height_mm = st.sidebar.slider("Custom Label Height (mm):", min_value=28.0, max_value=75.0, value=55.0, step=1.0)

    st.sidebar.subheader("🔄 Driver Feed Orientation")
    orientation = st.sidebar.radio(
        "Image Orientation:",
        ["Portrait (Vertical)", "Rotated 90° (Tape Feed / Driver Ready)"],
        index=0,
        help="Choose Rotated 90° if your Brother driver or P-Touch Editor expects horizontal ribbon feeds."
    )

    collections_df = fetch_collections()
    col_options = {"All Vault Polishes": None}
    for _, row in collections_df.iterrows():
        col_options[row["title"]] = row["id"]

    selected_col_title = st.sidebar.selectbox("Filter Collection:", list(col_options.keys()))
    selected_col_id = col_options[selected_col_title]

    polishes_df = fetch_polish_catalog(selected_col_id)
    if polishes_df.empty:
        st.warning("No items found in selected collection.")
        st.stop()

    polish_labels = [f"{clean_single_str(row['brand']) or 'Unknown'} - {clean_shade_name(row['shade_name'], clean_single_str(row['brand']))}" for _, row in polishes_df.iterrows()]
    selected_idx = st.selectbox("Select Polish to Export:", range(len(polish_labels)), format_func=lambda i: polish_labels[i])
    active_polish = polishes_df.iloc[selected_idx].to_dict()

    st.subheader("👁️ Live 180 DPI Label Preview")

    lbl_img, is_truncated, qr_payload = render_bottle_label(
        active_polish, 
        height_mm, 
        base_url=koillection_base_url
    )

    if orientation == "Rotated 90° (Tape Feed / Driver Ready)":
        final_export_img = lbl_img.rotate(90, expand=True)
    else:
        final_export_img = lbl_img

    col_preview, col_specs = st.columns([1, 2])

    with col_preview:
        st.image(lbl_img, caption=f"24mm Tape × {height_mm}mm Length", width=180)

    with col_specs:
        b_clean = clean_single_str(active_polish.get('brand'))
        s_clean = clean_shade_name(active_polish.get('shade_name'), b_clean)
        st.markdown(f"### **{b_clean} — {s_clean}**")
        
        if is_truncated:
            st.info("ℹ️ **Compact/Mini Truncation:** Lower-priority elements were omitted. The Hybrid QR code holds the complete offline specs!")
        else:
            st.success("✅ **Standard Full Label:** All badges fit cleanly on the bottle face.")

        img_buffer = BytesIO()
        final_export_img.save(img_buffer, format="PNG")
        file_slug = f"label_{b_clean}_{s_clean}".lower().replace(" ", "_").replace("'", "").replace("!", "")

        st.download_button(
            label="💾 Download Label Image (.png)",
            data=img_buffer.getvalue(),
            file_name=f"{file_slug}.png",
            mime="image/png",
            type="primary",
            use_container_width=True
        )

        st.caption("💡 **Print Tip:** Open this PNG with Brother P-Touch Editor / Windows Photo Viewer, or send it to your phone to print via the Brother mobile app over Bluetooth.")

        with st.expander("📱 View Decoded Phone QR Payload (Offline + Link)", expanded=True):
            st.code(qr_payload, language="text")