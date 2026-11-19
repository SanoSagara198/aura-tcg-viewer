from __future__ import annotations

import html
import math
import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="AURA! TCG — Comic Edition Card Viewer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).parent
CSV_FILES = [
    ("Alpha", ROOT / "aura_alpha_set.csv"),
    ("Beta", ROOT / "aura_beta_set.csv"),
    ("Delta", ROOT / "aura_delta_set.csv"),
]

COMIC_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=Barlow+Condensed:ital,wght@0,600;0,700;0,800;1,700&family=Chakra+Petch:ital,wght@0,500;0,600;0,700;1,600&family=Comic+Neue:ital,wght@0,700;1,700&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #0a0b10;
    --paper: #fffdf4;
    --yellow: #ffe24a;
  }

  .stApp {
    background-color: #11131b;
    background-image:
      radial-gradient(rgba(255, 226, 74, 0.06) 1.5px, transparent 1.5px),
      radial-gradient(circle at top, #1f2538 0%, #0d0f17 65%);
    background-size: 18px 18px, 100% 100%;
    font-family: 'Chakra Petch', 'Segoe UI', system-ui, sans-serif;
  }

  .aura-banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    background: #1a1e2b;
    border: 4px solid var(--ink);
    box-shadow: 6px 6px 0 var(--ink);
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 18px;
  }

  .aura-banner-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .aura-logo {
    font-family: 'Bangers', Impact, sans-serif;
    font-size: 2.2rem;
    letter-spacing: 0.08em;
    color: var(--yellow);
    background: #e11d48;
    padding: 4px 16px 2px;
    border: 3px solid var(--ink);
    box-shadow: 4px 4px 0 var(--ink);
    transform: skewX(-7deg) rotate(-1.5deg);
    text-shadow: 2px 2px 0 var(--ink);
    line-height: 1.05;
  }

  .aura-title h1 {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #f3f5fa;
    margin: 0;
    line-height: 1.15;
  }

  .aura-title p {
    font-size: 0.86rem;
    color: #a6afc4;
    margin: 3px 0 0;
  }

  .aura-tip {
    background: var(--yellow);
    color: var(--ink);
    border: 2.5px solid var(--ink);
    box-shadow: 3px 3px 0 var(--ink);
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 800;
    font-size: 0.85rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 5px 12px;
    transform: skewX(-5deg);
  }

  /* ==================== COMIC GRID & PURE-CSS 3D FLIP ==================== */
  .aura-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(288px, 1fr));
    gap: 2rem 1.55rem;
    padding: 10px 4px 28px;
  }

  .card-scene {
    display: block;
    perspective: 1100px;
    min-height: 422px;
    cursor: pointer;
    user-select: none;
  }

  .flip-chk {
    display: none;
  }

  .card-flipper {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 422px;
    transform-style: preserve-3d;
    transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .flip-chk:checked ~ .card-flipper {
    transform: rotateY(180deg);
  }

  .card-face {
    position: relative;
    width: 100%;
    min-height: 422px;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
    border-radius: 12px;
    border: 4px solid var(--ink);
    box-shadow: 7px 8px 0 var(--ink);
    transition: transform 0.14s ease, box-shadow 0.14s ease;
    display: flex;
    flex-direction: column;
    overflow: visible;
  }

  .card-scene:hover .card-face {
    transform: translate(-3px, -5px);
    box-shadow: 11px 13px 0 var(--ink);
  }

  .card-front {
    --c-bg1: #fff3b0;
    --c-bg2: #f4c430;
    --c-art1: #fef08a;
    --c-art2: #d97706;
    --c-tag-bg: #ffe24a;
    --c-tag-ink: #0a0b10;
    --c-dot: rgba(10, 11, 16, 0.14);
    padding: 10px 10px 12px;
    background-color: var(--c-bg1);
    background-image:
      radial-gradient(var(--c-dot) 1.6px, transparent 1.6px),
      linear-gradient(155deg, var(--c-bg1) 0%, var(--c-bg2) 100%);
    background-size: 9px 9px, 100% 100%;
    color: var(--ink);
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
    content: "";
    position: absolute;
    inset: 3px;
    border-radius: 7px;
    border: 2.5px dashed rgba(255, 250, 205, 0.72);
    pointer-events: none;
  }

  .comic-header {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 8px;
    position: relative;
    z-index: 3;
  }

  .energy-burst {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: var(--ink);
    border: 2.5px solid var(--ink);
    box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.45);
    padding: 3px 5px;
    border-radius: 8px;
    transform: rotate(-3deg);
    flex-shrink: 0;
  }

  .energy-burst.empty { display: none; }

  .pip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 21px;
    height: 21px;
    border-radius: 50%;
    font-family: 'Barlow Condensed', Impact, sans-serif;
    font-size: 0.82rem;
    font-weight: 800;
    border: 2px solid var(--ink);
    box-shadow: inset -1px -2px 0 rgba(0, 0, 0, 0.28), inset 1px 1px 0 rgba(255, 255, 255, 0.55);
    line-height: 1;
  }

  .pip-W { background: #fff4b8; color: #1c1404; }
  .pip-U { background: #38bdf8; color: #082f49; }
  .pip-B { background: #9333ea; color: #ffffff; }
  .pip-R { background: #ef4444; color: #ffffff; }
  .pip-G { background: #22c55e; color: #052e16; }
  .pip-N { background: #e2e8f0; color: #0f172a; }
  .pip-T { background: #ffe24a; color: #0a0b10; font-size: 0.78rem; }

  .title-plate {
    flex: 1;
    min-width: 0;
    background: var(--ink);
    border: 2.5px solid #ffffff;
    outline: 2.5px solid var(--ink);
    box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.45);
    padding: 4px 10px 3px;
    transform: skewX(-6deg);
  }

  .card-name {
    display: block;
    font-family: 'Bangers', Impact, sans-serif;
    font-size: 1.28rem;
    letter-spacing: 0.055em;
    line-height: 1.05;
    color: #ffffff;
    text-shadow: 2px 2px 0 #000000;
    transform: skewX(6deg);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .art-panel {
    position: relative;
    height: 146px;
    border: 3.5px solid var(--ink);
    border-radius: 6px;
    background:
      repeating-conic-gradient(
        from 0deg at 50% 48%,
        rgba(255, 255, 255, 0.18) 0deg 8deg,
        transparent 8deg 18deg
      ),
      radial-gradient(circle at 50% 48%, var(--c-art1) 0%, var(--c-art2) 78%, #090b12 100%);
    overflow: hidden;
    box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: -14px;
    clip-path: polygon(0 0, 100% 0, 100% 89%, 0 100%);
  }

  .art-burst {
    width: 82px;
    height: 82px;
    background: rgba(255, 255, 255, 0.24);
    border: 3px solid rgba(10, 11, 16, 0.55);
    transform: rotate(45deg);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 4px 4px 0 rgba(10, 11, 16, 0.35);
  }

  .art-burst span {
    transform: rotate(-45deg);
    font-family: 'Bangers', sans-serif;
    font-size: 0.92rem;
    letter-spacing: 0.08em;
    color: var(--ink);
    text-align: center;
    line-height: 1.05;
  }

  .annex-stamp {
    position: absolute;
    top: 7px;
    right: 7px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--yellow);
    color: var(--ink);
    border: 2.5px solid var(--ink);
    box-shadow: 2px 2px 0 var(--ink);
    font-family: 'Bangers', sans-serif;
    font-size: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2;
  }

  .comic-type-strip {
    position: relative;
    z-index: 4;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
    margin: 0 4px 8px;
    padding: 4px 9px;
    background: var(--c-tag-bg);
    color: var(--c-tag-ink);
    border: 3px solid var(--ink);
    box-shadow: 4px 4px 0 var(--ink);
    transform: skewX(-6deg) rotate(-1deg);
  }

  .comic-type-strip > * {
    transform: skewX(6deg);
  }

  .type-text {
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 800;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .rarity-stamp {
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 800;
    font-size: 0.72rem;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    padding: 1px 7px;
    border: 2px solid var(--ink);
    border-radius: 3px;
    box-shadow: 2px 2px 0 var(--ink);
  }
  .rarity-stamp.common   { background: #334155; color: #f8fafc; }
  .rarity-stamp.uncommon { background: #38bdf8; color: #082f49; }
  .rarity-stamp.rare     { background: #f59e0b; color: #0a0b10; }

  .comic-rules-box {
    position: relative;
    flex: 1;
    background-color: var(--paper);
    background-image: radial-gradient(rgba(10, 11, 16, 0.055) 1.2px, transparent 1.2px);
    background-size: 8px 8px;
    border: 3px solid var(--ink);
    border-radius: 6px;
    box-shadow: 4px 4px 0 var(--ink);
    padding: 9px 10px 10px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 7px;
    color: #14161f;
  }

  .rules-lines {
    font-family: 'Comic Neue', 'Chakra Petch', sans-serif;
    font-size: 0.83rem;
    font-weight: 700;
    line-height: 1.32;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .rules-lines p { margin: 0; }

  .rules-lines .pip {
    width: 17px;
    height: 17px;
    font-size: 0.68rem;
    vertical-align: -2px;
    margin: 0 1px;
  }

  .rules-lines .kw {
    font-family: 'Barlow Condensed', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #b91c1c;
    font-weight: 800;
  }

  .rules-lines .rem {
    font-weight: 700;
    color: #475569;
    font-style: italic;
  }

  .flavor-caption {
    background: #fef08a;
    border: 2px solid var(--ink);
    box-shadow: 2px 2px 0 var(--ink);
    padding: 4px 7px;
    font-family: 'Comic Neue', serif;
    font-style: italic;
    font-weight: 700;
    font-size: 0.74rem;
    line-height: 1.25;
    color: #1c1917;
    transform: rotate(-0.6deg);
  }

  .comic-footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 8px;
    gap: 8px;
    position: relative;
    z-index: 4;
  }

  .issue-stamp {
    background: var(--ink);
    color: #ffffff;
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 800;
    font-size: 0.74rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 3px 8px;
    border-radius: 3px;
    border: 2px solid rgba(255, 255, 255, 0.35);
    box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.5);
  }

  .stat-cluster {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-bottom: -4px;
    margin-right: -2px;
  }

  .stat-badge {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-width: 38px;
    padding: 2px 7px 1px;
    border: 3px solid var(--ink);
    box-shadow: 3px 3px 0 var(--ink);
    line-height: 1;
    transform: skewX(-7deg);
  }

  .stat-badge .lbl {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.56rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    transform: skewX(7deg);
  }

  .stat-badge .val {
    font-family: 'Bangers', Impact, sans-serif;
    font-size: 1.32rem;
    letter-spacing: 0.04em;
    transform: skewX(7deg);
  }

  .stat-pow {
    background: #ef4444;
    color: #ffffff;
    text-shadow: 1.5px 1.5px 0 var(--ink);
  }

  .stat-tgh {
    background: #38bdf8;
    color: #082f49;
  }

  /* ==================== COMIC CARD BACK ==================== */
  .card-back {
    position: absolute;
    inset: 0;
    transform: rotateY(180deg);
    background-color: #13182b;
    background-image:
      repeating-conic-gradient(
        from 8deg at 50% 50%,
        rgba(255, 226, 74, 0.1) 0deg 9deg,
        transparent 9deg 20deg
      ),
      radial-gradient(rgba(255, 255, 255, 0.11) 1.5px, transparent 1.5px),
      radial-gradient(circle at 50% 50%, #2b3564 0%, #0f1324 72%);
    background-size: 100% 100%, 10px 10px, 100% 100%;
    padding: 14px;
    align-items: center;
    justify-content: space-between;
    overflow: hidden;
  }

  .back-inner {
    width: 100%;
    height: 100%;
    border: 3.5px solid var(--yellow);
    outline: 3px solid var(--ink);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    padding: 16px 12px;
  }

  .back-issue {
    background: var(--yellow);
    color: var(--ink);
    border: 2.5px solid var(--ink);
    box-shadow: 3px 3px 0 var(--ink);
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 800;
    font-size: 0.78rem;
    letter-spacing: 0.1em;
    padding: 2px 10px;
    transform: skewX(-6deg);
  }

  .back-emblem {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
  }

  .back-logo {
    font-family: 'Bangers', Impact, sans-serif;
    font-size: 3.3rem;
    letter-spacing: 0.08em;
    color: var(--yellow);
    -webkit-text-stroke: 2.5px var(--ink);
    text-shadow: 5px 5px 0 #e11d48, 8px 8px 0 var(--ink);
    transform: rotate(-6deg) skewX(-6deg);
    line-height: 1;
  }

  .back-wheel {
    display: flex;
    gap: 8px;
    background: rgba(10, 11, 16, 0.78);
    border: 3px solid var(--ink);
    box-shadow: 4px 4px 0 var(--ink);
    padding: 7px 11px;
    border-radius: 999px;
    transform: rotate(-2deg);
  }

  .back-wheel .pip {
    width: 24px;
    height: 24px;
    font-size: 0.85rem;
  }

  .back-tagline {
    background: #e11d48;
    color: #ffffff;
    border: 2.5px solid var(--ink);
    box-shadow: 3px 3px 0 var(--ink);
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 800;
    font-size: 0.8rem;
    letter-spacing: 0.12em;
    padding: 3px 12px;
    transform: skewX(-6deg);
  }
</style>
"""


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


@st.cache_data(show_spinner=False)
def load_cards() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for set_name, path in CSV_FILES:
        if path.exists():
            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
            if "set" not in df.columns:
                df.insert(0, "set", set_name)
            df["set_number"] = range(1, len(df) + 1)
            frames.append(df)
    if not frames:
        return pd.DataFrame(
            columns=[
                "set", "name", "color", "rarity", "energy_cost",
                "card_type", "power", "toughness", "rules_text", "flavor_text", "set_number",
            ]
        )
    all_df = pd.concat(frames, ignore_index=True)
    all_df["energy_value"] = all_df["energy_cost"].map(energy_value)
    all_df["atk_num"] = all_df["power"].map(safe_int)
    all_df["base_type"] = all_df["card_type"].map(lambda t: str(t).split("—")[0].strip())
    return all_df


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
            r"^([A-Za-z][A-Za-z0-9 \-]+?(?:\s+<span class=\"pip[^\"]*\">[^<]+</span>)*)\s+(\([^)]+\)\.?)",
            r'<span class="kw">\1</span> <span class="rem">\2</span>',
            with_pips,
        )
        paragraphs.append(f"<p>{styled}</p>")
    return "".join(paragraphs)


def render_card_html(row: pd.Series, flip_all: bool, uid: str) -> str:
    name = html.escape(str(row["name"]))
    color = html.escape(str(row["color"]))
    rarity = html.escape(str(row["rarity"]).lower())
    card_type = html.escape(str(row["card_type"]))
    set_label = html.escape(str(row["set"] or "ALPHA").upper())
    num = f"{int(row['set_number']):03d}"
    pips_html = render_pips(html.escape(str(row["energy_cost"])))
    rar_icon = "★" if rarity == "rare" else ("◆" if rarity == "uncommon" else "●")
    rules_html = render_rules(str(row["rules_text"]))
    flavor = str(row["flavor_text"]).strip()
    flavor_html = f'<div class="flavor-caption">“{html.escape(flavor)}”</div>' if flavor else ""

    pow_str = str(row["power"]).strip()
    tgh_str = str(row["toughness"]).strip()
    stats_html = ""
    if pow_str != "":
        stats_html = (
            '<div class="stat-cluster">'
            f'<div class="stat-badge stat-pow"><span class="lbl">ATK</span><span class="val">{html.escape(pow_str)}</span></div>'
            f'<div class="stat-badge stat-tgh"><span class="lbl">DEF</span><span class="val">{html.escape(tgh_str)}</span></div>'
            "</div>"
        )

    checked_attr = "checked" if flip_all else ""
    empty_cls = "" if pips_html else " empty"

    return (
        f'<label class="card-scene" for="{uid}">'
        f'<input class="flip-chk" type="checkbox" id="{uid}" {checked_attr} />'
        '<div class="card-flipper">'
        f'<article class="card-face card-front {color} rarity-{rarity}">'
        '<div class="comic-header">'
        f'<div class="energy-burst{empty_cls}">{pips_html}</div>'
        f'<div class="title-plate"><span class="card-name" title="{name}">{name}</span></div>'
        "</div>"
        '<div class="art-panel">'
        f'<div class="art-burst"><span>{color}<br/>ART</span></div>'
        '<div class="annex-stamp" title="Card Info">?</div>'
        "</div>"
        '<div class="comic-type-strip">'
        f'<span class="type-text">{card_type}</span>'
        f'<span class="rarity-stamp {rarity}">{rar_icon} {rarity}</span>'
        "</div>"
        '<div class="comic-rules-box">'
        f'<div class="rules-lines">{rules_html}</div>'
        f"{flavor_html}"
        "</div>"
        '<div class="comic-footer">'
        f'<span class="issue-stamp">{set_label} #{num}</span>'
        f"{stats_html}"
        "</div>"
        "</article>"
        '<div class="card-face card-back">'
        '<div class="back-inner">'
        '<div class="back-issue">ISSUE № 01 · 1ST ED</div>'
        '<div class="back-emblem">'
        '<div class="back-logo">AURA!</div>'
        '<div class="back-wheel">'
        '<span class="pip pip-W">W</span>'
        '<span class="pip pip-U">U</span>'
        '<span class="pip pip-B">B</span>'
        '<span class="pip pip-R">R</span>'
        '<span class="pip pip-G">G</span>'
        "</div>"
        "</div>"
        '<div class="back-tagline">TRADING CARD GAME</div>'
        "</div>"
        "</div>"
        "</div>"
        "</label>"
    )


# ==================== APP LAYOUT ====================
st.markdown(COMIC_CSS, unsafe_allow_html=True)
df = load_cards()

st.markdown(
    """
    <div class="aura-banner">
      <div class="aura-banner-left">
        <div class="aura-logo">AURA!</div>
        <div class="aura-title">
          <h1>Comic Edition · Alpha · Beta · Delta</h1>
          <p>1,050 Original Cards · Pop-Art Ink Frame · Energy · Mudra · Mantra · Seal</p>
        </div>
      </div>
      <div class="aura-tip">Click any card to flip Front ↔ Back</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar Filters
with st.sidebar:
    st.markdown("### ⚡ Filter Cards")
    search = st.text_input("Search", placeholder="Name, type, rules, or flavor...")
    set_choice = st.selectbox("Set", ["All", "Alpha", "Beta", "Delta"])
    color_options = ["White", "Blue", "Black", "Red", "Green", "Multicolor", "Artifact", "Land"]
    selected_colors = st.multiselect("Colors", color_options, placeholder="All colors")
    type_choice = st.selectbox(
        "Card Type",
        ["All", "Creature", "Mudra", "Mantra", "Seal", "Artifact", "Land"],
    )
    rarity_choice = st.selectbox("Rarity", ["All", "common", "uncommon", "rare"])
    sort_choice = st.selectbox(
        "Sort By",
        ["Set Order", "Energy: Low → High", "Energy: High → Low", "Name: A → Z", "ATK: High → Low"],
    )

    st.divider()
    flip_all = st.toggle("Show Card Backs", value=False)
    page_size = st.select_slider("Cards per Page", options=[24, 48, 96, 200], value=48)

# Apply Filters
filtered = df.copy()
if set_choice != "All":
    filtered = filtered[filtered["set"] == set_choice]
if selected_colors:
    filtered = filtered[filtered["color"].isin(selected_colors)]
if type_choice != "All":
    if type_choice == "Creature":
        filtered = filtered[filtered["card_type"].str.contains("Creature|Casting", case=False, na=False)]
    else:
        filtered = filtered[filtered["card_type"].str.contains(type_choice, case=False, na=False)]
if rarity_choice != "All":
    filtered = filtered[filtered["rarity"].str.lower() == rarity_choice]
if search.strip():
    q = search.strip()
    mask = (
        filtered["name"].str.contains(q, case=False, na=False)
        | filtered["card_type"].str.contains(q, case=False, na=False)
        | filtered["rules_text"].str.contains(q, case=False, na=False)
        | filtered["flavor_text"].str.contains(q, case=False, na=False)
    )
    filtered = filtered[mask]

if sort_choice == "Energy: Low → High":
    filtered = filtered.sort_values(["energy_value", "name"], ascending=[True, True])
elif sort_choice == "Energy: High → Low":
    filtered = filtered.sort_values(["energy_value", "name"], ascending=[False, True])
elif sort_choice == "Name: A → Z":
    filtered = filtered.sort_values("name", ascending=True)
elif sort_choice == "ATK: High → Low":
    filtered = filtered.sort_values(["atk_num", "name"], ascending=[False, True])

total_shown = len(filtered)
with st.sidebar:
    st.divider()
    st.caption(f"Showing **{total_shown:,}** of **{len(df):,}** cards")
    export_cols = [
        "set", "name", "color", "rarity", "energy_cost",
        "card_type", "power", "toughness", "rules_text", "flavor_text",
    ]
    st.download_button(
        "⬇ Download Filtered CSV",
        data=filtered[export_cols].to_csv(index=False).encode("utf-8"),
        file_name=f"aura_filtered_{set_choice.lower()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# Main Tabs
tab_gallery, tab_analytics, tab_table = st.tabs(
    [f"🃏 Comic Gallery ({total_shown})", "📊 Set Analytics", "📋 CSV Table"]
)

with tab_gallery:
    if total_shown == 0:
        st.info("No cards match your current filters.")
    else:
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
            render_card_html(row, flip_all=flip_all, uid=f"c_{page_num}_{idx}")
            for idx, (_, row) in enumerate(page_df.iterrows())
        )
        st.markdown(f'<div class="aura-grid">{cards_html}</div>', unsafe_allow_html=True)

with tab_analytics:
    if total_shown == 0:
        st.info("No cards to analyze for the current filter.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Matching Cards", f"{total_shown:,}")
        m2.metric("Avg Energy Cost", f"{filtered['energy_value'].mean():.2f}")
        m3.metric("Rares", int((filtered["rarity"].str.lower() == "rare").sum()))
        m4.metric(
            "Creatures",
            int(filtered["card_type"].str.contains("Creature|Casting", case=False, na=False).sum()),
        )

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Energy Cost Curve")
            curve = filtered["energy_value"].value_counts().sort_index()
            st.bar_chart(curve)
        with c2:
            st.subheader("Color Distribution")
            colors = filtered["color"].value_counts()
            st.bar_chart(colors)

        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Base Card Types")
            st.bar_chart(filtered["base_type"].value_counts())
        with c4:
            st.subheader("Rarity Breakdown")
            st.bar_chart(filtered["rarity"].str.capitalize().value_counts())

with tab_table:
    st.dataframe(
        filtered[export_cols],
        use_container_width=True,
        hide_index=True,
        height=640,
    )
