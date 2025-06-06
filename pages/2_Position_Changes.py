import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import requests
from config import DB_NAME
st.set_page_config(page_title="Position Changes", page_icon="🔁")
st.title("🔁 Position Changes")

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Fetch all wallets with changes
wallets = [row[0] for row in cursor.execute("SELECT DISTINCT wallet FROM position_changes").fetchall()]
wallet_filter = st.selectbox("Select wallet", ["All"] + wallets, index=0, key="wallet_filter")

# Fetch all changes
query = "SELECT wallet, timestamp, change_type, market, size, entry, direction FROM position_changes"
params = ()
if wallet_filter != "All":
    query += " WHERE wallet = ?"
    params = (wallet_filter,)
query += " ORDER BY timestamp DESC"

rows = cursor.execute(query, params).fetchall()

if not rows:
    st.info("No position changes found.")
else:
    # Show change events
    for wallet, timestamp, change_type, market, size, entry, direction in rows:
        with st.container():
            pill_color = {
                "New": "#2ecc71",
                "Close": "#e74c3c",
                "Increase": "#3498db",
                "Decrease": "#f1c40f",
            }.get(change_type, "#bdc3c7")

            st.markdown(
                f"""
                <div style='padding: 10px; border: 1px solid #444; border-radius: 8px; margin-bottom: 10px;'>
                    <span style='background-color:{pill_color}; color:white; padding:3px 8px; border-radius:15px; margin-right:10px;'>
                        {change_type}
                    </span>
                    <strong>{market}</strong>: {direction} {size} @ {entry}
                    <div style='font-size: small; color: gray;'>🕒 {timestamp} | Wallet: {wallet}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Timeline chart
    df = pd.DataFrame(rows, columns=["wallet", "timestamp", "change_type", "market", "size", "entry", "direction"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    st.subheader("📈 Timeline of Changes")
    fig = px.scatter(
        df,
        x="timestamp",
        y="market",
        color="change_type",
        symbol="direction",
        hover_data=["wallet", "size", "entry"],
        color_discrete_map={
            "New": "#2ecc71",
            "Close": "#e74c3c",
            "Increase": "#3498db",
            "Decrease": "#f1c40f",
        },
    )
    fig.update_layout(height=400, xaxis_title="Timestamp", yaxis_title="Market")
    st.plotly_chart(fig, use_container_width=True)

conn.close()

# Safe fetch utility for external API (e.g., Hyperliquid)
def safe_fetch_json(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        try:
            return response.json()
        except ValueError:
            raise Exception("Invalid JSON response.")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None
