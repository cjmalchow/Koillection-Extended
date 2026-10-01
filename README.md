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
  │   1. Storage Grid Visualizer  │ (8501) │   5. Color Swatch Creator     │ (8509)
  │   2. Smart Color Matcher      │ (8503) │   6. Bottle Label Maker (24mm)│ (8511)
  │   3. Elo-Based Polish Ranker  │ (8505) │   7. Polish & Storage Dir     │ (8513)
  │   4. Mani Logger & Timers     │ (8507) └───────────────────────────────┘
  └───────────────────────────────┘
```

### 🗺️ 1. Storage Grid Visualizer & Sticker Generator (Port 8501 / 8502)
*Never lose a bottle again. Maps physical storage boxes into an interactive digital grid and generates customizable printable labels.*
* **Dynamic Grid Mapping:** Automatically arranges polishes by their `Location` coordinate (e.g. `1-A1` through `1-H8`). Unslotted storage locations (like `Display Shelf`) dynamically receive dedicated lists.
* **High-Res Printable Stickers:** Generates crisp, ink-friendly PNG labels designed to be affixed to the inside lids or exterior faces of physical drawers and acrylic boxes.
* **Deep Typography Customization:** Dozens of Google Fonts (Lobster, Caveat, Great Vibes), text alignment controls, custom background/border palettes, and auto-scaling font sizing.
* **Blackout Coordinates:** Allows structural dividers or broken physical slots to be flagged as "Unusable", blacking them out on both the on-screen grid and printed stickers.

### 🎯 2. Smart Color Matcher & Tagger (Port 8503 / 8504)
*Transform your physical vault into a searchable color studio. Extracts precise hex codes from swatch photos and finds color duplicates.*
* **Point-and-Click Hex Eyedropper:** Click directly on an uploaded swatch photo to sample and save Primary and Secondary hex colors directly to PostgreSQL.
* **Tolerance-Radius Dupe Search:** Pick a target color on an HSV color wheel and adjust tolerance distance to find exact twins or close substitutes in your existing collection.
* **Harmonic Color Theory Pairings:** Automatically calculates Complementary, Analogous, Triadic, and Tetradic pairings pulled strictly from polishes you already own.

### 🏆 3. Elo-Based Polish Ranker (Port 8505 / 8506)
*Definitively rank your collection using a competitive 1-on-1 Elo chess rating algorithm to discover your true holy grails.*
* **Wishlist & Filter Scoping:** Target specific subsets (e.g. "Summer Neons" or "Untried Creams") for focused voting gauntlets.
* **Smart Math (K-Factor 32):** Major rating swings occur during upsets, while expected favorites earn incremental gains.
* **Session Persistence & Merging:** Merge separate voting sessions to track taste evolution over time with delta movement indicators.
* **Portable HTML Archive:** Export standalone HTML leaderboards with Base64 images embedded directly inside for offline archival.

### 💅 4. Mani Logger & Digital Canvas (Port 8507 / 8508)
*An interactive digital manicure logbook with real-time timers and finger-by-finger formula mapping.*
* **10-Finger Digital Canvas:** Visually assign different polishes, toppers, and nail art designs to individual fingers on both hands.
* **Live Application Timers:** JavaScript coat timers tracking dry-times between base, color, and top coat layers.
* **Wear-Time Tracker:** Log longevity, chipping timelines, and upload high-resolution final manicure swatch photos.

### 🎨 5. Color Swatch Creator (Port 8509 / 8510)
*Design and compile physical swatch binder albums with vector PDF generation.*
* **200 DPI Vector PDF Engine:** Formatted for high-quality cardstock printing and direct swatch stick placement.
* **Multi-Book Management:** Organize swatches across multiple physical binders (e.g. "Indie Vault" vs "Main Creams").
* **Rainbow Chromatic Sorting:** Arranges swatches using perceptual HSV spectrum mathematics.

### 🏷️ 6. Precision Bottle Label Maker (Port 8511 / 8512)
*Industrial-grade label generation optimized for Brother P-Touch Cube Plus (PT-P710BT) 24mm continuous laminated tape.*
* **1-Bit Vector Graphics Engine (180 DPI):** Custom geometric polygon renderers for 22 nail finishes and half-star ratings to eliminate missing glyph boxes (`□`) on thermal print drivers.
* **Smart Dynamic Content Budgeting:** Automatically switches typography layouts from standard 55mm down to 34mm mini-labels based on bottle cap sizes.
* **Hybrid QR System:** Generates compact QR codes that bridge offline human-readable specs with instant online links to Koillection item profiles.
* **Archival 300 DPI Legend Sheets:** Compiles full 8.5" × 11" US Letter reference legends explaining all 22 finish symbols.

### 📖 7. Polish & Storage Directory Studio (Port 8513 / 8514)
*Publication-quality US Letter catalog generator designed for physical 3-ring desk binders and drawer index inserts.*
* **Multi-Dimensional Grouping:** Group and generate distinct section headers by **Color Spectrum** (natural rainbow ordering), **Brand**, **Storage Location**, **Finish Effect**, **Star Rating**, or **Acquisition Year**.
* **Smart Swatch Book Memory:** Decoupled JSON binder state tracking physical album pages. When new polishes arrive, it calculates and outputs **only the replacement last page** (filling its empty slots) plus any overflow sheets, saving paper and ink.
* **Crash-Proof HTML5 Base64 Pipeline:** Pure client-side data URI download buttons that bypass iframe WebSocket drops.
* **Dynamic Table Geometry:** Automatically recalculates column widths to fit 540 pt usable printable space regardless of which columns are toggled on/off.

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

### 🚀 Live FrankenPHP Development Mounts
* Solved the in-memory FrankenPHP worker disconnect by mounting Windows development directories directly to the active runtime path (`./src:/app/public/src` and `./templates:/app/public/templates`).
* Twig template and controller updates reflect immediately upon clearing the Symfony cache (`php bin/console cache:clear`) without requiring slow image rebuilds.

---

## 🌐 Port Allocation & Architecture

Both environments run concurrently on the same Docker host with strict network and port isolation:

| Service | Sandbox Port | Production Port | Internal Container Port |
| :--- | :--- | :--- | :--- |
| **Koillection Core (FrankenPHP)** | `8081` | `8144` | `80` |
| **App #1: Storage Grid (Locator)** | `8501` | `8502` | `8501` |
| **App #2: Color Matcher** | `8503` | `8504` | `8501` |
| **App #3: Elo Ranker** | `8505` | `8506` | `8501` |
| **App #4: Mani Logger** | `8507` | `8508` | `8501` |
| **App #5: Swatch Creator** | `8509` | `8510` | `8501` |
| **App #6: Bottle Label Maker** | `8511` | `8512` | `8501` |
| **App #7: Polish Directory** | `8513` | `8514` | `8501` |
| **PostgreSQL Database** | `5433` | `5432` | `5432` |
| **n8n Automation Engine** | `5679` | `5678` | `5678` |

---

## 🛠️ Sandbox Development Commands

```powershell
# Recreate modified micro-services
docker compose up -d --force-recreate koillection polish-directory

# Fast Symfony cache clear (2 seconds - live mounts active)
docker exec koillection-sandbox php bin/console cache:clear

# Full image baking (when adding new packages or assets)
docker buildx build -t my-custom-koillection .
```

---

## Upstream Documentation & License

Koillection is open-source software created by Benjamin Jonard, released under the [MIT License](LICENSE).
* Upstream Project: [https://github.com/koillection/koillection](https://github.com/koillection/koillection)
* Documentation & Wiki: [https://github.com/koillection/koillection/wiki](https://github.com/koillection/koillection/wiki)