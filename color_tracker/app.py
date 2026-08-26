import streamlit as st
import pandas as pd
import math
import os
import base64
import uuid
import datetime
import time
from sqlalchemy import text
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="Nail Polish Color Tracker", page_icon="💅", layout="wide")

# ==========================================
# ⚙️ DATABASE CONFIGURATION (POSTGRESQL)
# ==========================================
DB_URL = "postgresql://postgres:password@postgresql:5432/koillection"
KOILLECTION_WEB_URL = "http://10.0.0.207:8144" 
IMAGE_DIR = "/app/public/uploads"

FINISH_OPTIONS = [
    "Creme", "Holographic (Linear)", "Holographic (Scattered)", "Glitter", 
    "Magnetic", "Multichrome", "Duochrome", "Jelly", "Pearl", "Matte", 
    "Topper", "Flakie", "Shimmer", "Metallic", "Neon", "Thermal", "Solar"
]
# ==========================================

# --- COLOR MATH ---
def hex_to_rgb(hex_color):
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) != 6:
        return (0, 0, 0) 
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

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

# --- DIRECT DATABASE FUNCTIONS ---
@st.cache_data(ttl=0)
def fetch_collections():
    conn = st.connection("koillection_db", type="sql", url=DB_URL)
    query = "SELECT id::text AS id, title FROM koi_collection ORDER BY title ASC;"
    return conn.query(query, ttl=0)

@st.cache_data(ttl=0)
def fetch_polishes(collection_id):
    if not collection_id:
        return pd.DataFrame()
        
    conn = st.connection("koillection_db", type="sql", url=DB_URL)
    
    query = f"""
    SELECT 
        i.id::text AS id, 
        i.name, 
        i.image AS main_image, 
        STRING_AGG(DISTINCT CASE WHEN d.type = 'image' THEN d.value END, ',') AS gallery_images,
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
    conn = st.connection("koillection_db", type="sql", url=DB_URL)
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
                        text("UPDATE koi_datum SET value = :val, updated_at = :now WHERE id = :id::uuid"),
                        {"val": val, "now": now, "id": str(field_id)}
                    )
                elif val != "": 
                    new_id = str(uuid.uuid4())
                    session.execute(
                        text("""
                        INSERT INTO koi_datum (id, item_id, type, label, value, position, created_at, updated_at, visibility, final_visibility) 
                        VALUES (:id::uuid, :item_id::uuid, :type, :label, :val, 1, :now, :now, 'public', 'public')
                        """),
                        {"id": new_id, "item_id": str(item_id), "type": field_type, "label": label, "val": val, "now": now}
                    )
            
            session.execute(
                text("UPDATE koi_item SET updated_at = :now WHERE id = :item_id::uuid"),
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
        st.error(f"DEBUG: Missing file -> {full_path}")
        return None
    try:
        return Image.open(full_path).convert("RGB")
    except Exception as e:
        st.error(f"DEBUG: Corrupt file -> {e}")
        return None

# --- APP SETUP ---
st.title("💅 Nail Polish Color Tracker")

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
if "hide_color_instructions" not in st.session_state:
    st.session_state.hide_color_instructions = False

if not st.session_state.hide_color_instructions:
    with st.expander("ℹ️ How to use the Color Tracker", expanded=True):
        st.markdown("""
        **Welcome to the Color Tracker!**  
        This tool helps you assign exact colors to your nail polishes and search your collection for color matches.
        
        ### 📁 Getting Started
        * **Select a Collection:** Open the sidebar menu on the left and use the dropdown to choose which collection you want to work with. The app will instantly load all the polishes inside it!
        
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
        """)
        
        st.markdown("<br>", unsafe_allow_html=True)
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            if st.button("👍 Got it! Hide Instructions", use_container_width=True):
                st.session_state.hide_color_instructions = True
                st.rerun()
else:
    if st.button("ℹ️ Show Instructions"):
        st.session_state.hide_color_instructions = False
        st.rerun()

# --- COLLECTION SELECTOR SIDEBAR ---
try:
    collections_df = fetch_collections()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

if collections_df.empty:
    st.warning("No collections found in the database. Please create a collection in Koillection first.")
    st.stop()

collection_dict = dict(zip(collections_df['title'], collections_df['id']))

st.sidebar.header("📁 Select Collection")
selected_collection_title = st.sidebar.selectbox("Choose a collection to track:", list(collection_dict.keys()))
selected_collection_id = collection_dict[selected_collection_title]

try:
    df = fetch_polishes(selected_collection_id)
except Exception as e:
    st.error(f"Failed to fetch items: {e}")
    st.stop()

# --- UI TABS ---
tab1, tab2 = st.tabs(["🔍 Search Collection", "🏷️ Tag Existing Polish"])

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
                    
                    # Lightbox Image (Using main_image)
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

                    # Split Circle CSS Logic
                    c1 = row["color_hex"]
                    c2 = row["color_hex_2"] if pd.notna(row["color_hex_2"]) and row["color_hex_2"] != "" else c1
                    circle_css = f"background: linear-gradient(135deg, {c1} 50%, {c2} 50%);"

                    # Finish Badges HTML
                    badges_html = ""
                    if pd.notna(row['finish']) and row['finish'] != "":
                        finishes = [f.strip() for f in row['finish'].split(",")]
                        for f in finishes:
                            badges_html += f'<span class="finish-badge">{f}</span>'
                            
                    # Location HTML
                    location_html = ""
                    if pd.notna(row['location']) and str(row['location']).strip() != "":
                        location_html = f'<br><span style="color: #008080; font-size: 0.95em; font-weight: bold;">📍 Location: {row["location"]}</span>'

                    display_title = f"{row['brand']} - {row['name']}" if pd.notna(row['brand']) and row['brand'] else row['name']
                    item_url = f"{KOILLECTION_WEB_URL}/items/{row['id']}"

                    final_html = (
                        f'<div style="display: flex; align-items: center; margin-bottom: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 8px; color: #333;">'
                        f'{img_html}'
                        f'<div style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid #ddd; margin-right: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); {circle_css}"></div>'
                        f'<div>'
                        f'<a href="{item_url}" target="_blank" class="polish-link">'
                        f'<strong style="font-size: 1.2em;">{display_title}</strong>'
                        f'</a><br>'
                        f'<span style="color: #666; font-size: 0.9em;">Color Match Distance: {row["Distance"]:.1f}</span>'
                        f'{location_html}<br>'
                        f'{badges_html}'
                        f'</div>'
                        f'</div>'
                    )
                    
                    st.markdown(final_html, unsafe_allow_html=True)
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
        
        if search_name:
            filtered_df = filtered_df[filtered_df['name'].str.contains(search_name, case=False, na=False)]
        if search_brand:
            filtered_df['brand'] = filtered_df['brand'].fillna("")
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
            
            picker_key_1 = f"color_picker_1_{selected_row['id']}"
            picker_key_2 = f"color_picker_2_{selected_row['id']}"
            has_sec_key = f"has_sec_{selected_row['id']}"
            finish_key = f"finish_{selected_row['id']}"
            last_click_key = f"last_click_{selected_row['id']}"
            
            if picker_key_1 not in st.session_state:
                st.session_state[picker_key_1] = selected_row['color_hex'] if pd.notna(selected_row['color_hex']) else "#FF0000"
            
            if picker_key_2 not in st.session_state:
                st.session_state[picker_key_2] = selected_row['color_hex_2'] if pd.notna(selected_row['color_hex_2']) and selected_row['color_hex_2'] != "" else "#0000FF"
            
            if has_sec_key not in st.session_state:
                st.session_state[has_sec_key] = True if pd.notna(selected_row['color_hex_2']) and selected_row['color_hex_2'] != "" else False
                
            if finish_key not in st.session_state:
                current_finishes = []
                if pd.notna(selected_row['finish']) and selected_row['finish'] != "":
                    current_finishes = [f.strip() for f in selected_row['finish'].split(",")]
                st.session_state[finish_key] = current_finishes

            if last_click_key not in st.session_state:
                st.session_state[last_click_key] = None
            
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
                    for img in selected_row['gallery_images'].split(','):
                        if img and img not in images:
                            images.append(img)
                
                image_container = st.empty()
                radio_container = st.empty()
                
                if images:
                    selected_img_idx = 0
                    if len(images) > 1:
                        img_options = [f"Image {i+1}" for i in range(len(images))]
                        with radio_container:
                            selected_img_label = st.radio("📸 Switch Image:", img_options, horizontal=True, key=f"img_radio_{selected_row['id']}")
                        selected_img_idx = img_options.index(selected_img_label)
                    
                    selected_img_path = images[selected_img_idx]
                    pil_img = get_pil_image(selected_img_path)
                    
                    with image_container:
                        if pil_img:
                            st.write("👆 *Click the image to pick the color!*")
                            pil_img.thumbnail((350, 700)) 
                            
                            click_coords = streamlit_image_coordinates(pil_img, key=f"img_click_{selected_row['id']}_{selected_img_idx}")
                            
                            if click_coords and click_coords != st.session_state[last_click_key]:
                                st.session_state[last_click_key] = click_coords
                                x, y = click_coords["x"], click_coords["y"]
                                
                                if x < pil_img.width and y < pil_img.height:
                                    r, g, b = pil_img.getpixel((x, y))
                                    picked_hex = f"#{r:02x}{g:02x}{b:02x}"
                                    
                                    if eyedropper_target == "Primary Color":
                                        st.session_state[picker_key_1] = picked_hex
                                    else:
                                        st.session_state[picker_key_2] = picked_hex
                                        st.session_state[has_sec_key] = True 
                                    st.rerun() 
                        else:
                            st.info("Error loading image file.")
                else:
                    with image_container:
                        st.info("No images found for this polish.")

            with picker_col:
                st.subheader("🎨 Colors")
                color_1 = st.color_picker("Primary Color", key=picker_key_1)
                
                has_sec = st.checkbox("Add Secondary Color (Shifts/Duochromes)", key=has_sec_key)
                if has_sec:
                    color_2 = st.color_picker("Secondary Color", key=picker_key_2)
                else:
                    color_2 = "" 
                
                st.markdown("---")
                st.subheader("✨ Finish")
                selected_finishes = st.multiselect("Select Polish Finishes", FINISH_OPTIONS, key=finish_key)
                
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
                            for key in [picker_key_1, picker_key_2, has_sec_key, finish_key, last_click_key]:
                                if key in st.session_state:
                                    del st.session_state[key]
                            time.sleep(1)
                            st.rerun()
        else:
            if quick_setup and not (search_name or search_brand or is_date_filtered):
                st.success("🎉 **All caught up!** Every polish in your current filter has a color assigned.")
            else:
                st.warning("No polishes match your filter criteria.")
    else:
        st.warning("No polishes found in this collection.")