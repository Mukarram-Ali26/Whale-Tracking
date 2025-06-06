from hyperliquid.info import Info
from hyperliquid.utils import constants
import time

info = Info(constants.MAINNET_API_URL, skip_ws=True)

def detect_changes(wallet, new_positions, session_state):
    old_positions = session_state.position_history.get(wallet, {})
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
            session_state.position_history.setdefault(wallet, {})[key] = pos
        elif key in session_state.position_history.get(wallet, {}):
            del session_state.position_history[wallet][key]
    return changes

def get_positions(wallet):
    from streamlit import session_state as st
    import pandas as pd

    try:
        state = info.user_state(wallet)
        positions = state.get("assetPositions", [])
        changes = detect_changes(wallet, [p["position"] for p in positions], st)
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
        import streamlit as st
        st.error(f\"Error fetching data for wallet {wallet}: {e}\")
        return pd.DataFrame(), []
