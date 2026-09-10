<p align="center">
    <img src="https://user-images.githubusercontent.com/20560781/80213166-0e560e00-8639-11ea-944e-4f79fdbcef55.png" width="75" height="75">
</p>

<p align="center">
    <img src="https://img.shields.io/github/v/release/koillection/koillection" />
    <img src="https://img.shields.io/github/license/koillection/koillection" />    
    <img src="https://img.shields.io/github/actions/workflow/status/koillection/koillection/ci.yml" />
    <img src="https://img.shields.io/scrutinizer/g/koillection/koillection/1.4" />    
</p>
<p align="center">
    <img src="https://img.shields.io/packagist/php-v/koillection/koillection" />
    <img src="https://img.shields.io/badge/postgresql->=10.0-blue" />            
    <img src="https://img.shields.io/badge/mariadb->=10.0-blue" />
    <img src="https://img.shields.io/badge/mysql->=8.0-blue" />
<p>

# 💅 Koillection: The Ultimate Nail Polish Vault

*This is a highly customized, full-stack fork of the original [Koillection](https://github.com/benjaminjonard/koillection) app. It has been specifically engineered for nail polish collectors, integrating custom Python-powered tools to track physical storage, extract exact color hex codes from photos, and find color dupes.*

## ✨ Exclusive Nail Polish Features

### 🗺️ 1. Storage Grid Visualizer & Sticker Generator
*Never lose a bottle again. This custom Python/Streamlit app maps your physical storage boxes into a digital grid and generates highly customizable, printable labels.*
* **Dynamic Digital Grid:** Automatically places your polishes into a visual grid based on their `Location` data field (e.g., `1-A1`). Simple text locations (like `Display Shelf`) automatically get their own lists!
* **Printable Box Stickers:** Generates high-resolution, ink-friendly PNG labels designed to be printed and taped to the inside or outside of your physical boxes.
* **Ultimate Customization:** Choose from dozens of decorative Google Fonts (like Lobster, Caveat, and Great Vibes), adjust text alignment, and customize all colors (background, grid lines, and text) via a dedicated pop-up UI.
* **Smart Auto-Fitting:** The sticker heading automatically calculates and scales its font size to perfectly fill the available banner space.
* **Blackout Spaces:** Have a physically broken slot or a structural divider in your drawer? Mark specific coordinates as "Unusable" to black them out on the digital grid and sticker.

### 🎨 2. Smart Color Matcher & Tagger
*Turn your collection into a searchable color palette. This embedded Streamlit app extracts exact hex codes from your photos and searches for dupes.*
* **Point-and-Click Extraction:** Go to the **🏷️ Tag Existing Polish** tab, click directly on a polish's uploaded photo, and instantly extract the exact Primary (and Secondary) color hex codes.
* **Direct Database Integration:** Saves the extracted hex codes directly to your PostgreSQL database, ensuring your data is always in sync with the core app.
* **Dupe Finder:** Go to the **🔍 Search Collection** tab, pick a target color from a color wheel, and adjust the **Tolerance Radius** slider. The app will instantly search your entire vault to find exact matches or similar shades!
* **Nail Art Pairings:** Select a base polish, and the app uses mathematical color theory (HSV conversion) to suggest the perfect Complementary, Analogous, and Triadic matches from your actual collection.

### 🏆 3. Elo-Based Polish Ranker
*Definitively rank your nail polishes using a competitive 1-on-1 Elo rating system to discover your true favorites.*
* **Wishlist Integration:** Pulls directly from your Koillection Wishlists (e.g., "Summer Favorites" or "Untrieds") to create a focused ranking session.
* **1-on-1 Matchups:** Pits polishes against each other in head-to-head visual battles. Just click the picture of the one you prefer, and the algorithm handles the rest!
* **Smart Math (Elo System):** Uses a K-Factor of 32 to calculate expected outcomes. Upsets (underdogs beating heavyweights) result in massive point swings, while expected wins yield minor adjustments.
* **Session Merging:** Save your ranking sessions and merge them later to see how your preferences change over time, complete with up/down movement indicators.
* **Portable HTML Exports:** Download your final leaderboard as a standalone HTML file with Base64 images embedded directly inside, perfect for sharing or archiving!

### ⚡ 4. Bulk Actions (List View)
*Manage massive hauls with ease using the custom action bar integrated directly into the PHP/Twig core.*
* **Multi-Select:** Convenient checkboxes added to the main list view.
* **Bulk Duplicate:** Instantly clone multiple items at once. This is a lifesaver when adding an entire 10-piece collection from the same brand where only the name and color change!
* **Bulk Move & Delete:** Quickly reorganize your vault or clean up your database with a single click.

---

Koillection is a self-hosted collection manager created to keep track of physical (mostly) collections of any kind like books, DVDs, stamps, games... 
Koillection is meant to be used for any kind of collections and doesn't come with pre-built metadata download. But you can tailor your own HTML scraper, or you can add your own metadata freely.
    
You can find detailed information in the <a href="https://github.com/koillection/koillection/wiki">wiki</a> (under construction)

## Installation
See the <a href="https://github.com/koillection/koillection/wiki/Installation">Installation page</a> in the wiki

## Updating
See the <a href="https://github.com/koillection/koillection/wiki/Updating">Updating page</a> in the wiki

## Scraping
See the <a href="https://github.com/koillection/koillection/wiki/Scraping">Scraping page</a> in the wiki

## Demo

Gitpod will run a new and temporary instance for you.

When Gitpod has finished loading, select :

    More actions -> Open in browser


[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/koillection/koillection-gitpod)

## Screenshots

<p align="center">
    <img width="400px" src="https://user-images.githubusercontent.com/20560781/168048241-cfcb71ce-c296-4f1b-bbb8-ecfea1e31048.png">
    <img width="400px" src="https://user-images.githubusercontent.com/20560781/168048246-53e991d1-77e9-4397-80c4-f1aa82504068.png">
</p>

<p align="center">
    <img height="215px" src="https://user-images.githubusercontent.com/20560781/168049067-dbac37b1-1150-4be5-ab95-f784d606f300.png">
    <img height="215px" src="https://user-images.githubusercontent.com/20560781/168049077-efac8291-4f5c-48d9-b2fa-d65a51842d25.png">
    <img height="215px" src="https://user-images.githubusercontent.com/20560781/177819056-8f110583-08ae-42b6-9e32-3e3db4a3923a.png">
    <img height="215px" src="https://user-images.githubusercontent.com/20560781/177818960-6e988a73-67e0-47bc-a377-0c92c530d423.png">
    <img height="215px" src="https://user-images.githubusercontent.com/20560781/168049088-2cda1da5-6e55-4800-918f-001fad6559a6.png">
    <img height="215px" src="https://user-images.githubusercontent.com/20560781/168049095-5f26e2c6-7218-42ae-bde1-4b32abae7e35.png">
    <img height="215px" src="https://user-images.githubusercontent.com/20560781/177819233-f3aa62c4-ce48-4184-9864-d40708367dbf.png">
    <img height="215px" src="https://user-images.githubusercontent.com/20560781/177819299-048ea3ad-fa0a-463d-b5b7-1607773553e4.png">
</p>

## Warning

Please back up your database, especially when updating to a new version. I do my best to test new versions, especially when they contains data migrations but some edge cases may escape my vigilance.

Please do back up your database.

## Support Koillection

There are a few things you can do to support Koillection :
    
* If you like Koillection please consider leaving a ⭐, it gives additional motivation to continue working on the project
* Report any bug or error you see
* English is not my first language, it would be a huge help if you could report any mistakes in both Koillection or the wiki.

You can contribute and edit translations here: https://crowdin.com/project/koillection. 
If you wish to contribute to a new language, please open a discussion on GitHub or Crowdin and I'll gladly add it. 
You are also welcome if you want to proofread existing translations.

### Translations status
<!-- CROWDIN-TRANSLATIONS-PROGRESS-ACTION-START -->


#### Available

<table><tr><td align="center" valign="top"><img width="30px" height="30px" title="Dutch" alt="Dutch" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/nl.png"></div><div align="center" valign="top">100%</td><td align="center" valign="top"><img width="30px" height="30px" title="English" alt="English" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/en.png"></div><div align="center" valign="top">100%</td><td align="center" valign="top"><img width="30px" height="30px" title="French" alt="French" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/fr.png"></div><div align="center" valign="top">100%</td><td align="center" valign="top"><img width="30px" height="30px" title="German" alt="German" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/de.png"></div><div align="center" valign="top">99%</td><td align="center" valign="top"><img width="30px" height="30px" title="Italian" alt="Italian" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/it.png"></div><div align="center" valign="top">99%</td><td align="center" valign="top"><img width="30px" height="30px" title="Polish" alt="Polish" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/pl.png"></div><div align="center" valign="top">99%</td><td align="center" valign="top"><img width="30px" height="30px" title="Portuguese" alt="Portuguese" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/pt-PT.png"></div><div align="center" valign="top">99%</td><td align="center" valign="top"><img width="30px" height="30px" title="Portuguese, Brazilian" alt="Portuguese, Brazilian" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/pt-BR.png"></div><div align="center" valign="top">99%</td><td align="center" valign="top"><img width="30px" height="30px" title="Spanish" alt="Spanish" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/es-ES.png"></div><div align="center" valign="top">99%</td><td align="center" valign="top"><img width="30px" height="30px" title="Russian" alt="Russian" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/ru.png"></div><div align="center" valign="top">97%</td></tr><tr><td align="center" valign="top"><img width="30px" height="30px" title="Chinese Simplified" alt="Chinese Simplified" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/zh-CN.png"></div><div align="center" valign="top">95%</td></table>

#### In progress

<table><tr><td align="center" valign="top"><img width="30px" height="30px" title="Danish" alt="Danish" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/da.png"></div><div align="center" valign="top">75%</td><td align="center" valign="top"><img width="30px" height="30px" title="Turkish" alt="Turkish" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/tr.png"></div><div align="center" valign="top">30%</td><td align="center" valign="top"><img width="30px" height="30px" title="Ukrainian" alt="Ukrainian" src="https://raw.githubusercontent.com/benjaminjonard/crowdin-translations-progress-action/1.0/flags/uk.png"></div><div align="center" valign="top">2%</td></tr></table>
<!-- CROWDIN-TRANSLATIONS-PROGRESS-ACTION-END -->

## Licensing
Koillection is an Open Source software, released under the MIT License.