import streamlit as st
import pandas as pd
import math
import os
import re
import base64
import uuid
import datetime
import colorsys
import json
import time
from sqlalchemy import text
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="Smart Color Matcher & Quality Studio", page_icon="💅", layout="wide")

# --- SESSION STATE INITIALIZATION (GOLDEN RULE) ---
if "current_polish_id" not in st.session_state:
    st.session_state.current_polish_id = None
if "last_click" not in st.session_state:
    st.session_state.last_click = None
if "vault" not in st.session_state:
    st.session_state.vault = {}

# Strict Hex Validator
HEX_REGEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")

# ==========================================
# ⚙️ CONFIGURATION & SETTINGS
# ==========================================
KOILLECTION_WEB_URL = "http://localhost:8081" 
IMAGE_DIR = "/app/public/uploads"
SETTINGS_FILE = "settings.json"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"show_instructions": True, "last_collection_id": None}


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
    except Exception:
        pass


app_settings = load_settings()


# --- DATABASE CONNECTION ---
def get_db_url():
    user = os.getenv("DB_USER", "koillection_user")
    password = os.getenv("DB_PASSWORD", "local_polish_vault_2026")
    host = os.getenv("DB_HOST", "db")
    port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "koillection")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


def unwrap_datum_value(raw_val: str) -> str:
    """Safely unwraps Koillection's JSON array strings e.g. ['#FF0000'] -> #FF0000"""
    if raw_val is None:
        return ""
    val_str = str(raw_val).strip()
    if (val_str.startswith("[") and val_str.endswith("]")) or (val_str.startswith("{") and val_str.endswith("}")):
        try:
            parsed = json.loads(val_str)
            if isinstance(parsed, list):
                cleaned = [str(item).strip() for item in parsed if item is not None and str(item).strip()]
                return cleaned[0] if cleaned else ""
            elif isinstance(parsed, dict):
                return ", ".join(f"{k}: {v}" for k, v in parsed.items())
        except Exception:
            return val_str.strip('[]"\'')
    return val_str.strip('[]"\'')


# --- DYNAMIC FINISH OPTIONS ---
@st.cache_data(ttl=0, show_spinner="🔄 Fetching Lacquer Types...")
def fetch_finish_options():
    try:
        conn = st.connection("koillection_db", type="sql", url=get_db_url())
        query = """
            SELECT c.label 
            FROM koi_choice c 
            JOIN koi_choice_list cl ON c.choice_list_id = cl.id 
            WHERE cl.name = 'Lacquer Type'
            ORDER BY c.label ASC;
        """
        df = conn.query(query, ttl=0)
        if not df.empty:
            return df["label"].tolist()
    except Exception as e:
        print(f"Database error fetching choice list: {e}")
        
    return [
        "Creme", "Holographic (Linear)", "Holographic (Scattered)", "Glitter", 
        "Magnetic", "Multichrome", "Duochrome", "Jelly", "Pearl", "Matte", 
        "Topper", "Flakie", "Shimmer", "Metallic", "Neon", "Thermal", "Solar"
    ]


FINISH_OPTIONS = fetch_finish_options()


# --- COLOR VALIDATION & MATH ---
def is_valid_hex(val) -> bool:
    clean = unwrap_datum_value(val)
    if not clean:
        return False
    return bool(HEX_REGEX.match(clean))


def normalize_hex(val, default="#FF0000") -> str:
    clean = unwrap_datum_value(val)
    if not is_valid_hex(clean):
        return default
    if not clean.startswith("#"):
        clean = "#" + clean
    if len(clean) == 4:
        clean = f"#{clean[1]*2}{clean[2]*2}{clean[3]*2}"
    return clean.upper()


def hex_to_rgb(hex_color):
    hex_color = str(hex_color).lstrip("#")
    if len(hex_color) != 6:
        return (0, 0, 0) 
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (0, 0, 0)


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(int(round(rgb[0])), int(round(rgb[1])), int(round(rgb[2]))).upper()


def color_distance(hex1, hex2):
    if not is_valid_hex(hex1) or not is_valid_hex(hex2):
        return float("inf")
        
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)

    rmean = (r1 + r2) / 2
    r = r1 - r2
    g = g1 - g2
    b = b1 - b2

    weight_r = 2 + rmean / 256
    weight_g = 4.0
    weight_b = 2 + (255 - rmean) / 256

    return math.sqrt(weight_r * (r ** 2) + weight_g * (g ** 2) + weight_b * (b ** 2))


def get_color_harmonies(hex_color):
    r, g, b = hex_to_rgb(hex_color)
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
    
    comp_h = (h + 0.5) % 1.0
    comp_rgb = colorsys.hsv_to_rgb(comp_h, s, v)
    comp_hex = rgb_to_hex([x * 255 for x in comp_rgb])
    
    ana1_h = (h + (30/360)) % 1.0
    ana2_h = (h - (30/360)) % 1.0
    ana1_rgb = colorsys.hsv_to_rgb(ana1_h, s, v)
    ana2_rgb = colorsys.hsv_to_rgb(ana2_h, s, v)
    ana1_hex = rgb_to_hex([x * 255 for x in ana1_rgb])
    ana2_hex = rgb_to_hex([x * 255 for x in ana2_rgb])
    
    tri1_h = (h + (120/360)) % 1.0
    tri2_h = (h + (240/360)) % 1.0
    tri1_rgb = colorsys.hsv_to_rgb(tri1_h, s, v)
    tri2_rgb = colorsys.hsv_to_rgb(tri2_h, s, v)
    tri1_hex = rgb_to_hex([x * 255 for x in tri1_rgb])
    tri2_hex = rgb_to_hex([x * 255 for x in tri2_rgb])
    
    return {
        "Complementary": [comp_hex],
        "Analogous": [ana1_hex, ana2_hex],
        "Triadic": [tri1_hex, tri2_hex]
    }


def find_closest_polish(target_hex, tagged_df, exclude_id=None):
    temp_df = tagged_df.copy()
    if exclude_id:
        temp_df = temp_df[temp_df["id"] != exclude_id]
    if temp_df.empty: 
        return None
    
    temp_df["Dist"] = temp_df["color_hex"].apply(lambda x: color_distance(target_hex, x))
    best_match = temp_df.loc[temp_df["Dist"].idxmin()]
    return best_match


# --- DIRECT DATABASE FUNCTIONS (GOLDEN RULE 1.1: SAFE CAST) ---
@st.cache_data(ttl=0)
def fetch_collections():
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    query = "SELECT CAST(id AS text) AS id, title FROM koi_collection ORDER BY title ASC;"
    return conn.query(query, ttl=0)


@st.cache_data(ttl=0)
def fetch_polishes(collection_id):
    if not collection_id:
        return pd.DataFrame()
        
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    
    cols_df = conn.query("SELECT column_name FROM information_schema.columns WHERE table_name = 'koi_datum'", ttl=0)
    datum_cols = cols_df["column_name"].tolist()
    
    gallery_cols = ["d.value"]
    if "image" in datum_cols: gallery_cols.insert(0, "d.image")
    if "file" in datum_cols: gallery_cols.insert(0, "d.file")
    
    gallery_sql = f"COALESCE({', '.join(gallery_cols)})"
    
    # Explicit case isolation prevents collision with descriptive 'Color' field
    query = f"""
    SELECT 
        CAST(i.id AS text) AS id, 
        i.name, 
        i.image AS main_image, 
        STRING_AGG(DISTINCT CASE WHEN d.type = 'image' OR d.type = 'file' THEN {gallery_sql} END, ',') AS gallery_images,
        i.created_at,
        MAX(CASE WHEN (d.label ILIKE '%colour (hex)%' OR d.label ILIKE '%color (hex)%' OR d.label = 'Hex') AND d.label NOT ILIKE '%secondary%' THEN d.value END) AS raw_color_hex,
        MAX(CASE WHEN (d.label ILIKE '%colour (hex)%' OR d.label ILIKE '%color (hex)%' OR d.label = 'Hex') AND d.label NOT ILIKE '%secondary%' THEN CAST(d.id AS text) END) AS data_field_id,
        MAX(CASE WHEN d.label ILIKE '%secondary%hex%' THEN d.value END) AS raw_color_hex_2,
        MAX(CASE WHEN d.label ILIKE '%secondary%hex%' THEN CAST(d.id AS text) END) AS data_field_id_2,
        MAX(CASE WHEN d.label ILIKE 'Finish%' THEN d.value END) AS finish,
        MAX(CASE WHEN d.label ILIKE 'Finish%' THEN CAST(d.id AS text) END) AS finish_field_id,
        MAX(CASE WHEN d.label = 'Brand' THEN d.value END) AS brand,
        MAX(CASE WHEN d.label ILIKE 'Location%' THEN d.value END) AS location,
        MAX(CASE WHEN d.label IN ('Color', 'Colour') AND d.label NOT ILIKE '%hex%' THEN d.value END) AS descriptive_color
    FROM koi_item i
    LEFT JOIN koi_datum d ON i.id = d.item_id
    WHERE CAST(i.collection_id AS text) = '{collection_id}'
    GROUP BY i.id, i.name, i.image, i.created_at;
    """
    
    df = conn.query(query, ttl=0)
    
    if not df.empty:
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"]).dt.date
            
        # Unwrap JSON array wrappers from database strings
        df["color_hex"] = df["raw_color_hex"].apply(unwrap_datum_value)
        df["color_hex_2"] = df["raw_color_hex_2"].apply(unwrap_datum_value)
        df["descriptive_color"] = df["descriptive_color"].apply(unwrap_datum_value)
        df["brand"] = df["brand"].apply(unwrap_datum_value)
        
    return df


def save_polish_data_to_db(item_id, fields_to_save):
    """
    Saves or updates datum fields in PostgreSQL.
    Adheres strictly to Golden Rule 1.1 (CAST) and Golden Rule 3.4 (owner_id & public visibility).
    """
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    now = datetime.datetime.now(datetime.timezone.utc)
    
    try:
        with conn.session as session:
            owner_query = text("SELECT CAST(owner_id AS text) AS owner_id FROM koi_item WHERE id = CAST(:item_id AS text)")
            owner_row = session.execute(owner_query, {"item_id": str(item_id)}).fetchone()
            owner_id = owner_row[0] if owner_row and owner_row[0] else None

            for field in fields_to_save:
                field_id = field["id"]
                label = field["label"]
                val = str(field["value"] or "").strip()
                field_type = "color" if "Hex" in label else "text"
                
                if field_id and not pd.isna(field_id) and str(field_id).strip():
                    session.execute(
                        text("""
                        UPDATE koi_datum 
                        SET value = :val, type = :type, updated_at = :now 
                        WHERE id = CAST(:id AS text)
                        """),
                        {"val": val, "type": field_type, "now": now, "id": str(field_id)}
                    )
                elif val != "": 
                    new_id = str(uuid.uuid4())
                    session.execute(
                        text("""
                        INSERT INTO koi_datum (
                            id, item_id, owner_id, type, label, value, 
                            position, created_at, updated_at, visibility, final_visibility
                        ) 
                        VALUES (
                            CAST(:id AS text), CAST(:item_id AS text), CAST(:owner_id AS text), 
                            :type, :label, :val, 1, :now, :now, 'public', 'public'
                        )
                        """),
                        {
                            "id": new_id, 
                            "item_id": str(item_id), 
                            "owner_id": owner_id, 
                            "type": field_type, 
                            "label": label, 
                            "val": val, 
                            "now": now
                        }
                    )
            
            session.execute(
                text("UPDATE koi_item SET updated_at = :now WHERE id = CAST(:item_id AS text)"),
                {"now": now, "item_id": str(item_id)}
            )
            
            session.commit()
        return True
    except Exception as e:
        st.error(f"Database write error: {e}")
        return False


# --- LOCAL IMAGE LOADERS ---
def resolve_image_path(img_path):
    if not img_path or pd.isna(img_path): return None
    clean_path = str(img_path).replace("\\", "/").lstrip("/")
    
    possible_paths = [
        os.path.join("/app/public", clean_path), 
        os.path.join("/", clean_path),           
        os.path.join("/uploads", clean_path.replace("uploads/", "", 1)) 
    ]
    
    for p in possible_paths:
        if os.path.exists(p):
            return p
            
    return possible_paths[0]


def get_image_base64(img_path):
    full_path = resolve_image_path(img_path)
    if not full_path or not os.path.exists(full_path): return None
    try:
        with open(full_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception:
        return None


def get_pil_image(img_path):
    full_path = resolve_image_path(img_path)
    if not full_path or not os.path.exists(full_path): 
        return None
    try:
        return Image.open(full_path).convert("RGB")
    except Exception:
        return None


# --- HTML CARD GENERATOR ---
def create_polish_card_html(row, distance_text=None, math_color=None):
    img_html = ""
    img_b64 = get_image_base64(row["main_image"])
    if img_b64:
        img_html = (
            f'<label for="lb_{row["id"]}" style="cursor: zoom-in; margin: 0;">'
            f'<img src="data:image/jpeg;base64,{img_b64}" style="width: 70px; height: 70px; object-fit: cover; border-radius: 8px; margin-right: 15px; border: 1px solid #ddd; transition: transform 0.2s;" onmouseover="this.style.transform=\'scale(1.05)\'" onmouseout="this.style.transform=\'scale(1)\'">'
            f'</label>'
            f'<input type="checkbox" id="lb_{row["id"]}" class="lb-checkbox">'
            f'<div class="lb-overlay">'
            f'<label for="lb_{row["id"]}" class="lb-bg-close"></label>'
            f'<img src="data:image/jpeg;base64,{img_b64}" style="position: relative; z-index: 2;">'
            f'</div>'
        )

    c1 = normalize_hex(row.get("color_hex"), "#CCCCCC")
    c2 = normalize_hex(row.get("color_hex_2"), c1)
    circle_css = f"background: linear-gradient(135deg, {c1} 50%, {c2} 50%);"

    badges_html = ""
    if pd.notna(row.get("finish")) and row.get("finish") != "":
        finishes = [f.strip() for f in str(row["finish"]).split(",")]
        for f in finishes:
            badges_html += f'<span class="finish-badge">{f}</span>'
            
    location_html = ""
    if pd.notna(row.get("location")) and str(row["location"]).strip() != "":
        location_html = f'<br><span style="color: #008080; font-size: 0.95em; font-weight: bold;">📍 Location: {row["location"]}</span>'

    display_title = f"{row['brand']} - {row['name']}" if pd.notna(row.get("brand")) and row["brand"] else row["name"]
    item_url = f"{KOILLECTION_WEB_URL}/items/{row['id']}"

    dist_html = f'<span style="color: #666; font-size: 0.9em;">{distance_text}</span><br>' if distance_text else ""
    
    math_color_html = ""
    if math_color:
        math_color_html = f'<div style="display: flex; align-items: center; margin-top: 5px;"><div style="width: 15px; height: 15px; border-radius: 50%; background-color: {math_color}; border: 1px solid #999; margin-right: 5px;"></div><span style="font-size: 0.8em; color: #666;">Target: {math_color}</span></div>'

    final_html = (
        f'<div style="display: flex; align-items: center; margin-bottom: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 8px; color: #333;">'
        f'{img_html}'
        f'<div style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid #ddd; margin-right: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); {circle_css}"></div>'
        f'<div>'
        f'<a href="{item_url}" target="_blank" class="polish-link">'
        f'<strong style="font-size: 1.2em;">{display_title}</strong>'
        f'</a><br>'
        f'{dist_html}'
        f'{location_html}'
        f'{math_color_html}'
        f'<div style="margin-top: 4px;">{badges_html}</div>'
        f'</div>'
        f'</div>'
    )
    return final_html


# --- APP SETUP ---
st.title("💅 Smart Color Matcher & Quality Studio")

# Inject CSS for Lightbox and Badges
st.markdown("""
<style>
.lb-checkbox { display: none; }
.lb-overlay {
    display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(0,0,0,0.85); z-index: 999999; align-items: center; justify-content: center;
}
.lb-checkbox:checked + .lb-overlay { display: flex; }
.lb-overlay img { max-width: 90vw; max-height: 90vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.8); }
.lb-bg-close { position: absolute; top: 0; left: 0; width: 100%; height: 100%; cursor: zoom-out; }
.polish-link { text-decoration: none; color: #333; transition: color 0.2s; }
.polish-link:hover { color: #008080; text-decoration: underline; }
.finish-badge { 
    display: inline-block; background-color: #e0e0e0; color: #333; 
    padding: 2px 8px; border-radius: 12px; font-size: 0.75em; margin-right: 5px; margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# --- COLLECTION SELECTOR ---
try:
    collections_df = fetch_collections()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

if collections_df.empty:
    st.warning("No collections found in the database. Please create a collection in Koillection first.")
    st.stop()

collection_dict = dict(zip(collections_df["title"], collections_df["id"]))

st.markdown("### 📁 Select Collection")

last_col_id = app_settings.get("last_collection_id")
col_titles = list(collection_dict.keys())
default_index = 0

if last_col_id in collection_dict.values():
    for i, title in enumerate(col_titles):
        if collection_dict[title] == last_col_id:
            default_index = i
            break

selected_collection_title = st.selectbox("Choose a collection to track:", col_titles, index=default_index, label_visibility="collapsed")
selected_collection_id = collection_dict[selected_collection_title]

if selected_collection_id != last_col_id:
    app_settings["last_collection_id"] = selected_collection_id
    save_settings(app_settings)

try:
    df = fetch_polishes(selected_collection_id)
except Exception as e:
    st.error(f"Failed to fetch items: {e}")
    st.stop()

# --- CLASSIFY COLOR STATUS FOR TRIAGE ---
if not df.empty:
    def classify_row(row):
        val = row.get("color_hex")
        if not val or pd.isna(val) or not str(val).strip():
            return "untagged"
        if is_valid_hex(val):
            return "valid"
        return "invalid"

    df["color_status"] = df.apply(classify_row, axis=1)
else:
    df["color_status"] = []

# --- UI TABS ---
tab_triage, tab_search, tab_pairings = st.tabs(["🏷️ Tag & Audit Workstation", "🔍 Search Collection", "🎨 Nail Art Pairings"])

# =============================================================================
# TAB 1: TAG & AUDIT WORKSTATION (RADICALLY EASY ID)
# =============================================================================
with tab_triage:
    st.header("🏷️ Polish Color Quality Control & Triage")
    st.write(
        "Easily identify and resolve polishes with missing or corrupted color data. "
        "The descriptive `Color` field is safely preserved while writing verified hex codes to `Colour (Hex)`."
    )
    
    if not df.empty:
        # Compute exact counts
        invalid_count = len(df[df["color_status"] == "invalid"])
        untagged_count = len(df[df["color_status"] == "untagged"])
        valid_count = len(df[df["color_status"] == "valid"])
        action_count = invalid_count + untagged_count

        # Visual Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚨 Total Needing Action", f"{action_count} polishes")
        m2.metric("⚠️ Invalid Format (Corrupted)", f"{invalid_count} polishes", delta=f"{invalid_count} to fix" if invalid_count > 0 else "0 Clean", delta_color="inverse")
        m3.metric("⚪ Missing Hex (Untagged)", f"{untagged_count} polishes")
        m4.metric("✅ Verified Hex Codes", f"{valid_count} polishes")

        st.markdown("---")

        # Triage Queue Switcher
        st.subheader("1. Filter Your Work Queue")
        queue_choice = st.radio(
            "Select which polishes to display:",
            options=["needs_action", "invalid_only", "untagged_only", "valid_only", "all"],
            index=0 if action_count > 0 else 4,
            horizontal=True,
            format_func=lambda x: {
                "needs_action": f"🚨 All Incomplete ({action_count})",
                "invalid_only": f"⚠️ Invalid Format Only ({invalid_count})",
                "untagged_only": f"⚪ Untagged Only ({untagged_count})",
                "valid_only": f"✅ Verified Tagged ({valid_count})",
                "all": f"📂 All ({len(df)})"
            }[x]
        )

        # Apply Queue Filtering
        queue_df = df.copy()
        if queue_choice == "needs_action":
            queue_df = queue_df[queue_df["color_status"].isin(["invalid", "untagged"])]
        elif queue_choice == "invalid_only":
            queue_df = queue_df[queue_df["color_status"] == "invalid"]
        elif queue_choice == "untagged_only":
            queue_df = queue_df[queue_df["color_status"] == "untagged"]
        elif queue_choice == "valid_only":
            queue_df = queue_df[queue_df["color_status"] == "valid"]

        # Search Bar
        search_filter = st.text_input("🔍 Quick Search by Name / Brand in this Queue", placeholder="Type shade name...").strip().lower()
        if search_filter:
            queue_df = queue_df[
                queue_df["name"].str.lower().str.contains(search_filter) |
                queue_df["brand"].str.lower().str.contains(search_filter)
            ]

        # VISUAL AUDIT TABLE (Shows user exactly what is in DB)
        with st.expander("📋 View Polish Audit Table", expanded=True):
            audit_display = queue_df[["brand", "name", "color_status", "color_hex", "descriptive_color", "location"]].copy()
            audit_display.rename(columns={
                "brand": "Brand",
                "name": "Shade Name",
                "color_status": "Status",
                "color_hex": "Value in 'Colour (Hex)'",
                "descriptive_color": "Value in 'Color'",
                "location": "Location"
            }, inplace=True)
            
            # Map human status labels
            audit_display["Status"] = audit_display["Status"].map({
                "invalid": "⚠️ INVALID FORMAT",
                "untagged": "⚪ UNTAGGED",
                "valid": "✅ VERIFIED HEX"
            })

            st.dataframe(
                audit_display,
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")
        st.subheader("2. Select Polish to Tag / Fix")

        if not queue_df.empty:
            def format_dropdown_item(row):
                b = f"[{row['brand']}] " if row["brand"] else ""
                badge = ""
                if row["color_status"] == "invalid":
                    badge = f" ⚠️ [INVALID: '{row['color_hex']}']"
                elif row["color_status"] == "untagged":
                    badge = " ⚪ [MISSING HEX]"
                return f"{b}{row['name']}{badge}"

            queue_df["selector_label"] = queue_df.apply(format_dropdown_item, axis=1)
            selector_options = queue_df["selector_label"].tolist()

            selected_label = st.selectbox("Select Polish to Work On:", selector_options)
            selected_row = queue_df[queue_df["selector_label"] == selected_label].iloc[0]

            # Wipe vault when switching polishes
            if st.session_state.get("current_polish_id") != selected_row["id"]:
                st.session_state["current_polish_id"] = selected_row["id"]
                st.session_state.vault = {} 
                st.session_state["last_click"] = None
                st.rerun()

            # Prominent Problem Callout
            if selected_row["color_status"] == "invalid":
                st.error(
                    f"🚨 **Problem Detected on {selected_row['name']}!**  \n"
                    f"The database field `Colour (Hex)` currently contains: **`'{selected_row['color_hex']}'`**  \n"
                    f"This is text/corrupted data, not a `#RRGGBB` hex code. Click on the swatch photo below to assign a genuine color!"
                )
            elif selected_row["color_status"] == "untagged":
                st.info(f"⚪ **{selected_row['name']}** has no hex swatch assigned. Click on the photo below to sample its color.")
            else:
                st.success(f"✅ **{selected_row['name']}** has a verified hex code: **`{selected_row['color_hex']}`**.")

            # Vault Initialization with Safe Fallback
            if "color_1" not in st.session_state.vault:
                st.session_state.vault["color_1"] = normalize_hex(selected_row["color_hex"], "#FF0000")
            
            if "color_2" not in st.session_state.vault:
                st.session_state.vault["color_2"] = normalize_hex(selected_row["color_hex_2"], "#0000FF")
            
            if "has_sec" not in st.session_state.vault:
                st.session_state.vault["has_sec"] = is_valid_hex(selected_row["color_hex_2"])
                
            if "finishes" not in st.session_state.vault:
                current_finishes = []
                if pd.notna(selected_row["finish"]) and str(selected_row["finish"]).strip() != "":
                    raw_finishes = [f.strip() for f in str(selected_row["finish"]).split(",")]
                    current_finishes = [f for f in raw_finishes if f in FINISH_OPTIONS]
                st.session_state.vault["finishes"] = current_finishes
            
            picker_key_1 = f"color_picker_1_{selected_row['id']}"
            picker_key_2 = f"color_picker_2_{selected_row['id']}"
            has_sec_key = f"has_sec_{selected_row['id']}"
            finish_key = f"finish_{selected_row['id']}"

            img_col, picker_col = st.columns([1, 1]) 
            
            with img_col:
                eyedropper_target = st.radio(
                    "🎯 **Eyedropper Target:**", 
                    ["Primary Color", "Secondary Color"], 
                    horizontal=True
                )
                
                images = []
                if pd.notna(selected_row["main_image"]) and selected_row["main_image"]:
                    images.append(selected_row["main_image"])
                if pd.notna(selected_row["gallery_images"]) and selected_row["gallery_images"]:
                    for img in str(selected_row["gallery_images"]).split(","):
                        clean_img = img.strip()
                        if clean_img and clean_img not in images:
                            images.append(clean_img)
                
                if images:
                    selected_img_idx = 0
                    selected_img_path = images[0]
                    
                    if len(images) > 1:
                        img_options = ["Main Image"] + [f"Gallery Image {i}" for i in range(1, len(images))]
                        selected_img_label = st.selectbox("📸 Select Image to Pick From:", img_options, key=f"img_sel_{selected_row['id']}")
                        selected_img_idx = img_options.index(selected_img_label)
                        selected_img_path = images[selected_img_idx]
                    
                    pil_img = get_pil_image(selected_img_path)
                    
                    if pil_img:
                        st.write("👆 *Click anywhere on the image below to extract that exact color!*")
                        pil_img.thumbnail((400, 800)) 
                        
                        click_coords = streamlit_image_coordinates(
                            pil_img, 
                            key=f"img_click_{selected_row['id']}_{selected_img_idx}"
                        )
                        
                        if click_coords and click_coords != st.session_state.get("last_click"):
                            st.session_state["last_click"] = click_coords
                            x, y = click_coords["x"], click_coords["y"]
                            
                            if x < pil_img.width and y < pil_img.height:
                                r, g, b = pil_img.getpixel((x, y))
                                picked_hex = f"#{r:02x}{g:02x}{b:02x}".upper()
                                
                                if eyedropper_target == "Primary Color":
                                    st.session_state.vault["color_1"] = picked_hex
                                    st.session_state[picker_key_1] = picked_hex 
                                else:
                                    st.session_state.vault["color_2"] = picked_hex
                                    st.session_state[picker_key_2] = picked_hex 
                                    st.session_state.vault["has_sec"] = True 
                                    st.session_state[has_sec_key] = True 
                                st.rerun() 
                    else:
                        st.info("Error loading image file.")
                else:
                    st.info("No images found for this polish.")

            with picker_col:
                st.subheader("🎨 Assign Verified Colors")
                
                color_1 = st.color_picker("Primary Color (Hex)", value=st.session_state.vault["color_1"], key=picker_key_1)
                st.session_state.vault["color_1"] = color_1
                
                has_sec = st.checkbox("Add Secondary Color (Shifts/Duochromes)", value=st.session_state.vault["has_sec"], key=has_sec_key)
                st.session_state.vault["has_sec"] = has_sec
                
                if has_sec:
                    color_2 = st.color_picker("Secondary Color (Hex)", value=st.session_state.vault["color_2"], key=picker_key_2)
                    st.session_state.vault["color_2"] = color_2
                else:
                    color_2 = "" 
                
                st.markdown("---")
                st.subheader("✨ Finish")
                selected_finishes = st.multiselect("Select Polish Finishes", FINISH_OPTIONS, default=st.session_state.vault["finishes"], key=finish_key)
                st.session_state.vault["finishes"] = selected_finishes
                
                st.write("") 
                
                if st.button("💾 Save Verified Swatch to Database", use_container_width=True, type="primary"):
                    with st.spinner("Writing clean hex to PostgreSQL..."):
                        fields_to_save = [
                            {
                                "id": selected_row["data_field_id"],
                                "label": "Colour (Hex)",
                                "value": color_1
                            },
                            {
                                "id": selected_row["data_field_id_2"],
                                "label": "Secondary Colour (Hex)",
                                "value": color_2 if has_sec else ""
                            },
                            {
                                "id": selected_row["finish_field_id"],
                                "label": "Finish (Colour Picker)",
                                "value": ", ".join(selected_finishes) 
                            }
                        ]
                        
                        success = save_polish_data_to_db(selected_row["id"], fields_to_save)
                        
                        if success:
                            st.success(f"Successfully verified and saved {selected_row['name']}!")
                            st.session_state.vault = {}
                            st.session_state["last_click"] = None
                            time.sleep(0.5)
                            st.rerun()
        else:
            st.success("🎉 **Queue Clean!** No polishes in this collection match this triage queue.")
    else:
        st.warning("No polishes found in this collection.")


# =============================================================================
# TAB 2: SEARCH BY COLOR RADIUS
# =============================================================================
with tab_search:
    st.header("Search by Color Radius")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        target_color = st.color_picker("Target Color", "#FF0000", key="search_picker")
    with col2:
        radius = st.slider("Search Radius (Tolerance)", min_value=0, max_value=300, value=205)
    with col3:
        filter_finishes = st.multiselect("Filter by Finish (Optional)", FINISH_OPTIONS)

    if not df.empty:
        tagged_df = df[df["color_status"] == "valid"].copy()

        if not tagged_df.empty:
            if filter_finishes:
                tagged_df["finish"] = tagged_df["finish"].fillna("")
                mask = tagged_df["finish"].apply(lambda x: any(f in x for f in filter_finishes))
                tagged_df = tagged_df[mask]

            tagged_df["Dist_1"] = tagged_df["color_hex"].apply(lambda x: color_distance(target_color, x))
            tagged_df["Dist_2"] = tagged_df["color_hex_2"].apply(lambda x: color_distance(target_color, x) if is_valid_hex(x) else float("inf"))
            tagged_df["Distance"] = tagged_df[["Dist_1", "Dist_2"]].min(axis=1)
            
            matches = tagged_df[tagged_df["Distance"] <= radius].sort_values("Distance")

            if not matches.empty:
                st.write(f"### Found {len(matches)} matches:")
                for _, row in matches.iterrows():
                    st.markdown(create_polish_card_html(row, distance_text=f"Color Match Distance: {row['Distance']:.1f}"), unsafe_allow_html=True)
            else:
                st.info("No polishes found within this radius. Try increasing the tolerance slider or changing your finish filter!")
        else:
            st.info("You haven't tagged any polishes with valid hex colors yet! Head over to the Tagging tab.")


# =============================================================================
# TAB 3: NAIL ART PAIRINGS
# =============================================================================
with tab_pairings:
    st.header("🎨 Nail Art Pairings")
    st.write("Select a base polish to see mathematically calculated color harmonies from your collection!")
    
    if not df.empty:
        tagged_df = df[df["color_status"] == "valid"].copy()
        
        if not tagged_df.empty:
            tagged_df["display_name"] = tagged_df.apply(
                lambda x: f"{x['brand']} - {x['name']}" if x["brand"] else x["name"], axis=1
            )
            
            selected_base = st.selectbox("Select Base Polish", tagged_df["display_name"].tolist(), key="base_polish_select")
            base_row = tagged_df[tagged_df["display_name"] == selected_base].iloc[0]
            
            st.markdown("### Base Polish")
            st.markdown(create_polish_card_html(base_row), unsafe_allow_html=True)
            
            harmonies = get_color_harmonies(base_row["color_hex"])
            
            st.markdown("---")
            st.markdown("### 🎯 Perfect Pairings")
            
            st.subheader("Complementary (High Contrast)")
            st.write("Colors opposite each other on the color wheel. Great for bold, high-energy nail art!")
            comp_hex = harmonies["Complementary"][0]
            comp_match = find_closest_polish(comp_hex, tagged_df, exclude_id=base_row["id"])
            if comp_match is not None:
                st.markdown(create_polish_card_html(comp_match, distance_text=f"Match Distance: {comp_match['Dist']:.1f}", math_color=comp_hex), unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
                
            st.subheader("Analogous (Harmonious & Blended)")
            st.write("Colors next to each other on the color wheel. Perfect for smooth gradients and ombre designs!")
            col1, col2 = st.columns(2)
            ana_hexes = harmonies["Analogous"]
            for i, a_hex in enumerate(ana_hexes):
                a_match = find_closest_polish(a_hex, tagged_df, exclude_id=base_row["id"])
                with [col1, col2][i]:
                    if a_match is not None:
                        st.markdown(create_polish_card_html(a_match, distance_text=f"Match Distance: {a_match['Dist']:.1f}", math_color=a_hex), unsafe_allow_html=True)
                        
            st.markdown("<br>", unsafe_allow_html=True)
                        
            st.subheader("Triadic (Vibrant & Balanced)")
            st.write("Three colors evenly spaced around the color wheel. Excellent for colorful, dynamic patterns!")
            col1, col2 = st.columns(2)
            tri_hexes = harmonies["Triadic"]
            for i, t_hex in enumerate(tri_hexes):
                t_match = find_closest_polish(t_hex, tagged_df, exclude_id=base_row["id"])
                with [col1, col2][i]:
                    if t_match is not None:
                        st.markdown(create_polish_card_html(t_match, distance_text=f"Match Distance: {t_match['Dist']:.1f}", math_color=t_hex), unsafe_allow_html=True)
        else:
            st.info("You need to tag some polishes with valid colors first! Go to the Tagging tab.")
    else:
        st.warning("No polishes found in this collection.")