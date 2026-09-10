import streamlit as st
import pandas as pd
import math
import os
import base64
import uuid
import datetime
import colorsys
import json
import time
from sqlalchemy import text
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="Smart Color Matcher", page_icon="💅", layout="wide")

# --- SESSION STATE INITIALIZATION (GOLDEN RULE) ---
if "current_polish_id" not in st.session_state:
    st.session_state.current_polish_id = None
if "last_click" not in st.session_state:
    st.session_state.last_click = None
# THE NEW SAFE STATE VAULT!
if "vault" not in st.session_state:
    st.session_state.vault = {}

# ==========================================
# ⚙️ CONFIGURATION & SETTINGS
# ==========================================
KOILLECTION_WEB_URL = "http://localhost:8081" 
IMAGE_DIR = "/app/public/uploads"
SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"show_instructions": True, "last_collection_id": None}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

app_settings = load_settings()

# --- DATABASE CONNECTION ---
def get_db_url():
    user = os.getenv("DB_USER", "koillection_user")
    password = os.getenv("DB_PASSWORD", "local_polish_vault_2026")
    host = os.getenv("DB_HOST", "db")
    port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "koillection")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

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
            return df['label'].tolist()
    except Exception as e:
        print(f"Database error fetching choice list: {e}")
        
    return [
        "Creme", "Holographic (Linear)", "Holographic (Scattered)", "Glitter", 
        "Magnetic", "Multichrome", "Duochrome", "Jelly", "Pearl", "Matte", 
        "Topper", "Flakie", "Shimmer", "Metallic", "Neon", "Thermal", "Solar"
    ]

FINISH_OPTIONS = fetch_finish_options()

# --- COLOR MATH ---
def hex_to_rgb(hex_color):
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) != 6:
        return (0, 0, 0) 
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(round(rgb[0])), int(round(rgb[1])), int(round(rgb[2])))

def color_distance(hex1, hex2):
    if not hex1 or not hex2 or pd.isna(hex1) or pd.isna(hex2) or hex1 == "" or hex2 == "":
        return float('inf')
        
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
        temp_df = temp_df[temp_df['id'] != exclude_id]
    if temp_df.empty: 
        return None
    
    temp_df["Dist"] = temp_df["color_hex"].apply(lambda x: color_distance(target_hex, x))
    best_match = temp_df.loc[temp_df["Dist"].idxmin()]
    return best_match

# --- DIRECT DATABASE FUNCTIONS ---
@st.cache_data(ttl=0)
def fetch_collections():
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    query = "SELECT id::text AS id, title FROM koi_collection ORDER BY title ASC;"
    return conn.query(query, ttl=0)

@st.cache_data(ttl=0)
def fetch_polishes(collection_id):
    if not collection_id:
        return pd.DataFrame()
        
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    
    cols_df = conn.query("SELECT column_name FROM information_schema.columns WHERE table_name = 'koi_datum'", ttl=0)
    datum_cols = cols_df['column_name'].tolist()
    
    gallery_cols = ["d.value"]
    if 'image' in datum_cols: gallery_cols.insert(0, "d.image")
    if 'file' in datum_cols: gallery_cols.insert(0, "d.file")
    
    gallery_sql = f"COALESCE({', '.join(gallery_cols)})"
    
    query = f"""
    SELECT 
        i.id::text AS id, 
        i.name, 
        i.image AS main_image, 
        STRING_AGG(DISTINCT CASE WHEN d.type = 'image' OR d.type = 'file' THEN {gallery_sql} END, ',') AS gallery_images,
        i.created_at,
        MAX(CASE WHEN d.label = 'Colour (Hex)' THEN d.value END) AS color_hex,
        MAX(CASE WHEN d.label = 'Colour (Hex)' THEN d.id::text END) AS data_field_id,
        MAX(CASE WHEN d.label = 'Secondary Colour (Hex)' THEN d.value END) AS color_hex_2,
        MAX(CASE WHEN d.label = 'Secondary Colour (Hex)' THEN d.id::text END) AS data_field_id_2,
        MAX(CASE WHEN d.label = 'Finish (Colour Picker)' THEN d.value END) AS finish,
        MAX(CASE WHEN d.label = 'Finish (Colour Picker)' THEN d.id::text END) AS finish_field_id,
        MAX(CASE WHEN d.label = 'Brand' THEN d.value END) AS brand,
        MAX(CASE WHEN d.label ILIKE 'Location' OR d.label ILIKE 'Other Location(s)' THEN d.value END) AS location
    FROM koi_item i
    LEFT JOIN koi_datum d ON i.id = d.item_id
    WHERE i.collection_id = '{collection_id}'
    GROUP BY i.id, i.name, i.image, i.created_at;
    """
    
    df = conn.query(query, ttl=0)
    
    if not df.empty and 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at']).dt.date
        
    return df

def save_polish_data_to_db(item_id, fields_to_save):
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    now = datetime.datetime.now(datetime.timezone.utc)
    
    try:
        with conn.session as session:
            for field in fields_to_save:
                field_id = field['id']
                label = field['label']
                val = field['value']
                
                field_type = 'color' if 'Hex' in label else 'text'
                
                if field_id and not pd.isna(field_id):
                    session.execute(
                        text("UPDATE koi_datum SET value = :val, updated_at = :now WHERE id = CAST(:id AS text)"),
                        {"val": val, "now": now, "id": str(field_id)}
                    )
                elif val != "": 
                    new_id = str(uuid.uuid4())
                    session.execute(
                        text("""
                        INSERT INTO koi_datum (id, item_id, type, label, value, position, created_at, updated_at, visibility, final_visibility) 
                        VALUES (CAST(:id AS text), CAST(:item_id AS text), :type, :label, :val, 1, :now, :now, 'public', 'public')
                        """),
                        {"id": new_id, "item_id": str(item_id), "type": field_type, "label": label, "val": val, "now": now}
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
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        return None

def get_pil_image(img_path):
    full_path = resolve_image_path(img_path)
    if not full_path or not os.path.exists(full_path): 
        return None
    try:
        return Image.open(full_path).convert("RGB")
    except Exception as e:
        return None

# --- HTML CARD GENERATOR ---
def create_polish_card_html(row, distance_text=None, math_color=None):
    img_html = ""
    img_b64 = get_image_base64(row['main_image'])
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

    c1 = row["color_hex"]
    c2 = row["color_hex_2"] if pd.notna(row["color_hex_2"]) and row["color_hex_2"] != "" else c1
    circle_css = f"background: linear-gradient(135deg, {c1} 50%, {c2} 50%);"

    badges_html = ""
    if pd.notna(row['finish']) and row['finish'] != "":
        finishes = [f.strip() for f in row['finish'].split(",")]
        for f in finishes:
            badges_html += f'<span class="finish-badge">{f}</span>'
            
    location_html = ""
    if pd.notna(row['location']) and str(row['location']).strip() != "":
        location_html = f'<br><span style="color: #008080; font-size: 0.95em; font-weight: bold;">📍 Location: {row["location"]}</span>'

    display_title = f"{row['brand']} - {row['name']}" if pd.notna(row['brand']) and row['brand'] else row['name']
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
st.title("💅 Smart Color Matcher")

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

# --- USER FRIENDLY INSTRUCTIONS ---
with st.expander("ℹ️ How to use the Color Tracker", expanded=False):
    st.markdown("""
    **Welcome to the Color Tracker!**  
    This tool helps you assign exact colors to your nail polishes and search your collection for color matches.
    
    ### 📋 Required Koillection Setup
    For this app to work its magic, make sure you have the following set up in your Koillection database:
    * **Lacquer Type (Choice List):** You must create a Choice List named exactly **`Lacquer Type`** in Koillection. Add all your finishes (Creme, Holographic, etc.) to this list. The app will automatically load them!
    * **Brand (Data Field):** Add a field named **`Brand`** to your items so the app can display the brand name next to the polish name.
    * **Auto-Generated Fields:** When you tag a polish, this app will *automatically* create the **`Colour (Hex)`**, **`Secondary Colour (Hex)`**, and **`Finish (Colour Picker)`** fields for you! No need to create them manually.
    
    ---
    
    ### 📁 Getting Started
    * **Select a Collection:** Use the dropdown menu right below these instructions to choose which collection you want to work with. The app will instantly load all the polishes inside it!
    
    ---
    
    ### 🏷️ Tagging Polishes
    1. Go to the **Tag Existing Polish** tab.
    2. **Quick Setup Mode:** By default, the `🚀 Quick Setup Mode` checkbox is checked. This automatically hides any polishes that already have a primary color assigned, allowing you to quickly power through your untagged collection without losing your place!
    3. Select a polish from the dropdown menu. *(Tip: Use the "Filter Options" to narrow down the list by name, brand, or date!)*
    4. **Pick a Color:** Click anywhere on the polish image to extract that exact color! You can pick a **Primary Color** and an optional **Secondary Color** (great for shifts or duochromes).
    5. **Select Finishes:** Choose one or more finishes from the dropdown.
    6. Click **Save to Database**. This will automatically update the item in Koillection and draw a color swatch next to it!
    
    ---
    
    ### 🔍 Searching by Color
    1. Go to the **Search Collection** tab.
    2. Use the color picker to choose a target color you want to find in your collection.
    3. Adjust the **Search Radius (Tolerance)** slider. A lower number finds exact matches, while a higher number finds similar shades.
    4. (Optional) Filter the results by specific finishes.
    
    ---
    
    ### 🎨 Nail Art Pairings
    1. Go to the **Nail Art Pairings** tab.
    2. Select a base polish you want to use.
    3. The app will use mathematical color theory (HSV conversion) to suggest the perfect Complementary, Analogous, and Triadic matches from your actual collection!
    """)

# --- COLLECTION SELECTOR (MOVED TO MAIN PAGE) ---
try:
    collections_df = fetch_collections()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

if collections_df.empty:
    st.warning("No collections found in the database. Please create a collection in Koillection first.")
    st.stop()

collection_dict = dict(zip(collections_df['title'], collections_df['id']))

st.markdown("### 📁 Select Collection")

# --- LOAD LAST COLLECTION FROM MEMORY ---
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

# --- SAVE COLLECTION TO MEMORY IF CHANGED ---
if selected_collection_id != last_col_id:
    app_settings["last_collection_id"] = selected_collection_id
    save_settings(app_settings)

try:
    df = fetch_polishes(selected_collection_id)
except Exception as e:
    st.error(f"Failed to fetch items: {e}")
    st.stop()

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs(["🔍 Search Collection", "🏷️ Tag Existing Polish", "🎨 Nail Art Pairings"])

# TAB 1: SEARCHING
with tab1:
    st.header("Search by Color Radius")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        target_color = st.color_picker("Target Color", "#FF0000", key="search_picker")
    with col2:
        radius = st.slider("Search Radius (Tolerance)", min_value=0, max_value=300, value=205)
    with col3:
        filter_finishes = st.multiselect("Filter by Finish (Optional)", FINISH_OPTIONS)

    if not df.empty:
        tagged_df = df.dropna(subset=['color_hex']).copy()

        if not tagged_df.empty:
            if filter_finishes:
                tagged_df['finish'] = tagged_df['finish'].fillna("")
                mask = tagged_df['finish'].apply(lambda x: any(f in x for f in filter_finishes))
                tagged_df = tagged_df[mask]

            tagged_df["Dist_1"] = tagged_df["color_hex"].apply(lambda x: color_distance(target_color, x))
            tagged_df["Dist_2"] = tagged_df["color_hex_2"].apply(lambda x: color_distance(target_color, x))
            tagged_df["Distance"] = tagged_df[["Dist_1", "Dist_2"]].min(axis=1)
            
            matches = tagged_df[tagged_df["Distance"] <= radius].sort_values("Distance")

            if not matches.empty:
                st.write(f"### Found {len(matches)} matches:")
                
                for _, row in matches.iterrows():
                    st.markdown(create_polish_card_html(row, distance_text=f"Color Match Distance: {row['Distance']:.1f}"), unsafe_allow_html=True)
            else:
                st.info("No polishes found within this radius. Try increasing the tolerance slider or changing your finish filter!")
        else:
            st.info("You haven't tagged any polishes with colors yet! Go to the Tagging tab.")

# TAB 2: TAGGING
with tab2:
    st.header("Tag a Polish")
    st.write("Filter and select a polish from your database to assign it a color.")
    
    if not df.empty:
        with st.expander("🔍 Filter Options", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                search_name = st.text_input("Search by Name", "")
            with col2:
                search_brand = st.text_input("Search by Brand", "")
                
            min_date = df['created_at'].min() if not pd.isna(df['created_at'].min()) else datetime.date(2000, 1, 1)
            max_date = df['created_at'].max() if not pd.isna(df['created_at'].max()) else datetime.date.today()
            
            if min_date == max_date:
                min_date = min_date - datetime.timedelta(days=1)
                
            date_range = st.date_input("Date Added Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        is_date_filtered = False
        if len(date_range) == 2:
            if date_range[0] > min_date or date_range[1] < max_date:
                is_date_filtered = True
        elif len(date_range) == 1:
            if date_range[0] > min_date:
                is_date_filtered = True

        filtered_df = df.copy()
        
        # --- CLEAN UP BRAND NAMES (Remove JSON brackets) ---
        filtered_df['brand'] = filtered_df['brand'].apply(
            lambda x: str(x).replace('["', '').replace('"]', '').replace('"', '') if pd.notna(x) else ""
        )
        
        if search_name:
            filtered_df = filtered_df[filtered_df['name'].str.contains(search_name, case=False, na=False)]
        if search_brand:
            filtered_df = filtered_df[filtered_df['brand'].str.contains(search_brand, case=False, na=False)]
            
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[(filtered_df['created_at'] >= start_date) & (filtered_df['created_at'] <= end_date)]
        elif len(date_range) == 1:
            start_date = date_range[0]
            filtered_df = filtered_df[filtered_df['created_at'] >= start_date]

        st.markdown("---")
        quick_setup = st.checkbox("🚀 **Quick Setup Mode** (Hide polishes that already have a primary color)", value=True)
        
        if quick_setup:
            if search_name or search_brand or is_date_filtered:
                st.info("🔍 **Search Override:** Showing all matching polishes (tagged and untagged) because you are actively searching.")
            else:
                filtered_df = filtered_df[filtered_df['color_hex'].isna()]

        if not filtered_df.empty:
            filtered_df['display_name'] = filtered_df.apply(
                lambda x: f"{x['brand']} - {x['name']}" if x['brand'] else x['name'], axis=1
            )
            
            display_names = filtered_df['display_name'].tolist()
            
            if quick_setup and not (search_name or search_brand or is_date_filtered):
                st.caption(f"*{len(display_names)} polishes left to tag!*")
                
            selected_display = st.selectbox("Select Polish", display_names)
            
            selected_row = filtered_df[filtered_df['display_name'] == selected_display].iloc[0]
            
            # --- WIPE THE VAULT WHEN A NEW POLISH IS SELECTED ---
            if st.session_state.get("current_polish_id") != selected_row['id']:
                st.session_state["current_polish_id"] = selected_row['id']
                st.session_state.vault = {} 
                st.session_state["last_click"] = None
                st.rerun()
            
            # --- ROBUST DATA SANITIZER FOR THE VAULT ---
            def clean_hex(val, default):
                if pd.isna(val) or not str(val).strip(): return default
                val = str(val).strip()
                if not val.startswith('#'): val = '#' + val
                if len(val) != 7: return default
                return val

            if "color_1" not in st.session_state.vault:
                st.session_state.vault["color_1"] = clean_hex(selected_row['color_hex'], "#FF0000")
            
            if "color_2" not in st.session_state.vault:
                st.session_state.vault["color_2"] = clean_hex(selected_row['color_hex_2'], "#0000FF")
            
            if "has_sec" not in st.session_state.vault:
                st.session_state.vault["has_sec"] = True if pd.notna(selected_row['color_hex_2']) and str(selected_row['color_hex_2']).strip() != "" else False
                
            if "finishes" not in st.session_state.vault:
                current_finishes = []
                if pd.notna(selected_row['finish']) and str(selected_row['finish']).strip() != "":
                    raw_finishes = [f.strip() for f in str(selected_row['finish']).split(",")]
                    # Ensure the finish actually exists in the dropdown options to prevent crashes
                    current_finishes = [f for f in raw_finishes if f in FINISH_OPTIONS]
                st.session_state.vault["finishes"] = current_finishes
            
            # --- DYNAMIC KEYS SO WIDGETS RESET PROPERLY ---
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
                if pd.notna(selected_row['main_image']) and selected_row['main_image']:
                    images.append(selected_row['main_image'])
                if pd.notna(selected_row['gallery_images']) and selected_row['gallery_images']:
                    for img in str(selected_row['gallery_images']).split(','):
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
                        st.write("👆 *Click the image to pick the color!*")
                        pil_img.thumbnail((400, 800)) 
                        
                        # The key dynamically changes when you swap images, forcing a clean, lag-free remount!
                        click_coords = streamlit_image_coordinates(
                            pil_img, 
                            key=f"img_click_{selected_row['id']}_{selected_img_idx}"
                        )
                        
                        if click_coords and click_coords != st.session_state.get("last_click"):
                            st.session_state["last_click"] = click_coords
                            x, y = click_coords["x"], click_coords["y"]
                            
                            if x < pil_img.width and y < pil_img.height:
                                r, g, b = pil_img.getpixel((x, y))
                                picked_hex = f"#{r:02x}{g:02x}{b:02x}"
                                
                                # --- THE FIX: UPDATE BOTH THE VAULT AND THE WIDGET STATE ---
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
                st.subheader("🎨 Colors")
                
                # WIDGETS READ FROM AND WRITE TO THE VAULT (WITH DYNAMIC KEYS!)
                color_1 = st.color_picker("Primary Color", value=st.session_state.vault["color_1"], key=picker_key_1)
                st.session_state.vault["color_1"] = color_1
                
                has_sec = st.checkbox("Add Secondary Color (Shifts/Duochromes)", value=st.session_state.vault["has_sec"], key=has_sec_key)
                st.session_state.vault["has_sec"] = has_sec
                
                if has_sec:
                    color_2 = st.color_picker("Secondary Color", value=st.session_state.vault["color_2"], key=picker_key_2)
                    st.session_state.vault["color_2"] = color_2
                else:
                    color_2 = "" 
                
                st.markdown("---")
                st.subheader("✨ Finish")
                selected_finishes = st.multiselect("Select Polish Finishes", FINISH_OPTIONS, default=st.session_state.vault["finishes"], key=finish_key)
                st.session_state.vault["finishes"] = selected_finishes
                
                st.write("") 
                
                if st.button("Save to Database", use_container_width=True, type="primary"):
                    with st.spinner("Saving to database..."):
                        
                        fields_to_save = [
                            {
                                "id": selected_row['data_field_id'],
                                "label": "Colour (Hex)",
                                "value": color_1
                            },
                            {
                                "id": selected_row['data_field_id_2'],
                                "label": "Secondary Colour (Hex)",
                                "value": color_2
                            },
                            {
                                "id": selected_row['finish_field_id'],
                                "label": "Finish (Colour Picker)",
                                "value": ", ".join(selected_finishes) 
                            }
                        ]
                        
                        success = save_polish_data_to_db(selected_row['id'], fields_to_save)
                        
                        if success:
                            st.success(f"Successfully updated {selected_display}!")
                            st.session_state.vault = {}
                            st.session_state["last_click"] = None
                            time.sleep(0.5)
                            st.rerun()
        else:
            if quick_setup and not (search_name or search_brand or is_date_filtered):
                st.success("🎉 **All caught up!** Every polish in your current filter has a color assigned.")
            else:
                st.warning("No polishes match your filter criteria.")
    else:
        st.warning("No polishes found in this collection.")

# TAB 3: NAIL ART PAIRINGS
with tab3:
    st.header("🎨 Nail Art Pairings")
    st.write("Select a base polish to see mathematically calculated color harmonies from your collection!")
    
    if not df.empty:
        tagged_df = df.dropna(subset=['color_hex']).copy()
        
        if not tagged_df.empty:
            # Clean up JSON array formatting in brands here too!
            tagged_df['brand'] = tagged_df['brand'].apply(
                lambda x: str(x).replace('["', '').replace('"]', '').replace('"', '') if pd.notna(x) else ""
            )
            tagged_df['display_name'] = tagged_df.apply(
                lambda x: f"{x['brand']} - {x['name']}" if x['brand'] else x['name'], axis=1
            )
            
            selected_base = st.selectbox("Select Base Polish", tagged_df['display_name'].tolist(), key="base_polish_select")
            base_row = tagged_df[tagged_df['display_name'] == selected_base].iloc[0]
            
            st.markdown("### Base Polish")
            st.markdown(create_polish_card_html(base_row), unsafe_allow_html=True)
            
            # Calculate the math!
            harmonies = get_color_harmonies(base_row['color_hex'])
            
            st.markdown("---")
            st.markdown("### 🎯 Perfect Pairings")
            
            # Complementary
            st.subheader("Complementary (High Contrast)")
            st.write("Colors opposite each other on the color wheel. Great for bold, high-energy nail art!")
            comp_hex = harmonies["Complementary"][0]
            comp_match = find_closest_polish(comp_hex, tagged_df, exclude_id=base_row['id'])
            if comp_match is not None:
                st.markdown(create_polish_card_html(comp_match, distance_text=f"Match Distance: {comp_match['Dist']:.1f}", math_color=comp_hex), unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
                
            # Analogous
            st.subheader("Analogous (Harmonious & Blended)")
            st.write("Colors next to each other on the color wheel. Perfect for smooth gradients and ombre designs!")
            col1, col2 = st.columns(2)
            ana_hexes = harmonies["Analogous"]
            for i, a_hex in enumerate(ana_hexes):
                a_match = find_closest_polish(a_hex, tagged_df, exclude_id=base_row['id'])
                with [col1, col2][i]:
                    if a_match is not None:
                        st.markdown(create_polish_card_html(a_match, distance_text=f"Match Distance: {a_match['Dist']:.1f}", math_color=a_hex), unsafe_allow_html=True)
                        
            st.markdown("<br>", unsafe_allow_html=True)
                        
            # Triadic
            st.subheader("Triadic (Vibrant & Balanced)")
            st.write("Three colors evenly spaced around the color wheel. Excellent for colorful, dynamic patterns!")
            col1, col2 = st.columns(2)
            tri_hexes = harmonies["Triadic"]
            for i, t_hex in enumerate(tri_hexes):
                t_match = find_closest_polish(t_hex, tagged_df, exclude_id=base_row['id'])
                with [col1, col2][i]:
                    if t_match is not None:
                        st.markdown(create_polish_card_html(t_match, distance_text=f"Match Distance: {t_match['Dist']:.1f}", math_color=t_hex), unsafe_allow_html=True)
        else:
            st.info("You need to tag some polishes with colors first! Go to the Tagging tab.")
    else:
        st.warning("No polishes found in this collection.")