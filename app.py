from __future__ import annotations

import base64
import html
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="AURA! TCG — Comic Edition Card Viewer & Deck Editor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).parent
# Streamlit Cloud can keep a running server with static serving disabled after a deploy.
# Use the versioned public repository assets so the hosted and local views agree.
ASSET_BASE = "https://raw.githubusercontent.com/SanoSagara198/aura-tcg-viewer/9e8ca434c22fed899acc0385468d15639e8a91bb/static/"
CSV_FILES = [
    ("Alpha", "A", ROOT / "aura_alpha_set.csv"),
    ("Beta", "B", ROOT / "aura_beta_set.csv"),
    ("Delta", "D", ROOT / "aura_delta_set.csv"),
]

# Exact Basic Lands from src/shared/BasicLands.luau (unlimited copies in any deck)
BASIC_LANDS = [
    {
        "id": "L-W", "set": "Core", "set_number": 1, "name": "Sunfield", "color": "Land",
        "rarity": "common", "energy_cost": "", "card_type": "Basic Land — Sunfield",
        "power": "", "toughness": "", "rules_text": "{TURN}: Add {W} to your Energy pool.",
        "flavor_text": "Where the dawn first touches the world.", "basic": True, "produces": "W",
    },
    {
        "id": "L-U", "set": "Core", "set_number": 2, "name": "Tidepool", "color": "Land",
        "rarity": "common", "energy_cost": "", "card_type": "Basic Land — Tidepool",
        "power": "", "toughness": "", "rules_text": "{TURN}: Add {U} to your Energy pool.",
        "flavor_text": "Every current remembers where it came from.", "basic": True, "produces": "U",
    },
    {
        "id": "L-B", "set": "Core", "set_number": 3, "name": "Gloomfen", "color": "Land",
        "rarity": "common", "energy_cost": "", "card_type": "Basic Land — Gloomfen",
        "power": "", "toughness": "", "rules_text": "{TURN}: Add {B} to your Energy pool.",
        "flavor_text": "Nothing sinks here that doesn't come back changed.", "basic": True, "produces": "B",
    },
    {
        "id": "L-R", "set": "Core", "set_number": 4, "name": "Cinderpeak", "color": "Land",
        "rarity": "common", "energy_cost": "", "card_type": "Basic Land — Cinderpeak",
        "power": "", "toughness": "", "rules_text": "{TURN}: Add {R} to your Energy pool.",
        "flavor_text": "The mountain never stopped burning; it just learned patience.", "basic": True, "produces": "R",
    },
    {
        "id": "L-G", "set": "Core", "set_number": 5, "name": "Wildgrove", "color": "Land",
        "rarity": "common", "energy_cost": "", "card_type": "Basic Land — Wildgrove",
        "power": "", "toughness": "", "rules_text": "{TURN}: Add {G} to your Energy pool.",
        "flavor_text": "Roots older than any kingdom.", "basic": True, "produces": "G",
    },
]

COLOR_TO_BASIC_ID = {
    "White": "L-W",
    "Blue": "L-U",
    "Black": "L-B",
    "Red": "L-R",
    "Green": "L-G",
}

COLOR_CHIP_STYLE = {
    "White": ("#f5e6a8", "#ffffff"),
    "Blue": ("#2563eb", "#ffffff"),
    "Black": ("#4c1d95", "#ffffff"),
    "Red": ("#dc2626", "#ffffff"),
    "Green": ("#16a34a", "#ffffff"),
    "Multicolor": ("linear-gradient(135deg, #fde047, #ec4899)", "#ffffff"),
    "Artifact": ("#64748b", "#ffffff"),
    "Land": ("#b45309", "#ffffff"),
}

COLOR_SOLID_HEX = {
    "White": "#f5e6a8",
    "Blue": "#2563eb",
    "Black": "#5b21b6",
    "Red": "#dc2626",
    "Green": "#16a34a",
    "Multicolor": "#ec4899",
    "Artifact": "#64748b",
    "Land": "#b45309",
}

COLOR_CARD_TONE = {
    "White": ("#fff6cc", "#eab308"),
    "Blue": ("#38bdf8", "#1d4ed8"),
    "Black": ("#7c3aed", "#2e1065"),
    "Red": ("#fb7185", "#dc2626"),
    "Green": ("#4ade80", "#15803d"),
    "Artifact": ("#cbd5e1", "#475569"),
    "Land": ("#fdba74", "#9a3412"),
}

SYM_TO_COLOR = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}

MIN_DECK = 40
MAX_DECK = 200
MAX_COPIES = 4
OPENING_HAND = 7

@st.cache_data(show_spinner=False)
def build_ui_texture_css() -> str:
    """Base64-encode the Roblox 9-slice and softbrush UI PNGs from assets/ into CSS custom properties."""
    assets_dir = ROOT / "assets"
    files = {
        "--tex-frame-9slice": "brush_frame_9slice.png",
        "--tex-header-brush": "brush_header_banner.png",
        "--tex-rules-wash": "brush_rules_wash_v2.png",
        "--tex-aura-burst": "brush_aura_burst.png",
        "--tex-halftone": "comic_halftone_overlay.png",
    }
    decls: list[str] = []
    for var_name, filename in files.items():
        path = assets_dir / filename
        if path.exists():
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            decls.append(f'{var_name}: url("data:image/png;base64,{b64}");')
        else:
            decls.append(f"{var_name}: none;")
    return "<style>:root { " + " ".join(decls) + " }</style>"


COMIC_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Barlow+Condensed:ital,wght@0,600;0,700;0,800;1,700&family=Chakra+Petch:ital,wght@0,500;0,600;0,700;1,600&family=Comic+Neue:ital,wght@0,700;1,700&family=Montserrat:wght@500;700;800&family=Merriweather:ital@1&display=swap');
:root { --ink: #0a0b10; --paper: #fffdf4; --yellow: #ffe24a; }
.stApp {
  background-color: #11131b;
  background-image: radial-gradient(rgba(255, 226, 74, 0.06) 1.5px, transparent 1.5px), radial-gradient(circle at top, #1f2538 0%, #0d0f17 65%);
  background-size: 18px 18px, 100% 100%;
  font-family: 'Chakra Petch', 'Segoe UI', system-ui, sans-serif;
}
.block-container { max-width: 100% !important; padding-left: 2rem !important; padding-right: 2rem !important; }
button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  color: #0a0b10 !important; font-weight: 800 !important;
  border: 2.5px solid #0a0b10 !important; box-shadow: 3px 3px 0 #0a0b10 !important;
}
button[kind="primary"] *, button[data-testid="stBaseButton-primary"] * { color: #0a0b10 !important; }
/* ==================== LEGIBLE COLOR-CODED MULTISELECT CHIPS (BaseWeb + React Aria) ==================== */
[data-tag], [data-baseweb="tag"] {
  background: #263047 !important;
  background-color: #263047 !important;
  border: 2px solid #0a0b10 !important;
  box-shadow: 2px 2px 0 #0a0b10 !important;
  color: #ffffff !important;
  font-weight: 800 !important;
}
[data-tag] *, [data-baseweb="tag"] * {
  color: #ffffff !important;
  fill: #ffffff !important;
  text-shadow: -1.3px -1.3px 0 #000, 1.3px -1.3px 0 #000, -1.3px 1.3px 0 #000, 1.3px 1.3px 0 #000, 0 1.8px 0 #000 !important;
}
[data-tag][aria-label="White"],      [data-tag]:has([title="White"]),      [data-baseweb="tag"]:has([title="White"]),      [data-baseweb="tag"][aria-label^="White,"]      { background: #f5e6a8 !important; }
[data-tag][aria-label="Blue"],       [data-tag]:has([title="Blue"]),       [data-baseweb="tag"]:has([title="Blue"]),       [data-baseweb="tag"][aria-label^="Blue,"]       { background: #2563eb !important; }
[data-tag][aria-label="Black"],      [data-tag]:has([title="Black"]),      [data-baseweb="tag"]:has([title="Black"]),      [data-baseweb="tag"][aria-label^="Black,"]      { background: #4c1d95 !important; }
[data-tag][aria-label="Red"],        [data-tag]:has([title="Red"]),        [data-baseweb="tag"]:has([title="Red"]),        [data-baseweb="tag"][aria-label^="Red,"]        { background: #dc2626 !important; }
[data-tag][aria-label="Green"],      [data-tag]:has([title="Green"]),      [data-baseweb="tag"]:has([title="Green"]),      [data-baseweb="tag"][aria-label^="Green,"]      { background: #16a34a !important; }
[data-tag][aria-label="Artifact"],   [data-tag]:has([title="Artifact"]),   [data-baseweb="tag"]:has([title="Artifact"]),   [data-baseweb="tag"][aria-label^="Artifact,"]   { background: #64748b !important; }
[data-tag][aria-label="Land"],       [data-tag]:has([title="Land"]),       [data-baseweb="tag"]:has([title="Land"]),       [data-baseweb="tag"][aria-label^="Land,"]       { background: #b45309 !important; }
[data-tag][aria-label="Multicolor"], [data-tag]:has([title="Multicolor"]), [data-baseweb="tag"]:has([title="Multicolor"]), [data-baseweb="tag"][aria-label^="Multicolor,"] { background: linear-gradient(135deg, #fde047, #ec4899) !important; }
[data-tag][aria-label="common"],     [data-tag]:has([title="common"]),     [data-baseweb="tag"]:has([title="common"]),     [data-baseweb="tag"][aria-label^="common,"]     { background: #334155 !important; }
[data-tag][aria-label="uncommon"],   [data-tag]:has([title="uncommon"]),   [data-baseweb="tag"]:has([title="uncommon"]),   [data-baseweb="tag"][aria-label^="uncommon,"]   { background: #0284c7 !important; }
[data-tag][aria-label="rare"],       [data-tag]:has([title="rare"]),       [data-baseweb="tag"]:has([title="rare"]),       [data-baseweb="tag"][aria-label^="rare,"]       { background: #d97706 !important; }
.selected-filter-pane {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 10px 14px;
  border-radius: 10px; border: 3.5px solid #0a0b10; box-shadow: 5px 5px 0 #0a0b10;
  margin: 4px 0 14px;
}
.selected-filter-title {
  font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 0.92rem;
  letter-spacing: 0.08em; text-transform: uppercase; color: #ffffff; margin-right: 4px;
  text-shadow: -1.4px -1.4px 0 #000, 1.4px -1.4px 0 #000, -1.4px 1.4px 0 #000, 1.4px 1.4px 0 #000, 0 2px 0 #000;
}
.color-summary-bar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 4px 0 12px;
}
.color-pill-stat {
  display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px;
  border-radius: 6px; border: 2.5px solid #0a0b10; box-shadow: 2.5px 2.5px 0 #0a0b10;
  font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 0.88rem;
  letter-spacing: 0.05em; text-transform: uppercase; color: #ffffff;
  text-shadow: -1.3px -1.3px 0 #000, 1.3px -1.3px 0 #000, -1.3px 1.3px 0 #000, 1.3px 1.3px 0 #000, 0 2px 0 #000;
}
.aura-banner {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px;
  background: #1a1e2b; border: 4px solid var(--ink); box-shadow: 6px 6px 0 var(--ink);
  border-radius: 10px; padding: 14px 20px; margin-bottom: 18px;
}
.aura-banner-left { display: flex; align-items: center; gap: 16px; }
.aura-logo {
  font-family: 'Bangers', Impact, sans-serif; font-size: 2.2rem; letter-spacing: 0.08em;
  color: var(--yellow); background: #e11d48; padding: 4px 16px 2px;
  border: 3px solid var(--ink); box-shadow: 4px 4px 0 var(--ink);
  transform: skewX(-7deg) rotate(-1.5deg); text-shadow: 2px 2px 0 var(--ink); line-height: 1.05;
}
.aura-title h1 {
  font-family: 'Barlow Condensed', sans-serif; font-size: 1.45rem; font-weight: 800;
  text-transform: uppercase; letter-spacing: 0.08em; color: #f3f5fa; margin: 0; line-height: 1.15;
}
.aura-title p { font-size: 0.86rem; color: #a6afc4; margin: 3px 0 0; }
.aura-tip {
  background: var(--yellow); color: var(--ink); border: 2.5px solid var(--ink);
  box-shadow: 3px 3px 0 var(--ink); font-family: 'Barlow Condensed', sans-serif;
  font-weight: 800; font-size: 0.85rem; letter-spacing: 0.06em; text-transform: uppercase;
  padding: 5px 12px; transform: skewX(-5deg);
}
.aura-grid {
  width: 100%; display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 1.85rem 1.45rem; padding: 10px 4px 28px;
}
.card-scene {
  display: block; perspective: 1100px; min-height: 422px; cursor: pointer; user-select: none;
}
.flip-chk { display: none !important; }
.card-flipper {
  position: relative; width: 100%; height: 100%; min-height: 422px;
  transform-style: preserve-3d; transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1);
}
.flip-chk:checked ~ .card-flipper { transform: rotateY(180deg); }
.card-scene:hover .card-flipper { transform: translate(-3px, -5px); }
.card-scene:hover .flip-chk:checked ~ .card-flipper { transform: translate(-3px, -5px) rotateY(180deg); }
.card-face {
  position: relative; width: 100%; min-height: 422px;
  backface-visibility: hidden; -webkit-backface-visibility: hidden;
  border-radius: 12px; border: 4px solid var(--ink); box-shadow: 7px 8px 0 var(--ink);
  transition: box-shadow 0.14s ease;
  display: flex; flex-direction: column; overflow: visible; box-sizing: border-box;
}
.card-scene.compact, .card-scene.compact .card-flipper, .card-scene.compact .card-face {
  min-height: 358px;
}
.card-scene.compact .art-panel { height: 112px; }
.card-scene.compact .card-name { font-size: 1.12rem; }
.card-scene.compact .rules-lines { font-size: 0.77rem; line-height: 1.26; }
.card-scene.compact .flavor-caption { font-size: 0.7rem; }
.card-scene.compact .back-logo { font-size: 2.6rem; }
.card-scene:hover .card-face { box-shadow: 11px 13px 0 var(--ink); }
.card-front {
  --c-bg1: #fff3b0; --c-bg2: #f4c430; --c-art1: #fef08a; --c-art2: #d97706;
  --c-tag-bg: #ffe24a; --c-tag-ink: #0a0b10; --c-dot: rgba(10, 11, 16, 0.14);
  padding: 10px 10px 12px; background-color: var(--c-bg1);
  background-image: radial-gradient(var(--c-dot) 1.6px, transparent 1.6px), linear-gradient(155deg, var(--c-bg1) 0%, var(--c-bg2) 100%);
  background-size: 9px 9px, 100% 100%; color: var(--ink);
}
.card-front.White      { --c-bg1: #fff6cc; --c-bg2: #eab308; --c-art1: #fef9c3; --c-art2: #ca8a04; --c-tag-bg: #ffe24a; }
.card-front.Blue       { --c-bg1: #38bdf8; --c-bg2: #1d4ed8; --c-art1: #7dd3fc; --c-art2: #1e3a8a; --c-tag-bg: #ffe24a; --c-dot: rgba(255,255,255,0.16); }
.card-front.Black      { --c-bg1: #7c3aed; --c-bg2: #2e1065; --c-art1: #a78bfa; --c-art2: #1e1b4b; --c-tag-bg: #e879f9; --c-dot: rgba(255,255,255,0.14); }
.card-front.Red        { --c-bg1: #fb7185; --c-bg2: #dc2626; --c-art1: #fdba74; --c-art2: #991b1b; --c-tag-bg: #ffe24a; --c-dot: rgba(10,11,16,0.16); }
.card-front.Green      { --c-bg1: #4ade80; --c-bg2: #15803d; --c-art1: #bef264; --c-art2: #14532d; --c-tag-bg: #ffe24a; --c-dot: rgba(10,11,16,0.16); }
.card-front.Artifact   { --c-bg1: #cbd5e1; --c-bg2: #475569; --c-art1: #e2e8f0; --c-art2: #334155; --c-tag-bg: #38bdf8; --c-dot: rgba(10,11,16,0.15); }
.card-front.Land       { --c-bg1: #fdba74; --c-bg2: #9a3412; --c-art1: #fde68a; --c-art2: #78350f; --c-tag-bg: #fef08a; --c-dot: rgba(10,11,16,0.16); }
.card-front.Multicolor { --c-bg1: #fde047; --c-bg2: #ec4899; --c-art1: #f9a8d4; --c-art2: #7e22ce; --c-tag-bg: #ffe24a; --c-dot: rgba(255,255,255,0.2); }
.card-front.rarity-rare::before {
  content: ""; position: absolute; inset: 3px; border-radius: 7px;
  border: 2.5px dashed rgba(255, 250, 205, 0.72); pointer-events: none; z-index: 5;
}
/* Roblox 9-slice softbrush perimeter & comic halftone layers */
.brush-halftone {
  position: absolute; inset: 0; border-radius: 10px; pointer-events: none; z-index: 1;
  background-image: var(--tex-halftone); background-size: 100% 100%; background-repeat: no-repeat;
  opacity: 0.28;
}
.brush-frame-9slice {
  position: absolute; inset: -3px; pointer-events: none; z-index: 6;
  border-style: solid; border-width: 24px;
  border-image-source: var(--tex-frame-9slice);
  border-image-slice: 56;
  border-image-repeat: stretch;
  filter: drop-shadow(0 0 2px rgba(0, 0, 0, 0.45));
}
.comic-header { display: flex; align-items: center; gap: 7px; margin-bottom: 8px; position: relative; z-index: 3; }
.energy-burst {
  display: inline-flex; align-items: center; gap: 3px; background: var(--ink);
  border: 2.5px solid var(--ink); box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.45);
  padding: 3px 5px; border-radius: 8px; transform: rotate(-3deg); flex-shrink: 0;
}
.energy-burst.empty { display: none; }
.pip {
  display: inline-flex; align-items: center; justify-content: center; width: 21px; height: 21px;
  border-radius: 50%; font-family: 'Barlow Condensed', Impact, sans-serif; font-size: 0.84rem; font-weight: 800;
  border: 2px solid var(--ink); box-shadow: inset -1px -2px 0 rgba(0, 0, 0, 0.28), inset 1px 1px 0 rgba(255, 255, 255, 0.55);
  line-height: 1; color: #ffffff;
  text-shadow: -1.1px -1.1px 0 #000, 1.1px -1.1px 0 #000, -1.1px 1.1px 0 #000, 1.1px 1.1px 0 #000;
}
.pip-W { background: #f5e6a8; }
.pip-U { background: #2563eb; }
.pip-B { background: #6d28d9; }
.pip-R { background: #dc2626; }
.pip-G { background: #16a34a; }
.pip-N { background: #94a3b8; }
.pip-T { background: #f59e0b; font-size: 0.78rem; }
.title-plate {
  flex: 1; min-width: 0; background: transparent;
  background-image: var(--tex-header-brush); background-size: 100% 100%; background-repeat: no-repeat;
  border: none; outline: none; box-shadow: none;
  padding: 6px 14px 5px; transform: skewX(-4deg);
  filter: drop-shadow(2px 3px 0 rgba(0, 0, 0, 0.45));
}
.card-name {
  display: block; font-family: 'Bangers', Impact, sans-serif; font-size: 1.28rem;
  letter-spacing: 0.055em; line-height: 1.05; color: #ffffff;
  text-shadow: -1.5px -1.5px 0 #000, 1.5px -1.5px 0 #000, -1.5px 1.5px 0 #000, 1.5px 1.5px 0 #000, 2px 2px 0 #000;
  transform: skewX(6deg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.art-panel {
  position: relative; z-index: 2; height: 146px; border: 3px solid var(--ink); border-radius: 6px;
  background: var(--tex-aura-burst) center/135% 135% no-repeat, repeating-conic-gradient(from 0deg at 50% 48%, rgba(255, 255, 255, 0.16) 0deg 8deg, transparent 8deg 18deg), radial-gradient(circle at 50% 48%, var(--c-art1) 0%, var(--c-art2) 78%, #090b12 100%);
  overflow: hidden; box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.25);
  display: flex; align-items: center; justify-content: center; margin-bottom: -14px;
  clip-path: polygon(0 0, 100% 0, 100% 89%, 0 100%);
}
.art-burst {
  width: 82px; height: 82px; background: rgba(255, 255, 255, 0.24);
  border: 3px solid rgba(10, 11, 16, 0.65); transform: rotate(45deg);
  display: flex; align-items: center; justify-content: center; box-shadow: 4px 4px 0 rgba(10, 11, 16, 0.35);
}
.art-burst span {
  transform: rotate(-45deg); font-family: 'Bangers', sans-serif; font-size: 0.96rem;
  letter-spacing: 0.08em; color: #ffffff; text-align: center; line-height: 1.05;
  text-shadow: -1.3px -1.3px 0 #000, 1.3px -1.3px 0 #000, -1.3px 1.3px 0 #000, 1.3px 1.3px 0 #000;
}
.annex-stamp {
  position: absolute; top: 7px; right: 7px; width: 26px; height: 26px; border-radius: 50%;
  background: var(--yellow); color: var(--ink); border: 2.5px solid var(--ink);
  box-shadow: 2px 2px 0 var(--ink); font-family: 'Bangers', sans-serif; font-size: 1rem;
  display: flex; align-items: center; justify-content: center; z-index: 2;
}
.deck-count-pill {
  position: absolute; top: 7px; left: 7px; padding: 2px 8px; border-radius: 999px;
  background: #16a34a; color: #ffffff; border: 2.5px solid var(--ink);
  box-shadow: 2px 2px 0 var(--ink); font-family: 'Barlow Condensed', sans-serif;
  font-weight: 800; font-size: 0.8rem; letter-spacing: 0.04em; z-index: 2;
  text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
}
.comic-type-strip {
  position: relative; z-index: 4; display: flex; justify-content: space-between; align-items: center; gap: 6px;
  margin: 0 4px 8px; padding: 4px 9px; background: var(--c-tag-bg); color: var(--c-tag-ink);
  border: 3px solid var(--ink); box-shadow: 4px 4px 0 var(--ink); transform: skewX(-6deg) rotate(-1deg);
}
.comic-type-strip > * { transform: skewX(6deg); }
.type-text { font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; }
.rarity-stamp {
  font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 0.72rem;
  letter-spacing: 0.07em; text-transform: uppercase; padding: 1px 7px;
  border: 2px solid var(--ink); border-radius: 3px; box-shadow: 2px 2px 0 var(--ink); color: #ffffff;
  text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
}
.rarity-stamp.common   { background: #334155; }
.rarity-stamp.uncommon { background: #0284c7; }
.rarity-stamp.rare     { background: #d97706; }
.comic-rules-box {
  position: relative; z-index: 3; flex: 1; background-color: transparent;
  background-image: var(--tex-rules-wash);
  background-size: 100% 100%; background-repeat: no-repeat;
  border: none; border-radius: 6px;
  box-shadow: none; padding: 13px 14px 12px;
  display: flex; flex-direction: column; justify-content: space-between; gap: 7px; color: #14161f;
}
.rules-lines {
  font-family: 'Comic Neue', 'Chakra Petch', sans-serif; font-size: 0.83rem; font-weight: 700;
  line-height: 1.32; display: flex; flex-direction: column; gap: 5px;
}
.rules-lines p { margin: 0; color: #14161f; }
.rules-lines .pip { width: 17px; height: 17px; font-size: 0.68rem; vertical-align: -2px; margin: 0 1px; }
.rules-lines .kw { font-family: 'Barlow Condensed', sans-serif; text-transform: uppercase; letter-spacing: 0.03em; color: #b91c1c; font-weight: 800; }
.rules-lines .rem { font-weight: 700; color: #475569; font-style: italic; }
.flavor-caption {
  background: #fef08a; border: 2px solid var(--ink); box-shadow: 2px 2px 0 var(--ink);
  padding: 4px 7px; font-family: 'Comic Neue', serif; font-style: italic; font-weight: 700;
  font-size: 0.74rem; line-height: 1.25; color: #1c1917; transform: rotate(-0.6deg);
}
.comic-footer { display: flex; justify-content: space-between; align-items: flex-end; margin-top: 8px; gap: 8px; position: relative; z-index: 4; }
.issue-stamp {
  background: var(--ink); color: #ffffff; font-family: 'Barlow Condensed', sans-serif;
  font-weight: 800; font-size: 0.74rem; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 3px 8px; border-radius: 3px; border: 2px solid rgba(255, 255, 255, 0.35); box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.5);
}
.stat-cluster { display: flex; align-items: center; gap: 5px; margin-bottom: -4px; margin-right: -2px; }
.stat-badge {
  display: inline-flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 38px; padding: 2px 7px 1px; border: 3px solid var(--ink);
  box-shadow: 3px 3px 0 var(--ink); line-height: 1; transform: skewX(-7deg); color: #ffffff;
  text-shadow: -1.3px -1.3px 0 #000, 1.3px -1.3px 0 #000, -1.3px 1.3px 0 #000, 1.3px 1.3px 0 #000;
}
.stat-badge .lbl { font-family: 'Barlow Condensed', sans-serif; font-size: 0.56rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; transform: skewX(7deg); }
.stat-badge .val { font-family: 'Bangers', Impact, sans-serif; font-size: 1.32rem; letter-spacing: 0.04em; transform: skewX(7deg); }
.stat-pow { background: #ef4444; }
.stat-tgh { background: #0ea5e9; }
.card-back {
  position: absolute; inset: 0; transform: rotateY(180deg); background-color: #13182b;
  background-image: repeating-conic-gradient(from 8deg at 50% 50%, rgba(255, 226, 74, 0.1) 0deg 9deg, transparent 9deg 20deg), radial-gradient(rgba(255, 255, 255, 0.11) 1.5px, transparent 1.5px), radial-gradient(circle at 50% 50%, #2b3564 0%, #0f1324 72%);
  background-size: 100% 100%, 10px 10px, 100% 100%; padding: 14px; align-items: center; justify-content: space-between; overflow: hidden;
}
.back-inner {
  width: 100%; height: 100%; border: 3.5px solid var(--yellow); outline: 3px solid var(--ink);
  border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 16px 12px;
}
.back-issue {
  background: var(--yellow); color: var(--ink); border: 2.5px solid var(--ink);
  box-shadow: 3px 3px 0 var(--ink); font-family: 'Barlow Condensed', sans-serif;
  font-weight: 800; font-size: 0.78rem; letter-spacing: 0.1em; padding: 2px 10px; transform: skewX(-6deg);
}
.back-emblem { display: flex; flex-direction: column; align-items: center; gap: 14px; }
.back-logo {
  font-family: 'Bangers', Impact, sans-serif; font-size: 3.3rem; letter-spacing: 0.08em;
  color: var(--yellow); -webkit-text-stroke: 2.5px var(--ink);
  text-shadow: 5px 5px 0 #e11d48, 8px 8px 0 var(--ink); transform: rotate(-6deg) skewX(-6deg); line-height: 1;
}
.back-wheel {
  display: flex; gap: 8px; background: rgba(10, 11, 16, 0.78); border: 3px solid var(--ink);
  box-shadow: 4px 4px 0 var(--ink); padding: 7px 11px; border-radius: 999px; transform: rotate(-2deg);
}
.back-wheel .pip { width: 24px; height: 24px; font-size: 0.85rem; }
.back-tagline {
  background: #e11d48; color: #ffffff; border: 2.5px solid var(--ink);
  box-shadow: 3px 3px 0 var(--ink); font-family: 'Barlow Condensed', sans-serif;
  font-weight: 800; font-size: 0.8rem; letter-spacing: 0.12em; padding: 3px 12px; transform: skewX(-6deg);
}

.aura-card-scene, .aura-card-scene.compact {position:relative;width:100%;aspect-ratio:5/7;min-height:0;container-type:inline-size}
.aura-card-scene .card-flipper, .aura-card-scene.compact .card-flipper {width:100%;height:100%;min-height:0}
.aura-card-scene .card-face, .aura-card-scene.compact .card-face {position:absolute;inset:0;width:100%;height:100%;min-height:0;border:0;border-radius:4%;overflow:hidden;box-shadow:0 4px 15px #0009}
.aura-front {--glow:#f2c65c;--a:#fff3cf;--b:#c99a3a;--accent:#9a5b00;background:#0e0e12;color:#161210}
.aura-Blue {--glow:#5cb8f2;--a:#cdebff;--b:#1d4f8f;--accent:#1c5fa8}.aura-Black {--glow:#b07ce8;--a:#6b5a7e;--b:#15101c;--accent:#6a2fa0}.aura-Red {--glow:#ff7a45;--a:#ffc9a8;--b:#8f2410;--accent:#b3300f}.aura-Green {--glow:#7fd86a;--a:#d8f5c8;--b:#235a22;--accent:#2f7a26}.aura-Multicolor {--glow:#f5d36b;--a:#ffe9a6;--b:#7a3d8f;--accent:#8a5a00}.aura-Artifact {--glow:#b8c4cf;--a:#e3e8ee;--b:#4b5663;--accent:#4b5663}.aura-Land {--glow:#c9a77a;--a:#eadbc2;--b:#5a4630;--accent:#6e5332}
.aura-art,.aura-art-placeholder {position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.aura-art-placeholder {display:grid;place-items:center;background:radial-gradient(circle at 50% 37%,var(--a),var(--b))}.aura-art-placeholder span {color:#fff6;font:italic 800 9cqw 'Barlow Condensed',sans-serif}.aura-art-shade {position:absolute;inset:45% 0 0;background:linear-gradient(transparent,#1a120699);pointer-events:none}.aura-frame {position:absolute;inset:0;border:1.7cqw solid transparent;border-image:url('/app/static/brush_frame_9slice.png') 32 fill / 2.8cqw / 0 stretch;pointer-events:none}
.aura-name {position:absolute;left:2.3%;top:2%;width:70%;height:9%;background:#17120e url('/app/static/brush_header_banner.png') center/100% 100%;background-blend-mode:multiply;color:#ffe9a6;font:4.8cqw Bangers,cursive;display:flex;align-items:center;padding:0 5%;box-sizing:border-box;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:1px 2px #161210}.aura-costs {position:absolute;right:1%;top:1%;height:11%;display:flex;align-items:center}.aura-cost {display:grid;place-items:center;width:8.5cqw;height:8.5cqw;background:#fff4d6 url('/app/static/brush_aura_burst.png') center/100% 100%;color:#161210;font:5cqw Bangers,cursive;border-radius:50%}
.aura-type {position:absolute;top:51.4%;left:3.3%;width:93.4%;height:6.7%;background:url('/app/static/brush_header_banner.png') center/100% 100%,#fef8e8;display:flex;align-items:center;justify-content:space-between;padding:0 5%;box-sizing:border-box;gap:2%;font:700 2.8cqw Arial,sans-serif}.aura-type span {overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.aura-type b {background:#161210;color:var(--glow);padding:1% 2%;font:800 2.3cqw Arial,sans-serif;white-space:nowrap}
.aura-rules {position:absolute;top:58.7%;left:2.7%;width:94.6%;height:30%;background:url('/app/static/brush_rules_wash.png') center/100% 100%;display:flex;align-items:center;justify-content:center}.aura-rules-content {width:82%;max-height:84%;overflow:hidden;font:500 2.7cqw/1.2 Arial,sans-serif;color:#161210}.aura-rules-content p {margin:0 0 .25em;font:inherit;line-height:inherit;color:inherit}.aura-rules-content .pip {display:inline;font:inherit;padding:0;border:0;background:none;box-shadow:none}.aura-rules-content .rem {font-size:.85em;font-style:italic;color:#6b5d48}.aura-rules-content .kw {color:var(--accent);font-weight:800}.aura-flavor {font:italic 2.2cqw/1.15 Georgia,serif;color:#645646;margin-top:.45em}
.aura-footer {position:absolute;left:3%;top:90%;width:68%;height:7.4%;box-sizing:border-box;padding:2% 5%;background:#17120e url('/app/static/brush_header_banner.png') center/100% 100%;background-blend-mode:multiply;color:#ffe9a6;font:800 2.1cqw Arial,sans-serif;display:flex;justify-content:space-between}.aura-stats {position:absolute;right:1%;bottom:1%;width:24%;height:14%;display:grid;place-items:center;background:url('/app/static/brush_aura_burst.png') center/contain no-repeat;color:#161210;font:7cqw Bangers,cursive}.aura-qty {position:absolute;right:2%;top:15%;background:#161210;color:#ffe9a6;border-radius:1em;padding:.2em .5em;font:800 3cqw Arial,sans-serif}.aura-basic .aura-type {top:82.5%}.aura-basic .aura-rules {top:69%;height:13%}.aura-back {transform:rotateY(180deg);background:#0e0e12}.aura-back img {width:100%;height:100%;object-fit:cover}

/* Roblox CardBuilder: painted masks keep the original texture's feathered alpha. */
.aura-card-wrap {position:relative;min-width:0}
.aura-name,.aura-footer,.aura-type {background:none;isolation:isolate}
.aura-name::before,.aura-footer::before,.aura-type::before,.aura-rules::before,.aura-stats::before,.aura-cost::before {content:"";position:absolute;inset:0;z-index:-1;background:var(--paint,#161210);-webkit-mask: url('/app/static/brush_header_banner.png') center/100% 100% no-repeat;mask:url('/app/static/brush_header_banner.png') center/100% 100% no-repeat;filter:drop-shadow(0 1px 2px var(--glow))}
.aura-name {width:calc(97% - var(--pip-size)*.55);max-width:93%;padding-left:6%;font-size:6.6cqw}
.aura-name span {overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.aura-footer {font-family:Montserrat,sans-serif}
.aura-type {--paint:#fef8e8;font-family:Montserrat,sans-serif}.aura-type b {color:var(--rarity,#c9ced6)}
.aura-front.rarity-common {--rarity:#c9ced6}.aura-front.rarity-uncommon {--rarity:#6fe0d6}.aura-front.rarity-rare {--rarity:#ffd25c}.aura-front.rarity-mythic {--rarity:#ff8a3d}.aura-front.rarity-basic {--rarity:#eadbc2}
.aura-halftone {position:absolute;inset:0;background:url('/app/static/comic_halftone_overlay.png') center/cover;opacity:.45;pointer-events:none}.aura-basic .aura-halftone {opacity:.12}
.aura-frame {filter:drop-shadow(0 0 2px var(--glow));border-image-slice:32 fill}
.aura-art-placeholder {background:linear-gradient(115deg,var(--a),var(--b))}.aura-art-placeholder i {position:absolute;width:74%;aspect-ratio:1;top:13%;left:13%;background:var(--a);opacity:.45;-webkit-mask:url('/app/static/brush_aura_burst.png') center/contain no-repeat;mask:url('/app/static/brush_aura_burst.png') center/contain no-repeat}.aura-art-placeholder span {position:absolute;top:29%;width:90%;text-align:center;color:var(--a);opacity:.55}
.aura-costs {z-index:3;gap:0}.aura-cost {position:relative;isolation:isolate;width:var(--pip-size);height:var(--pip-size);margin-left:calc(var(--pip-size)*-.16);background:none;font-size:calc(var(--pip-size)*.38);color:var(--pip-ink,#3a342c)}.aura-cost::before {--paint:var(--pip-fill,#e6e2da);-webkit-mask-image:url('/app/static/brush_aura_burst.png');mask-image:url('/app/static/brush_aura_burst.png')}.aura-cost.pip-W {--pip-fill:#fff4d6;--pip-ink:#9a5b00}.aura-cost.pip-U {--pip-fill:#cdebff;--pip-ink:#1c5fa8}.aura-cost.pip-B {--pip-fill:#d9cde6;--pip-ink:#3a1f57}.aura-cost.pip-R {--pip-fill:#ffd2bd;--pip-ink:#b3300f}.aura-cost.pip-G {--pip-fill:#d3f2c4;--pip-ink:#2f7a26}
.aura-rules {isolation:isolate;background:none}.aura-rules::before {--paint:#fef8e8;-webkit-mask-image:url('/app/static/brush_rules_wash.png');mask-image:url('/app/static/brush_rules_wash.png');filter:drop-shadow(0 0 3px var(--glow))}.aura-rules-content {font-family:Montserrat,sans-serif;line-height:1.12;max-height:90%}.aura-flavor {font-family:Merriweather,serif}.aura-divider {height:1px;background:linear-gradient(90deg,transparent,var(--glow),transparent);margin:.4em 0}
.aura-stats {isolation:isolate;background:none;font-size:8.3cqw}.aura-stats::before {--paint:#ffe7a3;-webkit-mask-image:url('/app/static/brush_aura_burst.png');mask-image:url('/app/static/brush_aura_burst.png')}
.aura-inspect-toggle {position:absolute;opacity:0;pointer-events:none}.aura-inspect-button {position:absolute;right:3%;top:14%;z-index:4;padding:.35em .7em;border-radius:.3em;background:#17120ee8;color:#fff1be;font:700 12px Montserrat,sans-serif;cursor:pointer;opacity:.85}.aura-inspect-button:hover,.aura-inspect-button:focus {opacity:1;background:#6a4b1c}.aura-inspect-overlay {display:none;position:fixed;inset:0;z-index:999999;justify-content:center;align-items:center}.aura-inspect-toggle:checked ~ .aura-inspect-overlay {display:flex}.aura-inspect-dismiss {position:absolute;inset:0;background:#07060beb;cursor:pointer}.aura-inspect-panel {position:relative;height:min(88vh,850px);aspect-ratio:5/7;max-width:90vw}.aura-inspect-card {position:relative;width:100%;height:100%;container-type:inline-size}.aura-inspect-card .card-face {position:absolute;inset:0;width:100%;height:100%;min-height:0;border:0;border-radius:4.3%;overflow:hidden}.aura-inspect-close {position:absolute;z-index:5;right:0;top:-2.5em;color:#fff;background:#302724;padding:.4em .8em;border-radius:.3em;cursor:pointer;font:700 14px Montserrat,sans-serif}.aura-inspect-face .aura-type {top:39.7%}.aura-inspect-face .aura-rules {top:46.6%;height:41.8%}.aura-inspect-face.aura-basic .aura-type {top:82.5%}.aura-inspect-face.aura-basic .aura-rules {top:69%;height:13%}

/* The frame plate is sliced at the same 32 px insets as CardBuilder. */
.aura-frame {z-index:2; box-sizing:border-box; border:6cqw solid transparent; border-image-source:url('/app/static/brush_frame_9slice.png'); border-image-slice:32; border-image-width:1; border-image-outset:0; border-image-repeat:stretch; filter:sepia(.55) drop-shadow(0 0 .55cqw var(--glow));}
.aura-name,.aura-type,.aura-footer,.aura-costs,.aura-stats {z-index:4}
.aura-name {width:var(--name-width);max-width:93.3%;font-size:var(--name-size)}
.aura-type {overflow:visible}
.aura-type b {position:relative;isolation:isolate;display:flex;align-items:center;justify-content:center;background:none;width:31%;height:73%;padding:0 2%;box-sizing:border-box;font:800 3.3cqw Montserrat,sans-serif;color:var(--rarity,#c9ced6);overflow:visible}
.aura-type b::before {content:"";position:absolute;inset:0;z-index:-1;background:#161210;-webkit-mask:url('/app/static/brush_header_banner.png') center/100% 100% no-repeat;mask:url('/app/static/brush_header_banner.png') center/100% 100% no-repeat;filter:drop-shadow(.3cqw .3cqw .1cqw #0009)}
.aura-rules-content .pip {display:inline;width:auto;height:auto;min-width:0;margin:0;padding:0;vertical-align:baseline;line-height:inherit;border-radius:0;transform:none}
.aura-rules-content .pip {text-shadow:none;color:var(--accent);font-weight:800}
.aura-rules-content .pip::before {content:"("}.aura-rules-content .pip::after {content:")"}
.aura-rules-content .pip-W {color:#9a5b00}.aura-rules-content .pip-U {color:#1c5fa8}.aura-rules-content .pip-B {color:#3a1f57}.aura-rules-content .pip-R {color:#b3300f}.aura-rules-content .pip-G {color:#2f7a26}.aura-rules-content .pip-N {color:#3a342c}
.aura-inspect-face .aura-rules-content {overflow-y:auto;scrollbar-width:thin}
</style>"""


def energy_value(cost: str) -> int:
    if not cost:
        return 0
    total = 0
    for token in re.findall(r"\{([^}]+)\}", str(cost)):
        total += int(token) if token.isdigit() else 1
    return total


def safe_int(val: str) -> int:
    s = str(val).strip()
    return int(s) if s.lstrip("-").isdigit() else -1


def card_category(card_type: str) -> str:
    t = str(card_type)
    if "Land" in t:
        return "Land"
    if "Creature" in t or "Casting" in t:
        return "Creature"
    if "Mudra" in t:
        return "Mudra"
    if "Mantra" in t:
        return "Mantra"
    if "Seal" in t:
        return "Seal"
    if "Artifact" in t:
        return "Artifact"
    return "Other"


def extract_colors(color_field: str, energy_cost: str) -> list[str]:
    """Return every color a card belongs to. Multicolor cards count as all of their component colors simultaneously."""
    c = str(color_field).strip()
    if c != "Multicolor":
        return [c] if c else []
    found: list[str] = []
    for sym in re.findall(r"\{([WUBRG])\}", str(energy_cost)):
        cname = SYM_TO_COLOR[sym]
        if cname not in found:
            found.append(cname)
    found.append("Multicolor")
    return found


@st.cache_data(show_spinner=False)
def load_cards() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for set_name, prefix, path in CSV_FILES:
        if path.exists():
            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
            if "set" not in df.columns:
                df.insert(0, "set", set_name)
            nums = list(range(1, len(df) + 1))
            df["set_number"] = nums
            df["id"] = [f"{prefix}{n:03d}" for n in nums]
            df["basic"] = False
            df["produces"] = ""
            frames.append(df)

    basic_df = pd.DataFrame(json.loads((ROOT / "basic_lands.json").read_text(encoding="utf-8")))
    frames.append(basic_df)

    all_df = pd.concat(frames, ignore_index=True)
    all_df["variant"] = all_df["variant"].fillna(0)
    all_df["energy_value"] = all_df["energy_cost"].map(energy_value)
    all_df["atk_num"] = all_df["power"].map(safe_int)
    all_df["base_type"] = all_df["card_type"].map(lambda t: str(t).split("—")[0].strip())
    all_df["category"] = all_df["card_type"].map(card_category)
    all_df["color_list"] = [
        extract_colors(c, cost) for c, cost in zip(all_df["color"], all_df["energy_cost"])
    ]
    return all_df


def interleave_by_color(df: pd.DataFrame, colors: list[str]) -> pd.DataFrame:
    """Round-robin interleave rows across selected colors so multi-color queries show all chosen colors on page 1."""
    seen: set[int] = set()
    buckets: list[list[int]] = []
    for c in colors:
        idxs = [i for i, cl in zip(df.index, df["color_list"]) if c in cl]
        if idxs:
            buckets.append(idxs)
    if len(buckets) <= 1:
        return df
    ordered: list[int] = []
    max_len = max(len(b) for b in buckets)
    for i in range(max_len):
        for b in buckets:
            if i < len(b) and b[i] not in seen:
                ordered.append(b[i])
                seen.add(b[i])
    for i in df.index:
        if i not in seen:
            ordered.append(i)
    return df.loc[ordered]


def render_pips(text: str) -> str:
    if not text:
        return ""

    def repl(m: re.Match[str]) -> str:
        sym = m.group(1)
        if sym == "TURN":
            return '<span class="pip pip-T" title="Turn">↻</span>'
        cls = f"pip-{sym}" if sym in {"W", "U", "B", "R", "G"} else "pip-N"
        return f'<span class="pip {cls}">{html.escape(sym)}</span>'

    return re.sub(r"\{([^}]+)\}", repl, text)


def render_rules(raw: str) -> str:
    if not raw or not str(raw).strip():
        return "&nbsp;"
    paragraphs: list[str] = []
    for line in str(raw).splitlines():
        line = line.strip()
        if not line:
            continue
        escaped = html.escape(line)
        with_pips = render_pips(escaped)
        styled = re.sub(
            r'^([A-Za-z][A-Za-z0-9 \-]+?(?:\s+<span class="pip[^"]*">[^<]+</span>)*)\s+(\([^)]+\)\.?)',
            r'<span class="kw">\1</span> <span class="rem">\2</span>',
            with_pips,
        )
        paragraphs.append(f"<p>{styled}</p>")
    return "".join(paragraphs)


def card_art(row: pd.Series) -> str:
    card_id = str(row["id"])
    named = {"A001": "gilded_scarab_art.png", "A008": "A008-haloed-seraph.png", "A035": "A035-ivory-rupture-v2.png"}
    if card_id in named:
        return ASSET_BASE + named[card_id]
    if (ROOT / "static" / "rares" / f"{card_id}.png").exists():
        return f"{ASSET_BASE}rares/{card_id}.png"
    if bool(row.get("basic", False)):
        name = str(row["name"]).lower()
        variant = int(row.get("variant", 1) or 1)
        if name == "gloomfen" and variant == 4: variant = 1
        if name == "cinderpeak" and variant > 2: variant -= 2
        if name == "wildgrove": variant = 1
        if (ROOT / "static" / "lands" / f"{name}_v{variant}.jpg").exists():
            return f"{ASSET_BASE}lands/{name}_v{variant}.jpg"
    return ""


def render_card_html(row: pd.Series, flip_all: bool, uid: str, in_deck_qty: int = 0, compact: bool = False) -> str:
    name = html.escape(str(row["name"]))
    color = html.escape(str(row["color"]))
    basic = bool(row.get("basic", False))
    art = card_art(row)
    subtype = str(row["card_type"]).split("—")[-1].strip().upper()
    art_html = f'<img class="aura-art" src="{html.escape(art, quote=True)}" alt="" loading="lazy">' if art else f'<div class="aura-art-placeholder"><i></i><span>{html.escape(subtype)}</span></div>'
    tokens = re.findall(r"\{([^}]+)\}", str(row["energy_cost"]))
    pip_sizes = (20.33, 18.33, 15.33, 13.33, 11.67)
    pip_size = pip_sizes[min(max(len(tokens), 1), 5) - 1]
    pips = "".join(f'<span class="aura-cost pip-{html.escape(t)}">{html.escape(t)}</span>' for t in tokens)
    cost_width = len(tokens) * pip_size * .84 + (pip_size * .16 if tokens else 0)
    name_width = max(50, min(93.3, (590 - cost_width * 6 - 14 + 30) / 6))
    name_size = max(3.67, min(9.33, (name_width * 6 - 68) / (max(1, len(str(row["name"]))) * .48) / 6))
    raw = str(row["rules_text"])
    flavor = str(row["flavor_text"]).strip()
    n = len(raw) + (0 if basic else len(flavor) * .7)
    body_px, flavor_px = next((body, fl) for limit, body, fl in [(110,27,21), (190,24,19), (280,21,17), (380,19,16), (float("inf"),17,14)] if n < limit)
    flavor_html = f'<div class="aura-divider"></div><div class="aura-flavor" style="font-size:{flavor_px / 6:.2f}cqw">“{html.escape(flavor)}”</div>' if flavor and not basic else ""
    power = str(row["power"]).strip()
    stats = f'<div class="aura-stats"><span>{html.escape(power)}/{html.escape(str(row["toughness"]))}</span></div>' if power else ""
    number = f'{int(row["set_number"]):03d}/350' if not basic else ""
    qty = f'<div class="aura-qty">×{in_deck_qty}</div>' if in_deck_qty else ""
    checked = "checked" if flip_all else ""
    rarity = "basic" if basic else str(row["rarity"]).lower()
    safe_uid = html.escape(uid, quote=True)
    def face(inspect: bool = False) -> str:
        rules = re.sub(r"\(([^()]*)\)", lambda m: m.group(1) if re.match(r"\s*[+-]\d+\s*/\s*[+-]\d+", m.group(1)) else "", raw) if inspect else raw
        rules = re.sub(r" +([.,;:])", r"\1", rules)
        text_size = max(2.2, min(6.0, 6.0 - len(rules) / 85)) if inspect and not basic else body_px / 6
        return (
            f'<article class="card-face aura-front aura-{color} rarity-{html.escape(rarity)}{" aura-basic" if basic else ""}{" aura-inspect-face" if inspect else ""}" style="--pip-size:{pip_size:.2f}cqw;--name-width:{name_width:.2f}%;--name-size:{name_size:.2f}cqw">'
            f'{art_html}<div class="aura-halftone"></div><div class="aura-art-shade"></div><div class="aura-frame"></div>'
            f'<div class="aura-name"><span>{name}</span></div><div class="aura-costs">{pips}</div>'
            f'<div class="aura-type"><span>{html.escape(str(row["card_type"]).upper())}</span><b>★ {html.escape(rarity.upper())}</b></div>'
            f'<div class="aura-rules"><div class="aura-rules-content" style="font-size:{text_size:.2f}cqw">{render_rules(rules)}{flavor_html if not inspect else ""}</div></div>'
            f'<div class="aura-footer"><span>{html.escape(str(row["set"]).upper())} · 1ST ED.</span><span>{number}</span></div>{stats}{qty}</article>'
        )
    return (
        f'<div class="aura-card-wrap"><label class="card-scene aura-card-scene{" compact" if compact else ""}" for="{safe_uid}">'
        f'<input class="flip-chk" type="checkbox" id="{safe_uid}" {checked}><div class="card-flipper">{face()}'
        f'<div class="card-face aura-back"><img src="{ASSET_BASE}aura_card_back_upright.png" alt="Aura card back" loading="lazy"></div></div></label>'
        f'<input class="aura-inspect-toggle" type="checkbox" id="inspect_{safe_uid}">'
        f'<label class="aura-inspect-button" for="inspect_{safe_uid}">Inspect</label>'
        f'<div class="aura-inspect-overlay"><label class="aura-inspect-dismiss" for="inspect_{safe_uid}" aria-label="Close inspection"></label>'
        f'<div class="aura-inspect-panel"><label class="aura-inspect-close" for="inspect_{safe_uid}">Close ✕</label>'
        f'<div class="aura-inspect-card">{face(True)}</div></div></div></div>'
    )


def validate_deck(deck_cards: dict[str, int], id_map: dict[str, pd.Series]) -> tuple[bool, int, list[str]]:
    problems: list[str] = []
    total = 0
    for cid, count in deck_cards.items():
        if cid not in id_map:
            problems.append(f"Unknown card ID: {cid}")
            continue
        card = id_map[cid]
        if count < 1:
            problems.append(f"Invalid count for {card['name']}: {count}")
            continue
        if not bool(card["basic"]) and count > MAX_COPIES:
            problems.append(f"{card['name']} ({cid}): max {MAX_COPIES} copies (has {count})")
        total += count
    if total < MIN_DECK:
        problems.append(f"Deck needs at least {MIN_DECK} cards (currently {total}).")
    if total > MAX_DECK:
        problems.append(f"Deck can have at most {MAX_DECK} cards (currently {total}).")
    return len(problems) == 0, total, problems


def auto_generate_deck(
    all_df: pd.DataFrame,
    colors: list[str],
    sets: list[str],
    target_size: int,
    archetype: str,
    seed: int | None = None,
) -> dict[str, int]:
    rng = random.Random(seed)
    chosen_colors = [c for c in colors if c in COLOR_TO_BASIC_ID]
    if not chosen_colors:
        chosen_colors = ["White", "Blue"]

    pool = all_df[~all_df["basic"]].copy()
    if sets:
        pool = pool[pool["set"].isin(sets)]

    allowed_colors = set(chosen_colors) | {"Artifact"}
    pool = pool[
        pool["color_list"].map(
            lambda cl: len([c for c in cl if c != "Multicolor"]) > 0
            and all(c in allowed_colors for c in cl if c != "Multicolor")
        )
    ]

    # Split ratios by archetype
    if archetype == "Aggro (Low Curve)":
        land_ratio, creature_ratio, max_mv = 0.35, 0.45, 4
    elif archetype == "Control (Mudra / Mantra / Seal)":
        land_ratio, creature_ratio, max_mv = 0.42, 0.22, 6
    elif archetype == "Midrange":
        land_ratio, creature_ratio, max_mv = 0.40, 0.38, 6
    else:  # Balanced
        land_ratio, creature_ratio, max_mv = 0.38, 0.37, 5

    land_target = round(target_size * land_ratio)
    nonland_target = target_size - land_target
    creature_target = round(nonland_target * creature_ratio / max(1e-6, (1 - land_ratio)))
    spell_target = nonland_target - creature_target

    creatures = pool[(pool["category"] == "Creature") & (pool["energy_value"] <= max_mv)]
    if len(creatures) < 8:
        creatures = pool[pool["category"] == "Creature"]
    spells = pool[pool["category"].isin(["Mudra", "Mantra", "Seal", "Artifact"])]

    deck: dict[str, int] = {}

    # Authentic multi-cost energy curve buckets (1-drop through 5+ drop)
    if archetype == "Aggro (Low Curve)":
        curve_weights = {1: 0.34, 2: 0.36, 3: 0.22, 4: 0.08}
    elif archetype == "Control (Mudra / Mantra / Seal)":
        curve_weights = {1: 0.14, 2: 0.28, 3: 0.26, 4: 0.18, 5: 0.14}
    elif archetype == "Midrange":
        curve_weights = {1: 0.14, 2: 0.26, 3: 0.26, 4: 0.20, 5: 0.14}
    else:  # Balanced
        curve_weights = {1: 0.20, 2: 0.30, 3: 0.25, 4: 0.15, 5: 0.10}

    def pick_cards(sub_df: pd.DataFrame, need: int) -> None:
        if sub_df.empty or need <= 0:
            return
        added = 0
        # First pass: fill each energy-cost curve bucket
        for cost_slot, weight in curve_weights.items():
            slot_need = max(2, round(need * weight))
            if cost_slot >= 5:
                slot_df = sub_df[sub_df["energy_value"] >= 5]
            else:
                slot_df = sub_df[sub_df["energy_value"] == cost_slot]
            recs = list(slot_df.to_dict("records"))
            rng.shuffle(recs)
            slot_added = 0
            for rec in recs:
                if slot_added >= slot_need or added >= need:
                    break
                cid = rec["id"]
                if cid in deck:
                    continue
                copies = 2 if rec["rarity"] == "rare" else rng.choice([2, 3, 4])
                copies = min(copies, MAX_COPIES, slot_need - slot_added, need - added)
                if copies > 0:
                    deck[cid] = copies
                    slot_added += copies
                    added += copies
        # Second pass: top up any remainder across the full sub_df
        if added < need:
            recs = list(sub_df.to_dict("records"))
            rng.shuffle(recs)
            for rec in recs:
                if added >= need:
                    break
                cid = rec["id"]
                if cid in deck:
                    continue
                copies = 2 if rec["rarity"] == "rare" else rng.choice([2, 3])
                copies = min(copies, MAX_COPIES, need - added)
                if copies > 0:
                    deck[cid] = copies
                    added += copies

    pick_cards(creatures, creature_target)
    pick_cards(spells, spell_target)

    # Top up any remaining nonland slots from combined pool
    current_nonland = sum(deck.values())
    if current_nonland < nonland_target:
        pick_cards(pool[pool["category"] != "Land"], nonland_target - current_nonland)

    # Distribute Basic Lands proportional to colored pip symbols in the deck
    id_lookup = {row["id"]: row for _, row in all_df.iterrows()}
    sym_counts = Counter()
    sym_to_color = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
    for cid, cnt in deck.items():
        cost = str(id_lookup[cid]["energy_cost"])
        for sym in re.findall(r"\{([WUBRG])\}", cost):
            if sym_to_color[sym] in chosen_colors:
                sym_counts[sym_to_color[sym]] += cnt

    total_syms = sum(sym_counts.values())
    lands_added = 0
    for idx, col in enumerate(chosen_colors):
        lid = COLOR_TO_BASIC_ID[col]
        if idx == len(chosen_colors) - 1:
            qty = max(1, land_target - lands_added)
        elif total_syms > 0:
            qty = max(1, round(land_target * (sym_counts[col] / total_syms)))
        else:
            qty = max(1, land_target // len(chosen_colors))
        qty = min(qty, max(0, land_target - lands_added))
        if qty > 0:
            deck[lid] = qty
            lands_added += qty

    return deck


def deck_to_luau(deck_name: str, deck_cards: dict[str, int]) -> str:
    safe_name = deck_name.replace("\\", "\\\\").replace('"', '\\"')
    lines = [
        "-- Aura TCG Deck (compatible with DeckRules.luau & CardDatabase.luau)",
        "return {",
        f'\tname = "{safe_name}",',
        "\tcards = {",
    ]
    for cid in sorted(deck_cards.keys()):
        lines.append(f'\t\t["{cid}"] = {deck_cards[cid]},')
    lines.append("\t},")
    lines.append("}")
    return "\n".join(lines)


# ==================== INIT STATE & LOAD DATA ====================
st.html(build_ui_texture_css() + COMIC_CSS.replace("/app/static/", ASSET_BASE))
df = load_cards()
id_map = {row["id"]: row for _, row in df.iterrows()}

if "deck_name" not in st.session_state:
    st.session_state.deck_name = "My Aura Deck"
if "deck_cards" not in st.session_state:
    st.session_state.deck_cards = {}
if "test_hand" not in st.session_state:
    st.session_state.test_hand = []

st.html(
    """<div class="aura-banner">
      <div class="aura-banner-left">
        <div class="aura-logo">AURA!</div>
        <div class="aura-title">
          <h1>Card Viewer &amp; Deck Editor</h1>
          <p>Alpha · Beta · Delta · Basic Lands · Roblox Deck Export</p>
        </div>
      </div>
      <div class="aura-tip">Click a card to flip · Inspect to enlarge</div>
    </div>"""
)

# ==================== SIDEBAR MULTI-FILTERS ====================
with st.sidebar:
    st.markdown("### ⚡ Filter Cards")
    search = st.text_input("Search", placeholder="Name, ID, type, rules, or flavor...")
    selected_sets = st.multiselect(
        "Sets",
        ["Alpha", "Beta", "Delta", "Core"],
        default=["Alpha", "Beta", "Delta", "Core"],
        placeholder="All sets",
    )
    color_options = ["White", "Blue", "Black", "Red", "Green", "Multicolor", "Artifact", "Land"]
    selected_colors = st.multiselect("Colors", color_options, placeholder="All colors")
    selected_types = st.multiselect(
        "Card Types",
        ["Creature", "Mudra", "Mantra", "Seal", "Artifact", "Land"],
        placeholder="All types",
    )
    selected_rarities = st.multiselect(
        "Rarities",
        ["common", "uncommon", "rare"],
        placeholder="All rarities",
    )
    sort_choice = st.selectbox(
        "Sort By",
        ["Set Order (Color Mix)", "Set Order (Sequential)", "Energy: Low → High", "Energy: High → Low", "Name: A → Z", "ATK: High → Low"],
    )

    st.divider()
    flip_all = st.toggle("Show Card Backs", value=False)
    page_size = st.select_slider("Cards per Page", options=[24, 48, 96, 200], value=48)

# ==================== APPLY MULTI-FILTERS ====================
filtered = df.copy()
if selected_sets:
    filtered = filtered[filtered["set"].isin(selected_sets)]
if selected_colors:
    sel_set = set(selected_colors)
    filtered = filtered[filtered["color_list"].map(lambda cl: bool(sel_set.intersection(cl)))]
if selected_types:
    filtered = filtered[filtered["category"].isin(selected_types)]
if selected_rarities:
    filtered = filtered[filtered["rarity"].str.lower().isin(selected_rarities)]

# Paint the sidebar Colors filter pane dynamically with the selected color(s)
if selected_colors:
    hexes = [COLOR_SOLID_HEX.get(c, "#263047") for c in selected_colors]
    if len(hexes) == 1:
        pane_bg = hexes[0]
        sidebar_tint = f"linear-gradient(180deg, {hexes[0]}33 0%, #1a1e2b 42%)"
    else:
        stops = ", ".join(hexes)
        pane_bg = f"linear-gradient(135deg, {stops})"
        tint_stops = ", ".join(f"{h}38" for h in hexes)
        sidebar_tint = f"linear-gradient(160deg, {tint_stops}, #1a1e2b 58%)"
    st.html(
        f"""<style>
        section[data-testid="stSidebar"] > div:first-child {{
          background: {sidebar_tint} !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stMultiSelect"]:has([aria-label*="Colors"]) [data-baseweb="select"] > div,
        section[data-testid="stSidebar"] [data-testid="stMultiSelect"]:has(input[aria-label*="Colors"]) > div > div {{
          background: {pane_bg} !important;
          border: 2.5px solid #0a0b10 !important;
          box-shadow: 3px 3px 0 #0a0b10 !important;
        }}
        </style>"""
    )
else:
    pane_bg = "#1a1e2b"
if search.strip():
    q = search.strip()
    mask = (
        filtered["name"].str.contains(q, case=False, na=False)
        | filtered["id"].str.contains(q, case=False, na=False)
        | filtered["card_type"].str.contains(q, case=False, na=False)
        | filtered["rules_text"].str.contains(q, case=False, na=False)
        | filtered["flavor_text"].str.contains(q, case=False, na=False)
    )
    filtered = filtered[mask]

if sort_choice == "Set Order (Color Mix)":
    mix_colors = selected_colors if len(selected_colors) > 1 else []
    if mix_colors:
        filtered = interleave_by_color(filtered, mix_colors)
elif sort_choice == "Energy: Low → High":
    filtered = filtered.sort_values(["energy_value", "name"], ascending=[True, True])
elif sort_choice == "Energy: High → Low":
    filtered = filtered.sort_values(["energy_value", "name"], ascending=[False, True])
elif sort_choice == "Name: A → Z":
    filtered = filtered.sort_values("name", ascending=True)
elif sort_choice == "ATK: High → Low":
    filtered = filtered.sort_values(["atk_num", "name"], ascending=[False, True])

total_shown = len(filtered)
deck_total = sum(st.session_state.deck_cards.values())

export_cols = [
    "id", "set", "name", "color", "rarity", "energy_cost",
    "card_type", "power", "toughness", "rules_text", "flavor_text",
]

with st.sidebar:
    st.divider()
    st.caption(f"Showing **{total_shown:,}** of **{len(df):,}** cards · Deck: **{deck_total}** cards")
    st.download_button(
        "⬇ Download Filtered CSV",
        data=filtered[export_cols].to_csv(index=False).encode("utf-8"),
        file_name="aura_filtered_cards.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ==================== MAIN TABS (STATIC LABELS SO STREAMLIT NEVER RESETS ACTIVE TAB ON RERUN!) ====================
tab_gallery, tab_deck, tab_analytics, tab_table = st.tabs([
    "🃏 Comic Gallery",
    "🛠️ Deck Editor",
    "📊 Set Analytics",
    "📋 CSV Table",
])

# -------------------- TAB 1: COMIC GALLERY --------------------
with tab_gallery:
    if total_shown == 0:
        st.info("No cards match your current filters.")
    else:
        # Selected Filter Pane with selected color(s) as background + black-outlined labels!
        pills = []
        for col_name in color_options:
            cnt = int(filtered["color_list"].map(lambda cl, cn=col_name: cn in cl).sum())
            if cnt > 0:
                bg, _ = COLOR_CHIP_STYLE[col_name]
                pills.append(f'<span class="color-pill-stat" style="background:{bg};">{col_name}: {cnt}</span>')
        filter_label = (
            f"ACTIVE COLORS ({' + '.join(selected_colors)})"
            if selected_colors else "ALL COLORS"
        )
        st.html(
            f'<div class="selected-filter-pane" style="background:{pane_bg};">'
            f'<span class="selected-filter-title">{html.escape(filter_label)}:</span>'
            f'{"".join(pills)}</div>'
        )

        total_pages = max(1, math.ceil(total_shown / page_size))
        col_info, col_page = st.columns([3, 1])
        with col_page:
            page_num = int(
                st.number_input(
                    f"Page (1–{total_pages})",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    step=1,
                )
            )
        start = (page_num - 1) * page_size
        end = min(start + page_size, total_shown)
        with col_info:
            st.markdown(
                f"**Cards {start + 1}–{end}** of **{total_shown:,}** matching cards · "
                f"Page **{page_num}** / **{total_pages}**"
            )

        page_df = filtered.iloc[start:end]
        cards_html = "".join(
            render_card_html(
                row,
                flip_all=flip_all,
                uid=f"c_{page_num}_{idx}",
                in_deck_qty=st.session_state.deck_cards.get(row["id"], 0),
            )
            for idx, (_, row) in enumerate(page_df.iterrows())
        )
        st.html(f'<div class="aura-grid">{cards_html}</div>')

# -------------------- TAB 2: VISUAL GALLERY DECK EDITOR & AUTO-GENERATOR --------------------
def adjust_deck_card(cid: str, delta: int) -> None:
    cur = st.session_state.deck_cards.get(cid, 0)
    card = id_map[cid]
    cap = MAX_DECK if bool(card["basic"]) else MAX_COPIES
    nxt = max(0, min(cap, cur + delta))
    if nxt == 0:
        st.session_state.deck_cards.pop(cid, None)
    else:
        st.session_state.deck_cards[cid] = nxt


def render_interactive_card_grid(
    cards_df: pd.DataFrame,
    key_prefix: str,
    cols_per_row: int = 4,
    flip_cards: bool = False,
) -> None:
    """Render comic cards in a visual grid with instant 1-tap Add / Remove controls under each card."""
    records = [row for _, row in cards_df.iterrows()]
    for row_start in range(0, len(records), cols_per_row):
        batch = records[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row, gap="medium")
        for col_idx, row in enumerate(batch):
            cid = str(row["id"])
            is_basic = bool(row["basic"])
            cap = MAX_DECK if is_basic else MAX_COPIES
            qty = st.session_state.deck_cards.get(cid, 0)
            with cols[col_idx]:
                st.html(
                    render_card_html(
                        row,
                        flip_all=flip_cards,
                        uid=f"{key_prefix}_{cid}_{row_start + col_idx}",
                        in_deck_qty=qty,
                        compact=True,
                    )
                )
                if qty == 0:
                    st.button(
                        "➕ Add (+1)",
                        key=f"{key_prefix}_add0_{cid}_{row_start + col_idx}",
                        on_click=adjust_deck_card,
                        args=(cid, 1),
                        use_container_width=True,
                        help=f"Add 1 copy of {row['name']}",
                    )
                else:
                    b1, b2, b3 = st.columns([1, 1.35, 1])
                    with b1:
                        st.button(
                            "➖",
                            key=f"{key_prefix}_sub_{cid}_{row_start + col_idx}",
                            on_click=adjust_deck_card,
                            args=(cid, -1),
                            use_container_width=True,
                            help="Remove 1 copy",
                        )
                    with b2:
                        limit_txt = "∞" if is_basic else str(cap)
                        st.markdown(
                            f"<div style='text-align:center;font-weight:800;padding-top:6px;"
                            f"font-family:Barlow Condensed,sans-serif;font-size:1.05rem;color:#FFE24A;'>"
                            f"×{qty} / {limit_txt}</div>",
                            unsafe_allow_html=True,
                        )
                    with b3:
                        st.button(
                            "➕",
                            key=f"{key_prefix}_add_{cid}_{row_start + col_idx}",
                            on_click=adjust_deck_card,
                            args=(cid, 1),
                            disabled=(qty >= cap),
                            use_container_width=True,
                            help="Add 1 copy",
                        )


if "deck_view_mode" not in st.session_state:
    st.session_state.deck_view_mode = "➕ Tap Cards to Add"

with tab_deck:
    is_valid, total_cards, problems = validate_deck(st.session_state.deck_cards, id_map)

    top_left, top_right = st.columns([2, 3])
    with top_left:
        st.session_state.deck_name = st.text_input("Deck Name", value=st.session_state.deck_name)
    with top_right:
        if is_valid:
            st.success(f"✅ Valid Aura Deck — **{total_cards}** cards (Rules: {MIN_DECK}–{MAX_DECK} cards, max {MAX_COPIES} per non-basic)")
        else:
            st.warning(f"⚠️ **{total_cards}** / {MIN_DECK} min cards — " + " · ".join(problems[:3]))

    # --- Auto-Generate Balanced Deck Bar ---
    with st.expander("⚡ Auto-Generate a Playable Deck", expanded=(total_cards == 0)):
        g1, g2, g3, g4 = st.columns([2, 1.4, 1.1, 1.3])
        with g1:
            gen_colors = st.multiselect(
                "Deck Colors",
                ["White", "Blue", "Black", "Red", "Green"],
                default=[c for c in selected_colors if c in COLOR_TO_BASIC_ID] or ["White", "Blue"],
                key="gen_colors",
            )
        with g2:
            gen_archetype = st.selectbox(
                "Archetype",
                ["Balanced", "Aggro (Low Curve)", "Midrange", "Control (Mudra / Mantra / Seal)"],
                key="gen_arch",
            )
        with g3:
            gen_size = st.selectbox("Deck Size", [40, 60], index=1, key="gen_size")
        with g4:
            gen_sets = st.multiselect(
                "Pool Sets",
                ["Alpha", "Beta", "Delta"],
                default=[s for s in selected_sets if s != "Core"] or ["Alpha", "Beta", "Delta"],
                key="gen_sets",
            )

        b_gen, b_clear, b_hand = st.columns([1.4, 1, 1.4])
        with b_gen:
            if st.button("⚡ Auto-Generate Deck", type="primary", use_container_width=True):
                st.session_state.deck_cards = auto_generate_deck(
                    df, gen_colors, gen_sets, int(gen_size), gen_archetype
                )
                st.session_state.deck_name = f"{'/'.join(gen_colors or ['White', 'Blue'])} {gen_archetype.split(' ')[0]}"
                st.session_state.test_hand = []
                st.session_state.deck_view_mode = "🃏 My Deck Gallery"
                st.rerun()
        with b_clear:
            if st.button("🗑️ Clear Deck", use_container_width=True):
                st.session_state.deck_cards = {}
                st.session_state.test_hand = []
                st.rerun()
        with b_hand:
            if st.button(f"🎲 Pick {OPENING_HAND}-Card Hand", use_container_width=True, disabled=(total_cards < OPENING_HAND)):
                expanded = [cid for cid, qty in st.session_state.deck_cards.items() for _ in range(qty)]
                random.shuffle(expanded)
                st.session_state.test_hand = expanded[:OPENING_HAND]
                st.session_state.deck_view_mode = "🃏 My Deck Gallery"

    # --- Deck Editor Visual Mode Switcher ---
    v_col, c_col = st.columns([3.2, 1])
    with v_col:
        view_options = ["➕ Tap Cards to Add", "🃏 My Deck Gallery", "📊 Curve, Table & Export"]
        cur_idx = view_options.index(st.session_state.deck_view_mode) if st.session_state.deck_view_mode in view_options else 0
        chosen_view = st.radio(
            "Deck Editor View",
            options=view_options,
            index=cur_idx,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state.deck_view_mode = chosen_view
    with c_col:
        grid_cols = st.select_slider("Cards / Row", options=[2, 3, 4], value=3, key="deck_grid_cols")

    # ==================== MODE 1: TAP-TO-ADD VISUAL CARD GALLERY ====================
    if chosen_view == "➕ Tap Cards to Add":
        # Quick-Add Basic Lands Strip (1 tap adds +2, visible right above card pool)
        st.markdown("##### 🌿 Quick-Add Basic Lands (+2 per tap · Unlimited)")
        land_cols = st.columns(5)
        for col_widget, (cname, lid) in zip(land_cols, COLOR_TO_BASIC_ID.items()):
            land_card = id_map[lid]
            l_qty = st.session_state.deck_cards.get(lid, 0)
            with col_widget:
                st.button(
                    f"➕ {land_card['name']} ({l_qty})",
                    key=f"quickland_{lid}",
                    on_click=adjust_deck_card,
                    args=(lid, 2),
                    use_container_width=True,
                )

        add_pool = filtered if len(filtered) > 0 else df
        # Active filter color banner so users see active sidebar filters while picking
        pool_pills = []
        for col_name in color_options:
            cnt = int(add_pool["color_list"].map(lambda cl, cn=col_name: cn in cl).sum())
            if cnt > 0:
                bg, _ = COLOR_CHIP_STYLE[col_name]
                pool_pills.append(f'<span class="color-pill-stat" style="background:{bg};">{col_name}: {cnt}</span>')
        pool_label = f"PICKER POOL ({' + '.join(selected_colors)})" if selected_colors else "PICKER POOL (ALL COLORS)"
        st.html(
            f'<div class="selected-filter-pane" style="background:{pane_bg};">'
            f'<span class="selected-filter-title">{html.escape(pool_label)}:</span>'
            f'{"".join(pool_pills)}</div>'
        )

        p_size_col, p_info_col, p_num_col = st.columns([1.2, 2.5, 1.1])
        with p_size_col:
            picker_page_size = st.selectbox("Show per page", [12, 16, 24], index=1, key="picker_ps")
        picker_pages = max(1, math.ceil(len(add_pool) / picker_page_size))
        with p_num_col:
            picker_page = int(
                st.number_input(
                    f"Picker Page (1–{picker_pages})",
                    min_value=1,
                    max_value=picker_pages,
                    value=1,
                    step=1,
                    key="picker_pg",
                )
            )
        p_start = (picker_page - 1) * picker_page_size
        p_end = min(p_start + picker_page_size, len(add_pool))
        with p_info_col:
            st.markdown(
                f"<div style='padding-top:30px;'>Tap <b>➕ Add</b> under any card to add a copy · "
                f"Showing <b>{p_start + 1}–{p_end}</b> of <b>{len(add_pool):,}</b> filtered cards "
                f"(use sidebar to search/filter)</div>",
                unsafe_allow_html=True,
            )

        render_interactive_card_grid(
            add_pool.iloc[p_start:p_end],
            key_prefix=f"pick_p{picker_page}",
            cols_per_row=grid_cols,
            flip_cards=flip_all,
        )

    # ==================== MODE 2: MY DECK VISUAL COMIC GALLERY ====================
    elif chosen_view == "🃏 My Deck Gallery":
        if not st.session_state.deck_cards:
            st.info("Your deck is empty! Click **⚡ Auto-Generate Deck** above or switch to **➕ Tap Cards to Add** to visually pick cards.")
        else:
            # Build ordered dataframe of chosen cards
            chosen_ids = [cid for cid in st.session_state.deck_cards if cid in id_map]
            deck_cards_df = pd.DataFrame([id_map[cid] for cid in chosen_ids])
            deck_cards_df["qty"] = deck_cards_df["id"].map(st.session_state.deck_cards)

            # Summary metrics bar + Quick Export right on top of the visual deck gallery!
            n_creatures = int(deck_cards_df[deck_cards_df["category"] == "Creature"]["qty"].sum())
            n_spells = int(deck_cards_df[deck_cards_df["category"].isin(["Mudra", "Mantra", "Seal", "Artifact"])]["qty"].sum())
            n_lands = int(deck_cards_df[deck_cards_df["category"] == "Land"]["qty"].sum())
            nonland_df = deck_cards_df[deck_cards_df["category"] != "Land"]
            avg_cost = (
                (nonland_df["energy_value"] * nonland_df["qty"]).sum() / nonland_df["qty"].sum()
                if nonland_df["qty"].sum() > 0 else 0.0
            )
            dm1, dm2, dm3, dm4, dm5 = st.columns([1, 1, 1, 1, 1.3])
            dm1.metric("Total Cards", total_cards)
            dm2.metric("Creatures", n_creatures)
            dm3.metric("Techniques / Art.", n_spells)
            dm4.metric("Lands", n_lands)
            dm5.metric("Avg Energy Cost", f"{avg_cost:.2f}")

            # Render chosen cards grouped cleanly by role in full Comic Edition gallery!
            groups = [
                ("⚔️ Creatures", deck_cards_df[deck_cards_df["category"] == "Creature"]),
                ("⚡ Techniques & Artifacts (Mudra · Mantra · Seal · Artifact)", deck_cards_df[deck_cards_df["category"].isin(["Mudra", "Mantra", "Seal", "Artifact"])]),
                ("🌿 Lands", deck_cards_df[deck_cards_df["category"] == "Land"]),
            ]
            for grp_title, grp_df in groups:
                if grp_df.empty:
                    continue
                grp_total = int(grp_df["qty"].sum())
                grp_sorted = grp_df.sort_values(["energy_value", "name"])
                st.markdown(f"#### {grp_title} ({grp_total} cards · {len(grp_sorted)} unique)")
                render_interactive_card_grid(
                    grp_sorted,
                    key_prefix=f"deck_{grp_title[:4]}",
                    cols_per_row=grid_cols,
                    flip_cards=flip_all,
                )

        # Opening 7-Card Hand Simulator Preview (also visual comic cards!)
        if st.session_state.test_hand:
            st.divider()
            st.markdown(f"#### 🎲 Opening {OPENING_HAND}-Card Hand Preview")
            hand_html = "".join(
                render_card_html(id_map[cid], flip_all=False, uid=f"hand_{i}")
                for i, cid in enumerate(st.session_state.test_hand)
                if cid in id_map
            )
            st.html(f'<div class="aura-grid">{hand_html}</div>')

    # ==================== MODE 3: CURVE, EDITABLE TABLE, IMPORT & EXPORT ====================
    else:
        ex_left, ex_right = st.columns([1.45, 1.25])
        with ex_left:
            st.markdown(f"#### 📜 Decklist Table — {st.session_state.deck_name} ({total_cards} cards)")
            if not st.session_state.deck_cards:
                st.info("Your deck is empty. Auto-generate a deck or tap cards in **➕ Tap Cards to Add**.")
            else:
                deck_rows = []
                for cid, qty in st.session_state.deck_cards.items():
                    if cid in id_map:
                        c = id_map[cid]
                        deck_rows.append({
                            "Qty": qty,
                            "ID": cid,
                            "Name": c["name"],
                            "Color": c["color"],
                            "Cost": c["energy_cost"],
                            "Energy": int(c["energy_value"]),
                            "Type": c["category"],
                            "Rarity": c["rarity"],
                        })
                deck_df = pd.DataFrame(deck_rows).sort_values(["Type", "Energy", "Name"])
                edited_df = st.data_editor(
                    deck_df[["Qty", "ID", "Name", "Color", "Cost", "Type", "Rarity"]],
                    column_config={
                        "Qty": st.column_config.NumberColumn("Qty", min_value=0, max_value=60, step=1),
                        "ID": st.column_config.TextColumn("ID", disabled=True),
                        "Name": st.column_config.TextColumn("Name", disabled=True),
                        "Color": st.column_config.TextColumn("Color", disabled=True),
                        "Cost": st.column_config.TextColumn("Cost", disabled=True),
                        "Type": st.column_config.TextColumn("Type", disabled=True),
                        "Rarity": st.column_config.TextColumn("Rarity", disabled=True),
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=380,
                    key="deck_table_editor",
                )
                if st.button("💾 Apply Quantity Changes (set Qty=0 to remove)", use_container_width=True):
                    updated: dict[str, int] = {}
                    for _, erow in edited_df.iterrows():
                        q_new = int(erow["Qty"])
                        cid = str(erow["ID"])
                        if q_new > 0:
                            cap = MAX_DECK if bool(id_map[cid]["basic"]) else MAX_COPIES
                            updated[cid] = min(q_new, cap)
                    st.session_state.deck_cards = updated
                    st.rerun()

        with ex_right:
            if st.session_state.deck_cards:
                nonland_df = deck_df[deck_df["Type"] != "Land"]
                st.markdown("#### 📈 Non-Land Energy Curve")
                if nonland_df["Qty"].sum() > 0:
                    curve_series = nonland_df.groupby("Energy")["Qty"].sum().sort_index()
                    st.bar_chart(curve_series, height=220)

                st.markdown("#### 💾 Export Deck")
                ex1, ex2, ex3 = st.columns(3)
                safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", st.session_state.deck_name).strip("_") or "aura_deck"
                luau_src = deck_to_luau(st.session_state.deck_name, st.session_state.deck_cards)
                json_src = json.dumps({"name": st.session_state.deck_name, "cards": st.session_state.deck_cards}, indent=2)
                full_csv_rows = []
                for cid, qty in st.session_state.deck_cards.items():
                    if cid in id_map:
                        rec = id_map[cid][export_cols].to_dict()
                        rec["count"] = qty
                        full_csv_rows.append(rec)
                csv_src = pd.DataFrame(full_csv_rows).to_csv(index=False)

                with ex1:
                    st.download_button("🎮 Luau", data=luau_src.encode("utf-8"), file_name=f"{safe_slug}.luau", mime="text/plain", use_container_width=True)
                with ex2:
                    st.download_button("📄 JSON", data=json_src.encode("utf-8"), file_name=f"{safe_slug}.json", mime="application/json", use_container_width=True)
                with ex3:
                    st.download_button("📊 CSV", data=csv_src.encode("utf-8"), file_name=f"{safe_slug}.csv", mime="text/csv", use_container_width=True)

            st.markdown("#### 📤 Import Saved Deck (JSON)")
            uploaded = st.file_uploader("Load saved deck .json", type=["json"], label_visibility="collapsed")
            if uploaded is not None:
                try:
                    payload = json.load(uploaded)
                    if isinstance(payload, dict) and isinstance(payload.get("cards"), dict):
                        valid_cards = {k: int(v) for k, v in payload["cards"].items() if k in id_map and int(v) > 0}
                        if st.button("Apply Imported Deck", use_container_width=True):
                            st.session_state.deck_name = str(payload.get("name", "Imported Deck"))
                            st.session_state.deck_cards = valid_cards
                            st.session_state.deck_view_mode = "🃏 My Deck Gallery"
                            st.rerun()
                    else:
                        st.error('JSON must contain `{ "name": ..., "cards": { "A001": 4 } }`.')
                except Exception as exc:
                    st.error(f"Could not parse JSON: {exc}")

# -------------------- TAB 3: SET ANALYTICS --------------------
with tab_analytics:
    if total_shown == 0:
        st.info("No cards to analyze for the current filter.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Matching Cards", f"{total_shown:,}")
        m2.metric("Avg Energy Cost", f"{filtered['energy_value'].mean():.2f}")
        m3.metric("Rares", int((filtered["rarity"].str.lower() == "rare").sum()))
        m4.metric("Creatures", int((filtered["category"] == "Creature").sum()))

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Energy Cost Curve")
            st.bar_chart(filtered["energy_value"].value_counts().sort_index())
        with c2:
            st.subheader("Color Distribution")
            st.bar_chart(filtered["color"].value_counts())

        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Card Categories")
            st.bar_chart(filtered["category"].value_counts())
        with c4:
            st.subheader("Rarity Breakdown")
            st.bar_chart(filtered["rarity"].str.capitalize().value_counts())

# -------------------- TAB 4: CSV TABLE --------------------
with tab_table:
    st.dataframe(
        filtered[export_cols],
        use_container_width=True,
        hide_index=True,
        height=640,
    )

