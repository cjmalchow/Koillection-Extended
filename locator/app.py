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
@st.cache_resource
def ensure_fonts():
    base_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/static/"
    fonts = {
        "Roboto-Regular.ttf": base_url + "Roboto-Regular.ttf",
        "Roboto-Bold.ttf": base_url + "Roboto-Bold.ttf",
        "Roboto-Italic.ttf": base_url + "Roboto-Italic.ttf",
        "Roboto-BoldItalic.ttf": base_url + "Roboto-BoldItalic.ttf"
    }
    errors = []
    for f_name, url in fonts.items():
        f_path = os.path.join("/app", f_name)
        if not os.path.exists(f_path) or os.path.getsize(f_path) < 10000:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response, open(f_path, 'wb') as out_file:
                    out_file.write(response.read())
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
    return {"title": "💅 Storage Grid Visualizer", "display_fields": ["Name"], "field_formats": {}}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

box_config = load_config()
app_settings = load_settings()
app_title = app_settings.get("title", "💅 Storage Grid Visualizer")
display_fields = app_settings.get("display_fields", ["Name"])
field_formats = app_settings.get("field_formats", {})

# --- TITLE EDIT POPUP (DIALOG) ---
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

# --- DATABASE CONNECTION & DATA PROCESSING ---
@st.cache_data(ttl=0)
def load_data():
    db_url = "postgresql://postgres:password@postgresql:5432/koillection"
    conn = st.connection("koillection_db", type="sql", url=db_url)
    
    # BULLETPROOF QUERY: Fetch everything!
    query = """
    SELECT i.id::text AS id, i.name, i.image, d.label, d.value
    FROM koi_item i
    LEFT JOIN koi_datum d ON i.id = d.item_id;
    """
    return conn.query(query, ttl=0)
df = load_data()

items_data = {}
all_custom_fields = set()

# Let Python do the filtering so we don't rely on strict SQL syntax
for _, row in df.iterrows():
    iid = str(row['id'])
    if iid not in items_data:
        items_data[iid] = {"name": str(row['name']), "image": row['image'], "location": "", "fields": {}}
    
    lbl = row['label']
    val = row['value']
    
    if pd.notna(lbl) and pd.notna(val):
        lbl_str = str(lbl).strip()
        val_str = str(val).strip()
        
        # Case-insensitive check for the word "location"
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

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("⚙️ Settings")

if font_errors:
    st.sidebar.error("⚠️ Font Download Failed:\n" + "\n".join(font_errors))

if st.sidebar.button("🔄 Refresh Database", help="Click this to instantly pull the newest items and fields from Koillection!"):
    st.cache_data.clear()
    st.rerun()

# 1. DISPLAY SETTINGS
with st.sidebar.expander("👁️ Customize Grid Text", expanded=False):
    st.markdown("<small>Select, reorder, and format the information displayed on the grid. <b>To reorder, clear the box and click them in the order you want!</b></small>", unsafe_allow_html=True)
    
    selected_fields = st.multiselect(
        "Fields to display:",
        options=available_fields,
        default=display_fields
    )
    
    st.markdown("---")
    st.markdown("**Text Formatting:**")
    new_formats = {}
    for f in selected_fields:
        st.markdown(f"<strong style='color: #26a69a;'>{f}</strong>", unsafe_allow_html=True)
        current_fmt = field_formats.get(f, {"bold": False, "italic": False, "underline": False, "align": "Center", "size": "Auto-Fit"})
        
        col1, col2, col3 = st.columns(3)
        with col1: b = st.checkbox("Bold", value=current_fmt.get("bold", False), key=f"b_{f}")
        with col2: i = st.checkbox("Italic", value=current_fmt.get("italic", False), key=f"i_{f}")
        with col3: u = st.checkbox("Underline", value=current_fmt.get("underline", False), key=f"u_{f}")
        
        col_a, col_s = st.columns(2)
        with col_a: align = st.selectbox("Alignment", ["Left", "Center", "Right"], index=["Left", "Center", "Right"].index(current_fmt.get("align", "Center")), key=f"a_{f}")
        with col_s: size = st.selectbox("Size", ["Auto-Fit", "Small", "Medium", "Large"], index=["Auto-Fit", "Small", "Medium", "Large"].index(current_fmt.get("size", "Auto-Fit")), key=f"s_{f}")
        
        new_formats[f] = {"bold": b, "italic": i, "underline": u, "align": align, "size": size}
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    
    if st.button("Save Display Settings"):
        with st.spinner("Saving display settings..."):
            app_settings["display_fields"] = selected_fields
            app_settings["field_formats"] = new_formats
            save_settings(app_settings)
            time.sleep(0.5)
        st.toast("Display settings saved!", icon="✅")
        time.sleep(1)
        st.rerun()

# 2. ADD A NEW BOX
with st.sidebar.expander("➕ Add a New Box", expanded=False):
    st.markdown("<small>Define the physical size of a new storage box.</small>", unsafe_allow_html=True)
    new_box = st.text_input("New Box Number/Name", help="E.g., type '1' if your location is '1-A1'.")
    new_cols = st.number_input("Columns (Letters)", min_value=1, max_value=26, value=8, help="How many items wide is the box?", key="new_cols")
    new_rows = st.number_input("Rows (Numbers)", min_value=1, max_value=50, value=5, help="How many items deep is the box?", key="new_rows")
    if st.button("Add Box"):
        if new_box:
            with st.spinner(f"Creating Box {new_box}..."):
                box_config[str(new_box)] = {"cols": new_cols, "rows": new_rows}
                save_config(box_config)
                time.sleep(0.5)
            st.toast(f"Added Box {new_box}!", icon="✅")
            time.sleep(1)
            st.rerun()

# 3. EDIT OR DELETE AN EXISTING BOX
if box_config:
    with st.sidebar.expander("✏️ Edit / Delete a Box", expanded=False):
        st.markdown("<small>Modify or remove an existing box.</small>", unsafe_allow_html=True)
        selected_box = st.selectbox("Select Box", options=sorted(list(box_config.keys())))
        if selected_box:
            current_cols = box_config[selected_box]["cols"]
            current_rows = box_config[selected_box]["rows"]
            edit_cols = st.number_input("Update Columns", min_value=1, max_value=26, value=current_cols, key="edit_cols")
            edit_rows = st.number_input("Update Rows", min_value=1, max_value=50, value=current_rows, key="edit_rows")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update"):
                    with st.spinner("Updating box..."):
                        box_config[selected_box] = {"cols": edit_cols, "rows": edit_rows}
                        save_config(box_config)
                        time.sleep(0.5)
                    st.toast(f"Updated Box {selected_box}!", icon="✅")
                    time.sleep(1)
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete"):
                    with st.spinner("Deleting box..."):
                        del box_config[selected_box]
                        save_config(box_config)
                        time.sleep(0.5)
                    st.toast(f"Deleted Box {selected_box}!", icon="🗑️")
                    time.sleep(1)
                    st.rerun()

st.sidebar.markdown("### 📦 Current Boxes")
if box_config:
    for b_name, b_dims in box_config.items():
        st.sidebar.markdown(f"**Box {b_name}**: {b_dims['cols']} Columns × {b_dims['rows']} Rows")
else:
    st.sidebar.info("No boxes configured yet.")

st.sidebar.markdown("---")
if st.sidebar.button("Clear All Box Configurations"):
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
        * **Customize Text:** Use the **👁️ Customize Grid Text** menu on the left to choose what information (Brand, Name, Color, etc.) is displayed on the grid and stickers. 
            * **Auto-Fit:** By default, the text size is set to "Auto-Fit". The app will automatically calculate the absolute largest font size possible to make your text fill the cell without overflowing!
            * **Format:** You can apply **Bold**, *Italic*, <u>Underline</u>, and change the **Alignment** (Left, Center, Right) for every single field!
        * **Visual Grid:** By default, you will see a visual representation of your boxes with item images. Use the tabs at the top to switch between different boxes.
        * **Printable Stickers:** Select **"Sticker Grid (Printable)"** at the top of the page. This strips away the dark background and images, giving you a clean, ink-friendly table.
        * **Download & Print:** While in the Sticker Grid view, click the **"📥 Download Box Sticker"** button to save a high-resolution PNG image of the grid, perfect for printing and attaching to the lid or inside of your physical box!
        * **Other Locations:** If you have items with locations that don't match your configured boxes (e.g., "In Transit" or "Display Shelf"), they will automatically be grouped into their own tabs at the top of the screen.
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

for b_name, b_dims in box_config.items():
    cols_str = "".join([chr(65 + i) for i in range(b_dims['cols'])])
    boxes[b_name] = {r: {c: None for c in cols_str} for r in range(1, b_dims['rows'] + 1)}

pattern = re.compile(r'^([a-zA-Z0-9]+)-([a-zA-Z])(\d+)$', re.IGNORECASE)

for item in items_data.values():
    raw_loc = item['location'].strip() if item['location'] else "Unassigned"
    locations = [l.strip() for l in raw_loc.split(',')]
    
    for loc in locations:
        if not loc: continue
        match = pattern.match(loc)
        
        if match:
            box_num = str(match.group(1))
            col = match.group(2).upper()
            row_num = int(match.group(3))
            
            if box_num in boxes and row_num in boxes[box_num] and col in boxes[box_num][row_num]:
                boxes[box_num][row_num][col] = item
            else:
                if loc not in other_containers: other_containers[loc] = []
                other_containers[loc].append(item)
        else:
            if loc not in other_containers: other_containers[loc] = []
            other_containers[loc].append(item)

# --- UI GENERATION ---
view_mode = st.radio("Select Grid View:", ["Visual Grid (Images)", "Sticker Grid (Printable)"], horizontal=True)

html_size_map = {"Small": "9px", "Medium": "11px", "Large": "14px", "Auto-Fit": "12px"}
print_size_map = {"Small": 20, "Medium": 28, "Large": 36}

def get_html_grid(box_num, box_data):
    dims = box_config[box_num]
    cols = "".join([chr(65 + i) for i in range(dims['cols'])])
    rows = dims['rows']
        
    html = "<table style='width: 100%; border-collapse: collapse; table-layout: fixed; color: white;'>"
    html += "<tr><th style='width: 40px;'></th>" + "".join([f"<th style='text-align: center; padding: 5px;'>{c}</th>" for c in cols]) + "</tr>"
    for r in range(1, rows + 1):
        html += f"<tr><th style='text-align: center; padding: 10px;'>{r}</th>"
        for c in cols:
            item = box_data[r][c]
            cell_style = "border: 1px solid #555; height: 140px; position: relative; padding: 0;"
            if item is None:
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
    col_width = f"{100 / (len(cols) + 1):.2f}%"
        
    teal = "#008080"
    html = f"<div style='width: 100%; max-width: 800px; background: white; padding: 20px; box-sizing: border-box;'>"
    html += f"<h2 style='text-align: center; color: black; margin-top: 0;'>Box {box_num}</h2>"
    html += "<table style='width: 100%; border-collapse: collapse; table-layout: fixed; color: black; font-family: Arial, sans-serif;'>"
    
    html += f"<tr><th style='width: {col_width}; border: 1px solid black; background: {teal}; color: white;'></th>"
    for c in cols:
        html += f"<th style='width: {col_width}; border: 1px solid black; background: {teal}; color: white; padding: 10px 2px;'>{c}</th>"
    html += "</tr>"
    
    for r in range(1, rows + 1):
        html += f"<tr><th style='border: 1px solid black; background: {teal}; color: white; padding: 10px 2px;'>{r}</th>"
        for c in cols:
            item = box_data[r][c]
            html += f"<td style='border: 1px solid black; height: 120px; vertical-align: top; padding: 5px; overflow: hidden;'>"
            html += f"<div style='font-weight: bold; font-size: 12px;'>{c}{r}</div>"
            
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
                        
                        html += f"<div style='font-size: {fz}; margin-top: 3px; word-wrap: break-word; font-weight:{fw}; font-style:{fs}; text-decoration:{td}; text-align:{ta};'>{val}</div>"
            
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
        if is_bold and is_italic:
            return ImageFont.truetype("/app/Roboto-BoldItalic.ttf", size)
        elif is_bold:
            return ImageFont.truetype("/app/Roboto-Bold.ttf", size)
        elif is_italic:
            return ImageFont.truetype("/app/Roboto-Italic.ttf", size)
        else:
            return ImageFont.truetype("/app/Roboto-Regular.ttf", size)
    except:
        return ImageFont.load_default()

def get_sticker_image_bytes(box_num, box_data):
    dims = box_config[box_num]
    cols = "".join([chr(65 + i) for i in range(dims['cols'])])
    rows = dims['rows']
    num_cols = len(cols)

    w, h = 1600, 1800 
    title_area = 150
    header_col_w = 120
    header_row_h = 120
    
    cell_w = (w - header_col_w) / num_cols
    cell_h = (h - title_area - header_row_h) / rows
    
    img = Image.new('RGB', (w, h), 'white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("/app/Roboto-Bold.ttf", 80)
        font_header = ImageFont.truetype("/app/Roboto-Bold.ttf", 60)
        font_cell_id = ImageFont.truetype("/app/Roboto-Bold.ttf", 40)
    except:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_cell_id = ImageFont.load_default()

    title_text = f"Box {box_num}"
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w - tw) / 2, (title_area - th) / 2), title_text, font=font_title, fill="black")

    teal = "#008080"
    draw.rectangle([0, title_area, w, title_area + header_row_h], fill=teal)
    draw.rectangle([0, title_area, header_col_w, h], fill=teal)
    
    for i in range(num_cols + 1):
        x = header_col_w + (i * cell_w)
        draw.line([(x, title_area), (x, h)], fill="black", width=4)
        if i < num_cols:
            txt = cols[i]
            bbox = draw.textbbox((0, 0), txt, font=font_header)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((x + (cell_w - tw)/2, title_area + (header_row_h - th)/2), txt, font=font_header, fill="white")
            
    for i in range(rows + 1):
        y = title_area + header_row_h + (i * cell_h)
        draw.line([(0, y), (w, y)], fill="black", width=4)
        if i < rows:
            txt = str(i + 1)
            bbox = draw.textbbox((0, 0), txt, font=font_header)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((header_col_w - tw)/2, y + (cell_h - th)/2), txt, font=font_header, fill="white")

    for r in range(1, rows + 1):
        for c_idx, c in enumerate(cols):
            item = box_data[r][c]
            x0 = header_col_w + (c_idx * cell_w)
            y0 = title_area + header_row_h + ((r - 1) * cell_h)
            
            draw.text((x0 + 10, y0 + 10), f"{c}{r}", font=font_cell_id, fill="black")
            
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
                            
                        draw.text((x_draw, y_text), line, font=font_text, fill="black")
                        
                        if is_underline:
                            draw.line([(x_draw, y_text + th + 2), (x_draw + tw, y_text + th + 2)], fill="black", width=2)
                        
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
                if view_mode == "Sticker Grid (Printable)":
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