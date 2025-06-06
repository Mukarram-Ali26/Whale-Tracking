### main.py

import streamlit as st
from wallet_manager import init_wallet_db, get_wallets, add_wallet, remove_wallet

# Initialize wallet database
init_wallet_db()

# Sidebar layout for navigation
st.sidebar.title("📊 Whale Tracker")

# Wallet management
st.sidebar.markdown("---")
new_wallet = st.sidebar.text_input("Enter Wallet Address")
if st.sidebar.button("➕ Add to Tracking"):
    if new_wallet and new_wallet.startswith("0x") and len(new_wallet) == 42:
        add_wallet(new_wallet)
        if "positions_cache" not in st.session_state:
            st.session_state["positions_cache"] = {}
        st.session_state["positions_cache"][new_wallet] = []  # Initialize with empty list
        st.sidebar.success("Wallet added successfully")

wallets = get_wallets()
if wallets:
    st.sidebar.markdown("**Tracked Wallets**")
    for wallet in wallets:
        st.sidebar.write(wallet)
    if st.sidebar.button("🗑️ Remove Last Wallet"):
        remove_wallet(wallets[-1])
        st.sidebar.success("Removed last wallet")
else:
    st.sidebar.info("No wallets tracked yet.")

# Navigation links

st.title("Welcome to Hyperliquid Whale Tracker 🐋")
st.write("Use the sidebar to navigate pages and manage wallets.")

# Initialize cache for tracking positions if not already set
if "positions_cache" not in st.session_state:
    st.session_state["positions_cache"] = {}

# Logic for comparison and storing changes can be done in 1_Live_Positions.py or a separate utility
