# Aura TCG card viewer and deck editor

The Streamlit app renders the card catalog using the Roblox card builder's 5:7 layout, frame assets, card back, colors, and available artwork. The catalog includes Alpha, Beta, Delta, Chi, Psi, Omega, and the basic-land variants. Click a card to turn it over, filter the gallery, or use the deck editor and Roblox deck export.

The CSV files and `basic_lands.json` are snapshots of the corresponding Roblox Luau data. When card definitions change in Roblox, update these files and the artwork in `static` to keep the app aligned. Cards without artwork use a colored placeholder. The web renderer is a separate implementation, so rendering may differ from Roblox.

## Run locally

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Static file serving is enabled in `.streamlit/config.toml`; retain that setting when deploying.

Chi, Psi, and Omega are 15-card mini-expansions. Chi rewards confronting and responding, Psi explores the Pit and resource recovery by color, and Omega closes the initial lineup with straightforward early plays and late-game payoffs. The viewer and Luau exports expose card data. Match resolution belongs to the Roblox server.
