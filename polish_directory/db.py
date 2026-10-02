import os
import re
import json
import logging
import colorsys
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

logger = logging.getLogger("polish_directory.db")

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "koillection")
DB_USER = os.getenv("DB_USER", "koillection_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "local_polish_vault_2026")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

HEX_REGEX = re.compile(r'#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')

TYPE_KEYWORDS = [
    "regular nail lacquer", "regular", "uv gel nail lacquer", "uv gel", "gel",
    "cuticle oil", "nail treatment", "liquid latex", "drying drops",
    "stamping air dry lacquer", "latex tape", "top coat", "baee coat", "base coat",
    "press on glue/releaser", "press on glue", "glue"
]


def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)


def unwrap_datum_value(raw_val: str) -> str:
    if raw_val is None:
        return ""
    val_str = str(raw_val).strip()
    if (val_str.startswith("[") and val_str.endswith("]")) or (val_str.startswith("{") and val_str.endswith("}")):
        try:
            parsed = json.loads(val_str)
            if isinstance(parsed, list):
                cleaned = [str(item).strip() for item in parsed if item is not None and str(item).strip()]
                return ", ".join(cleaned)
            elif isinstance(parsed, dict):
                return ", ".join(f"{k}: {v}" for k, v in parsed.items())
        except Exception:
            return val_str.strip('[]"\'')
    return val_str.strip('[]"\'')


def clean_shade_name(raw_shade: str, brand: str) -> str:
    if not raw_shade:
        return "Untitled Shade"
    s = str(raw_shade).strip()
    b = str(brand or "").strip()
    if b and b.lower() != "unknown brand":
        for sep in [" - ", " – ", " — ", " : ", " | "]:
            prefix = f"{b}{sep}".lower()
            if s.lower().startswith(prefix):
                return s[len(prefix):].strip()
    return s


def extract_valid_hex(raw_text: str) -> str:
    if not raw_text:
        return ""
    clean = unwrap_datum_value(raw_text)
    match = HEX_REGEX.search(clean)
    if match:
        hex_str = match.group(0).upper()
        if not hex_str.startswith("#"):
            hex_str = f"#{hex_str}"
        if len(hex_str) == 4:
            hex_str = f"#{hex_str[1]*2}{hex_str[2]*2}{hex_str[3]*2}"
        return hex_str
    return ""


def hex_to_color_profile(hex_code: str):
    if not hex_code:
        return 999.0, 0.0, 0.0, "No Color Set", 99

    clean = hex_code.strip().lstrip("#")
    if len(clean) != 6:
        return 999.0, 0.0, 0.0, "No Color Set", 99

    try:
        r = int(clean[0:2], 16) / 255.0
        g = int(clean[2:4], 16) / 255.0
        b = int(clean[4:6], 16) / 255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        h_deg = h * 360.0

        if v < 0.20:
            family = "Blacks & Deep Charcoals"
            sort_order = 1
        elif s < 0.12 and v > 0.80:
            family = "Whites & Soft Creams"
            sort_order = 2
        elif s < 0.15:
            family = "Grays & Neutrals"
            sort_order = 3
        elif h_deg < 15 or h_deg >= 345:
            family = "Reds & Crimsons"
            sort_order = 4
        elif 15 <= h_deg < 45:
            family = "Oranges & Corals"
            sort_order = 5
        elif 45 <= h_deg < 70:
            family = "Yellows & Golds"
            sort_order = 6
        elif 70 <= h_deg < 165:
            family = "Greens & Mints"
            sort_order = 7
        elif 165 <= h_deg < 195:
            family = "Teals & Aquas"
            sort_order = 8
        elif 195 <= h_deg < 255:
            family = "Blues & Navies"
            sort_order = 9
        elif 255 <= h_deg < 290:
            family = "Purples & Violets"
            sort_order = 10
        elif 290 <= h_deg < 345:
            family = "Pinks & Magentas"
            sort_order = 11
        else:
            family = "Specialty & Earth"
            sort_order = 12

        return round(h_deg, 1), round(s, 2), round(v, 2), family, sort_order
    except Exception:
        return 999.0, 0.0, 0.0, "No Color Set", 99


@st.cache_data(ttl=0)
def fetch_polish_inventory() -> pd.DataFrame:
    engine = get_engine()
    query = text("""
        SELECT 
            CAST(i.id AS text) AS item_id,
            i.name AS shade_name,
            CAST(c.id AS text) AS collection_id,
            c.title AS collection_title,
            d.label AS datum_label,
            d.value AS datum_value,
            d.type AS datum_type
        FROM koi_item i
        LEFT JOIN koi_collection c ON i.collection_id = c.id
        LEFT JOIN koi_datum d ON d.item_id = i.id
        ORDER BY i.name ASC
    """)
    
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
        
    if not rows:
        return pd.DataFrame()

    polishes = {}
    for row in rows:
        item_id = row.item_id
        if item_id not in polishes:
            polishes[item_id] = {
                "item_id": item_id,
                "raw_shade_name": row.shade_name or "Untitled Shade",
                "shade_name": row.shade_name or "Untitled Shade",
                "collection": row.collection_title or "Uncategorized",
                "brand": "Unknown Brand",
                "color_hex": "",
                "has_exact_hex": False,
                "nail_type": "Regular Nail Lacquer",
                "finish": "Creme",
                "coats": "",       # Unset so app setting default can apply dynamically
                "size_oz": "",
                "purchase_date": "",
                "location": "Unassigned",
                "rating_10": None,
                "rating_5": 0.0,
            }
            
        label = (row.datum_label or "").strip()
        val = row.datum_value
        if not label or val is None:
            continue
            
        clean_val = unwrap_datum_value(val)
        label_lower = label.lower()
        datum_type = (row.datum_type or "").lower()
        
        # 1. Exact Hex Fields
        if "colour (hex)" in label_lower or "color (hex)" in label_lower or label_lower == "hex" or datum_type == "color":
            if not polishes[item_id]["has_exact_hex"]:
                found_hex = extract_valid_hex(clean_val)
                if found_hex:
                    polishes[item_id]["color_hex"] = found_hex
                    polishes[item_id]["has_exact_hex"] = True

        # 2. Descriptive Color Fallback
        elif label_lower in ["color", "colour", "primary color", "swatch color"]:
            if not polishes[item_id]["has_exact_hex"] and not polishes[item_id]["color_hex"]:
                found_hex = extract_valid_hex(clean_val)
                if found_hex:
                    polishes[item_id]["color_hex"] = found_hex

        # 3. Formulation Type
        elif label_lower in ["nail polish type", "polish type", "type"]:
            if clean_val:
                polishes[item_id]["nail_type"] = clean_val

        # 4. Brand
        elif label_lower == "brand":
            polishes[item_id]["brand"] = clean_val or "Unknown Brand"

        # 5. Aesthetic Finish
        elif label_lower in ["finish", "finish (colour picker)", "lacquer finish", "effect"]:
            if clean_val:
                polishes[item_id]["finish"] = clean_val

        # 6. Coats (Only sets if explicitly entered in Koillection)
        elif label_lower in ["coats", "coat count"]:
            if clean_val and clean_val.strip() not in ["", "None", "nan", "0"]:
                polishes[item_id]["coats"] = clean_val.strip()

        # 7. Size
        elif "size" in label_lower:
            polishes[item_id]["size_oz"] = clean_val

        # 8. Purchase Date
        elif label_lower in ["purchase date", "acquisition date", "date"]:
            polishes[item_id]["purchase_date"] = clean_val

        # 9. Location
        elif label_lower in ["location", "storage location", "slot"]:
            polishes[item_id]["location"] = clean_val or "Unassigned"

        # 10. Star Rating
        elif label_lower in ["overall rating", "rating"]:
            try:
                raw_score = float(clean_val)
                polishes[item_id]["rating_10"] = raw_score
                polishes[item_id]["rating_5"] = round(raw_score / 2.0, 1)
            except (ValueError, TypeError):
                polishes[item_id]["rating_5"] = 0.0

    # Clean & Deduplicate fields
    for p in polishes.values():
        p["shade_name"] = clean_shade_name(p["raw_shade_name"], p["brand"])
        
        raw_finish_parts = [piece.strip() for piece in str(p["finish"]).split(",") if piece.strip()]
        cleaned_finish_parts = []
        for part in raw_finish_parts:
            part_lower = part.lower()
            if any(tk in part_lower for tk in TYPE_KEYWORDS):
                if p["nail_type"] == "Regular Nail Lacquer":
                    p["nail_type"] = part
            else:
                cleaned_finish_parts.append(part)
                
        p["finish"] = ", ".join(cleaned_finish_parts) if cleaned_finish_parts else "Creme"

        t_lower = p["nail_type"].lower()
        if "uv gel" in t_lower or "gel" in t_lower:
            p["nail_type"] = "UV Gel Nail Lacquer"
        elif "regular" in t_lower or "lacquer" in t_lower and not any(k in t_lower for k in ["top", "base", "stamping"]):
            p["nail_type"] = "Regular Nail Lacquer"

        h_deg, s, v, family, sort_order = hex_to_color_profile(p["color_hex"])
        p["hue"] = h_deg
        p["saturation"] = s
        p["value"] = v
        p["color_family"] = family
        p["color_sort_key"] = sort_order

        r = p["rating_5"]
        if r >= 4.5:
            p["rating_group"] = "5 Stars (Holy Grails)"
        elif r >= 3.5:
            p["rating_group"] = "4 Stars (Great Formulations)"
        elif r >= 2.5:
            p["rating_group"] = "3 Stars (Average)"
        elif r > 0.0:
            p["rating_group"] = "1-2 Stars (Low Rating)"
        else:
            p["rating_group"] = "Unrated"

        acq = str(p["purchase_date"] or "")
        p["acquisition_year"] = acq[:4] if (len(acq) >= 4 and acq[:4].isdigit()) else "Undated"

    df = pd.DataFrame(list(polishes.values()))
    
    if not df.empty:
        df["_loc_sort"] = df["location"].astype(str).str.lower()
        df["_brand_sort"] = df["brand"].astype(str).str.lower()
        df["_shade_sort"] = df["shade_name"].astype(str).str.lower()
        df.sort_values(by=["_loc_sort", "_brand_sort", "_shade_sort"], inplace=True)
        df.drop(columns=["_loc_sort", "_brand_sort", "_shade_sort"], errors="ignore", inplace=True)
        df.reset_index(drop=True, inplace=True)
        
    return df


def get_unique_filter_values(df: pd.DataFrame):
    if df.empty:
        return [], [], [], [], []
    locations = sorted([loc for loc in df["location"].unique() if loc], key=str.lower)
    brands = sorted([b for b in df["brand"].unique() if b and b != "Unknown Brand"], key=str.lower)
    types = sorted([t for t in df["nail_type"].unique() if t], key=str.lower)
    color_families = sorted([cf for cf in df["color_family"].unique() if cf])
    finishes = set()
    for f_val in df["finish"].dropna():
        for piece in str(f_val).split(","):
            p = piece.strip()
            if p:
                finishes.add(p)
    return locations, brands, sorted(list(finishes), key=str.lower), color_families, types