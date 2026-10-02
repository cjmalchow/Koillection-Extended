<p align="center">
    <img src="https://user-images.githubusercontent.com/20560781/80213166-0e560e00-8639-11ea-944e-4f79fdbcef55.png" width="75" height="75">
</p>

<p align="center">
    <img src="https://img.shields.io/github/v/release/koillection/koillection" />
    <img src="https://img.shields.io/github/license/koillection/koillection" />    
    <img src="https://img.shields.io/badge/PHP-8.3-blue" />
    <img src="https://img.shields.io/badge/Symfony-8.0-black" />
    <img src="https://img.shields.io/badge/Server-FrankenPHP-00ADD8" />
    <img src="https://img.shields.io/badge/Python-3.11-yellow" />
    <img src="https://img.shields.io/badge/Database-PostgreSQL%2016-336791" />
</p>

# 💅 Koillection: The Ultimate Nail Polish Vault

*A highly customized, full-stack fork of [Koillection](https://github.com/benjaminjonard/koillection) running on Symfony 8, Twig, and FrankenPHP. It has been engineered specifically for extensive nail polish vaults, integrating an ecosystem of independent Python 3.11/Streamlit micro-apps embedded seamlessly into the core UI via dynamic iframes.*

---

## ✨ The Custom Nail Polish Application Suite

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 KOILLECTION CORE (PHP 8+ / FrankenPHP)                 │
  └───────┬────────────────────────────────────────────────────────┬───────┘
          │ (Port 8081 / 8144)                                     │
          ▼                                                        ▼
  ┌───────────────────────────────┐        ┌───────────────────────────────┐
  │   App 1: Storage Grid Visual  │ (8501) │   App 5: Color Swatch Creator │ (8509)
  │   App 2: Smart Color Matcher  │ (8503) │   App 6: Bottle Label Maker   │ (8511)
  │   App 3: Elo Polish Ranker    │ (8505) │   App 7: Polish & Storage Dir │ (8513)
  │   App 4: Mani Logger & Timers │ (8507) └───────────────────────────────┘
  └───────────────────────────────┘
```

### 🗺️ App 1: Storage Grid Visualizer & Sticker Generator (Port 8501 / 8502)
*Never lose a bottle again. Maps physical storage boxes into an interactive digital grid and generates customizable printable labels.*
* **Dynamic Grid Mapping:** Automatically arranges polishes by their `Location` coordinate (e.g. `1-A1` through `1-H8`). Unslotted storage locations (like `Display Shelf`) dynamically receive dedicated lists.
* **High-Res Printable Stickers:** Generates crisp, ink-friendly PNG labels designed to be affixed to the inside lids or exterior faces of physical drawers and acrylic boxes.
* **Deep Typography Customization:** Dozens of Google Fonts (Lobster, Caveat, Great Vibes), text alignment controls, custom background/border palettes, and auto-scaling font sizing.
* **Blackout Coordinates:** Allows structural dividers or broken physical slots to be flagged as "Unusable", blacking them out on both the on-screen grid and printed stickers.

### 🎯 App 2: Smart Color Matcher & Quality Control Studio (Port 8503 / 8504)
*Transform your physical vault into a searchable color studio and audit your database for pristine color fidelity.*
* **Point-and-Click Hex Eyedropper:** Click directly on an uploaded swatch photo to sample and save Primary and Secondary hex colors directly to PostgreSQL.
* **Automated Format Audit & Triage Queue:** Scans your collection with strict regex validation (`^#?[0-9A-Fa-f]{6}$`) to automatically detect and flag polishes containing descriptive words (like *"Purple"*) in their hex fields. Isolates items into `⚠️ Invalid Format`, `⚪ Untagged`, and `✅ Verified` queues for one-click repair.
* **Surgical Database Persistence:** Writes verified color codes specifically to `Colour (Hex)` without touching the descriptive `Color` field, automatically inserting valid UUIDs, `owner_id`, and public visibility adhering to Koillection entity rules.
* **Tolerance-Radius Dupe Search:** Pick a target color on an HSV color wheel and adjust tolerance distance to find exact twins or close substitutes in your existing collection.
* **Harmonic Color Theory Pairings:** Automatically calculates Complementary, Analogous, Triadic, and Tetradic pairings pulled strictly from polishes you already own.

### 🏆 App 3: Elo-Based Polish Ranker (Port 8505 / 8506)
*Definitively rank your collection using a competitive 1-on-1 Elo chess rating algorithm to discover your true holy grails.*
* **Wishlist & Filter Scoping:** Target specific subsets (e.g. "Summer Neons" or "Untried Creams") for focused voting gauntlets.
* **Smart Math (K-Factor 32):** Major rating swings occur during upsets, while expected favorites earn incremental gains.
* **Session Persistence & Merging:** Merge separate voting sessions to track taste evolution over time with delta movement indicators.
* **Portable HTML Archive:** Export standalone HTML leaderboards with Base64 images embedded directly inside for offline archival.

### 💅 App 4: Mani Logger & Digital Canvas (Port 8507 / 8508)
*An interactive digital manicure logbook with real-time timers and finger-by-finger formula mapping.*
* **10-Finger Digital Canvas:** Visually assign different polishes, toppers, and nail art designs to individual fingers on both hands.
* **Live Application Timers:** Interactive JavaScript timers tracking dry-times between base, color, and top coat layers with customizable auditory chimes.
* **Automated Koillection Integration:** Creates new diary entries in your dedicated `Manicure Diary` collection, attaches 10-finger digital map graphics, and automatically links the polishes used via Koillection's internal related items bridge table (`koi_item_related_item`).

### 🎨 App 5: Color Swatch Creator (Port 8509 / 8510)
*Design and compile physical swatch binder albums with vector PDF generation.*
* **200 DPI Vector PDF Engine:** Formatted for high-quality cardstock printing and direct swatch stick placement.
* **Multi-Book Management:** Organize swatches across multiple physical binders (e.g. "Indie Vault" vs "Main Creams").
* **Rainbow Chromatic Sorting:** Arranges swatches using perceptual HSV spectrum mathematics.

### 🏷️ App 6: Precision Bottle Label Maker (Port 8511 / 8512)
*Industrial-grade label generation optimized for Brother P-Touch Cube Plus (PT-P710BT) 24mm continuous laminated tape.*
* **1-Bit Vector Graphics Engine (180 DPI):** Custom geometric polygon renderers for 22 nail finishes and half-star ratings to eliminate missing glyph boxes (`□`) on thermal print drivers.
* **Smart Dynamic Content Budgeting:** Automatically switches typography layouts from standard 55mm down to 34mm mini-labels based on bottle cap sizes.
* **Hybrid QR System:** Generates compact QR codes that bridge offline human-readable specs with instant online links to Koillection item profiles.
* **Archival 300 DPI Legend Sheets:** Compiles full 8.5" × 11" US Letter reference legends explaining all 22 finish symbols.

### 📖 App 7: Polish & Storage Directory Studio (Port 8513 / 8514)
*Publication-quality US Letter catalog generator designed for physical 3-ring desk binders and drawer index inserts.*
* **Perceptual Chromatic Spectrum Sorting:** Automatically converts hex color codes into the HSV color space to organize polishes into natural rainbow groups (*Reds → Oranges → Yellows → Greens → Blues → Purples → Pinks*) with dedicated group banners.
* **Formulation Type vs. Aesthetic Finish Separation:**
  * **Formulation Type Column (`Type`):** Features custom vector glyphs for all 11 application systems (*Regular Nail Lacquer, UV Gel Nail Lacquer, Top Coat, Base Coat, Cuticle Oil, Nail Treatment, Liquid Latex, Drying Drops, Stamping Lacquer, Press-On Glue, Flakies*).
  * **Aesthetic Finish Column (`Finish`):** Displays visual lacquer effects (*Linear Holo, Creme, Shimmer, Flakie, Metallic, etc.*) with zero repetition.
  * **Multi-Icon Mode:** Displays up to 4 distinct vector finish icons side-by-side across the column for hybrid/compound polishes without text clutter.
* **Full-Color 300 DPI Vector Icons:** 22 distinct geometric vector silhouettes with custom color themes (e.g. *Neon* is high-voltage lime, *Thermal* is two-tone coral/cobalt, *Solar* is a golden sun with violet UV rays, and *Crackle* is a fractured ceramic tile).
* **Configurable Default Coat Count:** Unspecified polishes dynamically inherit an app-level coat count setting (defaulting to **3 coats** `●●●`) while preserving explicit coat counts.
* **Smart Swatch Book Memory:** Decoupled JSON binder state tracking physical album pages. When new polishes arrive, it calculates and outputs **only the replacement last page** (filling its empty slots) plus any overflow sheets, keeping previous binder pages untouched.
* **Advanced Exclusion Filtering (Filter OUT):** Filter out specific formulation types (e.g. hide UV Gel for regular lacquer binders), omit specific storage locations (e.g. hide Destash bins or Unassigned bottles), search negative keywords, or hide unswatched polishes.
* **Standalone 1-Page Icon Legend:** Generates a single-page 8.5" × 11" US Letter guide explaining all 11 formulation types, 22 lacquer finishes, coat opacities, and swatch indicators with guaranteed zero overflow to page 2.
* **Crash-Proof HTML5 Base64 Pipeline:** Pure client-side data URI download buttons that bypass iframe WebSocket drops.

---

## ⚡ Core Koillection Enhancements

### 📋 Bulk Actions (List View)
* Integrated directly into the core Symfony/Twig templates (`_items_list.html.twig`).
* Multi-select checkboxes for batch operations.
* **Bulk Duplicate:** Clone multiple polishes with identical brand/finish metadata in one click.
* **Bulk Move & Delete:** Rapidly migrate entire collections between physical storage boxes.

### 🛡️ Null-Safe Table View Engine
* Patched strict PHP 8 typing in `src/Entity/Item.php` (`getDatumByLabel(?string $label)`) to gracefully handle unassigned, custom, or empty datum fields.
* Guarded Twig column rendering in both table headers and rows, permanently preventing 500 crashes on fields containing special characters or parentheses (e.g. `Size (oz)` and `Colour (Hex)`).

### 🔤 Natural Case-Insensitive Alphabetical Sorting
* Normalized sort keys in both `db.py` and `app.py`, completely eliminating the ASCIIbetical trap where lowercase brand names (e.g. *cirque colors*, *essie*) were sorted at the end after *Zoya*.

### 🚀 Live FrankenPHP Development Mounts
* Solved the in-memory FrankenPHP worker disconnect by mounting Windows development directories directly to the active runtime path (`./src:/app/public/src` and `./templates:/app/public/templates`).
* Twig template and controller updates reflect immediately upon clearing the Symfony cache (`php bin/console cache:clear`) without requiring slow image rebuilds.

---

## 🛠️ Complete Fresh Installation Guide (Zero to Running Vault)

Follow these instructions if you are setting up this vault on a brand-new Windows computer.

### Step 1: Install Prerequisites on Windows
1. **Enable WSL 2 (Windows Subsystem for Linux):**
   Open PowerShell as Administrator and run:
   ```powershell
   wsl --install
   ```
   Restart your computer if prompted.
2. **Install Docker Desktop:**
   * Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
   * During installation, ensure **"Use the WSL 2 based engine"** is checked.
   * Start Docker Desktop and wait until the whale icon in your system tray shows the engine is running.
3. **Install Git:**
   * Download and install [Git for Windows](https://git-scm.com/download/win).

---

### Step 2: Clone the Vault Repository
Open PowerShell and clone directly from the official **`KoillectionForNailPolish`** branch into your working directory (e.g. `C:\Koillection-Extended`):

```powershell
git clone -b KoillectionForNailPolish https://github.com/cjmalchow/Koillection-Extended.git C:\Koillection-Extended
cd C:\Koillection-Extended
```

---

### Step 3: Prepare Local Storage Directories
Koillection requires dedicated local directories for persistent PostgreSQL data, uploaded swatch photos, and database backup dumps:

```powershell
New-Item -ItemType Directory -Force -Path uploads, db_data, backups
```

---

### Step 4: Build the Core FrankenPHP Koillection Image
Because Koillection runs on FrankenPHP in high-performance worker mode from `/app/public`, the custom routes, entity methods, and Twig templates must be baked into the base image:

```powershell
docker buildx build -t my-custom-koillection .
```
*(This process takes a few minutes on the initial build as it installs system libraries, PHP extensions, and composer assets).*

---

### Step 5: Launch the Entire 7-App Stack
Start PostgreSQL, the core Koillection app, the backup scheduler, n8n, and all 7 custom Python Streamlit apps in the background:

```powershell
docker compose up -d
```

Verify that all containers are running healthy:
```powershell
docker compose ps
```

---

### Step 6: Flush the In-Memory Symfony Cache
Ensure all compiled routing tables and templates are freshly indexed by FrankenPHP:

```powershell
docker exec koillection-sandbox php bin/console cache:clear
```

---

### Step 7: Initial Koillection Setup & Real-World Vault Configuration

Open your web browser to **`http://localhost:8081`** and complete the initial account wizard to create your **Administrator account**.

To ensure all 7 custom applications can read, match, sort, and label your nail polishes seamlessly, configure the following **Choice Lists**, **Templates**, and **Collections**.

---

#### Phase A: Create the Choice Lists (Dropdowns)
In Koillection's sidebar, click **Tools** (wrench icon) → **Choice Lists** → **Add Choice List**:

1. **Choice List: `Lacquer Type`** *(⭐ Required for Finish Icons)*:
   * Used by: *Color Matcher, Swatch Creator, Directory, & Label Maker*.
   * Add these 23 finish options:  
     `Creme`, `Holographic (Linear)`, `Holographic (Scattered)`, `Shimmer`, `Glitter`, `Flakie`, `Metallic`, `Pearl`, `Matte`, `Jelly`, `Thermal`, `Magnetic`, `Solar`, `Neon`, `Foil`, `Satin`, `Iridescent`, `Sheer`, `Glow-in-the-Dark`, `Glass Fleck`, `Multichrome`, `Duochrome`, `Crackle`, `Textured / Sand`, `Topper`.

2. **Choice List: `Nail Polish Type`** *(⭐ Required for Formulation System)*:
   * Used by: *Polish Directory & Bottle Label Maker*.
   * Add these 11 options:  
     `Regular Nail Lacquer`, `UV Gel Nail Lacquer`, `Top Coat`, `Base Coat`, `Nail Treatment`, `Cuticle Oil`, `Liquid Latex`, `Latex Tape`, `Drying Drops`, `Stamping Air Dry Lacquer`, `Press on Glue/Releaser`.

3. **Choice List: `Nail Polish Brands`** *(Optional / Recommended)*:
   * Populate with your favorite brands (*Mooncat, ILNP, Holo Taco, Cirque Colors, OPI, Essie, etc.*) to ensure standardized brand naming across all apps.

4. **Choice List: `Primary Colour`** *(Optional / Recommended)*:
   * Standardized broad color families (*Red, Orange, Yellow, Green, Blue, Purple, Pink, Brown/Nude, White, Grey, Black, Multicolour*).

5. **Choice List: `Bottle Status`** *(Optional / Recommended)*:
   * Inventory status options (*In Collection, Incoming, Borrowed, Lent Out, Destash/Sold*).

6. **Choice List: `Fill Level`** *(Optional / Recommended)*:
   * Usage volume markers (*100% Full, 75%, 50%, 25%, Empty*).

---

#### Phase B: The Real-World Master Template (`Nail Polish Template`)
In the sidebar, navigate to **Tools** → **Templates** → **Add Template**:
* **Template Title:** `Nail Polish Template`
* Below is the complete, logically reordered 36-field schema. It flows naturally from basic identity through physical storage, usage tracking, and finally **all image swatches grouped at the very bottom**:

| # | Field Name *(Exact Label)* | Type | Choice List / Config | Status | Purpose Across the Vault |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **`Brand`** | `Choice list` | `Nail Polish Brands` (or Text) | ⭐ **Required** | All Apps: Sorting, filtering, label headers |
| **2** | **`Product Name`** | `Text` | Single-line text | ✨ Archival | Full commercial product name |
| **3** | **`Shade Name/Number`** | `Text` | Single-line text | ✨ Archival | Internal brand code / shade number |
| **4** | **`Type`** | `Choice list` | `Nail Polish Type` | ⭐ **Required** | Directory & Label Maker: Formulation icon column |
| **5** | **`Finish`** | `Choice list` | `Lacquer Type` *(Multi-select)* | ⭐ **Required** | All Apps: Vector finish icons & multi-icon clusters |
| **6** | **`Finish (Colour Picker)`** | `Text` | Single-line text | 💡 Recommended | Color Matcher: Eyedropper studio finish record |
| **7** | **`Big 5 Free`** | `Checkbox` | Boolean | ✨ Chemical | Non-toxic formula specification |
| **8** | **`Primary Colour`** | `Choice list` | `Primary Colour` | ✨ Archival | Broad color family classification |
| **9** | **`Colour (Hex)`** | `Text` | Single-line text | ⭐ **Required** | Color Matcher, Directory, & Swatch Creator: True hex |
| **10** | **`Secondary Colour (Hex)`**| `Text` | Single-line text | 💡 Recommended | Color Matcher: Duochrome & shift color matching |
| **11** | **`Size (oz)`** | `Number` | e.g. `0.50` | 💡 Recommended | Directory & Label Maker: Bottle volume specs |
| **12** | **`Coats`** | `Number` / `Text` | Default: `2` or `3` | ⭐ **Required** | Directory & Label Maker: Opacity dots (`●●○`) |
| **13** | **`Location`** | `Text` | Format: `1-A1` or `Shelf B` | ⭐ **Required** | Locator (Grid), Directory, & Label Maker: Storage slot |
| **14** | **`Other Location(s)`** | `Text` | Single-line text | 💡 Recommended | Locator: Secondary storage or travel cases |
| **15** | **`Status`** | `Choice list` | `Bottle Status` | ✨ Inventory | In Collection, Sold, Destashed, etc. |
| **16** | **`Fill Level`** | `Choice list` | `Fill Level` | ✨ Inventory | 100%, 75%, 50%, 25%, Empty |
| **17** | **`Other Bottles`** | `Section` | Form section divider | ✨ Structure | Visual divider for backup bottles |
| **18** | **`Bottle Number`** | `Number` | Integer | ✨ Inventory | Bottle ID for duplicate/backup bottles |
| **19** | **`Empty Bottle`** | `Checkbox` | Boolean | ✨ Inventory | Empty bottle archive flag |
| **20** | **`Empty Bottle Date`** | `Date` | Standard date | ✨ Inventory | Date bottle was finished |
| **21** | **`Cost`** | `Price` | Currency format | ✨ Financial | Purchase price |
| **22** | **`Purchase Date`** | `Date` | Standard date | 💡 Recommended | Directory & Ranker: Acquisition archive |
| **23** | **`Purchased From`** | `Text` | Single-line text | ✨ Sourcing | Retailer, stockist, or indie maker shop |
| **24** | **`Product WebPage`** | `Link` | URL | ✨ External | Direct web link to brand listing |
| **25** | **`Discontinued?`** | `Checkbox` | Boolean | ✨ Rarity | Rare / Deadstock / Limited Edition flag |
| **26** | **`Date Added`** | `Date` | Auto/Manual date | ✨ Archival | Vault intake date |
| **27** | **`Overall Rating`** | `Rating` | Koillection Rating *(0–10)* | ⭐ **Required** | Directory, Label Maker, & Ranker: Half-stars |
| **28** | **`Colour Rating`** | `Rating` | Koillection Rating | ✨ Evaluation | Subjective color aesthetic score |
| **29** | **`Date Opened`** | `Date` | Standard date | ✨ Longevity | Tracking PAO (Period After Opening) |
| **30** | **`Usage Count`** | `Number` | Integer counter | ✨ Usage | Total times worn in manicures |
| **31** | **`Last Used Date`** | `Date` | Standard date | ✨ Usage | Date of most recent manicure |
| **32** | **`Description`** | `Long text` | Multi-line text | ✨ Notes | Brand description, inspiration, and notes |
| **33** | **`Bottle Picture`** | `Image` | Image upload | ✨ Visual | Physical bottle photo |
| **34** | **`Shade Picture`** | `Image` | Image upload | ✨ Visual | Direct close-up swatch photo |
| **35** | **`Painted On Picture`** | `Image` | Image upload | ✨ Visual | Manicure swatch on real nails |
| **36** | **`Matte Top Coat`** | `Image` | Image upload | ✨ Visual | Swatch showing finish with matte topper |

---

#### Phase C: Create Your Two Core Collections
1. **Collection 1: Your Main Vault (e.g. `Nail Polish Vault`):**
   * Go to **Collections** → **Add Collection**.
   * Title: `Nail Polish Vault` (or your preferred name).
   * **Template:** Select **`Nail Polish Template`**.
   * *Every polish added here will automatically have all required fields ready for all 7 apps!*
2. **Collection 2: The Manicure Diary (Required for App 4 - Mani Logger):**
   * Go to **Collections** → **Add Collection**.
   * Title: **`Manicure Diary`**.
   * *When you use Mani Logger, select this collection in its sidebar. Mani Logger will automatically save your wear dates, ratings, notes, 10-finger nail maps, and link the polishes you used via Koillection's internal related items table!*

---

## 🌐 Port Allocation & Architecture Matrix

Both environments run concurrently on the same Docker host with strict network and port isolation:

| Service | Sandbox Port | Production Port | Internal Container Port |
| :--- | :--- | :--- | :--- |
| **Koillection Core (FrankenPHP)** | `8081` | `8144` | `80` |
| **App 1: Storage Grid (Locator)** | `8501` | `8502` | `8501` |
| **App 2: Color Matcher** | `8503` | `8504` | `8501` |
| **App 3: Elo Ranker** | `8505` | `8506` | `8501` |
| **App 4: Mani Logger** | `8507` | `8508` | `8501` |
| **App 5: Swatch Creator** | `8509` | `8510` | `8501` |
| **App 6: Bottle Label Maker** | `8511` | `8512` | `8501` |
| **App 7: Polish Directory** | `8513` | `8514` | `8501` |
| **PostgreSQL Database** | `5433` | `5432` | `5432` |
| **n8n Automation Engine** | `5679` | `5678` | `5678` |

---

## 🔄 Daily Maintenance & Helpful Commands

```powershell
# Stop all services gracefully
docker compose down

# Start all services back up
docker compose up -d

# Fast Symfony cache clear (2 seconds - live mounts active)
docker exec koillection-sandbox php bin/console cache:clear

# Take an instant manual database backup
docker exec db-sandbox pg_dump -U koillection_user koillection > C:\Koillection-Extended\manual_backup.sql
```

---

## Project Repository & License

* Repository: [https://github.com/cjmalchow/Koillection-Extended/tree/KoillectionForNailPolish](https://github.com/cjmalchow/Koillection-Extended/tree/KoillectionForNailPolish)
* Upstream Project: [https://github.com/koillection/koillection](https://github.com/koillection/koillection)
* License: Released under the [MIT License](LICENSE).