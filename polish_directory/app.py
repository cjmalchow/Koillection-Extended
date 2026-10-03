import base64
from datetime import datetime
import streamlit as st
import pandas as pd

from db import fetch_polish_inventory, get_unique_filter_values
from pdf_generator import build_tabular_directory_pdf, build_legend_pdf
import book_manager as bm

if "vault" not in st.session_state:
    st.session_state.vault = {}

if "pdf_bytes" not in st.session_state.vault:
    st.session_state.vault["pdf_bytes"] = None

if "legend_bytes" not in st.session_state.vault:
    st.session_state.vault["legend_bytes"] = None

if "pending_commit_ids" not in st.session_state.vault:
    st.session_state.vault["pending_commit_ids"] = []

st.set_page_config(
    page_title="Polish & Storage Directory",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def render_html5_download_button(pdf_bytes: bytes, filename: str, label: str = "⬇️ Download PDF"):
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    button_html = f"""
    <div style="margin: 12px 0;">
        <a href="data:application/pdf;base64,{b64}" download="{filename}" style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background-color: #ff4b4b;
            color: #ffffff !important;
            padding: 0.65rem 1.25rem;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 8px;
            text-decoration: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            transition: all 0.2s ease-in-out;
            border: none;
            width: 100%;
            text-align: center;
            cursor: pointer;
        " onmouseover="this.style.backgroundColor='#d32f2f'; this.style.transform='translateY(-1px)';"
           onmouseout="this.style.backgroundColor='#ff4b4b'; this.style.transform='translateY(0)';">
            {label}
        </a>
    </div>
    """
    st.markdown(button_html, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Data Loading
# -----------------------------------------------------------------------------
try:
    df_raw = fetch_polish_inventory()
except Exception as e:
    st.error(f"Failed to connect to Koillection database: {str(e)}")
    st.stop()

if df_raw.empty:
    st.warning("No polishes found in Koillection! Please add items to your collection first.")
    st.stop()

# -----------------------------------------------------------------------------
# Theme Presets
# -----------------------------------------------------------------------------
PALETTE_PRESETS = {
    "Navy Slate (Standard)": {"banner_bg": "#2C3E50", "banner_text": "#FFFFFF", "header_bg": "#ECEFF1", "header_text": "#111111", "zebra_bg": "#F8F9FA"},
    "Classic Monolith": {"banner_bg": "#1A1A1A", "banner_text": "#FFFFFF", "header_bg": "#E0E0E0", "header_text": "#000000", "zebra_bg": "#F4F4F4"},
    "Plum Velvet": {"banner_bg": "#581845", "banner_text": "#FFFFFF", "header_bg": "#F2E6EE", "header_text": "#330022", "zebra_bg": "#FAF5F8"},
    "Emerald Garden": {"banner_bg": "#1E4D2B", "banner_text": "#FFFFFF", "header_bg": "#E5EFE7", "header_text": "#0D2B16", "zebra_bg": "#F6FBF7"},
    "Rose Mauve": {"banner_bg": "#8E44AD", "banner_text": "#FFFFFF", "header_bg": "#EFE6F3", "header_text": "#3A104E", "zebra_bg": "#FAF7FB"},
    "Custom Colors...": None
}

# -----------------------------------------------------------------------------
# Sidebar: Controls & Customization
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("📖 Directory Studio")
    
    if st.button("🔄 Refresh Data from Koillection", use_container_width=True):
        st.cache_data.clear()
        st.session_state.vault["pdf_bytes"] = None
        st.rerun()

    st.markdown("---")
    st.subheader("📑 Quick Tools")
    if st.button("🖨️ Compile 1-Page Icon Legend", type="secondary", use_container_width=True):
        with st.spinner("Rendering icon key on single 8.5x11 sheet..."):
            legend_pdf = build_legend_pdf(font_family="Helvetica", banner_bg="#2C3E50", banner_text="#FFFFFF")
            st.session_state.vault["legend_bytes"] = legend_pdf
            st.success("Legend sheet compiled!")

    st.markdown("---")
    
    with st.expander("🎨 Document Styling & Columns", expanded=False):
        font_choice = st.selectbox("Typography Font", ["Helvetica", "Times-Roman", "Courier"], index=0)
        
        palette_choice = st.selectbox("Color Theme", list(PALETTE_PRESETS.keys()), index=0)
        if palette_choice == "Custom Colors...":
            c_banner_bg = st.color_picker("Section Banner Background", "#2C3E50")
            c_banner_txt = st.color_picker("Section Banner Text", "#FFFFFF")
            c_header_bg = st.color_picker("Table Header Background", "#ECEFF1")
            c_header_txt = st.color_picker("Table Header Text", "#111111")
            c_zebra_bg = st.color_picker("Zebra Row Background", "#F8F9FA")
        else:
            preset = PALETTE_PRESETS[palette_choice]
            c_banner_bg = preset["banner_bg"]
            c_banner_txt = preset["banner_text"]
            c_header_bg = preset["header_bg"]
            c_header_txt = preset["header_text"]
            c_zebra_bg = preset["zebra_bg"]

        compact_density = st.checkbox("Compact Row Density", value=True)
        
        finish_icon_only = st.checkbox(
            "Multi-Icon Finish Mode (Shows multiple finish icons side-by-side, no text)",
            value=True
        )

        default_coats = st.number_input(
            "Default # of Coats (when unlisted)",
            min_value=1,
            max_value=3,
            value=3,
            step=1,
            help="Fallback coat count for polishes that don't have a coat count specified in Koillection."
        )

        # DYNAMIC FIT OPTIMIZER SELECTOR
        density_mode = st.radio(
            "Page Density Strategy",
            options=["⚡ Automatic (Optimal Dynamic Fit)", "Manual Row Count"],
            index=0,
            help="Automatic uses our constraint algorithm to dynamically fill 100% of the page based on row wrapping and legend footprint."
        )

        if density_mode == "Manual Row Count":
            rows_per_page = st.number_input("Fixed Polishes per Page", min_value=20, max_value=36, value=30, step=1)
        else:
            rows_per_page = 0  # 0 signals the dynamic knapsack algorithm

        legend_choice = st.selectbox(
            "Directory Legend Mode",
            options=[
                "Contextual Per-Page Footer (Active icons only)",
                "None (Standalone Only)",
                "First Page Cover Sheet (Full master key)",
                "Last Page Appendix (Full master key)"
            ],
            index=0,
            help="Choose how visual decode keys are embedded into your printable directory."
        )

        legend_mode_map = {
            "Contextual Per-Page Footer (Active icons only)": "per_page",
            "None (Standalone Only)": "none",
            "First Page Cover Sheet (Full master key)": "first_page",
            "Last Page Appendix (Full master key)": "last_page"
        }
        selected_legend_mode = legend_mode_map[legend_choice]

        st.markdown("**Columns to Print:**")
        all_col_options = {
            "location": "Location ID",
            "color_swatch": "Color Swatch Pip",
            "nail_type": "Formulation Type (Icon)",
            "brand": "Brand",
            "shade_name": "Shade Name",
            "finish": "Finish (Icons)",
            "coats": "Coats (Opacity Pips)",
            "rating": "Star Rating",
            "size_acq": "Size & Acquisition Date",
            "item_id": "Koillection ID"
        }
        selected_columns = st.multiselect(
            "Select Columns",
            options=list(all_col_options.keys()),
            default=["location", "color_swatch", "nail_type", "brand", "shade_name", "finish", "coats", "rating", "size_acq"],
            format_func=lambda x: all_col_options[x]
        )

    st.markdown("---")
    st.subheader("📑 Organization & Sorting")

    grouping_choice = st.selectbox(
        "Primary Grouping (PDF Banners)",
        options=["color_family", "brand", "nail_type", "location", "finish", "rating_group", "acquisition_year", "none"],
        index=0,
        format_func=lambda x: {
            "color_family": "🌈 Color Spectrum (Reds, Blues, Purples)",
            "brand": "🏷️ Brand (OPI, Mooncat, ILNP)",
            "nail_type": "🧪 Formulation Type (Regular, Gel, Top Coat)",
            "location": "📦 Storage Location (Drawer / Box)",
            "finish": "✨ Finish / Effect (Holo, Creme, Flake)",
            "rating_group": "⭐ Star Rating Tiers",
            "acquisition_year": "📅 Acquisition Year",
            "none": "📄 Flat Directory (No Section Banners)"
        }[x]
    )

    sort_choice = st.selectbox(
        "Sort Order within Groups",
        options=["chromatic", "shade_name", "brand", "location", "rating_desc", "acq_desc"],
        index=0,
        format_func=lambda x: {
            "chromatic": "🌈 Chromatic (Rainbow Hue Spectrum)",
            "shade_name": "🔤 Shade Name (A-Z)",
            "brand": "🏷️ Brand (A-Z)",
            "location": "📍 Location ID (Ascending)",
            "rating_desc": "⭐ Rating (Highest to Lowest)",
            "acq_desc": "🕒 Purchase Date (Newest First)"
        }[x]
    )

    st.markdown("---")
    st.subheader("🔍 Filters (Inclusion)")

    search_query = st.text_input("Search Shade / Brand / Location", placeholder="e.g. OPI, 1-A1, Holo").strip().lower()

    all_locations, all_brands, all_finishes, all_color_families, all_types = get_unique_filter_values(df_raw)
    all_collections = sorted([c for c in df_raw["collection"].unique() if c], key=str.lower)

    sel_collections = st.multiselect("Collections", options=all_collections, default=[])
    sel_types = st.multiselect("Nail Polish Types", options=all_types, default=[])
    sel_color_families = st.multiselect("Color Families", options=all_color_families, default=[])
    sel_locations = st.multiselect("Storage Locations", options=all_locations, default=[])
    sel_brands = st.multiselect("Brands", options=all_brands, default=[])
    sel_finishes = st.multiselect("Finishes", options=all_finishes, default=[])

    # -------------------------------------------------------------
    # EXCLUSION FILTERS (FILTER OUT)
    # -------------------------------------------------------------
    st.markdown("---")
    with st.expander("🚫 Exclusion Filters (Filter OUT)", expanded=False):
        st.caption("Select attributes or keywords you want to **EXCLUDE / HIDE** from the printed directory:")
        
        ex_types = st.multiselect("Exclude Formulation Types", options=all_types, default=[])
        ex_brands = st.multiselect("Exclude Brands", options=all_brands, default=[])
        ex_locations = st.multiselect("Exclude Storage Locations", options=all_locations, default=[])
        ex_finishes = st.multiselect("Exclude Finishes", options=all_finishes, default=[])
        ex_collections = st.multiselect("Exclude Collections", options=all_collections, default=[])
        ex_search = st.text_input("Exclude Keyword / Search Word", placeholder="e.g. Destash, Sample, Topper").strip().lower()

        st.markdown("**Quick Toggles:**")
        ex_missing_color = st.checkbox("Hide Unswatched Polishes (Exclude missing color dots)", value=False)
        ex_unrated = st.checkbox("Hide Unrated Polishes (Exclude 0.0 star rating)", value=False)

    doc_title = st.text_input("Directory Title", value="Nail Polish & Storage Location Directory")

# -----------------------------------------------------------------------------
# Filter Application (Inclusion & Negative Exclusion)
# -----------------------------------------------------------------------------
df_filtered = df_raw.copy()

if search_query:
    mask = (
        df_filtered["shade_name"].str.lower().str.contains(search_query) |
        df_filtered["brand"].str.lower().str.contains(search_query) |
        df_filtered["location"].str.lower().str.contains(search_query) |
        df_filtered["nail_type"].str.lower().str.contains(search_query) |
        df_filtered["finish"].str.lower().str.contains(search_query)
    )
    df_filtered = df_filtered[mask]

if sel_collections:
    df_filtered = df_filtered[df_filtered["collection"].isin(sel_collections)]

if sel_types:
    df_filtered = df_filtered[df_filtered["nail_type"].isin(sel_types)]

if sel_color_families:
    df_filtered = df_filtered[df_filtered["color_family"].isin(sel_color_families)]

if sel_locations:
    df_filtered = df_filtered[df_filtered["location"].isin(sel_locations)]

if sel_brands:
    df_filtered = df_filtered[df_filtered["brand"].isin(sel_brands)]

if sel_finishes:
    pattern = "|".join(sel_finishes)
    df_filtered = df_filtered[df_filtered["finish"].str.contains(pattern, case=False, na=False)]

if ex_collections:
    df_filtered = df_filtered[~df_filtered["collection"].isin(ex_collections)]

if ex_types:
    df_filtered = df_filtered[~df_filtered["nail_type"].isin(ex_types)]

if ex_brands:
    df_filtered = df_filtered[~df_filtered["brand"].isin(ex_brands)]

if ex_locations:
    df_filtered = df_filtered[~df_filtered["location"].isin(ex_locations)]

if ex_finishes:
    ex_pattern = "|".join(ex_finishes)
    df_filtered = df_filtered[~df_filtered["finish"].str.contains(ex_pattern, case=False, na=False)]

if ex_search:
    ex_mask = (
        df_filtered["shade_name"].str.lower().str.contains(ex_search) |
        df_filtered["brand"].str.lower().str.contains(ex_search) |
        df_filtered["location"].str.lower().str.contains(ex_search) |
        df_filtered["nail_type"].str.lower().str.contains(ex_search) |
        df_filtered["finish"].str.lower().str.contains(ex_search)
    )
    df_filtered = df_filtered[~ex_mask]

if ex_missing_color:
    df_filtered = df_filtered[df_filtered["color_hex"] != ""]

if ex_unrated:
    df_filtered = df_filtered[df_filtered["rating_5"] > 0.0]

# -----------------------------------------------------------------------------
# CASE-INSENSITIVE NATURAL SORTING EXECUTION
# -----------------------------------------------------------------------------
df_filtered["_brand_sort"] = df_filtered["brand"].astype(str).str.lower()
df_filtered["_shade_sort"] = df_filtered["shade_name"].astype(str).str.lower()
df_filtered["_loc_sort"] = df_filtered["location"].astype(str).str.lower()
df_filtered["_type_sort"] = df_filtered["nail_type"].astype(str).str.lower()

sort_columns = []
sort_ascending = []

if grouping_choice == "color_family":
    sort_columns.append("color_sort_key")
    sort_ascending.append(True)
elif grouping_choice == "brand":
    sort_columns.append("_brand_sort")
    sort_ascending.append(True)
elif grouping_choice == "location":
    sort_columns.append("_loc_sort")
    sort_ascending.append(True)
elif grouping_choice == "nail_type":
    sort_columns.append("_type_sort")
    sort_ascending.append(True)
elif grouping_choice != "none":
    sort_columns.append(grouping_choice)
    sort_ascending.append(True)

if sort_choice == "chromatic":
    sort_columns.extend(["hue", "saturation", "value"])
    sort_ascending.extend([True, False, False])
elif sort_choice == "shade_name":
    sort_columns.append("_shade_sort")
    sort_ascending.append(True)
elif sort_choice == "brand":
    sort_columns.append("_brand_sort")
    sort_ascending.append(True)
elif sort_choice == "location":
    sort_columns.append("_loc_sort")
    sort_ascending.append(True)
elif sort_choice == "rating_desc":
    sort_columns.append("rating_5")
    sort_ascending.append(False)
elif sort_choice == "acq_desc":
    sort_columns.append("purchase_date")
    sort_ascending.append(False)

if "_shade_sort" not in sort_columns:
    sort_columns.append("_shade_sort")
    sort_ascending.append(True)

if sort_columns:
    df_filtered.sort_values(by=sort_columns, ascending=sort_ascending, inplace=True)
    df_filtered.drop(columns=["_brand_sort", "_shade_sort", "_loc_sort", "_type_sort"], errors="ignore", inplace=True)
    df_filtered.reset_index(drop=True, inplace=True)

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

st.title("💅 Polish & Storage Location Directory")

with st.expander("📖 User Guide & Operating Instructions", expanded=False):
    st.markdown("""
### Welcome to the Polish & Storage Directory Studio!

This application generates archival, publication-quality 300 DPI reference catalogs formatted specifically for physical 3-ring binders, desk reference sheets, and drawer inserts.

---

#### 1. 💅 Default Coat Count Configuration
* **Configurable Default Coats:** You can configure the default coat count fallback (default is **3 coats** $\\rightarrow$ `●●●`). Any polish in your collection without a specific coat count recorded in Koillection will display this default.

---

#### 2. 🔤 Natural Case-Insensitive Alphabetical Sorting
* **Case-Insensitive A–Z:** Brands and shade names sort in true natural order. Lowercase brand names (e.g. *cirque colors* or *essie*) appear alongside capitalized brands without being shoved to the end of the alphabet.

---

#### 3. 🔍 Filtering In & Filtering OUT
* **Inclusion Filters:** Select specific Brands, Collections, Formulation Types, or Finishes you want to include.
* **🚫 Exclusion Filters (Filter OUT):** Open the *"Exclusion Filters"* panel in the sidebar to omit specific records.

---

#### 4. 🧪 Formulation Types vs. Aesthetic Finishes
* **Formulation Type Column (`Type`):** Features dedicated vector icons for your application system.
* **Aesthetic Finish Column (`Finish`):** Displays visual lacquer effects.
* **Multi-Icon Mode:** Displays up to 4 vector icons side-by-side across the column without text clutter.
    """)

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Polishes Selected", f"{len(df_filtered)} / {len(df_raw)}")
col2.metric("Unique Brands", len(df_filtered["brand"].unique()))
col3.metric("Storage Locations", len(df_filtered["location"].unique()))
avg_rating = df_filtered[df_filtered["rating_5"] > 0]["rating_5"].mean()
col4.metric("Avg Rating", f"{avg_rating:.1f} ★" if not pd.isna(avg_rating) else "N/A")

st.markdown("---")

tab_books, tab_table, tab_full_pdf, tab_legend = st.tabs([
    "📚 Swatch Book Manager & Incremental Print",
    "📋 Live Inventory Preview",
    "🖨️ Full Catalog Print",
    "📑 Icon Legend (1-Page)"
])

# -----------------------------------------------------------------------------
# TAB 1: SWATCH BOOK MANAGER
# -----------------------------------------------------------------------------
with tab_books:
    st.subheader("Physical Swatch Binder Memory")
    st.write(
        "Track which polishes are bound in each physical album. "
        "When you add new polishes, the directory automatically outputs **only the replacement last page** "
        "(filling its free slots) plus any new continuation pages."
    )

    all_books = bm.load_all_books()
    book_options = {b_id: b["name"] for b_id, b in all_books.items()}
    book_options["__new__"] = "➕ [Create New Swatch Book]"

    col_select, _ = st.columns([2, 1])
    with col_select:
        selected_book_id = st.selectbox(
            "Select Physical Swatch Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options[x]
        )

    if selected_book_id == "__new__":
        with st.form("new_book_form"):
            st.markdown("### ➕ Create a New Swatch Book")
            new_name = st.text_input("Book / Binder Name", placeholder="e.g. Rainbow Swatch Binder, Helmer Album A")
            new_cap = st.number_input("Polishes per Page Sheet", min_value=10, max_value=40, value=24, step=1)
            new_notes = st.text_area("Notes", placeholder="e.g. Sorted chromatically by hue")
            submit_create = st.form_submit_button("Create Book", type="primary")

            if submit_create:
                if new_name.strip():
                    bm.create_book(new_name, new_cap, new_notes)
                    st.success(f"Book '{new_name}' created!")
                    st.rerun()
                else:
                    st.error("Please enter a book name.")
    else:
        current_book = all_books[selected_book_id]
        page_state = bm.calculate_book_pagination_state(current_book, df_filtered)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Committed to Binder", f"{page_state['total_committed']} polishes")
        m2.metric("Total Binder Pages", f"{page_state['total_pages']} pages")
        m3.metric("Last Page Status", f"{page_state['slots_on_last_page']} / {current_book['items_per_page']} slots")
        unprinted_count = len(page_state["unprinted_df"])
        m4.metric("Unprinted Polishes", f"{unprinted_count} waiting", delta=f"+{unprinted_count}" if unprinted_count > 0 else "All Caught Up!")

        st.markdown("---")
        act_col, preview_col = st.columns([1, 1])

        with act_col:
            st.markdown("### 📑 Incremental Printing")
            if unprinted_count == 0:
                st.info("🎉 All matching polishes in this selection are already committed to this swatch book!")
            else:
                if page_state["is_last_page_partial"]:
                    st.write(
                        f"**Plan:** Replace physical **Page {page_state['start_page_num']}** "
                        f"(carrying forward its {len(page_state['last_page_df'])} existing polishes + appending your new additions)."
                    )
                else:
                    st.write(
                        f"**Plan:** The last page in your binder is full. "
                        f"Printing will start cleanly on new **Page {page_state['start_page_num']}**."
                    )

                if st.button("🚀 Compile Incremental Update Sheet(s)", type="primary", use_container_width=True):
                    incremental_df = pd.concat([page_state["last_page_df"], page_state["unprinted_df"]]).drop_duplicates(subset=["item_id"])
                    
                    sub_title = (
                        f"Book: {current_book['name']} • "
                        f"{'Replacement Page ' + str(page_state['start_page_num']) if page_state['is_last_page_partial'] else 'Continuation Sheet'} "
                        f"• Generated: {datetime.now().strftime('%B %d, %Y')}"
                    )

                    try:
                        pdf_bytes = build_tabular_directory_pdf(
                            df=incremental_df,
                            group_by="none",
                            collection_title=f"{current_book['name']} (Update Sheet)",
                            active_columns=selected_columns,
                            font_family=font_choice,
                            banner_bg=c_banner_bg,
                            banner_text=c_banner_txt,
                            header_bg=c_header_bg,
                            header_text=c_header_txt,
                            zebra_bg=c_zebra_bg,
                            compact_mode=compact_density,
                            start_page_num=page_state["start_page_num"],
                            header_subtitle=sub_title,
                            finish_icon_only=finish_icon_only,
                            default_coats=default_coats,
                            legend_mode=selected_legend_mode,
                            rows_per_page=rows_per_page
                        )
                        st.session_state.vault["pdf_bytes"] = pdf_bytes
                        st.session_state.vault["pending_commit_ids"] = page_state["unprinted_df"]["item_id"].tolist()
                        st.success("Incremental update compiled successfully!")
                    except Exception as ex:
                        st.error(f"Error compiling PDF: {str(ex)}")

            pending_ids = st.session_state.vault.get("pending_commit_ids", [])
            if pending_ids:
                st.markdown("---")
                st.warning(f"⚠️ You have compiled updates for **{len(pending_ids)} polishes**.")
                if st.button("✅ Mark as Printed & Commit to Book", type="secondary", use_container_width=True):
                    bm.commit_items_to_book(selected_book_id, pending_ids)
                    st.session_state.vault["pending_commit_ids"] = []
                    st.session_state.vault["pdf_bytes"] = None
                    st.success("Book state committed successfully! Future prints will build off this point.")
                    st.rerun()

        with preview_col:
            st.markdown("### ⚙️ Book Management")
            with st.expander("✏️ Edit Book Settings"):
                edit_name = st.text_input("Name", value=current_book["name"])
                edit_cap = st.number_input("Capacity Per Page", min_value=10, max_value=40, value=current_book.get("items_per_page", 24))
                edit_notes = st.text_area("Notes", value=current_book.get("notes", ""))
                if st.button("Save Book Settings"):
                    bm.update_book_metadata(selected_book_id, edit_name, edit_cap, edit_notes)
                    st.success("Settings saved.")
                    st.rerun()

            with st.expander("🔄 Reset or Delete Book"):
                if st.button("⚠️ Clear Printed History (Reprint From Page 1)"):
                    bm.reset_book_printed_items(selected_book_id)
                    st.warning("Book history cleared.")
                    st.rerun()

                st.write("---")
                if st.button("🗑️ Delete this Book Permanently", type="primary"):
                    bm.delete_book(selected_book_id)
                    st.error("Book deleted.")
                    st.rerun()

        current_pdf = st.session_state.vault.get("pdf_bytes")
        if current_pdf:
            st.markdown("---")
            st.subheader("📄 Printable Update Preview")
            
            safe_filename = f"Update_{current_book['name'].replace(' ', '_')}.pdf"
            render_html5_download_button(current_pdf, safe_filename, "⬇️ Download Incremental PDF")
            
            base64_pdf = base64.b64encode(current_pdf).decode("utf-8")
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf" style="border: 1px solid #ddd; border-radius: 8px;"></iframe>',
                unsafe_allow_html=True
            )

# -----------------------------------------------------------------------------
# TAB 2: LIVE INVENTORY PREVIEW
# -----------------------------------------------------------------------------
with tab_table:
    st.caption(f"Showing {len(df_filtered)} matching polishes after active inclusion and exclusion filters.")
    for expected_col in ["color_hex", "color_family", "nail_type", "location", "brand", "shade_name", "finish", "coats", "rating_5", "size_oz", "purchase_date"]:
        if expected_col not in df_filtered.columns:
            df_filtered[expected_col] = ""

    display_df = df_filtered[[
        "location", "color_hex", "nail_type", "color_family", "brand", "shade_name", "finish", "coats", "rating_5", "size_oz", "purchase_date"
    ]].copy()
    
    display_df["coats"] = display_df["coats"].apply(
        lambda x: f"{default_coats} (default)" if not str(x).strip() or str(x).strip() in ["", "None", "nan", "0"] else str(x).strip()
    )

    display_df.rename(columns={
        "location": "Location",
        "color_hex": "Hex",
        "nail_type": "Formulation Type",
        "color_family": "Spectrum Family",
        "brand": "Brand",
        "shade_name": "Shade Name",
        "finish": "Finish (Aesthetic)",
        "coats": "Coats",
        "rating_5": "Rating (0-5)",
        "size_oz": "Size",
        "purchase_date": "Acquired"
    }, inplace=True)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rating (0-5)": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
            "Location": st.column_config.TextColumn("Location", help="Drawer or Slot ID"),
            "Hex": st.column_config.TextColumn("Hex", width="small")
        }
    )

# -----------------------------------------------------------------------------
# TAB 3: FULL CATALOG PRINT
# -----------------------------------------------------------------------------
with tab_full_pdf:
    st.subheader("Publication-Quality Complete Catalog")
    st.write(
        "Compile your complete collection from scratch with distinct section headers, "
        "separated Type / Finish columns, and respecting all active inclusion and exclusion filters."
    )

    if st.button("🚀 Compile Full Collection PDF", type="primary"):
        with st.spinner("Rendering vector swatch dots, icons, and compiling pages..."):
            try:
                full_pdf_data = build_tabular_directory_pdf(
                    df=df_filtered,
                    group_by=grouping_choice,
                    collection_title=doc_title,
                    active_columns=selected_columns,
                    font_family=font_choice,
                    banner_bg=c_banner_bg,
                    banner_text=c_banner_txt,
                    header_bg=c_header_bg,
                    header_text=c_header_txt,
                    zebra_bg=c_zebra_bg,
                    compact_mode=compact_density,
                    start_page_num=1,
                    finish_icon_only=finish_icon_only,
                    default_coats=default_coats,
                    legend_mode=selected_legend_mode,
                    rows_per_page=rows_per_page
                )
                st.session_state.vault["pdf_bytes"] = full_pdf_data
                st.success("Complete catalog compiled!")
            except Exception as ex:
                st.error(f"Error compiling PDF: {str(ex)}")

    current_pdf = st.session_state.vault.get("pdf_bytes")
    if current_pdf:
        catalog_filename = f"Full_Directory_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        render_html5_download_button(current_pdf, catalog_filename, "⬇️ Download Complete Catalog PDF")
        
        base64_pdf = base64.b64encode(current_pdf).decode("utf-8")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf" style="border: 1px solid #ddd; border-radius: 8px;"></iframe>',
            unsafe_allow_html=True
        )

# -----------------------------------------------------------------------------
# TAB 4: ICON LEGEND (EXACTLY 1 PAGE)
# -----------------------------------------------------------------------------
with tab_legend:
    st.subheader("📑 Visual Icon & Formulation Legend Sheet")
    st.write(
        "Generate a standalone, publication-quality **single 8.5\" × 11\" US Letter page** "
        "explaining all 11 formulation types, 22 lacquer finishes, coat opacities, and swatch indicators."
    )

    if st.button("🖨️ Compile 1-Page Icon Legend Sheet", type="primary"):
        with st.spinner("Formatting legend grid..."):
            legend_data = build_legend_pdf(font_family=font_choice, banner_bg=c_banner_bg, banner_text=c_banner_txt)
            st.session_state.vault["legend_bytes"] = legend_data
            st.success("1-Page Legend sheet compiled successfully!")

    current_legend = st.session_state.vault.get("legend_bytes")
    if current_legend:
        render_html5_download_button(current_legend, "Nail_Polish_Icon_Legend_Sheet.pdf", "⬇️ Download 1-Page Legend PDF")
        base64_legend = base64.b64encode(current_legend).decode("utf-8")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{base64_legend}" width="100%" height="850" type="application/pdf" style="border: 1px solid #ddd; border-radius: 8px;"></iframe>',
            unsafe_allow_html=True
        )