import streamlit as st
import pandas as pd
import time
from hyperliquid.info import Info
from hyperliquid.utils import constants
from streamlit.components.v1 import html

st.set_page_config(page_title="Hyperliquid Whale Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0e0e0e;
        color: white;
    }
    .wallet-header {
        background-color: #1f1f1f;
        color: #00ff99;
        padding: 8px 15px;
        border-radius: 10px;
        display: inline-block;
        font-weight: bold;
        font-size: 18px;
    }
    .type-pill {
        padding: 4px 10px;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        display: inline-block;
    }
    .short-pill {
        background-color: #e60000;
    }
    .long-pill {
        background-color: #00cc66;
    }
    .pnl-green {
        color: #00ff99;
        font-weight: bold;
    }
    .pnl-red {
        color: #ff4d4d;
        font-weight: bold;
    }
    .datatable-cell {
        white-space: pre-line;
    }
    </style>
""", unsafe_allow_html=True)

info = Info(constants.MAINNET_API_URL, skip_ws=True)

# Sidebar for wallet input
st.sidebar.header("🔍 Track Multiple Wallets")
new_wallet = st.sidebar.text_input("Enter Wallet Address")
if "wallets" not in st.session_state:
    st.session_state.wallets = []
if "position_history" not in st.session_state:
    st.session_state.position_history = {}
if st.sidebar.button("➕ Add to Tracking"):
    if new_wallet and new_wallet not in st.session_state.wallets:
        st.session_state.wallets.append(new_wallet)

# Navigation
page = st.sidebar.radio("📄 Page", ["Live Positions", "Position Changes"])

# Auto refresh every 30 seconds
REFRESH_INTERVAL = 30  # seconds
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    st.session_state.last_refresh = time.time()
    st.rerun()
else:
    remaining = REFRESH_INTERVAL - int(time.time() - st.session_state.last_refresh)
    st.sidebar.info(f"⏳ Auto-refreshing in {remaining} seconds...")

def detect_changes(wallet, new_positions):
    old_positions = st.session_state.position_history.get(wallet, {})
    changes = []
    for pos in new_positions:
        coin = pos["coin"]
        size = float(pos["szi"])
        key = coin
        old_size = float(old_positions.get(key, {}).get("szi", 0))
        if size != old_size:
            action = "Opened" if old_size == 0 and size != 0 else "Closed" if size == 0 else "Updated"
            changes.append({
                "wallet": wallet,
                "coin": coin,
                "action": action,
                "old_size": old_size,
                "new_size": size,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            })
        if size != 0:
            st.session_state.position_history.setdefault(wallet, {})[key] = pos
        elif key in st.session_state.position_history.get(wallet, {}):
            del st.session_state.position_history[wallet][key]
    return changes

def get_real_positions(wallet):
    try:
        state = info.user_state(wallet)
        positions = state.get("assetPositions", [])
        changes = detect_changes(wallet, [p["position"] for p in positions])
        rows = []
        for pos in positions:
            position = pos["position"]
            coin = position["coin"]
            size = float(position["szi"])
            type_str = "SHORT" if size < 0 else "LONG"
            leverage = f"{pos.get('leverage', 1)}x"
            entry = float(position.get("entryPx", 0))
            liq = float(position.get("liqPx", 0))
            current = float(pos.get("markPx", 0))
            pnl = float(position.get("unrealizedPnl", 0))
            funding = float(position.get("fundingFee", 0))
            position_value = abs(size) * current
            pnl_pct = (pnl / (abs(size) * entry)) * 100 if entry else 0

            type_html = f"<span class='type-pill {'short-pill' if type_str == 'SHORT' else 'long-pill'}'>{type_str}</span>"
            value_str = f"${position_value:,.2f}"
            size_str = f"{size:,.2f} {coin}"
            value_cell = f"{value_str}<br><span style='color:gray'>{size_str}</span>"
            pnl_color_class = "pnl-green" if pnl >= 0 else "pnl-red"
            pnl_cell = f"<span class='{pnl_color_class}'>${pnl:,.2f}<br>{pnl_pct:.2f}%</span>"

            rows.append({
                "Asset": f"{coin}<br>{leverage}",
                "Type": type_html,
                "Position Value / Size": value_cell,
                "Unrealized PnL": pnl_cell,
                "Entry Price": f"${entry:,.2f}",
                "Current Price": f"${current:,.2f}",
                "Liq. Price": f"${liq:,.2f}" if liq > 0 else "N/A",
                "Margin Used": "N/A",
                "Funding": f"<span class='pnl-green'>${funding:,.2f}</span>"
            })
        return pd.DataFrame(rows), changes
    except Exception as e:
        st.error(f"Error fetching data for wallet {wallet}: {e}")
        return pd.DataFrame(), []

def render_html_table(df):
    headers = "".join([f"<th>{col}</th>" for col in df.columns])
    rows = ""
    for _, row in df.iterrows():
        row_html = "".join([f"<td class='datatable-cell'>{val}</td>" for val in row])
        rows += f"<tr>{row_html}</tr>"

    table_html = f"""
    <div style="overflow-x: auto;">
    <table style="width: 100%; border-collapse: collapse; font-size: 15px;">
        <thead style="background-color: #1a1a1a; color: white;">
            <tr>{headers}</tr>
        </thead>
        <tbody style="background-color: #121212;">{rows}</tbody>
    </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

if page == "Live Positions":
    for wallet in st.session_state.wallets:
        st.markdown(f"### 👤 Wallet: <span class='wallet-header'>{wallet}</span>", unsafe_allow_html=True)
        df, _ = get_real_positions(wallet)
        if not df.empty:
            render_html_table(df)
            st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info("No open positions found.")

elif page == "Position Changes":
    st.header("🔄 Detected Position Changes")
    all_changes = []
    for wallet in st.session_state.wallets:
        _, changes = get_real_positions(wallet)
        all_changes.extend(changes)

    if all_changes:
        change_df = pd.DataFrame(all_changes)
        st.dataframe(change_df, use_container_width=True)
    else:
        st.info("No position changes detected yet.")
