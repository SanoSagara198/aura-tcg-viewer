# AURA! TCG — Comic Edition Card Viewer (Streamlit)

Interactive Streamlit web app for browsing, filtering, analyzing, and exporting all **1,050 original Aura TCG cards** across **Alpha**, **Beta**, and **Delta** sets in the **Comic Edition** card frame.

## Features
- **Comic-Book Card Gallery**: Heavy ink outlines, Ben-Day halftone backdrops, diagonal action panels, tilted narration strips, yellow flavor caption tags, and split `ATK` / `DEF` impact badges.
- **Click-to-Flip 3D Card Backs**: Click any card (or toggle **Flip All Backs**) to inspect the **AURA!** comic card back.
- **Live Filtering & Sorting**: Search name/type/rules/flavor, filter by Set, Color, Card Type, and Rarity, and sort by Set Order, Energy Cost, Name, or ATK.
- **Set Analytics & Energy Curve**: Visual breakdown of color distribution, energy curve, rarity split, and card types.
- **CSV Table Inspector & Export**: Browse the filtered cards in a data table and download the filtered CSV.

## Run Locally
```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**.
2. Select this repository, branch `main`, and main file path `app.py`.
3. Click **Deploy!**
