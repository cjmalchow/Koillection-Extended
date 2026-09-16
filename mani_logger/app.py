import streamlit as st
import pandas as pd
import os
import uuid
import datetime
import json
import time
import urllib.request
from sqlalchemy import text
from PIL import Image, ImageDraw, ImageFont
import streamlit.components.v1 as components

st.set_page_config(page_title="Mani Logger", page_icon="💅", layout="wide")

# --- SESSION STATE INITIALIZATION (GOLDEN RULE) ---
if "hide_instructions" not in st.session_state:
    st.session_state.hide_instructions = False
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

# Initialize the 10 fingers in session state
FINGERS = ["L_Pinky", "L_Ring", "L_Middle", "L_Index", "L_Thumb", "R_Thumb", "R_Index", "R_Middle", "R_Ring", "R_Pinky"]
LAYERS = ["Base", "Color", "Topper", "Other", "Top"]

if "nail_map" not in st.session_state:
    st.session_state.nail_map = {f: {l: "None" for l in LAYERS} for f in FINGERS}

# --- ASSET DOWNLOADER (FONTS & EMOJI PNGS) ---
@st.cache_resource(show_spinner="📥 Downloading Assets for Nail Map...")
def ensure_assets():
    assets = {
        "Roboto-Bold.ttf": "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf",
        "Roboto-Regular.ttf": "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf",
        # FIX: Download actual PNG images of the emojis to bypass Pillow's font rendering bug!
        "emoji_palette.png": "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/1f3a8.png",
        "emoji_sparkles.png": "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/2728.png"
    }
    for f_name, url in assets.items():
        f_path = os.path.join("/app", f_name)
        if not os.path.exists(f_path) or os.path.getsize(f_path) < 100:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response, open(f_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception as e:
                print(f"Failed to download {f_name}: {e}")
ensure_assets()

# ==========================================
# ⚙️ CONFIGURATION & SETTINGS
# ==========================================
SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"diary_collection_id": None}

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

# --- DATABASE FETCHING ---
@st.cache_data(ttl=0)
def fetch_collections():
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    query = "SELECT id::text AS id, title FROM koi_collection ORDER BY title ASC;"
    return conn.query(query, ttl=0)

@st.cache_data(ttl=0)
def fetch_all_polishes():
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    query = """
    SELECT 
        i.id::text AS id, 
        i.name, 
        MAX(CASE WHEN d.label = 'Brand' THEN d.value END) AS brand,
        MAX(CASE WHEN d.label = 'Colour (Hex)' THEN d.value END) AS color_hex
    FROM koi_item i
    LEFT JOIN koi_datum d ON i.id = d.item_id
    GROUP BY i.id, i.name
    ORDER BY brand ASC, name ASC;
    """
    df = conn.query(query, ttl=0)
    df['brand'] = df['brand'].apply(lambda x: str(x).replace('["', '').replace('"]', '').replace('"', '') if pd.notna(x) else "")
    df['display_name'] = df.apply(lambda x: f"{x['brand']} - {x['name']}" if x['brand'] else x['name'], axis=1)
    return df

# --- IMAGE GENERATOR WITH LEGEND ---
def generate_nail_map_image(mani_name, nail_map, hex_dict, save_path):
    colors_used = set()
    toppers_used = set()
    for f in FINGERS:
        if nail_map[f]["Color"] != "None": colors_used.add(nail_map[f]["Color"])
        if nail_map[f]["Topper"] != "None": toppers_used.add(nail_map[f]["Topper"])
        
    legend_rows = max(len(colors_used), len(toppers_used))
    extra_height = 0
    if legend_rows > 0:
        extra_height = 100 + (legend_rows * 40) 
        
    # FIX: Increased canvas width to 1200px to prevent text overlapping!
    img_w = 1200
    img_h = 400 + extra_height
    img = Image.new('RGB', (img_w, img_h), color='#f9f9f9')
    draw = ImageDraw.Draw(img)
    
    try: font_title = ImageFont.truetype("/app/Roboto-Bold.ttf", 60)
    except: font_title = ImageFont.load_default()
        
    try: font_subtitle = ImageFont.truetype("/app/Roboto-Regular.ttf", 30)
    except: font_subtitle = ImageFont.load_default()
        
    try: font_legend_header = ImageFont.truetype("/app/Roboto-Bold.ttf", 28)
    except: font_legend_header = ImageFont.load_default()
        
    # FIX: Set label font to 22px so it's readable but fits perfectly under the nails
    try: font_label = ImageFont.truetype("/app/Roboto-Regular.ttf", 22)
    except: font_label = ImageFont.load_default()
        
    # Draw Title
    title_text = mani_name if mani_name else "Manicure Nail Map"
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) / 2, 40), title_text, font=font_title, fill="#31333F")
    
    # Draw Date Subtitle
    date_str = datetime.date.today().strftime("%B %d, %Y")
    bbox_sub = draw.textbbox((0, 0), date_str, font=font_subtitle)
    tw_sub = bbox_sub[2] - bbox_sub[0]
    draw.text(((img_w - tw_sub) / 2, 110), date_str, font=font_subtitle, fill="#666666")
    
    # FIX: Recalculated X-coordinates for 1200px width to give labels breathing room!
    specs = [
        ("L_Pinky", "L Pinky", 140, 45, 90),
        ("L_Ring", "L Ring", 230, 55, 110),
        ("L_Middle", "L Middle", 320, 60, 120),
        ("L_Index", "L Index", 410, 55, 110),
        ("L_Thumb", "L Thumb", 510, 65, 95),
        ("R_Thumb", "R Thumb", 690, 65, 95),
        ("R_Index", "R Index", 790, 55, 110),
        ("R_Middle", "R Middle", 880, 60, 120),
        ("R_Ring", "R Ring", 970, 55, 110),
        ("R_Pinky", "R Pinky", 1060, 45, 90),
    ]
    
    base_y = 320 
    
    for key, label, cx, w, h in specs:
        polish_name = nail_map[key]["Color"]
        hex_color = hex_dict.get(polish_name, "#e0e0e0") if polish_name != "None" else "#e0e0e0"
        
        x0, x1 = cx - w//2, cx + w//2
        y0, y1 = base_y - h, base_y
        
        draw.rounded_rectangle([x0, y0, x1, y1], radius=20, fill=hex_color, outline="#999999", width=3)
        draw.rectangle([x0+2, y1-20, x1-2, y1-2], fill=hex_color)
        draw.line([(x0, y1-20), (x0, y1)], fill="#999999", width=3)
        draw.line([(x1, y1-20), (x1, y1)], fill="#999999", width=3)
        draw.line([(x0-1, y1), (x1+1, y1)], fill="#999999", width=3)
        
        l_bbox = draw.textbbox((0, 0), label, font=font_label)
        lw = l_bbox[2] - l_bbox[0]
        draw.text((cx - lw//2, base_y + 20), label, font=font_label, fill="#666666")
        
    # Draw Legend
    if legend_rows > 0:
        draw.line([(100, 380), (1100, 380)], fill="#dddddd", width=2)
        
        if colors_used:
            # FIX: Paste the actual Emoji PNG instead of relying on Pillow fonts!
            try:
                pal_img = Image.open("/app/emoji_palette.png").convert("RGBA")
                pal_img = pal_img.resize((28, 28))
                img.paste(pal_img, (120, 410), pal_img) # The 3rd argument uses the image as its own alpha mask
                draw.text((156, 408), "Colors Used:", font=font_legend_header, fill="#31333F")
            except:
                draw.text((120, 408), "Colors Used:", font=font_legend_header, fill="#31333F")
            
            cy = 460
            for p in sorted(colors_used):
                hx = hex_dict.get(p, "#e0e0e0")
                draw.rectangle([120, cy, 150, cy+30], fill=hx, outline="#999999", width=2)
                draw.text((170, cy + 2), p, font=font_label, fill="#555555")
                cy += 40
                
        if toppers_used:
            # FIX: Paste the actual Emoji PNG!
            try:
                spark_img = Image.open("/app/emoji_sparkles.png").convert("RGBA")
                spark_img = spark_img.resize((28, 28))
                img.paste(spark_img, (650, 410), spark_img)
                draw.text((686, 408), "Toppers Used:", font=font_legend_header, fill="#31333F")
            except:
                draw.text((650, 408), "Toppers Used:", font=font_legend_header, fill="#31333F")
            
            ty = 460
            for p in sorted(toppers_used):
                hx = hex_dict.get(p, "#e0e0e0")
                draw.rectangle([650, ty, 680, ty+30], fill=hx, outline="#999999", width=2)
                draw.text((700, ty + 2), p, font=font_label, fill="#555555")
                ty += 40
                
    img.save(save_path, "JPEG", quality=90)

# --- SAVE MANICURE LOGIC ---
def save_manicure(name, date, rating, notes, cover_image, gallery_images, collection_id, nail_map, polish_dict, hex_dict):
    conn = st.connection("koillection_db", type="sql", url=get_db_url())
    now = datetime.datetime.now(datetime.timezone.utc)
    mani_id = str(uuid.uuid4())

    try:
        with conn.session as session:
            owner_query = text("SELECT owner_id FROM koi_collection WHERE id = CAST(:cid AS text)")
            owner_id = session.execute(owner_query, {"cid": collection_id}).scalar()
            owner_folder = str(owner_id) if owner_id else "mani_diary"
            upload_dir = f"/uploads/{owner_folder}"
            os.makedirs(upload_dir, exist_ok=True)
            try: os.chmod(upload_dir, 0o777)
            except: pass

            main_image_db = None
            if cover_image is not None:
                file_ext = os.path.splitext(cover_image.name)[1]
                image_filename = f"{mani_id}{file_ext}"
                full_path = os.path.join(upload_dir, image_filename)
                
                img = Image.open(cover_image)
                if img.mode != 'RGB': img = img.convert('RGB')
                img.thumbnail((1920, 1920)) 
                img.save(full_path, "JPEG", quality=85)
                try: os.chmod(full_path, 0o666)
                except: pass
                
                main_image_db = f"uploads/{owner_folder}/{image_filename}"

            gallery_db_paths = []
            if gallery_images:
                for g_img_file in gallery_images:
                    g_id = str(uuid.uuid4())
                    g_ext = os.path.splitext(g_img_file.name)[1]
                    g_filename = f"{g_id}{g_ext}"
                    g_full_path = os.path.join(upload_dir, g_filename)
                    
                    g_img = Image.open(g_img_file)
                    if g_img.mode != 'RGB': g_img = g_img.convert('RGB')
                    g_img.thumbnail((1920, 1920)) 
                    g_img.save(g_full_path, "JPEG", quality=85)
                    try: os.chmod(g_full_path, 0o666)
                    except: pass
                    
                    gallery_db_paths.append(f"uploads/{owner_folder}/{g_filename}")

            map_id = str(uuid.uuid4())
            map_filename = f"{map_id}_map.jpg"
            map_full_path = os.path.join(upload_dir, map_filename)
            generate_nail_map_image(name, nail_map, hex_dict, map_full_path)
            try: os.chmod(map_full_path, 0o666)
            except: pass
            gallery_db_paths.append(f"uploads/{owner_folder}/{map_filename}")

            session.execute(
                text("""
                INSERT INTO koi_item (id, collection_id, name, image, quantity, seen_counter, created_at, updated_at, visibility, final_visibility, owner_id) 
                VALUES (CAST(:id AS text), CAST(:cid AS text), :name, :img, 1, 0, :now, :now, 'public', 'public', CAST(:owner_id AS text))
                """),
                {"id": mani_id, "cid": collection_id, "name": name, "img": main_image_db, "now": now, "owner_id": owner_id}
            )
            
            fields = [
                {"label": "Date Created", "val": str(date), "type": "date"},
                {"label": "Rating", "val": str(rating * 2), "type": "rating"},
                {"label": "Notes", "val": notes, "type": "text"}
            ]
            
            for i, g_path in enumerate(gallery_db_paths):
                label_name = "Digital Nail Map" if i == len(gallery_db_paths) - 1 else f"Gallery Image {i+1}"
                fields.append({"label": label_name, "val": g_path, "type": "image"})
            
            for finger in FINGERS:
                layers_used = []
                for layer in LAYERS:
                    val = nail_map[finger][layer]
                    if val != "None":
                        layers_used.append(f"{layer}: {val}")
                
                if layers_used:
                    pretty_name = finger.replace("_", " ")
                    fields.append({"label": pretty_name, "val": " | ".join(layers_used), "type": "text"})
            
            for i, f in enumerate(fields):
                if f["val"]:
                    if f["type"] == "image":
                        sql = """
                        INSERT INTO koi_datum (id, item_id, type, label, image, position, created_at, updated_at, visibility, final_visibility, owner_id) 
                        VALUES (CAST(:id AS text), CAST(:item_id AS text), :type, :label, :val, :pos, :now, :now, 'public', 'public', CAST(:owner_id AS text))
                        """
                    else:
                        sql = """
                        INSERT INTO koi_datum (id, item_id, type, label, value, position, created_at, updated_at, visibility, final_visibility, owner_id) 
                        VALUES (CAST(:id AS text), CAST(:item_id AS text), :type, :label, :val, :pos, :now, :now, 'public', 'public', CAST(:owner_id AS text))
                        """
                    
                    session.execute(
                        text(sql),
                        {"id": str(uuid.uuid4()), "item_id": mani_id, "type": f["type"], "label": f["label"], "val": f["val"], "pos": i, "now": now, "owner_id": owner_id}
                    )
            
            unique_polishes_used = set()
            for finger in FINGERS:
                for layer in LAYERS:
                    p_name = nail_map[finger][layer]
                    if p_name != "None" and p_name in polish_dict:
                        unique_polishes_used.add(polish_dict[p_name])
                        
            for p_id in unique_polishes_used:
                session.execute(
                    text("""
                    INSERT INTO koi_item_related_item (item_id, related_item_id) 
                    VALUES (CAST(:item_id AS text), CAST(:related_id AS text))
                    """),
                    {"item_id": mani_id, "related_id": p_id}
                )
                
            cache_raw = session.execute(
                text("SELECT cached_values FROM koi_collection WHERE id = CAST(:cid AS text)"),
                {"cid": collection_id}
            ).scalar()
            
            if cache_raw and isinstance(cache_raw, str):
                cache_data = json.loads(cache_raw)
            elif cache_raw and isinstance(cache_raw, dict):
                cache_data = cache_raw
            else:
                cache_data = {}
                
            if "counters" not in cache_data:
                cache_data["counters"] = {}
            if "publicCounters" not in cache_data["counters"]:
                cache_data["counters"]["publicCounters"] = {"items": 0, "children": 0}
                
            actual_count = session.execute(
                text("SELECT COUNT(*) FROM koi_item WHERE collection_id = CAST(:cid AS text)"),
                {"cid": collection_id}
            ).scalar()
            
            cache_data["counters"]["publicCounters"]["items"] = actual_count
            
            session.execute(
                text("UPDATE koi_collection SET cached_values = :cache_json, updated_at = :now WHERE id = CAST(:cid AS text)"),
                {"cache_json": json.dumps(cache_data), "now": now, "cid": collection_id}
            )
            
            session.commit()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

# --- UI SETUP ---
st.title("💅 The Mani Logger")

with st.expander("ℹ️ How to use the Mani Logger", expanded=not st.session_state.hide_instructions):
    st.markdown("""
    **Welcome to the Mani Logger!**
    This app lets you record your manicures, save photos, and link the exact polishes you used.
    
    **First Time Setup:**
    1. Go to Koillection and create a new Collection called **"Manicure Diary"**.
    2. Select that collection in the sidebar of this app so it knows where to save your entries!
    
    **Features:**
    * **Custom Timers:** Add as many timers as you want! They run safely in the background and have custom chimes. Click the 🎵 icon on any timer to change its sound!
    * **Multiple Photos:** You can upload a main cover photo and as many gallery photos as you want!
    * **Detailed Nail Map:** Use the Global Settings to quickly apply a base/color/top to all nails, then click individual fingers to customize accent nails!
    """)
    if st.button("Got it! Hide Instructions"):
        st.session_state.hide_instructions = True
        st.rerun()

# --- SIDEBAR: COLLECTION SETUP ---
st.sidebar.header("⚙️ Setup")
collections_df = fetch_collections()
col_dict = dict(zip(collections_df['title'], collections_df['id']))

st.sidebar.markdown("<small>Select your 'Manicure Diary' collection:</small>", unsafe_allow_html=True)
default_idx = 0
if app_settings["diary_collection_id"] in col_dict.values():
    default_idx = list(col_dict.values()).index(app_settings["diary_collection_id"])

selected_col_title = st.sidebar.selectbox("Diary Collection", list(col_dict.keys()), index=default_idx)
selected_col_id = col_dict[selected_col_title]

if selected_col_id != app_settings["diary_collection_id"]:
    app_settings["diary_collection_id"] = selected_col_id
    save_settings(app_settings)

# --- TOP: ROBUST CUSTOM JS TIMERS WITH MODAL ---
st.markdown("### ⏱️ Salon Timers")
timer_html = """
<div style="font-family: sans-serif; background: #f9f9f9; padding: 15px; border-radius: 10px; border: 1px solid #ddd; position: relative;">
    
    <!-- THE CHIME SELECTION MODAL -->
    <div id="chimeModal" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center; border-radius: 10px;">
        <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; width: 300px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
            <h4 style="margin-top: 0;">Select New Chime</h4>
            <select id="modalChimeSelect" style="padding: 8px; width: 100%; margin-bottom: 15px; border-radius: 4px; border: 1px solid #ccc;">
                <option value="beep">Classic Beep</option>
                <option value="double_beep">Double Beep</option>
                <option value="chime">Spa Chime</option>
                <option value="gong">Zen Gong</option>
                <option value="alarm">Digital Alarm</option>
                <option value="arcade">Arcade Level Up</option>
                <option value="melody">Success Melody</option>
            </select>
            <div style="display: flex; gap: 10px; justify-content: center;">
                <button onclick="previewModalChime()" style="padding: 8px 15px; background: #03a9f4; color: white; border: none; border-radius: 4px; cursor: pointer;">🔊 Preview</button>
                <button onclick="saveModalChime()" style="padding: 8px 15px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">💾 Save</button>
                <button onclick="closeModal()" style="padding: 8px 15px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">Cancel</button>
            </div>
        </div>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 20px; align-items: center; flex-wrap: wrap;">
        <strong style="font-size: 16px; color: #333;">➕ Add Timer:</strong>
        
        <input type="text" id="newTName" placeholder="Timer Name" style="padding: 6px; border-radius: 4px; border: 1px solid #ccc; width: 130px;">
        
        <div style="display: flex; align-items: center; gap: 4px;">
            <input type="number" id="newTMins" value="5" min="0" style="padding: 6px; border-radius: 4px; border: 1px solid #ccc; width: 55px; text-align: center;">
            <span style="font-size: 14px; color: #555;">mins</span>
        </div>
        
        <div style="display: flex; align-items: center; gap: 4px;">
            <input type="number" id="newTSecs" value="0" min="0" max="59" style="padding: 6px; border-radius: 4px; border: 1px solid #ccc; width: 55px; text-align: center;">
            <span style="font-size: 14px; color: #555;">secs</span>
        </div>
        
        <select id="newTChime" style="padding: 6px; border-radius: 4px; border: 1px solid #ccc;">
            <option value="beep">Classic Beep</option>
            <option value="double_beep">Double Beep</option>
            <option value="chime">Spa Chime</option>
            <option value="gong">Zen Gong</option>
            <option value="alarm">Digital Alarm</option>
            <option value="arcade">Arcade Level Up</option>
            <option value="melody">Success Melody</option>
        </select>
        
        <div style="display: flex; align-items: center; gap: 4px;" title="Repeat chime every X seconds (0 to disable)">
            <span style="font-size: 14px; color: #555;">Repeat:</span>
            <input type="number" id="newTRepeat" value="5" min="0" style="padding: 6px; border-radius: 4px; border: 1px solid #ccc; width: 55px; text-align: center;">
            <span style="font-size: 14px; color: #555;">secs</span>
        </div>
        
        <button onclick="previewChime()" style="padding: 6px 12px; background: #03a9f4; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">🔊 Preview</button>
        <button onclick="addTimer()" style="padding: 6px 18px; background: #26a69a; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">Add</button>
    </div>
    <div id="timerContainer" style="display: flex; gap: 15px; flex-wrap: wrap;"></div>
</div>

<script>
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
let timerCount = 0;
const timers = {};
let activeModalTimerId = null;

// --- SYNTHESIZED CHIMES ---
function playTone(freq, type, duration, startTime, vol=1) {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, startTime);
    gain.gain.setValueAtTime(vol, startTime);
    gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start(startTime);
    osc.stop(startTime + duration);
}

function playChime(type) {
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    
    const now = audioCtx.currentTime;
    if (type === 'beep') {
        playTone(800, 'sine', 0.5, now);
        playTone(800, 'sine', 0.5, now + 0.6);
    } else if (type === 'double_beep') {
        playTone(900, 'square', 0.1, now, 0.2);
        playTone(900, 'square', 0.1, now + 0.2, 0.2);
        playTone(900, 'square', 0.1, now + 0.6, 0.2);
        playTone(900, 'square', 0.1, now + 0.8, 0.2);
    } else if (type === 'chime') {
        playTone(523.25, 'sine', 2, now, 0.5); // C5
        playTone(659.25, 'sine', 2, now + 0.2, 0.5); // E5
        playTone(783.99, 'sine', 3, now + 0.4, 0.5); // G5
    } else if (type === 'gong') {
        playTone(200, 'sine', 4, now, 0.8);
        playTone(203, 'sine', 4, now, 0.6); // slight dissonance for bell effect
    } else if (type === 'alarm') {
        for(let i=0; i<6; i++) {
            playTone(1000, 'square', 0.1, now + (i*0.2), 0.2);
        }
    } else if (type === 'arcade') {
        playTone(440, 'square', 0.1, now, 0.2);
        playTone(554.37, 'square', 0.1, now + 0.1, 0.2);
        playTone(659.25, 'square', 0.1, now + 0.2, 0.2);
        playTone(880, 'square', 0.4, now + 0.3, 0.2);
    } else if (type === 'melody') {
        playTone(523.25, 'triangle', 0.2, now); // C5
        playTone(659.25, 'triangle', 0.2, now + 0.2); // E5
        playTone(783.99, 'triangle', 0.2, now + 0.4); // G5
        playTone(1046.50, 'triangle', 0.6, now + 0.6); // C6
    }
}

function previewChime() {
    const type = document.getElementById('newTChime').value;
    playChime(type);
}

// --- MODAL LOGIC ---
function openModal(id) {
    activeModalTimerId = id;
    document.getElementById('modalChimeSelect').value = timers[id].chimeType;
    document.getElementById('chimeModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('chimeModal').style.display = 'none';
    activeModalTimerId = null;
}

function previewModalChime() {
    const type = document.getElementById('modalChimeSelect').value;
    playChime(type);
}

function saveModalChime() {
    if (activeModalTimerId) {
        timers[activeModalTimerId].chimeType = document.getElementById('modalChimeSelect').value;
    }
    closeModal();
}

function formatTime(totalSeconds) {
    const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const s = (totalSeconds % 60).toString().padStart(2, '0');
    return m + ":" + s;
}

function updateDisplay(id) {
    document.getElementById('display_' + id).innerText = formatTime(timers[id].timeLeft);
}

function toggleTimer(id) {
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    
    const t = timers[id];
    const btn = document.getElementById('btn_' + id);
    
    if (t.isAlarming) {
        if (t.alarmInterval) {
            clearInterval(t.alarmInterval);
            t.alarmInterval = null;
        }
        t.isAlarming = false;
        t.timeLeft = t.originalTime; 
        updateDisplay(id);
        btn.innerText = "Start";
        btn.style.background = "#4CAF50"; 
        return;
    }
    
    if (t.interval) {
        clearInterval(t.interval);
        t.interval = null;
        btn.innerText = "Start";
        btn.style.background = "#4CAF50"; 
    } else {
        if (t.timeLeft <= 0) t.timeLeft = t.originalTime; 
        
        t.endTime = Date.now() + (t.timeLeft * 1000);
        
        updateDisplay(id);
        btn.innerText = "Pause";
        btn.style.background = "#ff9800"; 
        
        t.interval = setInterval(() => {
            let now = Date.now();
            t.timeLeft = Math.ceil((t.endTime - now) / 1000);
            
            if (t.timeLeft <= 0) {
                t.timeLeft = 0;
                updateDisplay(id);
                clearInterval(t.interval);
                t.interval = null;
                t.isAlarming = true;
                
                btn.innerText = "🔕 Silence";
                btn.style.background = "#f44336"; 
                
                playChime(t.chimeType);
                
                if (t.repeatSecs > 0) {
                    t.alarmInterval = setInterval(() => {
                        playChime(t.chimeType);
                    }, t.repeatSecs * 1000);
                }
            } else {
                updateDisplay(id);
            }
        }, 250);
    }
}

function deleteTimer(id) {
    if (timers[id].interval) clearInterval(timers[id].interval);
    if (timers[id].alarmInterval) clearInterval(timers[id].alarmInterval);
    document.getElementById('card_' + id).remove();
    delete timers[id];
}

function addTimer(name="New Timer", mins=0, secs=0, chime="beep", repeat=5) {
    if(arguments.length === 0) {
        name = document.getElementById('newTName').value || "Timer";
        mins = parseInt(document.getElementById('newTMins').value) || 0;
        secs = parseInt(document.getElementById('newTSecs').value) || 0;
        chime = document.getElementById('newTChime').value;
        repeat = parseInt(document.getElementById('newTRepeat').value) || 0;
    }
    
    const totalSecs = (mins * 60) + secs;
    if (totalSecs <= 0) return;
    
    timerCount++;
    const id = timerCount;
    timers[id] = { 
        originalTime: totalSecs, 
        timeLeft: totalSecs, 
        interval: null, 
        chimeType: chime,
        repeatSecs: repeat,
        alarmInterval: null,
        isAlarming: false,
        endTime: 0
    };
    
    const card = document.createElement('div');
    card.id = 'card_' + id;
    card.style = "background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd; text-align: center; min-width: 140px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);";
    
    card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <strong style="color: #333; font-size: 14px;">${name}</strong>
            <div>
                <span onclick="openModal(${id})" style="cursor: pointer; color: #03a9f4; font-size: 14px; margin-right: 8px;" title="Change Chime">🎵</span>
                <span onclick="deleteTimer(${id})" style="cursor: pointer; color: #999; font-size: 12px;" title="Delete Timer">❌</span>
            </div>
        </div>
        <div id="display_${id}" style="font-size: 28px; font-weight: bold; color: #26a69a; margin-bottom: 15px;">${formatTime(totalSecs)}</div>
        <button id="btn_${id}" onclick="toggleTimer(${id})" style="padding: 6px 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">Start</button>
    `;
    
    document.getElementById('timerContainer').appendChild(card);
}

// Add Default Timers on load
addTimer("Prep", 10, 0, "chime", 10);
addTimer("Drying", 1, 30, "double_beep", 5);
addTimer("Mixing", 0, 30, "arcade", 5);
</script>
"""
components.html(timer_html, height=300)

st.markdown("---")

# --- MAIN LOGGING FORM ---
polishes_df = fetch_all_polishes()
polish_dict = dict(zip(polishes_df['display_name'], polishes_df['id']))
hex_dict = dict(zip(polishes_df['display_name'], polishes_df['color_hex']))
polish_options = ["None"] + list(polish_dict.keys())

fk = st.session_state.form_key

col_form, col_map = st.columns([1, 1.8])

with col_form:
    st.subheader("📝 Log Details")
    mani_name = st.text_input("Manicure Name", placeholder="e.g., Spooky Halloween Skittle", key=f"name_{fk}")
    mani_date = st.date_input("Date", datetime.date.today(), key=f"date_{fk}")
    mani_rating = st.slider("Rating (1-5)", 1, 5, 5, key=f"rating_{fk}")
    mani_notes = st.text_area("Notes / Techniques Used", placeholder="Used a sponge for the gradient...", key=f"notes_{fk}")
    
    st.markdown("### 📸 Photos")
    st.info("The first photo will be the cover image. The rest will be saved to the gallery!")
    mani_cover = st.file_uploader("Cover Photo (Required)", type=["jpg", "jpeg", "png"], key=f"cover_{fk}")
    mani_gallery = st.file_uploader("Additional Gallery Photos (Optional)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=f"gallery_{fk}")

with col_map:
    st.subheader("🖐️ Detailed Nail Map")
    
    st.markdown("### 🎨 Polishes Used")
    selected_polish_names = st.multiselect(
        "Select all polishes used in this manicure:", 
        list(polish_dict.keys()),
        key=f"polishes_{fk}"
    )
    
    if not selected_polish_names:
        st.info("👈 Select some polishes above to activate the nail map!")
    else:
        map_options = ["None"] + selected_polish_names
        
        # --- GLOBAL SETTINGS ---
        st.markdown("**1. Global Settings (Apply to all nails)**")
        g_col1, g_col2 = st.columns(2)
        with g_col1: 
            g_base = st.selectbox("Global Base", map_options, key=f"g_base_{fk}")
            g_color = st.selectbox("Global Color", map_options, key=f"g_color_{fk}")
        with g_col2: 
            g_top = st.selectbox("Global Top", map_options, key=f"g_top_{fk}")
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("⬇️ Apply Globals to All Fingers", use_container_width=True):
                for f in FINGERS:
                    st.session_state.nail_map[f]["Base"] = g_base
                    st.session_state.nail_map[f]["Color"] = g_color
                    st.session_state.nail_map[f]["Top"] = g_top
                st.rerun()
            
        st.markdown("<br>**2. Individual Finger Overrides**", unsafe_allow_html=True)
        st.caption("Click a finger to customize its specific layers (Accent nails, toppers, etc.)")
        
        # --- 10 FINGER POPOVERS ---
        st.markdown("**Left Hand**")
        lh_cols = st.columns(5)
        lh_fingers = ["L_Pinky", "L_Ring", "L_Middle", "L_Index", "L_Thumb"]
        lh_labels = ["Pinky", "Ring", "Middle", "Index", "Thumb"]
        
        for i, finger in enumerate(lh_fingers):
            with lh_cols[i]:
                with st.popover(f"💅 {lh_labels[i]}", use_container_width=True):
                    st.markdown(f"**Left {lh_labels[i]}**")
                    for layer in LAYERS:
                        current_val = st.session_state.nail_map[finger][layer]
                        idx = map_options.index(current_val) if current_val in map_options else 0
                        new_val = st.selectbox(layer, map_options, index=idx, key=f"sel_{finger}_{layer}_{fk}")
                        st.session_state.nail_map[finger][layer] = new_val

        st.markdown("**Right Hand**")
        rh_cols = st.columns(5)
        rh_fingers = ["R_Thumb", "R_Index", "R_Middle", "R_Ring", "R_Pinky"]
        rh_labels = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        
        for i, finger in enumerate(rh_fingers):
            with rh_cols[i]:
                with st.popover(f"💅 {rh_labels[i]}", use_container_width=True):
                    st.markdown(f"**Right {rh_labels[i]}**")
                    for layer in LAYERS:
                        current_val = st.session_state.nail_map[finger][layer]
                        idx = map_options.index(current_val) if current_val in map_options else 0
                        new_val = st.selectbox(layer, map_options, index=idx, key=f"sel_{finger}_{layer}_{fk}")
                        st.session_state.nail_map[finger][layer] = new_val

        # --- VISUAL HTML MAP ---
        def get_hex(polish_name):
            if polish_name == "None": return "#e0e0e0" 
            h = hex_dict.get(polish_name)
            return h if pd.notna(h) and h else "#ffffff"

        c_lp = get_hex(st.session_state.nail_map["L_Pinky"]["Color"])
        c_lr = get_hex(st.session_state.nail_map["L_Ring"]["Color"])
        c_lm = get_hex(st.session_state.nail_map["L_Middle"]["Color"])
        c_li = get_hex(st.session_state.nail_map["L_Index"]["Color"])
        c_lt = get_hex(st.session_state.nail_map["L_Thumb"]["Color"])
        
        c_rt = get_hex(st.session_state.nail_map["R_Thumb"]["Color"])
        c_ri = get_hex(st.session_state.nail_map["R_Index"]["Color"])
        c_rm = get_hex(st.session_state.nail_map["R_Middle"]["Color"])
        c_rr = get_hex(st.session_state.nail_map["R_Ring"]["Color"])
        c_rp = get_hex(st.session_state.nail_map["R_Pinky"]["Color"])

        nails_html = f"""
        <div style="display: flex; justify-content: space-between; align-items: flex-end; height: 150px; padding: 20px; background: #f9f9f9; border-radius: 10px; border: 1px solid #ddd; margin-top: 15px;">
            <!-- LEFT HAND -->
            <div style="display: flex; gap: 8px; align-items: flex-end;">
                <div style="width: 30px; height: 45px; background-color: {c_lp}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2);"></div>
                <div style="width: 35px; height: 60px; background-color: {c_lr}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); margin-bottom: 10px;"></div>
                <div style="width: 37px; height: 65px; background-color: {c_lm}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); margin-bottom: 20px;"></div>
                <div style="width: 35px; height: 60px; background-color: {c_li}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); margin-bottom: 10px;"></div>
                <div style="width: 40px; height: 50px; background-color: {c_lt}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); margin-left: 15px;"></div>
            </div>
            <!-- RIGHT HAND -->
            <div style="display: flex; gap: 8px; align-items: flex-end;">
                <div style="width: 40px; height: 50px; background-color: {c_rt}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); margin-right: 15px;"></div>
                <div style="width: 35px; height: 60px; background-color: {c_ri}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); margin-bottom: 10px;"></div>
                <div style="width: 37px; height: 65px; background-color: {c_rm}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); margin-bottom: 20px;"></div>
                <div style="width: 35px; height: 60px; background-color: {c_rr}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); margin-bottom: 10px;"></div>
                <div style="width: 30px; height: 45px; background-color: {c_rp}; border-radius: 40% 40% 10% 10%; border: 2px solid #999; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2);"></div>
            </div>
        </div>
        """
        st.markdown(nails_html, unsafe_allow_html=True)

st.markdown("---")

# --- SAVE BUTTON ---
if st.button("💾 Save Manicure to Koillection", type="primary", use_container_width=True):
    if not mani_name:
        st.error("Please give your manicure a name!")
    elif not mani_cover:
        st.error("Please upload a Cover Photo!")
    else:
        with st.spinner("Saving to database..."):
            polish_ids = [polish_dict[name] for name in selected_polish_names]
            
            success = save_manicure(
                name=mani_name,
                date=mani_date,
                rating=mani_rating,
                notes=mani_notes,
                cover_image=mani_cover,
                gallery_images=mani_gallery,
                collection_id=selected_col_id,
                nail_map=st.session_state.nail_map,
                polish_dict=polish_dict,
                hex_dict=hex_dict
            )
            if success:
                st.success("🎉 Manicure saved successfully! Check Koillection to see it.")
                st.session_state.form_key += 1
                st.session_state.nail_map = {f: {l: "None" for l in LAYERS} for f in FINGERS}
                time.sleep(2)
                st.rerun()