import streamlit as st
import pandas as pd
import re
import os
import base64
import mimetypes
import io
import textwrap
import json
import urllib.request
import time
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Nail Polish Locator", layout="wide")

# --- FONT DOWNLOADER ---
@st.cache_resource(show_spinner="📥 Downloading Google Fonts...")
def ensure_fonts():
    fonts_to_download = {
        "Roboto-Regular.ttf": ("Roboto", "400", False),
        "Roboto-Bold.ttf": ("Roboto", "700", False),
        "Roboto-Italic.ttf": ("Roboto", "400", True),
        "Roboto-BoldItalic.ttf": ("Roboto", "700", True),
        "Montserrat-Regular.ttf": ("Montserrat", "400", False),
        "Montserrat-Bold.ttf": ("Montserrat", "700", False),
        "Montserrat-Italic.ttf": ("Montserrat", "400", True),
        "Montserrat-BoldItalic.ttf": ("Montserrat", "700", True),
        "Oswald-Regular.ttf": ("Oswald", "400", False),
        "Oswald-Bold.ttf": ("Oswald", "700", False),
        "DancingScript-Regular.ttf": ("Dancing Script", "400", False),
        "DancingScript-Bold.ttf": ("Dancing Script", "700", False),
        "OpenSans-Regular.ttf": ("Open Sans", "400", False),
        "OpenSans-Bold.ttf": ("Open Sans", "700", False),
        "OpenSans-Italic.ttf": ("Open Sans", "400", True),
        "OpenSans-BoldItalic.ttf": ("Open Sans", "700", True),
        "Lato-Regular.ttf": ("Lato", "400", False),
        "Lato-Bold.ttf": ("Lato", "700", False),
        "Lato-Italic.ttf": ("Lato", "400", True),
        "Lato-BoldItalic.ttf": ("Lato", "700", True),
        "Merriweather-Regular.ttf": ("Merriweather", "400", False),
        "Merriweather-Bold.ttf": ("Merriweather", "700", False),
        "Merriweather-Italic.ttf": ("Merriweather", "400", True),
        "Merriweather-BoldItalic.ttf": ("Merriweather", "700", True),
        "PlayfairDisplay-Regular.ttf": ("Playfair Display", "400", False),
        "PlayfairDisplay-Bold.ttf": ("Playfair Display", "700", False),
        "PlayfairDisplay-Italic.ttf": ("Playfair Display", "400", True),
        "PlayfairDisplay-BoldItalic.ttf": ("Playfair Display", "700", True),
        "Pacifico-Regular.ttf": ("Pacifico", "400", False),
        "Lobster-Regular.ttf": ("Lobster", "400", False),
        "Caveat-Regular.ttf": ("Caveat", "400", False),
        "Caveat-Bold.ttf": ("Caveat", "700", False),
        "AmaticSC-Regular.ttf": ("Amatic SC", "400", False),
        "AmaticSC-Bold.ttf": ("Amatic SC", "700", False),
        "Cinzel-Regular.ttf": ("Cinzel", "400", False),
        "Cinzel-Bold.ttf": ("Cinzel", "700", False),
        "GreatVibes-Regular.ttf": ("Great Vibes", "400", False),
        "BebasNeue-Regular.ttf": ("Bebas Neue", "400", False),
    }
    
    errors = []
    ua = 'Mozilla/5.0 (Linux; U; Android 4.1.1; en-gb; Build/KLP) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Safari/534.30'
    
    for f_name, (family, weight, is_italic) in fonts_to_download.items():
        f_path = os.path.join("/app", f_name)
        if not os.path.exists(f_path) or os.path.getsize(f_path) < 10000:
            try:
                family_fmt = family.replace(" ", "+")
                ital_str = "1" if is_italic else "0"
                css_url = f"https://fonts.googleapis.com/css2?family={family_fmt}:ital,wght@{ital_str},{weight}"
                
                req_css = urllib.request.Request(css_url, headers={'User-Agent': ua})
                with urllib.request.urlopen(req_css, timeout=10) as response:
                    css = response.read().decode('utf-8')
                
                match = re.search(r'url\([\'"]?(https://[^\'")]+\.ttf)[\'"]?\)', css, re.IGNORECASE)
                
                if match:
                    ttf_url = match.group(1)
                    req_ttf = urllib.request.Request(ttf_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req_ttf, timeout=10) as response_ttf, open(f_path, 'wb') as out_file:
                        out_file.write(response_ttf.read())
                else:
                    errors.append(f"{f_name}: Could not find TTF URL in Google Fonts CSS.")
            except Exception as e:
                errors.append(f"{f_name}: {e}")
    return errors

font_errors = ensure_fonts()

# --- CONFIGURATION MANAGERS ---
CONFIG_FILE = "box_config.json"
SETTINGS_FILE = "settings.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {
        "title": "💅 Storage Grid Visualizer", 
        "display_fields": ["Name"], 
        "field_formats": {},
        "sticker_settings": {}
    }

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

box_config = load_config()
app_settings = load_settings()
app_title = app_settings.get("title", "💅 Storage Grid Visualizer")
display_fields = app_settings.get("display_fields", ["Name"])
field_formats = app_settings.get("field_formats", {})
sticker_settings = app_settings.get("sticker_settings", {})

# --- DATABASE CONNECTION & DATA PROCESSING ---
@st.cache_data(ttl=0, show_spinner="🔄 Fetching latest items from Koillection...")
def load_data():
    # This will use the Production URL if it exists, otherwise it defaults to the Sandbox URL!
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgresql:5432/koillection")
    conn = st.connection("koillection_db", type="sql", url=db_url)
    
    query = """
    SELECT i.id::text AS id, i.name, i.image, d.label, d.value
    FROM koi_item i
    LEFT JOIN koi_datum d ON i.id = d.item_id;
    """
    return conn.query(query, ttl=0)
df = load_data()

items_data = {}
all_custom_fields = set()

for _, row in df.iterrows():
    iid = str(row['id'])
    if iid not in items_data:
        items_data[iid] = {"name": str(row['name']), "image": row['image'], "location": "", "fields": {}}
    
    lbl = row['label']
    val = row['value']
    
    if pd.notna(lbl) and pd.notna(val):
        lbl_str = str(lbl).strip()
        val_str = str(val).strip()
        
        if 'location' in lbl_str.lower():
            if items_data[iid]["location"]:
                items_data[iid]["location"] += f", {val_str}"
            else:
                items_data[iid]["location"] = val_str
        else:
            items_data[iid]["fields"][lbl_str] = val_str
            all_custom_fields.add(lbl_str)

available_fields = ["Name"] + sorted(list(all_custom_fields))

display_fields = [f for f in display_fields if f in available_fields]
if not display_fields:
    display_fields = ["Name"]


# --- POP-UP DIALOGS (NEW!) ---

@st.dialog("Change App Title")
def edit_title_dialog(current_title):
    st.markdown("Enter a new title for your locator app:")
    new_title = st.text_input("Title", value=current_title, label_visibility="collapsed")
    if st.button("Save Title", type="primary"):
        with st.spinner("Saving new title..."):
            app_settings["title"] = new_title
            save_settings(app_settings)
            time.sleep(0.5)
        st.rerun()

@st.dialog("👁️ Customize Grid Text", width="large")
def grid_text_dialog():
    st.markdown("Select, reorder, and format the information displayed on the grid. **To reorder, clear the box and click them in the order you want!**")
    
    selected_fields = st.multiselect(
        "Fields to display:",
        options=available_fields,
        default=display_fields
    )
    
    st.markdown("---")
    st.markdown("### Text Formatting")
    new_formats = {}
    
    for f in selected_fields:
        st.markdown(f"<strong style='color: #26a69a; font-size: 1.1em;'>{f}</strong>", unsafe_allow_html=True)
        current_fmt = field_formats.get(f, {"bold": False, "italic": False, "underline": False, "align": "Center", "size": "Auto-Fit"})
        
        # Because we are in a wide dialog, we can put all 5 settings in one row!
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: b = st.checkbox("Bold", value=current_fmt.get("bold", False), key=f"b_{f}")
        with col2: i = st.checkbox("Italic", value=current_fmt.get("italic", False), key=f"i_{f}")
        with col3: u = st.checkbox("Underline", value=current_fmt.get("underline", False), key=f"u_{f}")
        with col4: align = st.selectbox("Alignment", ["Left", "Center", "Right"], index=["Left", "Center", "Right"].index(current_fmt.get("align", "Center")), key=f"a_{f}", label_visibility="collapsed")
        with col5: size = st.selectbox("Size", ["Auto-Fit", "Small", "Medium", "Large"], index=["Auto-Fit", "Small", "Medium", "Large"].index(current_fmt.get("size", "Auto-Fit")), key=f"s_{f}", label_visibility="collapsed")
        
        new_formats[f] = {"bold": b, "italic": i, "underline": u, "align": align, "size": size}
        st.markdown("<hr style='margin: 10px 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    if st.button("Save Display Settings", type="primary", use_container_width=True):
        with st.spinner("Saving display settings..."):
            app_settings["display_fields"] = selected_fields
            app_settings["field_formats"] = new_formats
            save_settings(app_settings)
            time.sleep(0.5)
        st.rerun()

@st.dialog("🎨 Sticker Customization", width="large")
def sticker_customization_dialog():
    st.markdown("Customize the look of your printable stickers.")
    
    new_h_template = st.text_input("Heading Text", value=sticker_settings.get("heading_template", "Box {box}"), help="Type {box} where you want the box name to appear.")
    
    font_options = [
        "Roboto", "Montserrat", "Oswald", "Dancing Script", "Open Sans", 
        "Lato", "Merriweather", "Playfair Display", "Pacifico",
        "Lobster", "Caveat", "Amatic SC", "Cinzel", "Great Vibes", "Bebas Neue"
    ]
    new_h_font = st.selectbox("Heading Font", font_options, index=font_options.index(sticker_settings.get("heading_font", "Roboto")))
    
    # --- LIVE FONT PREVIEW ---
    preview_font_url = new_h_font.replace(" ", "+")
    preview_text = new_h_template.replace("{box}", "1")
    if not preview_text.strip():
        preview_text = "Preview Text"
        
    st.markdown(f"<style>@import url('https://fonts.googleapis.com/css2?family={preview_font_url}&display=swap');</style>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style='
            font-family: "{new_h_font}", sans-serif; 
            font-size: 36px; 
            padding: 15px; 
            background: #f0f2f6; 
            color: #31333F;
            border-radius: 8px; 
            text-align: center; 
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
            word-wrap: break-word;
        '>
            {preview_text}
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.markdown("### Font Styles & Colors")
    col1, col2, col3 = st.columns(3)
    with col1: new_h_bold = st.checkbox("Bold Heading", value=sticker_settings.get("heading_bold", True), key="sh_bold")
    with col2: new_h_italic = st.checkbox("Italic Heading", value=sticker_settings.get("heading_italic", False), key="sh_italic")
    with col3: new_h_underline = st.checkbox("Underline Heading", value=sticker_settings.get("heading_underline", False), key="sh_underline")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
    with col_c1: new_h_color = st.color_picker("Heading Text", value=sticker_settings.get("heading_color", "#000000"))
    with col_c2: new_bg_color = st.color_picker("Background", value=sticker_settings.get("bg_color", "#FFFFFF"))
    with col_c3: new_grid_bg_color = st.color_picker("Grid Header", value=sticker_settings.get("grid_bg_color", "#008080"))
    with col_c4: new_grid_color = st.color_picker("Grid Lines", value=sticker_settings.get("grid_color", "#000000"))
    with col_c5: new_text_color = st.color_picker("Grid Text", value=sticker_settings.get("text_color", "#000000"))
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Save Sticker Settings", type="primary", use_container_width=True):
        with st.spinner("Saving sticker settings..."):
            app_settings["sticker_settings"] = {
                "heading_template": new_h_template,
                "heading_font": new_h_font,
                "heading_bold": new_h_bold,
                "heading_italic": new_h_italic,
                "heading_underline": new_h_underline,
                "heading_color": new_h_color,
                "bg_color": new_bg_color,
                "grid_bg_color": new_grid_bg_color,
                "grid_color": new_grid_color,
                "text_color": new_text_color
            }
            save_settings(app_settings)
            time.sleep(0.5)
        
        st.session_state.view_mode = "Sticker Grid (Printable)"
        st.rerun()


# --- SIDEBAR ---
st.sidebar.header("⚙️ Global Settings")

if font_errors:
    st.sidebar.error("⚠️ Font Download Failed:\n" + "\n".join(font_errors))

# Buttons to launch our new pop-up dialogs!
if st.sidebar.button("👁️ Customize Grid Text", use_container_width=True):
    grid_text_dialog()
    
if st.sidebar.button("🎨 Customize Sticker Design", use_container_width=True):
    sticker_customization_dialog()

st.sidebar.markdown("---")
st.sidebar.header("📦 Box Management")

# 1. ADD A NEW BOX
with st.sidebar.expander("➕ Add a New Box", expanded=False):
    st.markdown("<small>Define the physical size of a new storage box.</small>", unsafe_allow_html=True)
    new_box = st.text_input("New Box Number/Name", help="E.g., type '1' if your location is '1-A1'.")
    new_cols = st.number_input("Columns (Letters)", min_value=1, max_value=26, value=8, help="How many items wide is the box?", key="new_cols")
    new_rows = st.number_input("Rows (Numbers)", min_value=1, max_value=50, value=5, help="How many items deep is the box?", key="new_rows")
    if st.button("Add Box", use_container_width=True):
        if new_box:
            with st.spinner(f"Creating Box {new_box}..."):
                box_config[str(new_box)] = {"cols": new_cols, "rows": new_rows, "unusable": []}
                save_config(box_config)
                time.sleep(0.5)
            st.toast(f"Added Box {new_box}!", icon="✅")
            time.sleep(1)
            st.rerun()

# 2. EDIT OR DELETE AN EXISTING BOX
if box_config:
    with st.sidebar.expander("✏️ Edit / Delete a Box", expanded=False):
        st.markdown("<small>Modify or remove an existing box.</small>", unsafe_allow_html=True)
        selected_box = st.selectbox("Select Box", options=sorted(list(box_config.keys())))
        if selected_box:
            current_cols = box_config[selected_box]["cols"]
            current_rows = box_config[selected_box]["rows"]
            current_unusable = box_config[selected_box].get("unusable", [])
            
            edit_cols = st.number_input("Update Columns", min_value=1, max_value=26, value=current_cols, key="edit_cols")
            edit_rows = st.number_input("Update Rows", min_value=1, max_value=50, value=current_rows, key="edit_rows")
            
            all_possible_cells = [f"{chr(65+c)}{r}" for r in range(1, edit_rows + 1) for c in range(edit_cols)]
            valid_unusable = [cell for cell in current_unusable if cell in all_possible_cells]
            
            st.markdown("---")
            st.markdown("**🚫 Blackout Spaces**")
            st.markdown("<small>Select spaces that are physically unusable (e.g., broken slots, dividers). They will appear solid black on the grid.</small>", unsafe_allow_html=True)
            edit_unusable = st.multiselect("Unusable Spaces", options=all_possible_cells, default=valid_unusable)
            
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update Box", use_container_width=True):
                    with st.spinner("Updating box..."):
                        box_config[selected_box] = {
                            "cols": edit_cols, 
                            "rows": edit_rows,
                            "unusable": edit_unusable
                        }
                        save_config(box_config)
                        time.sleep(0.5)
                    st.toast(f"Updated Box {selected_box}!", icon="✅")
                    time.sleep(1)
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete Box", use_container_width=True):
                    with st.spinner("Deleting box..."):
                        del box_config[selected_box]
                        save_config(box_config)
                        time.sleep(0.5)
                    st.toast(f"Deleted Box {selected_box}!", icon="🗑️")
                    time.sleep(1)
                    st.rerun()

st.sidebar.markdown("### Current Boxes")
if box_config:
    for b_name, b_dims in box_config.items():
        st.sidebar.markdown(f"**Box {b_name}**: {b_dims['cols']} Columns × {b_dims['rows']} Rows")
else:
    st.sidebar.info("No boxes configured yet.")

st.sidebar.markdown("---")
if st.sidebar.button("Clear All Box Configurations", use_container_width=True):
    with st.spinner("Clearing all boxes..."):
        save_config({})
        time.sleep(0.5)
    st.toast("All boxes cleared!", icon="🧹")
    time.sleep(1)
    st.rerun()

# --- MAIN PAGE HEADER ---
st.markdown("<div style='color: #26a69a; font-weight: 600; margin-top: -40px; margin-bottom: 15px;'>↖️ Click the arrow icon above to open the sidebar and configure your boxes!</div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([8, 2, 2])
with col1:
    st.title(app_title)
with col2:
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Database", use_container_width=True):
        with st.spinner("Fetching latest data from Koillection..."):
            st.cache_data.clear()
            time.sleep(0.8)
        st.toast("Database refreshed successfully!", icon="✅")
        time.sleep(0.5)
        st.rerun()
with col3:
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    if st.button("✏️ Edit Title", use_container_width=True):
        edit_title_dialog(app_title)

# --- USER FRIENDLY INSTRUCTIONS ---
if "hide_instructions" not in st.session_state:
    st.session_state.hide_instructions = bool(box_config)

if not st.session_state.hide_instructions:
    with st.expander("ℹ️ How to use the Locator Guide", expanded=True):
        st.markdown("""
        **Welcome to the Locator Grid!**  
        This tool helps you visualize your physical storage boxes and print sticker labels for them.
        
        ### 🛠️ Setup Instructions
        **Step 1: Add Locations in Koillection**
        When editing an item in Koillection, add a Data field named exactly **`Location`** or **`Other Location(s)`**.
        
        **Step 2: Format your Locations**
        Type your locations using the format `Box-ColumnRow`. 
        * Example 1: `1-A1` (Box 1, Column A, Row 1)
        * Example 2: `Main-B4` (Box Main, Column B, Row 4)
        * Example 3: `Display Shelf` (Simple text locations will automatically get their own tab!)
        
        **Step 3: Configure your Boxes**
        Use the **⚙️ Box Configuration** menu on the left sidebar to tell this app how big your physical boxes are. Once configured, your items will automatically appear in the grid!
        
        ---
        
        ### 🚀 Using the Locator
        * **Customize Text:** Click **👁️ Customize Grid Text** in the sidebar to choose what information (Brand, Name, Color, etc.) is displayed on the grid and stickers. 
        * **Customize Stickers:** Click **🎨 Customize Sticker Design** in the sidebar to change fonts, colors, and heading text for your printable stickers!
        * **Blackout Spaces:** If your physical box has broken slots or dividers, use the **✏️ Edit Box** menu to mark those spaces as "Unusable". They will appear solid black on your grid!
        * **Visual Grid:** By default, you will see a visual representation of your boxes with item images. Use the tabs at the top to switch between different boxes.
        * **Printable Stickers:** Select **"Sticker Grid (Printable)"** at the top of the page. This strips away the dark background and images, giving you a clean, ink-friendly table.
        * **Download & Print:** While in the Sticker Grid view, click the **"📥 Download Box Sticker"** button to save a high-resolution PNG image of the grid, perfect for printing and attaching to the lid or inside of your physical box!
        """)
        
        st.markdown("<br>", unsafe_allow_html=True)
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            if st.button("👍 Got it! Hide Instructions", use_container_width=True):
                st.session_state.hide_instructions = True
                st.rerun()
else:
    if st.button("ℹ️ Show Instructions"):
        st.session_state.hide_instructions = False
        st.rerun()

# --- IMAGE LOADER ---
def get_image_base64(img_path):
    if not img_path or pd.isna(img_path):
        return None, None
    full_path = os.path.join("/uploads", str(img_path).replace("\\", "/"))
    if not os.path.exists(full_path):
        return None, None
    try:
        mime_type, _ = mimetypes.guess_type(full_path)
        with open(full_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8'), mime_type or "image/jpeg"
    except Exception:
        return None, None

# --- PROCESSING ---
boxes = {}
other_containers = {}

# Create a mapping for case-insensitive box name lookups
box_name_map = {}

for b_name, b_dims in box_config.items():
    cols_str = "".join([chr(65 + i) for i in range(b_dims['cols'])])
    boxes[b_name] = {r: {c: None for c in cols_str} for r in range(1, b_dims['rows'] + 1)}
    # Store a lowercase version of the box name so we can match it easily
    box_name_map[str(b_name).strip().lower()] = b_name

# NEW FORGIVING REGEX: Allows spaces around the hyphen and inside the box name!
pattern = re.compile(r'^\s*([a-zA-Z0-9\s]+?)\s*-\s*([a-zA-Z])\s*(\d+)\s*$', re.IGNORECASE)

for item in items_data.values():
    raw_loc = item['location'].strip() if item['location'] else "Unassigned"
    locations = [l.strip() for l in raw_loc.split(',')]
    
    for loc in locations:
        if not loc: continue
        match = pattern.match(loc)
        
        if match:
            # Clean up the extracted text
            parsed_box_name = str(match.group(1)).strip().lower()
            col = match.group(2).upper()
            row_num = int(match.group(3))
            
            # 1. Check if the box exists (case-insensitive)
            if parsed_box_name in box_name_map:
                actual_box_name = box_name_map[parsed_box_name]
                
                # 2. Check if the Row and Column actually exist inside this box's dimensions
                if row_num in boxes[actual_box_name] and col in boxes[actual_box_name][row_num]:
                    boxes[actual_box_name][row_num][col] = item
                else:
                    # The box exists, but the coordinates are out of bounds!
                    if loc not in other_containers: other_containers[loc] = []
                    other_containers[loc].append(item)
            else:
                # The box name doesn't match any configured boxes
                if loc not in other_containers: other_containers[loc] = []
                other_containers[loc].append(item)
        else:
            # The text didn't match the Box-A1 format at all
            if loc not in other_containers: other_containers[loc] = []
            other_containers[loc].append(item)
# --- UI GENERATION ---
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Visual Grid (Images)"

view_mode = st.radio("Select Grid View:", ["Visual Grid (Images)", "Sticker Grid (Printable)"], horizontal=True, key="view_mode")

html_size_map = {"Small": "9px", "Medium": "11px", "Large": "14px", "Auto-Fit": "12px"}
print_size_map = {"Small": 20, "Medium": 28, "Large": 36}

def get_html_grid(box_num, box_data):
    dims = box_config[box_num]
    cols = "".join([chr(65 + i) for i in range(dims['cols'])])
    rows = dims['rows']
    unusable_cells = dims.get("unusable", [])
        
    html = "<table style='width: 100%; border-collapse: collapse; table-layout: fixed; color: white;'>"
    html += "<tr><th style='width: 40px;'></th>" + "".join([f"<th style='text-align: center; padding: 5px;'>{c}</th>" for c in cols]) + "</tr>"
    for r in range(1, rows + 1):
        html += f"<tr><th style='text-align: center; padding: 10px;'>{r}</th>"
        for c in cols:
            item = box_data[r][c]
            cell_id = f"{c}{r}"
            cell_style = "border: 1px solid #555; height: 140px; position: relative; padding: 0;"
            
            if cell_id in unusable_cells:
                html += f"<td style='{cell_style} background: #000000;'></td>"
            elif item is None:
                html += f"<td style='{cell_style} background: #222;'></td>"
            else:
                img_b64, mime = get_image_base64(item["image"])
                img_tag = f"<img src='data:{mime};base64,{img_b64}' style='width: 100%; height: 100%; object-fit: cover; position: absolute; top: 0; left: 0;'>" if img_b64 else ""
                
                text_html = ""
                for f in display_fields:
                    val = item['name'] if f == "Name" else item['fields'].get(f, "")
                    if val:
                        fmt = field_formats.get(f, {})
                        fw = "bold" if fmt.get("bold") else "normal"
                        fs = "italic" if fmt.get("italic") else "normal"
                        td = "underline" if fmt.get("underline") else "none"
                        ta = fmt.get("align", "Center").lower()
                        fz = html_size_map.get(fmt.get("size", "Auto-Fit"))
                        
                        text_html += f"<div style='font-size: {fz}; font-weight:{fw}; font-style:{fs}; text-decoration:{td}; text-align:{ta}; color:white; text-shadow: 1px 1px 2px black; width: 100%;'>{val}</div>"
                
                html += f"<td style='{cell_style} background: #222;'>{img_tag}<div style='position: relative; z-index: 1; padding: 5px; display: flex; flex-direction: column; align-items: center;'><div style='background: rgba(0,0,0,0.7); display: inline-block; padding: 3px 6px; border-radius: 4px; width: 90%;'>{text_html}</div></div></td>"
        html += "</tr>"
    html += "</table>"
    return html

def get_sticker_html_grid(box_num, box_data):
    dims = box_config[box_num]
    cols = "".join([chr(65 + i) for i in range(dims['cols'])])
    rows = dims['rows']
    unusable_cells = dims.get("unusable", [])
    col_width = f"{100 / (len(cols) + 1):.2f}%"
    
    ss = app_settings.get("sticker_settings", {})
    h_temp = ss.get("heading_template", "Box {box}")
    h_font = ss.get("heading_font", "Roboto")
    h_bold = "bold" if ss.get("heading_bold", True) else "normal"
    h_italic = "italic" if ss.get("heading_italic", False) else "normal"
    h_underline = "underline" if ss.get("heading_underline", False) else "none"
    h_color = ss.get("heading_color", "#000000")
    bg_color = ss.get("bg_color", "#FFFFFF")
    grid_bg_color = ss.get("grid_bg_color", "#008080")
    grid_color = ss.get("grid_color", "#000000")
    text_color = ss.get("text_color", "#000000")
    
    heading_text = h_temp.replace("{box}", str(box_num))
    font_family_url = h_font.replace(" ", "+")
    
    html = f"<style>@import url('https://fonts.googleapis.com/css2?family={font_family_url}:ital,wght@0,400;0,700;1,400;1,700&display=swap');</style>"
    
    html += f"<div style='width: 100%; max-width: 800px; background: {bg_color}; padding: 20px; box-sizing: border-box;'>"
    html += f"<h2 style='text-align: center; font-size: 3em; color: {h_color}; font-family: \"{h_font}\", sans-serif; font-weight: {h_bold}; font-style: {h_italic}; text-decoration: {h_underline}; margin-top: 0; margin-bottom: 15px;'>{heading_text}</h2>"
    html += f"<table style='width: 100%; border-collapse: collapse; table-layout: fixed; color: {text_color}; font-family: Arial, sans-serif;'>"
    
    html += f"<tr><th style='width: {col_width}; border: 1px solid {grid_color}; background: {grid_bg_color}; color: white;'></th>"
    for c in cols:
        html += f"<th style='width: {col_width}; border: 1px solid {grid_color}; background: {grid_bg_color}; color: white; padding: 10px 2px;'>{c}</th>"
    html += "</tr>"
    
    for r in range(1, rows + 1):
        html += f"<tr><th style='border: 1px solid {grid_color}; background: {grid_bg_color}; color: white; padding: 10px 2px;'>{r}</th>"
        for c in cols:
            item = box_data[r][c]
            cell_id = f"{c}{r}"
            
            if cell_id in unusable_cells:
                html += f"<td style='border: 1px solid {grid_color}; height: 120px; background: #000000;'></td>"
            else:
                html += f"<td style='border: 1px solid {grid_color}; height: 120px; vertical-align: top; padding: 5px; overflow: hidden;'>"
                html += f"<div style='font-weight: bold; font-size: 12px; color: {text_color};'>{c}{r}</div>"
                
                if item:
                    for f in display_fields:
                        val = item['name'] if f == "Name" else item['fields'].get(f, "")
                        if val:
                            fmt = field_formats.get(f, {})
                            fw = "bold" if fmt.get("bold") else "normal"
                            fs = "italic" if fmt.get("italic") else "normal"
                            td = "underline" if fmt.get("underline") else "none"
                            ta = fmt.get("align", "Center").lower()
                            fz = html_size_map.get(fmt.get("size", "Auto-Fit"))
                            
                            html += f"<div style='font-size: {fz}; margin-top: 3px; word-wrap: break-word; font-weight:{fw}; font-style:{fs}; text-decoration:{td}; text-align:{ta}; color: {text_color};'>{val}</div>"
                
                html += "</td>"
        html += "</tr>"
    html += "</table></div>"
    return html

def wrap_text_pil(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line.strip())
            current_line = word + " "
    if current_line:
        lines.append(current_line.strip())
    return lines

def get_font(is_bold, is_italic, size):
    try:
        if is_bold and is_italic: return ImageFont.truetype("/app/Roboto-BoldItalic.ttf", size)
        elif is_bold: return ImageFont.truetype("/app/Roboto-Bold.ttf", size)
        elif is_italic: return ImageFont.truetype("/app/Roboto-Italic.ttf", size)
        else: return ImageFont.truetype("/app/Roboto-Regular.ttf", size)
    except:
        return ImageFont.load_default()

def get_heading_font(font_name, is_bold, is_italic, size):
    font_name_no_space = font_name.replace(" ", "")
    style = ""
    if is_bold and is_italic: style = "-BoldItalic"
    elif is_bold: style = "-Bold"
    elif is_italic: style = "-Italic"
    else: style = "-Regular"
    
    path = f"/app/{font_name_no_space}{style}.ttf"
    if not os.path.exists(path):
        path = f"/app/{font_name_no_space}-Regular.ttf"
        if not os.path.exists(path):
            path = f"/app/Roboto{style}.ttf"
            if not os.path.exists(path):
                path = "/app/Roboto-Regular.ttf"
                
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def get_sticker_image_bytes(box_num, box_data):
    dims = box_config[box_num]
    cols = "".join([chr(65 + i) for i in range(dims['cols'])])
    rows = dims['rows']
    unusable_cells = dims.get("unusable", [])
    num_cols = len(cols)

    ss = app_settings.get("sticker_settings", {})
    h_temp = ss.get("heading_template", "Box {box}")
    h_font = ss.get("heading_font", "Roboto")
    h_bold = ss.get("heading_bold", True)
    h_italic = ss.get("heading_italic", False)
    h_underline = ss.get("heading_underline", False)
    h_color = ss.get("heading_color", "#000000")
    bg_color = ss.get("bg_color", "#FFFFFF")
    grid_bg_color = ss.get("grid_bg_color", "#008080")
    grid_color = ss.get("grid_color", "#000000")
    text_color = ss.get("text_color", "#000000")

    w, h = 1600, 1800 
    title_area = 150
    header_col_w = 120
    header_row_h = 120
    
    cell_w = (w - header_col_w) / num_cols
    cell_h = (h - title_area - header_row_h) / rows
    
    img = Image.new('RGB', (w, h), bg_color)
    draw = ImageDraw.Draw(img)
    
    try:
        font_header = ImageFont.truetype("/app/Roboto-Bold.ttf", 60)
        font_cell_id = ImageFont.truetype("/app/Roboto-Bold.ttf", 40)
    except:
        font_header = ImageFont.load_default()
        font_cell_id = ImageFont.load_default()

    title_text = h_temp.replace("{box}", str(box_num))
    
    max_title_w = w - 80 
    max_title_h = title_area - 40 
    
    title_font_size = 160 
    
    while title_font_size > 20:
        try:
            font_title = get_heading_font(h_font, h_bold, h_italic, title_font_size)
        except:
            font_title = ImageFont.load_default()
            break 
            
        bbox = draw.textbbox((0, 0), title_text, font=font_title)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        if tw <= max_title_w and th <= max_title_h:
            break
            
        title_font_size -= 2

    title_x = (w - tw) / 2
    title_y = (title_area - th) / 2
    draw.text((title_x, title_y), title_text, font=font_title, fill=h_color)
    
    if h_underline:
        underline_thickness = max(4, int(title_font_size / 15))
        draw.line([(title_x, title_y + th + 10), (title_x + tw, title_y + th + 10)], fill=h_color, width=underline_thickness)

    draw.rectangle([0, title_area, w, title_area + header_row_h], fill=grid_bg_color)
    draw.rectangle([0, title_area, header_col_w, h], fill=grid_bg_color)
    
    for i in range(num_cols + 1):
        x = header_col_w + (i * cell_w)
        draw.line([(x, title_area), (x, h)], fill=grid_color, width=4)
        if i < num_cols:
            txt = cols[i]
            bbox = draw.textbbox((0, 0), txt, font=font_header)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((x + (cell_w - tw)/2, title_area + (header_row_h - th)/2), txt, font=font_header, fill="white")
            
    for i in range(rows + 1):
        y = title_area + header_row_h + (i * cell_h)
        draw.line([(0, y), (w, y)], fill=grid_color, width=4)
        if i < rows:
            txt = str(i + 1)
            bbox = draw.textbbox((0, 0), txt, font=font_header)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((header_col_w - tw)/2, y + (cell_h - th)/2), txt, font=font_header, fill="white")

    for r in range(1, rows + 1):
        for c_idx, c in enumerate(cols):
            item = box_data[r][c]
            cell_id = f"{c}{r}"
            
            x0 = header_col_w + (c_idx * cell_w)
            y0 = title_area + header_row_h + ((r - 1) * cell_h)
            
            if cell_id in unusable_cells:
                draw.rectangle([x0, y0, x0 + cell_w, y0 + cell_h], fill="#000000", outline=grid_color, width=4)
                continue 
            
            draw.text((x0 + 10, y0 + 10), cell_id, font=font_cell_id, fill=text_color)
            
            if item:
                max_w = cell_w - 20
                max_h = cell_h - 70 
                
                auto_size = 40
                while auto_size > 10:
                    total_h = 0
                    for f in display_fields:
                        val = item['name'] if f == "Name" else item['fields'].get(f, "")
                        if not val: continue
                        
                        fmt = field_formats.get(f, {})
                        test_size_str = fmt.get("size", "Auto-Fit")
                        test_size = auto_size if test_size_str == "Auto-Fit" else print_size_map.get(test_size_str, 28)
                        
                        font = get_font(fmt.get("bold", False), fmt.get("italic", False), test_size)
                        lines = wrap_text_pil(val, font, max_w, draw)
                        
                        for line in lines:
                            bbox = draw.textbbox((0, 0), line, font=font)
                            total_h += (bbox[3] - bbox[1]) + 4
                        total_h += 4 
                        
                    if total_h <= max_h:
                        break 
                    auto_size -= 2
                
                y_text = y0 + 60
                for f in display_fields:
                    val = item['name'] if f == "Name" else item['fields'].get(f, "")
                    if not val: continue
                    
                    fmt = field_formats.get(f, {})
                    is_bold = fmt.get("bold", False)
                    is_italic = fmt.get("italic", False)
                    is_underline = fmt.get("underline", False)
                    align = fmt.get("align", "Center")
                    size_str = fmt.get("size", "Auto-Fit")
                    
                    final_size = auto_size if size_str == "Auto-Fit" else print_size_map.get(size_str, 28)
                    font_text = get_font(is_bold, is_italic, final_size)
                    
                    lines = wrap_text_pil(val, font_text, max_w, draw)
                    
                    for line in lines:
                        bbox = draw.textbbox((0, 0), line, font=font_text)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        
                        if align == "Left":
                            x_draw = x0 + 10
                        elif align == "Right":
                            x_draw = x0 + cell_w - tw - 10
                        else: 
                            x_draw = x0 + (cell_w - tw) / 2
                            
                        draw.text((x_draw, y_text), line, font=font_text, fill=text_color)
                        
                        if is_underline:
                            draw.line([(x_draw, y_text + th + 2), (x_draw + tw, y_text + th + 2)], fill=text_color, width=2)
                        
                        y_text += th + 4
                    y_text += 4

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- TABS ---
if not box_config:
    st.info("👈 Please configure your box sizes in the sidebar to get started!")
elif df.empty:
    st.warning("⚠️ No items found in the database! Add some items in Koillection to get started.")
else:
    all_tabs = [f"Box {b}" for b in sorted(boxes.keys())] + sorted(list(other_containers.keys()))
    if all_tabs:
        tabs = st.tabs(all_tabs)
        box_keys = sorted(boxes.keys())

        for i, b in enumerate(box_keys):
            with tabs[i]:
                if st.session_state.view_mode == "Sticker Grid (Printable)":
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        png_bytes = get_sticker_image_bytes(b, boxes[b])
                        st.download_button(f"📥 Download Box {b} Sticker", png_bytes, f"box_{b}_sticker.png", "image/png")
                    st.html(get_sticker_html_grid(b, boxes[b]))
                else:
                    st.html(get_html_grid(b, boxes[b]))

        for i, c in enumerate(sorted(list(other_containers.keys()))):
            with tabs[i + len(box_keys)]:
                st.subheader(f"Location: {c}")
                st.table(pd.DataFrame({"Polish Name": [item['name'] for item in other_containers[c]]}))