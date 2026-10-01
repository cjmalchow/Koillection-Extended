import base64
from datetime import datetime
import streamlit as st
import pandas as pd

from db import fetch_polish_inventory, get_unique_filter_values
from pdf_generator import build_tabular_directory_pdf
import book_manager as bm

if "vault" not in st.session_state:
    st.session_state.vault = {}

if "pdf_bytes" not in st.session_state.vault:
    st.session_state.vault["pdf_bytes"] = None

if "pending_commit_ids" not in st.session_state.vault:
    st.session_state.vault["pending_commit_ids"] = []

st.set_page_config(
    page_title="Polish & Storage Directory",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def render_html5_download_button(pdf_bytes: bytes, filename: str, label: str = "⬇️ Download PDF"):
    """
    Renders an archival, crash-proof HTML5 download button using a Base64 data URI.
    Bypasses Streamlit's internal WebSocket requireServerUri crash in iframe environments.
    """
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

        st.markdown("**Columns to Print:**")
        all_col_options = {
            "location": "Location ID",
            "color_swatch": "Color Swatch Pip",
            "brand": "Brand",
            "shade_name": "Shade Name",
            "finish": "Finish & Icon",
            "coats": "Coats (Opacity Pips)",
            "rating": "Star Rating",
            "size_acq": "Size & Acquisition Date",
            "item_id": "Koillection ID"
        }
        selected_columns = st.multiselect(
            "Select Columns",
            options=list(all_col_options.keys()),
            default=["location", "color_swatch", "brand", "shade_name", "finish", "coats", "rating", "size_acq"],
            format_func=lambda x: all_col_options[x]
        )

    st.markdown("---")
    st.subheader("📑 Organization & Sorting")

    grouping_choice = st.selectbox(
        "Primary Grouping (PDF Banners)",
        options=["color_family", "brand", "location", "finish", "rating_group", "acquisition_year", "none"],
        index=0,
        format_func=lambda x: {
            "color_family": "🌈 Color Spectrum (Reds, Blues, Purples)",
            "brand": "🏷️ Brand (OPI, Mooncat, ILNP)",
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
    st.subheader("🔍 Filters")

    search_query = st.text_input("Search Shade / Brand / Location", placeholder="e.g. OPI, 1-A1, Holo").strip().lower()

    all_locations, all_brands, all_finishes, all_color_families = get_unique_filter_values(df_raw)
    all_collections = sorted([c for c in df_raw["collection"].unique() if c])

    sel_collections = st.multiselect("Collections", options=all_collections, default=[])
    sel_color_families = st.multiselect("Color Families", options=all_color_families, default=[])
    sel_locations = st.multiselect("Storage Locations", options=all_locations, default=[])
    sel_brands = st.multiselect("Brands", options=all_brands, default=[])
    sel_finishes = st.multiselect("Finishes", options=all_finishes, default=[])

    doc_title = st.text_input("Directory Title", value="Nail Polish & Storage Location Directory")

# -----------------------------------------------------------------------------
# Filter Application
# -----------------------------------------------------------------------------
df_filtered = df_raw.copy()

if search_query:
    mask = (
        df_filtered["shade_name"].str.lower().str.contains(search_query) |
        df_filtered["brand"].str.lower().str.contains(search_query) |
        df_filtered["location"].str.lower().str.contains(search_query) |
        df_filtered["finish"].str.lower().str.contains(search_query)
    )
    df_filtered = df_filtered[mask]

if sel_collections:
    df_filtered = df_filtered[df_filtered["collection"].isin(sel_collections)]

if sel_color_families:
    df_filtered = df_filtered[df_filtered["color_family"].isin(sel_color_families)]

if sel_locations:
    df_filtered = df_filtered[df_filtered["location"].isin(sel_locations)]

if sel_brands:
    df_filtered = df_filtered[df_filtered["brand"].isin(sel_brands)]

if sel_finishes:
    pattern = "|".join(sel_finishes)
    df_filtered = df_filtered[df_filtered["finish"].str.contains(pattern, case=False, na=False)]

# -----------------------------------------------------------------------------
# Sorting Execution
# -----------------------------------------------------------------------------
sort_columns = []
sort_ascending = []

if grouping_choice == "color_family":
    sort_columns.append("color_sort_key")
    sort_ascending.append(True)
elif grouping_choice != "none":
    sort_columns.append(grouping_choice)
    sort_ascending.append(True)

if sort_choice == "chromatic":
    sort_columns.extend(["hue", "saturation", "value"])
    sort_ascending.extend([True, False, False])
elif sort_choice == "shade_name":
    sort_columns.append("shade_name")
    sort_ascending.append(True)
elif sort_choice == "brand":
    sort_columns.append("brand")
    sort_ascending.append(True)
elif sort_choice == "location":
    sort_columns.append("location")
    sort_ascending.append(True)
elif sort_choice == "rating_desc":
    sort_columns.append("rating_5")
    sort_ascending.append(False)
elif sort_choice == "acq_desc":
    sort_columns.append("purchase_date")
    sort_ascending.append(False)

if sort_columns:
    df_filtered.sort_values(by=sort_columns, ascending=sort_ascending, inplace=True)
    df_filtered.reset_index(drop=True, inplace=True)

# -----------------------------------------------------------------------------
# Large Red Centered "EXPERIMENTAL" Header
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Instructions & User Guide Expander
# -----------------------------------------------------------------------------
with st.expander("📖 User Guide & Operating Instructions", expanded=False):
    st.markdown("""
### How to Use the Directory Studio

Welcome to the **Polish & Storage Location Directory** generator! This application produces publication-quality, 300 DPI reference documents formatted for physical 3-ring binders, desk index sheets, and drawer walk-throughs.

---

#### 1. 📑 Organization & Ordering Modes
* **🌈 Color Spectrum:** Converts your polish hex codes to the HSV color space and groups them into natural rainbow families (*Reds $\\rightarrow$ Oranges $\\rightarrow$ Yellows $\\rightarrow$ Greens $\\rightarrow$ Blues $\\rightarrow$ Purples $\\rightarrow$ Pinks*).
* **🏷️ Brand:** Alphabetizes by manufacturer (e.g. *ILNP, Mooncat, OPI*) with dedicated group headers. Redundant brand prefixes in shade names are stripped automatically.
* **📦 Storage Location:** Groups polishes by their physical Helmer drawer, box, or grid slot (e.g. *1-A1 through 1-H8*).
* **✨ Finish / Effect:** Groups items by lacquer formulation (e.g. *Linear Holo, Creme, Flake, Magnetic*).

---

#### 2. 📚 Swatch Book Manager (Incremental Printing)
* **Never Waste Paper or Cardstock:** When you add 5 new polishes to your collection, you do *not* need to reprint your entire binder.
* **Replacement Page Logic:** The manager tracks how many polishes are in your physical book. If your last sheet has empty slots (e.g. 6 polishes on a 24-slot sheet), the incremental generator outputs **only that last sheet** (filled with your 5 new additions) plus any subsequent overflow sheets.
* **The Workflow:**
  1. Select or create your physical album in the **📚 Swatch Book Manager** tab.
  2. Click **'🚀 Compile Incremental Update Sheet(s)'**.
  3. Print the PDF, slip the replacement sheet into your binder, and click **'✅ Mark as Printed & Commit to Book'**.

---

#### 3. 🎨 Customization Deck (Sidebar)
* **Typography:** Choose between clean sans-serif (*Helvetica*), classic editorial serif (*Times-Roman*), or technical (*Courier*).
* **Color Themes:** Select from elegant pre-built palettes (*Navy Slate, Plum Velvet, Emerald Garden, Classic Monolith*) or pick your own custom hex colors for section banners, table headers, and zebra stripes.
* **Column Selector:** Turn columns on or off. Table widths dynamically re-balance to exactly fill the 8.5" × 11" printable area.

---

#### 4. 🖨️ Recommended Print Settings
* **Paper Stock:** Standard 24–28 lb bright white paper for daily binders, or 65 lb smooth cardstock for durable reference manuals.
* **Printer Driver:** Set page scaling to **'Actual Size'** or **'100%'** (do *not* use "Fit to Page") to preserve razor-sharp 300 DPI vector clarity.
    """)

st.markdown("---")

# -----------------------------------------------------------------------------
# Main Navigation Tabs
# -----------------------------------------------------------------------------
tab_books, tab_table, tab_full_pdf = st.tabs([
    "📚 Swatch Book Manager & Incremental Print",
    "📋 Live Inventory Preview",
    "🖨️ Full Catalog Print"
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
                            header_subtitle=sub_title
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
    st.caption(f"Showing {len(df_filtered)} polishes sorted by: {grouping_choice} ➜ {sort_choice}")
    for expected_col in ["color_hex", "color_family", "location", "brand", "shade_name", "finish", "coats", "rating_5", "size_oz", "purchase_date"]:
        if expected_col not in df_filtered.columns:
            df_filtered[expected_col] = ""

    display_df = df_filtered[[
        "location", "color_hex", "color_family", "brand", "shade_name", "finish", "coats", "rating_5", "size_oz", "purchase_date"
    ]].copy()
    
    display_df.rename(columns={
        "location": "Location",
        "color_hex": "Hex",
        "color_family": "Spectrum Family",
        "brand": "Brand",
        "shade_name": "Shade Name",
        "finish": "Finish",
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
        "Compile your complete collection from scratch with distinct section headers "
        "for every group (e.g. Color Spectrum, Brand, or Location)."
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
                    start_page_num=1
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