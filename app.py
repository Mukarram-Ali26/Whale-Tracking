import streamlit as st
import pandas as pd
import time
from urllib.parse import unquote
from pymongo import MongoClient
from hyperliquid.info import Info
from hyperliquid.utils import constants
import os

# Streamlit settings
st.set_page_config(page_title="Hyperdash Whale Tracker", layout="wide")

# CSS Styling
st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: white; }
.wallet-header { background-color: #1f1f1f; color: #00ff99; padding: 8px 15px; border-radius: 10px; display: inline-block; font-weight: bold; font-size: 18px; }
.type-pill { padding: 4px 10px; border-radius: 8px; color: white; font-weight: bold; display: inline-block; }
.short-pill { background-color: #e60000; }
.long-pill { background-color: #00cc66; }
.pnl-green { color: #00ff99; font-weight: bold; }
.pnl-red { color: #ff4d4d; font-weight: bold; }
.datatable-cell { white-space: pre-line; }
a.wallet-link { color: #00ff99; text-decoration: none; }
a.wallet-link:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# MongoDB setup
MONGO_URI = st.secrets("MONGO_URI", "mongodb+srv://tracker_user:password@cluster0.mongodb.net/?retryWrites=true&w=majority")
client = MongoClient(MONGO_URI)
db = client["hypertracker"]
changes_collection = db["position_changes"]

# Session state initialization
for key in ["wallets", "selected_wallet", "position_history", "pnl_history", "latest_positions_data"]:
    if key not in st.session_state:
        st.session_state[key] = {} if 'history' in key else [] if key == "wallets" else None

# Setup Hyperliquid Info
info = Info(constants.MAINNET_API_URL, skip_ws=True)

def detect_changes(wallet, new_positions):
    old_positions = st.session_state.position_history.get(wallet, {})
    changes = []
    for pos in new_positions:
        coin = pos["coin"]
        size = float(pos["szi"])
        old_size = float(old_positions.get(coin, {}).get("szi", 0))
        if size != old_size:
            action = "Opened" if old_size == 0 and size != 0 else "Closed" if size == 0 else "Updated"
            change = {
                "wallet": wallet,
                "coin": coin,
                "action": action,
                "old_size": old_size,
                "new_size": size,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }
            changes.append(change)
        if size != 0:
            st.session_state.position_history.setdefault(wallet, {})[coin] = pos
        elif coin in st.session_state.position_history.get(wallet, {}):
            del st.session_state.position_history[wallet][coin]
    if changes:
        changes_collection.insert_many(changes)
    return changes

def get_positions(wallet):
    if not wallet or not isinstance(wallet, str) or not wallet.startswith("0x") or len(wallet) != 42:
        raise ValueError(f"Invalid wallet address: {wallet}")
    try:
        state = info.user_state(wallet)
        positions = state.get("assetPositions", [])
        changes = detect_changes(wallet, [p["position"] for p in positions])
        rows = []
        for pos in positions:
            p = pos["position"]
            coin = p["coin"]
            size = float(p["szi"])
            type_str = "SHORT" if size < 0 else "LONG"
            leverage = f"{pos.get('leverage', 1)}x"
            entry = float(p.get("entryPx", 0))
            liq = float(p.get("liqPx", 0))
            current = float(pos.get("markPx", 0))
            pnl = float(p.get("unrealizedPnl", 0))
            funding = float(p.get("fundingFee", 0))
            position_value = abs(size) * current
            pnl_pct = (pnl / (abs(size) * entry)) * 100 if entry else 0

            rows.append({
                "Asset": f"{coin}<br>{leverage}",
                "Type": f"<span class='type-pill {'short-pill' if type_str == 'SHORT' else 'long-pill'}'>{type_str}</span>",
                "Position Value / Size": f"${position_value:,.2f}<br><span style='color:gray'>{size:,.2f} {coin}</span>",
                "Unrealized PnL": f"<span class='{'pnl-green' if pnl >= 0 else 'pnl-red'}'>${pnl:,.2f}<br>{pnl_pct:.2f}%</span>",
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

# URL param integration
query_params = st.query_params
if "wallet" in query_params:
    url_wallet = unquote(query_params["wallet"][0])
    if url_wallet and url_wallet not in st.session_state.wallets:
        st.session_state.wallets.append(url_wallet)
    st.session_state.selected_wallet = url_wallet

# Sidebar wallet management
st.sidebar.header("🔍 Track Multiple Wallets")
new_wallet = st.sidebar.text_input("Enter Wallet Address")

if st.sidebar.button("➕ Add to Tracking"):
    if new_wallet and new_wallet.startswith("0x") and len(new_wallet) == 42 and new_wallet not in st.session_state.wallets:
        st.session_state.wallets.append(new_wallet)
        st.session_state.selected_wallet = new_wallet

page = st.sidebar.radio("📄 Page", ["Live Positions", "Position Changes"])

wallet_options = st.session_state.wallets
selected_wallet = st.session_state.selected_wallet
if selected_wallet not in wallet_options and wallet_options:
    selected_wallet = wallet_options[0]
    st.session_state.selected_wallet = selected_wallet

if wallet_options:
    st.sidebar.markdown("**👥 Traders**")
    for wallet in wallet_options:
        if st.sidebar.button(wallet, key=f"wallet_{wallet}"):
            st.session_state.selected_wallet = wallet
            st.query_params.update({"wallet": wallet})

    if st.sidebar.button("🗑️ Remove Trader"):
        confirm_key = f"confirm_remove_{st.session_state.selected_wallet}"
        st.session_state[confirm_key] = True

    confirm_key = f"confirm_remove_{st.session_state.selected_wallet}"
    if st.session_state.get(confirm_key):
        if st.sidebar.button("✅ Confirm Remove"):
            st.session_state.wallets.remove(st.session_state.selected_wallet)
            st.session_state.selected_wallet = st.session_state.wallets[0] if st.session_state.wallets else None
            del st.session_state[confirm_key]
        if st.sidebar.button("❌ Cancel"):
            del st.session_state[confirm_key]

# Auto-refresh
REFRESH_INTERVAL = 30
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    st.session_state.last_refresh = time.time()
    st.rerun()
else:
    remaining = REFRESH_INTERVAL - int(time.time() - st.session_state.last_refresh)
    st.sidebar.info(f"⏳ Auto-refreshing in {remaining} seconds...")

# Main pages
if page == "Live Positions":
    if selected_wallet:
        st.markdown(f"### 👤 Wallet: <span class='wallet-header'>{selected_wallet}</span>", unsafe_allow_html=True)
        df, _ = get_positions(selected_wallet)
        if not df.empty:
            render_html_table(df)
            st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info("No open positions found.")
    else:
        st.info("Select a wallet to view positions.")

elif page == "Position Changes":
    st.header("🔄 Detected Position Changes")
    all_changes = []
    for wallet in st.session_state.wallets:
        try:
            _, changes = get_positions(wallet)
            all_changes.extend(changes)
        except Exception as e:
            st.warning(f"Skipping wallet {wallet} due to error: {e}")

    if all_changes:
        change_df = pd.DataFrame(all_changes)
        st.dataframe(change_df, use_container_width=True)
    else:
        st.info("No position changes detected yet.")
