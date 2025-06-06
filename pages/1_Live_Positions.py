import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from utils import get_tracked_wallets
import time

st.set_page_config(page_title="Live Positions", page_icon="📈", layout="wide")
st.title("📈 Live Positions")

# Auto-refresh every 15 minutes
st.experimental_rerun_interval = 900

wallets = get_tracked_wallets()
if not wallets:
    st.info("No wallets being tracked. Add one from the sidebar.")
    st.stop()

selected_wallet = st.selectbox("Select wallet", ["All"] + wallets, index=0)

def fetch_wallet_data(wallet_address):
    url = "https://api.hyperliquid.xyz/info"
    try:
        # Get equity & positions
        equity_body = {"type": "clearinghouseState", "user": wallet_address}
        equity_resp = requests.post(url, json=equity_body)
        equity_data = equity_resp.json()
        equity = equity_data.get("accountValue", None)

        # Get positions
        positions_body = {"type": "perpPositions", "user": wallet_address}
        pos_resp = requests.post(url, json=positions_body)
        positions = pos_resp.json().get("positions", [])

        return equity, positions
    except Exception as e:
        st.error(f"Error fetching data for {wallet_address}: {e}")
        return None, []

all_rows = []

for wallet in wallets:
    if selected_wallet != "All" and wallet != selected_wallet:
        continue

    equity, positions = fetch_wallet_data(wallet)
    if equity is None:
        continue

    for pos in positions:
        sz = pos.get("sz", 0)
        if sz == 0:
            continue

        entry_px = pos.get("entryPx", 0)
        current_px = pos.get("markPx", 0)
        is_long = pos.get("isLong", True)
        notional = abs(sz) * current_px

        pnl = (current_px - entry_px) * sz if is_long else (entry_px - current_px) * sz
        roe = (pnl / notional) * 100 if notional != 0 else 0

        all_rows.append({
            "Wallet": wallet,
            "Market": pos.get("market", "N/A"),
            "Size": sz,
            "Entry Price": entry_px,
            "Mark Price": current_px,
            "PnL": round(pnl, 4),
            "ROE (%)": round(roe, 2),
            "Equity": round(equity, 2),
            "Direction": "Long" if is_long else "Short",
            "Updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })

if all_rows:
    df = pd.DataFrame(all_rows)

    def color_rows(row):
        color = "#d4f4dd" if row["Direction"] == "Long" else "#fddede"
        return [f"background-color: {color}"] * len(row)

    styled_df = df.style.apply(color_rows, axis=1)\
        .format({"PnL": "{:.2f}", "ROE (%)": "{:.2f}", "Equity": "{:.2f}"})

    st.dataframe(styled_df, use_container_width=True)
else:
    st.info("No open positions found.")
