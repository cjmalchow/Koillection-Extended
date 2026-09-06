import streamlit as st
import pandas as pd
import sqlalchemy
import random
import json
import math
import os
import signal
import copy

# --- CONFIGURATION ---
st.set_page_config(page_title="LabNotes Ranker", layout="centered")

# Golden Rule #2: Use os.getenv for seamless Sandbox -> Prod deployments!
# Updated to match the Color Matcher's internal Docker database credentials
DB_URL = os.getenv("DATABASE_URL", "postgresql://koillection_user:local_polish_vault_2026@db:5432/koillection")
engine = sqlalchemy.create_engine(DB_URL)

# Fallback is set to your Sandbox Koillection port (8081). 
# In Prod, you can pass IMAGE_BASE_URL="http://10.0.0.207:8144" in your docker-compose.yml
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "http://10.0.0.207:8081")

# --- CUSTOM SVGS ---
SVG_DOWN = '<svg width="16" height="11" viewBox="0 0 632 433"><polygon points="316 433 0 0 201 0 319 173 455 0 632 0 316 433"/><polygon fill="#d71920" points="316 361 549 42 476 42 317 244 179 42 84 42 316 361"/></svg>'
SVG_UP = '<svg width="16" height="11" viewBox="0 0 632 433"><polygon points="316 0 0 433 201 433 319 260 455 433 632 433 316 0"/><polygon fill="#54b948" points="316 72 549 391 476 391 317 189 179 391 84 391 316 72"/></svg>'

def get_movement_svg(movement):
    if movement > 0: return f"{SVG_UP} {movement}"
    if movement < 0: return f"{SVG_DOWN} {abs(movement)}"
    return "➖"

# --- HELPER FUNCTIONS ---
def get_image_url(image_name):
    if image_name is None or pd.isna(image_name): return ""
    image_name = str(image_name).lstrip('/\\')
    
    # Pass through external URLs immediately
    if image_name.startswith('http'): 
        return image_name
        
    # Prevent duplication by intelligently checking the string format from the database
    if image_name.startswith('uploads/'):
        return f"{IMAGE_BASE_URL}/{image_name}"
    elif "019e740a-ac68-72b3-91d9-c028ccde7943" in image_name:
        return f"{IMAGE_BASE_URL}/uploads/{image_name}"
    else:
        # Fallback for just the raw image filename
        return f"{IMAGE_BASE_URL}/uploads/019e740a-ac68-72b3-91d9-c028ccde7943/{image_name}"

def update_elo(winner, loser, k=32):
    e_w = 1 / (1 + 10 ** ((loser['elo'] - winner['elo']) / 400))
    e_l = 1 / (1 + 10 ** ((winner['elo'] - loser['elo']) / 400))
    winner['elo'] += k * (1 - e_w)
    loser['elo'] += k * (0 - e_l)
    return winner, loser

def save_session(session_name, data, lists):
    query = sqlalchemy.text("""
        INSERT INTO koi_ranking_history (session_name, data, lists, timestamp) 
        VALUES (:name, :data, :lists, NOW())
    """)
    with engine.connect() as conn:
        conn.execute(query, {"name": session_name, "data": json.dumps(data), "lists": ", ".join(lists)})
        conn.commit()

def safe_load(data):
    return json.loads(data) if isinstance(data, str) else data
# --- INITIALIZATION ---
# We initialize everything one-by-one at the very top so Streamlit never gets confused!
if 'my_polishes' not in st.session_state:
    st.session_state.my_polishes = None
    st.session_state.count = 0
    st.session_state.goal = 1
    st.session_state.selected_lists = []
    st.session_state.is_history = False
    st.session_state.undo_stack = []
    st.session_state.hide_ranker_instructions = False

st.title("💅 Ranker Dashboard")

# --- USER FRIENDLY INSTRUCTIONS ---
if not st.session_state.hide_ranker_instructions:
    with st.expander("ℹ️ How to use the Ranker", expanded=True):
        st.markdown("""
        **Welcome to the Ranker!**  
        This tool uses an Elo rating system (like in chess or competitive gaming) to help you definitively rank your nail polishes by pitting them against each other in 1-on-1 matchups.
        
        ### 📋 Getting Started
        1. **Create a Wishlist:** Before you can rank polishes, you need to group them together. Go to your Koillection **Wishlists** and add the polishes you want to rank into a specific wishlist (e.g., "Summer 2026 Favorites" or "Untried Indies").
        2. **Upload Pictures:** Make sure each polish in your wishlist has an image uploaded! The Ranker relies on these pictures to show you the matchups. *(Note: Polishes without images will be automatically skipped).*
        3. **Start a Session:** In the **🆕 Start New** tab below, select one or more of your wishlists from the dropdown and click "Start New Session".
        
        ### 🥊 The Ranking Process
        * You will be shown two polishes at a time. Simply click the button for the one you prefer!
        * **Made a mistake?** Use the ⏪ **Undo Last Match** button to go back.
        * A progress bar will track how many matchups are left until your ranking is statistically accurate.
        
        ### 💾 Saving & Merging
        * **Save:** Once the progress bar is full, you can name and save your session.
        * **Load:** Use the **📂 Load History** tab to view past rankings.
        * **Merge:** Use the **🔗 Merge Histories** tab to combine two different ranking sessions. The app will calculate how much each polish moved up or down in the ranks between the two sessions!
        """)
        
        st.markdown("<br>", unsafe_allow_html=True)
        _, center_col1, _ = st.columns([1, 2, 1])
        with center_col1:
            if st.button("👍 Got it! Hide Instructions", key="hide_btn_1", use_container_width=True):
                st.session_state.hide_ranker_instructions = True
                st.rerun()
                
        st.markdown("---")
        
        st.markdown("""
        ### 🤓 Nerd Corner: Exactly how does the math work?
        
        **The Point System (K-Factor = 32)**  
        Every polish starts with a baseline score of **1500**. The maximum amount of points a polish can win or lose in a single match is **32 points**.
        
        When two polishes face off, the system calculates the expected outcome based on their current scores:
        * **Even Match:** If two polishes are tied at 1500, the winner gets **+16 points** and the loser gets **-16 points**.
        * **Expected Win:** If a Heavyweight (1900) beats an Underdog (1100), the system expected that! The Heavyweight only gains a fraction of a point (e.g., **+0.3**), and the Underdog barely loses anything (**-0.3**).
        * **The Upset:** If an Underdog (1100) beats a Heavyweight (1900), it steals almost the entire 32 points! The Underdog gets **+31.7 points**, and the Heavyweight is punished with **-31.7 points**.
        
        **How many matchups do I have to do?**  
        To get a mathematically accurate ranking without making you vote on every single possible combination, the app uses a sorting formula: `(Number of Polishes) × Log2(Number of Polishes) × 2`.
        
        * If you rank **10 polishes**, you will do about **66 matchups**.
        * If you rank **20 polishes**, you will do about **172 matchups**.
        * If you rank **50 polishes**, you will do about **564 matchups**.
        
        This ensures every polish is tested enough times against different opponents to find its true, mathematically perfect place on your leaderboard!
        """)
        
        st.markdown("<br>", unsafe_allow_html=True)
        _, center_col2, _ = st.columns([1, 2, 1])
        with center_col2:
            if st.button("👍 Got it! Hide Instructions", key="hide_btn_2", use_container_width=True):
                st.session_state.hide_ranker_instructions = True
                st.rerun()
else:
    if st.button("ℹ️ Show Instructions"):
        st.session_state.hide_ranker_instructions = False
        st.rerun()

# --- DASHBOARD LOGIC ---
# --- DASHBOARD LOGIC ---
if st.session_state.my_polishes is None:
    history_df = pd.read_sql("SELECT session_name, data, lists FROM koi_ranking_history ORDER BY timestamp DESC;", engine)
    tab1, tab2, tab3 = st.tabs(["🆕 Start New", "📂 Load History", "🔗 Merge Histories"])
    
    with tab1:
        wishlists = pd.read_sql("SELECT id, name FROM koi_wishlist;", engine)
        selected_names = st.multiselect("Select Wishlists:", wishlists['name'].tolist())
        if st.button("Start New Session"):
            # Updated query to pull wishlist_name
            query = """
                SELECT w.name, w.image, wl.name AS wishlist_name 
                FROM koi_wish w 
                JOIN koi_wishlist wl ON w.wishlist_id = wl.id 
                WHERE wl.name IN %s AND w.image IS NOT NULL;
            """
            df = pd.read_sql(query, engine, params=(tuple(selected_names),))
            polishes = df.to_dict('records')
            for p in polishes: p['elo'] = 1500
            st.session_state.my_polishes, st.session_state.goal = polishes, int(len(df) * math.log2(len(df)) * 2) if len(df) > 1 else 10
            st.session_state.selected_lists = selected_names
            st.session_state.undo_stack = []
            st.rerun()

    with tab2:
        selected_session = st.selectbox("Load session:", history_df['session_name'].tolist(), key="load_sel")
        if st.button("Load Selected Session"):
            row = history_df[history_df['session_name'] == selected_session].iloc[0]
            data = safe_load(row['data'])
            for item in data: item.setdefault('image', None)
            st.session_state.my_polishes = data
            st.session_state.selected_lists = row['lists'].split(", ") if row['lists'] else []
            st.session_state.count, st.session_state.goal, st.session_state.is_history = 9999, 9999, True
            st.session_state.undo_stack = []
            st.rerun()

    with tab3:
        s1, s2 = st.selectbox("Session 1", history_df['session_name'].tolist(), key="m1"), st.selectbox("Session 2", history_df['session_name'].tolist(), key="m2")
        if st.button("Merge Histories", key="btn_merge"):
            d1 = safe_load(history_df[history_df['session_name']==s1].iloc[0]['data']) or []
            d2 = safe_load(history_df[history_df['session_name']==s2].iloc[0]['data']) or []
            combined = {p['name']: {'data': p, 'e1': p.get('elo', 1500), 'w1': len(d1), 'e2': 0, 'w2': 0} for p in d1}
            for p in d2:
                name = p.get('name')
                if not name: continue
                if name in combined: combined[name].update({'e2': p.get('elo', 1500), 'w2': len(d2)})
                else: combined[name] = {'data': p, 'e1': 0, 'w1': 0, 'e2': p.get('elo', 1500), 'w2': len(d2)}
            st.session_state.my_polishes = [ {**item['data'], 'elo': ((item['e1']*item['w1'])+(item['e2']*item['w2']))/(item['w1']+item['w2']), 'elo1': item['e1'], 'elo2': item['e2']} for item in combined.values() ]
            for item in st.session_state.my_polishes: item.setdefault('image', None)
            st.session_state.count, st.session_state.goal = 1, 1
            st.session_state.is_history = False
            st.session_state.undo_stack = []
            st.rerun()
    st.stop()

# --- RANKING ---
if not st.session_state.is_history and st.session_state.count < st.session_state.goal:
    if 'pair' not in st.session_state: st.session_state.pair = random.sample(st.session_state.my_polishes, 2)
    progress = st.session_state.count / st.session_state.goal
    st.progress(min(progress, 1.0))
    
    col_prog, col_undo = st.columns([3, 1])
    with col_prog:
        st.caption(f"Progress: {st.session_state.count} / {st.session_state.goal} pairs")
    
    with col_undo:
        # Undo logic implementation
        if len(st.session_state.undo_stack) > 0:
            if st.button("⏪ Undo Last Match", use_container_width=True):
                last_state = st.session_state.undo_stack.pop()
                st.session_state.my_polishes = last_state['polishes']
                st.session_state.count = last_state['count']
                st.session_state.pair = [p for p in st.session_state.my_polishes if p['name'] in last_state['pair_names']]
                st.rerun()
    
    pair_id = f"{st.session_state.pair[0]['name']}_{st.session_state.pair[1]['name']}"
    col1, col2 = st.columns(2)
    
    def render_button(item, col, p_id):
        url = get_image_url(item.get('image'))
        with col:
            st.markdown(f'<a href="{url}" target="_blank"><img src="{url}" style="width:100%; border-radius:15px; border:2px solid #ddd; margin-bottom: 10px;"></a>', unsafe_allow_html=True)
            return st.button(f"Choose {item['name']}", key=f"btn_{item['name']}_{p_id}", use_container_width=True)
            
    btn1, btn2 = render_button(st.session_state.pair[0], col1, pair_id), render_button(st.session_state.pair[1], col2, pair_id)
    
    if btn1 or btn2:
        # Save state before updating Elo
        st.session_state.undo_stack.append({
            'polishes': copy.deepcopy(st.session_state.my_polishes),
            'count': st.session_state.count,
            'pair_names': [st.session_state.pair[0]['name'], st.session_state.pair[1]['name']]
        })
        
        if btn1: update_elo(st.session_state.pair[0], st.session_state.pair[1])
        else: update_elo(st.session_state.pair[1], st.session_state.pair[0])
        st.session_state.count += 1
        del st.session_state.pair
        st.rerun()
        
elif not st.session_state.is_history and st.session_state.count >= st.session_state.goal:
    st.success("Ranking Complete!")
    session_name = st.text_input("Name your session:")
    if st.button("Save Session"):
        save_session(session_name, st.session_state.my_polishes, st.session_state.selected_lists)
        st.success("Session Saved!")

# --- RESULTS ---
df_data = pd.DataFrame(st.session_state.my_polishes)
if 'image' not in df_data.columns: df_data['image'] = None
ranked_df = df_data.sort_values(by='elo', ascending=False).reset_index(drop=True)
ranked_df['Rank_Current'] = ranked_df.index + 1
ranked_df['full_image_url'] = ranked_df['image'].apply(get_image_url)

is_merged = 'elo1' in ranked_df.columns

if is_merged:
    s1, s2 = ranked_df.sort_values(by='elo1', ascending=False).reset_index(drop=True), ranked_df.sort_values(by='elo2', ascending=False).reset_index(drop=True)
    ranked_df['Rank_Session_1'], ranked_df['Rank_Session_2'] = ranked_df['name'].map(dict(zip(s1['name'], s1.index + 1))), ranked_df['name'].map(dict(zip(s2['name'], s2.index + 1)))
    ranked_df['Movement'] = ranked_df['Rank_Session_1'] - ranked_df['Rank_Current']
else:
    ranked_df['Rank_Session_1'], ranked_df['Rank_Session_2'], ranked_df['Movement'] = "N/A", "N/A", 0

with st.expander("📊 Data Table", expanded=True):
    table_style = "<style>table{width:100%; border-collapse: collapse;} th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; } img.large-img { width: 150px; border-radius: 10px; } td { vertical-align: middle; }</style>"
    
    # Conditional HTML based on whether the session is a merge or a standard rank
    if is_merged:
        html_body = "<h1>💅 Rankings</h1><table><tr><th>Rank</th><th>S1</th><th>S2</th><th>Move</th><th>Wishlist</th><th>Image</th><th>Name</th><th>Elo</th></tr>"
    else:
        html_body = "<h1>💅 Rankings</h1><table><tr><th>Rank</th><th>Wishlist</th><th>Image</th><th>Name</th><th>Elo</th></tr>"
        
    for _, r in ranked_df.iterrows():
        # Fallback to 'Unknown' in case older JSON history doesn't have the new wishlist_name key
        w_name = r.get('wishlist_name', 'Unknown') 
        
        if is_merged:
            m_svg = get_movement_svg(r['Movement'])
            html_body += f"<tr><td>#{r['Rank_Current']}</td><td>{r['Rank_Session_1']}</td><td>{r['Rank_Session_2']}</td><td>{m_svg}</td><td>{w_name}</td><td><a href='{r['full_image_url']}' target='_blank'><img src='{r['full_image_url']}' class='large-img'></a></td><td>{r['name']}</td><td>{r['elo']:.0f}</td></tr>"
        else:
            html_body += f"<tr><td>#{r['Rank_Current']}</td><td>{w_name}</td><td><a href='{r['full_image_url']}' target='_blank'><img src='{r['full_image_url']}' class='large-img'></a></td><td>{r['name']}</td><td>{r['elo']:.0f}</td></tr>"
            
    st.markdown(table_style + "<body>" + html_body + "</table></body>", unsafe_allow_html=True)
    st.download_button("📥 Download HTML", data="<html>"+table_style+"<body>"+html_body+"</table></body></html>", file_name='lab_report.html', mime='text/html')

if st.sidebar.button("🛑 Shutdown"): os.kill(os.getpid(), signal.SIGTERM)