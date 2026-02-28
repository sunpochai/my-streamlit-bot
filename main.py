import streamlit as st

import pandas as pd
import json
import os
from PIL import Image
import altair as alt
import math
import requests
from io import BytesIO
from datetime import datetime, timedelta, time # <--- [NEW] เพิ่ม Import datetime

# --- FIRESTORE SETUP ---
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore
from google.oauth2 import service_account
# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="QUANT-X | Analytics Core", layout="wide", initial_sidebar_state="expanded")

# CSS: Enterprise Dark Theme & Indicators
st.markdown("""
    <style>
    /* Global Settings */
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    
    /* KPI Cards */
    .kpi-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); border-color: #58a6ff; }
    .kpi-val { font-size: 2rem; font-weight: bold; margin: 0; color: #f0f6fc; }
    .kpi-lbl { font-size: 0.85rem; color: #8b949e; text-transform: uppercase; margin-top: 5px; letter-spacing: 1px; }
    
    /* Status Badges */
    .badge { padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.75rem; display: inline-block; }
    .bg-buy { background: rgba(35, 134, 54, 0.2); color: #4ade80; border: 1px solid #238636; }
    .bg-sell { background: rgba(218, 54, 51, 0.2); color: #f87171; border: 1px solid #da3633; }
    .bg-open { background: rgba(56, 139, 253, 0.2); color: #58a6ff; border: 1px solid #1f6feb; }
    .bg-closed { background: rgba(110, 118, 129, 0.2); color: #8b949e; border: 1px solid #30363d; }
    .bg-wait { background: rgba(110, 118, 129, 0.2); color: #8b949e; border: 1px solid #30363d; }

    /* KV Row Style for Data Inspector */
    .kv-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 6px 0;
        border-bottom: 1px solid rgba(48, 54, 61, 0.5);
        font-size: 0.85rem;
    }
    .kv-key { color: #8b949e; font-weight: 600; min-width: 100px; padding-right: 10px; }
    .kv-val { color: #e6edf3; font-family: 'Consolas', monospace; text-align: right; word-break: break-all; }
    
    /* Headers */
    .section-header { 
        font-size: 1.1rem; font-weight: 600; color: #58a6ff; 
        margin-bottom: 15px; border-bottom: 1px solid #30363d; padding-bottom: 8px; 
        display: flex; align-items: center; gap: 10px;
    }
    
    /* Code Block Style */
    code {
        font-family: 'Consolas', 'Courier New', monospace !important;
        font-size: 0.9rem !important;
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        color: #e6edf3 !important;
        padding: 10px !important;
        display: block;
        white-space: pre-wrap;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (FIRESTORE) ---
FIRESTORE_COLLECTION = "Signal-Trading-Journal" 
import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# ฟังก์ชันดึงข้อมูลจาก Secrets มาแปลงเป็น Dictionary



def init_firebase():
# ป้องกันการ Initialize ซ้ำเมื่อ Streamlit รีรัน
    if not firebase_admin._apps:
        try:
            # ดึงค่าจาก secrets และแปลงเป็น dict
            fb_info = dict(st.secrets["firebase"])
            
            # บังคับจัดการตัวอักษรขึ้นบรรทัดใหม่ให้ถูกต้อง
            if "private_key" in fb_info:
                fb_info["private_key"] = fb_info["private_key"].replace("\\n", "\n")
            
            cred = credentials.Certificate(fb_info)
            firebase_admin.initialize_app(cred)
            st.toast("เชื่อมต่อ Firebase สำเร็จ!", icon="🔥")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
            return None
            
    return firestore.client()
 

# เรียกใช้ฐานข้อมูล
db = init_firebase()


# Session State Management
if 'page' not in st.session_state: st.session_state.page = 'dashboard'
if 'selected_doc_id' not in st.session_state: st.session_state.selected_doc_id = None
if 'current_page_num' not in st.session_state: st.session_state.current_page_num = 1

def get_account_ids_from_firestore():
    if not db: return []
    try:
        docs = db.collection(FIRESTORE_COLLECTION).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
        accounts = set()
        for doc in docs:
            d = doc.to_dict()
            if 'sys_account' in d: accounts.add(d['sys_account'])
        return sorted(list(accounts))
    except Exception as e:
        st.error(f"Error fetching accounts: {e}")
        return []

@st.cache_data(ttl=300)
def load_firestore_data(account_id, limit=500):
    if not db: return []
    data = []
    try:
        try: target_account = int(account_id)
        except: target_account = account_id

        query = db.collection(FIRESTORE_COLLECTION)\
            .where("sys_account", "==", target_account)\
            .order_by("timestamp", direction=firestore.Query.DESCENDING)\
            .limit(limit)
             
        docs = query.stream()
        for doc in docs:
            item = doc.to_dict()
            item['firestore_id'] = doc.id
            data.append(item)
    except Exception as e:
        st.error(f"Firestore Query Error: {e}")
    return data

def navigate(page, doc_id=None):
    st.session_state.page = page
    st.session_state.selected_doc_id = doc_id
    st.rerun()

# --- 3. SIDEBAR ---
st.sidebar.title("☁️ QUANT-X Cloud")
st.sidebar.caption(f"DB: {FIRESTORE_COLLECTION}")
st.sidebar.markdown("---")

accounts = get_account_ids_from_firestore()
if not accounts:
    manual_account = st.sidebar.text_input("Manually Enter Account ID")
    if manual_account: accounts = [manual_account]

selected_account = st.sidebar.selectbox("📂 Account ID", accounts) if accounts else None

raw_data = []
if selected_account:
    limit_option = st.sidebar.select_slider("📅 Load Records Limit", options=[20, 100, 500], value=100)
    
    if db:
        with st.spinner(f"Fetching live signals..."):
            raw_data = load_firestore_data(selected_account, limit=limit_option)
        if raw_data: 
            st.sidebar.success(f"Synced: {len(raw_data)} Signals")
        else: 
            st.sidebar.warning("No records found.")
    else:
        st.sidebar.error("Database connection failed. Check Key File.")
else:
    st.sidebar.info("Please select Account ID.")

# --- 4. DASHBOARD PAGE ---
def render_dashboard():
    st.title("🛡️ Analytics Core v5.9")
    if not raw_data: return

    # --- DATA PROCESSING ---
    df_list = []
    for d in raw_data:
        ts = d.get('timestamp', pd.Timestamp.now())
        
        # ---------------------------------------------------------
        # 🔥 ลบอันเก่าออก (ที่เขียนว่า pd.to_datetime(ts) เฉยๆ)
        # แล้วใส่ก้อนนี้เข้าไปแทนครับ 👇👇👇
        # ---------------------------------------------------------
        try:
            # 1. บังคับอ่านค่าเวลาให้เป็น UTC (ป้องกัน Timezone ผสมกัน)
            dt_utc = pd.to_datetime(ts, utc=True)
            
            # 2. ล้าง Timezone ออกให้เป็นเวลาดิบๆ (Naive)
            dt_naive = dt_utc.tz_convert(None)
            
            # 3. บวก 7 ชั่วโมง (เพื่อให้เป็นเวลาไทยแน่นอน)
            local_time = dt_naive + pd.Timedelta(hours=7)
        except:
            # กันเหนียว: ถ้าข้อมูลเวลาพัง ให้ใช้วันนี้แทน
            local_time = pd.Timestamp.now()
        # ---------------------------------------------------------
        df_list.append({
            "FirestoreID": d.get('firestore_id'),
            "Time": local_time,
            "Symbol": d.get('symbol', 'UNKNOWN'), 
            "Action": d.get('s_action', 'WAIT'),
            "Strategy": d.get('s_strategy_label', 'General'), 
            "Conf": d.get('s_confidence_score', 0),
            "Status": d.get('trade_status', 'OPEN'),
            "PnL": d.get('r_net_pnl', 0.0),
            "Ticket": d.get('r_ticket', '-'),          
            "ExitReason": d.get('r_exit_reason', '-'), 
            "FullData": d 
        })
    df = pd.DataFrame(df_list)

    # --- [MODIFIED] FILTER BAR WITH DATE RANGE ---
    # หาค่าวันปัจจุบัน (UTC+7) เพื่อใช้เป็น Default
    now_th = datetime.utcnow() + timedelta(hours=7)
    today_date = now_th.date()

    with st.expander("🔍 Filter & Sort Options", expanded=True):
        # แถวแรก: Filters ทั่วไป
        f1, f2, f3 = st.columns(3)
        with f1: sel_sym = st.multiselect("Symbol", ["All"] + sorted(list(df['Symbol'].unique())), default=[])
        with f2: sel_act = st.multiselect("Action", ["All"] + sorted(list(df['Action'].astype(str).unique())), default=[])
        with f3: sel_strat = st.multiselect("Strategy", ["All"] + sorted(list(df['Strategy'].unique())), default=[])
        
        # แถวสอง: Date Range & Sort
        d1, d2 = st.columns([2, 1])
        with d1:
            # [NEW] Date Range Picker (Default = Today)
            date_range = st.date_input(
                "📅 Date Range (From - To)",
                value=(today_date, today_date),
                max_value=today_date + timedelta(days=1)
            )
        with d2:
            sort_order = st.radio("Sort Time:", ["Newest First", "Oldest First"], horizontal=True)

    # --- APPLY FILTERS ---
    filtered_df = df.copy()
    
    # 1. Date Filter Logic
    if len(date_range) == 2:
        start_d, end_d = date_range
        # กรองโดยดูที่ .dt.date
        filtered_df = filtered_df[
            (filtered_df['Time'].dt.date >= start_d) & 
            (filtered_df['Time'].dt.date <= end_d)
        ]
    elif len(date_range) == 1:
        # กรณีเลือกแค่วันเดียว (ระบบกำลังรอเลือกวันจบ)
        start_d = date_range[0]
        filtered_df = filtered_df[filtered_df['Time'].dt.date == start_d]

    # 2. Attribute Filters
    if sel_sym and "All" not in sel_sym: filtered_df = filtered_df[filtered_df['Symbol'].isin(sel_sym)]
    if sel_act and "All" not in sel_act: filtered_df = filtered_df[filtered_df['Action'].isin(sel_act)]
    if sel_strat and "All" not in sel_strat: filtered_df = filtered_df[filtered_df['Strategy'].isin(sel_strat)]
    
    # 3. Sort
    ascending = True if sort_order == "Oldest First" else False
    filtered_df = filtered_df.sort_values(by="Time", ascending=ascending)

    # --- KPI SECTION ---
    # คำนวณ KPI จาก filtered_df (เปลี่ยนไปตามวันที่เลือก)
    closed_trades = filtered_df[filtered_df['Status'] == 'CLOSED']
    total_pnl = closed_trades['PnL'].sum()
    wins = len(closed_trades[closed_trades['PnL'] > 0])
    total_closed = len(closed_trades)
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f"<div class='kpi-card'><p class='kpi-val'>{len(filtered_df)}</p><p class='kpi-lbl'>Total Signals</p></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='kpi-card'><p class='kpi-val' style='color:#58a6ff'>{len(filtered_df[filtered_df['Status']=='OPEN'])}</p><p class='kpi-lbl'>Active Trades</p></div>", unsafe_allow_html=True)
    pnl_color = "#4ade80" if total_pnl >= 0 else "#f87171"
    with k3: st.markdown(f"<div class='kpi-card'><p class='kpi-val' style='color:{pnl_color}'>${total_pnl:,.2f}</p><p class='kpi-lbl'>Realized PnL</p></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='kpi-card'><p class='kpi-val' style='color:#d29922'>{win_rate:.1f}%</p><p class='kpi-lbl'>Total Win Rate</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- CHARTS SECTION ---
    if not filtered_df.empty:
        c1, c2 = st.columns([1, 1.5])
        
        with c1:
            st.markdown("<div class='section-header'>🍩 Strategy Mix</div>", unsafe_allow_html=True)
            base = alt.Chart(filtered_df).encode(theta=alt.Theta("count()", stack=True))
            pie = base.mark_arc(outerRadius=120, innerRadius=80).encode(
                color=alt.Color("Strategy", scale=alt.Scale(scheme='set2')),
                order=alt.Order("count()", sort="descending"),
                tooltip=["Strategy", "count()"]
            )
            text = base.mark_text(radius=140).encode(text=alt.Text("count()"), order=alt.Order("count()", sort="descending"), color=alt.value("white"))
            st.altair_chart((pie + text).properties(height=350), use_container_width=True)

        with c2:
            st.markdown("<div class='section-header'>🏆 Win Rate by Strategy</div>", unsafe_allow_html=True)
            
            if not closed_trades.empty:
                strat_stats = closed_trades.groupby('Strategy').apply(
                    lambda x: pd.Series({
                        'WinRate': (x['PnL'] > 0).sum() / len(x) * 100,
                        'Trades': len(x)
                    })
                ).reset_index()

                bar_chart = alt.Chart(strat_stats).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
                    x=alt.X('WinRate:Q', title='Win Rate (%)', scale=alt.Scale(domain=[0, 100])),
                    y=alt.Y('Strategy:N', sort='-x', title=None),
                    color=alt.Color('WinRate:Q', scale=alt.Scale(scheme='redyellowgreen'), legend=None),
                    tooltip=['Strategy', alt.Tooltip('WinRate', format='.1f'), 'Trades']
                ).properties(height=350)
                
                text_labels = bar_chart.mark_text(align='left', dx=2, color='white').encode(
                    text=alt.Text('WinRate', format='.1f')
                )
                
                st.altair_chart(bar_chart + text_labels, use_container_width=True)
            else:
                st.info("No closed trades in selected range.")
    else:
        st.warning(f"No data found for date: {date_range}")

    # --- TABLE ---
    ITEMS_PER_PAGE = 20
    total_pages = math.ceil(len(filtered_df) / ITEMS_PER_PAGE)
    if total_pages == 0: total_pages = 1
    if st.session_state.current_page_num > total_pages: st.session_state.current_page_num = 1
    
    start_idx = (st.session_state.current_page_num - 1) * ITEMS_PER_PAGE
    display_df = filtered_df.iloc[start_idx : start_idx + ITEMS_PER_PAGE]

    st.markdown("---")
    st.markdown(f"<div class='section-header'>📑 Transaction Feed (Page {st.session_state.current_page_num}/{total_pages})</div>", unsafe_allow_html=True)
    
    h_col = st.columns([1.2, 0.8, 1, 1, 1.2, 0.8, 1.2, 1, 0.5])
    headers = ["TIME", "SYMBOL", "TICKET", "ACTION", "STRATEGY", "STATUS", "EXIT REASON", "PNL", ""]
    
    for c, h in zip(h_col, headers): c.markdown(f"**{h}**")
    st.divider()

    for _, row in display_df.iterrows():
        r_col = st.columns([1.2, 0.8, 1, 1, 1.2, 0.8, 1.2, 1, 0.5])
        
        r_col[0].write(row['Time'].strftime('%Y-%m-%d %H:%M:%S'))
        r_col[1].write(f"**{row['Symbol']}**")
        r_col[2].write(f"{row['Ticket']}")

        act_str = str(row['Action']).upper()
        if act_str == "BUY":
            act_html = f'<span style="color:#2ecc71;">🔼 BUY</span>'
        elif act_str == "SELL":
            act_html = f'<span style="color:#e74c3c;">🔽 SELL</span>'
        else:
            act_html = f'<span style="color:#bdc3c7;">⏸ {act_str}</span>'
        r_col[3].markdown(act_html, unsafe_allow_html=True)

        strat_str = str(row['Strategy'])
        r_col[4].markdown(f'<span style="color:#ddd6fe; font-size:0.8rem;">⚡ {strat_str}</span>', unsafe_allow_html=True)
        
        status = row['Status']
        s_bg = "bg-closed" if status == "CLOSED" else "bg-open"
        r_col[5].markdown(f"<span class='badge {s_bg}'>{status}</span>", unsafe_allow_html=True)
        
        exit_r = row['ExitReason']
        if len(exit_r) > 15: exit_r = exit_r[:15] + "..." 
        r_col[6].write(f"{exit_r}")

        pnl_val = row['PnL'] if row['PnL'] is not None else 0.0
        pnl_color = "green" if pnl_val > 0 else "red" if pnl_val < 0 else "gray"
        r_col[7].markdown(f":{pnl_color}[${pnl_val:,.2f}]")

        if r_col[8].button("➤", key=f"btn_{row['FirestoreID']}"):
            navigate('detail', row['FirestoreID'])
        st.markdown("<hr style='margin:5px 0; border-color:#30363d; opacity:0.3;'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    if st.session_state.current_page_num > 1 and c1.button("⬅ Previous"):
        st.session_state.current_page_num -= 1; st.rerun()
    c2.markdown(f"<div style='text-align:center; color:#8b949e; margin-top:5px;'>Showing {start_idx+1}-{min(start_idx+ITEMS_PER_PAGE, len(filtered_df))} of {len(filtered_df)}</div>", unsafe_allow_html=True)
    if st.session_state.current_page_num < total_pages and c3.button("Next ➡"):
        st.session_state.current_page_num += 1; st.rerun()

# --- 5. DETAIL PAGE (REVISED) ---
def load_image_hybrid(path_or_url):
    """Helper to load images from URL or Local Path"""
    if not path_or_url: return None
    try:
        if path_or_url.startswith('http'):
            response = requests.get(path_or_url, timeout=5)
            return Image.open(BytesIO(response.content))
        elif os.path.exists(path_or_url):
            return Image.open(path_or_url)
        else: return None
    except: return None

# [NEW] Helper for KV rows
def render_kv_rows(data_dict):
    """Helper to render Key-Value pairs in HTML"""
    html_content = ""
    sorted_keys = sorted(data_dict.keys())
    for k in sorted_keys:
        v = data_dict[k]
        # Format Value
        if isinstance(v, float): val_str = f"{v:,.4f}"
        elif isinstance(v, (dict, list)): val_str = "..." # ซ่อน Object ใหญ่
        else: val_str = str(v)
        
        row = f"""
        <div class="kv-row">
            <span class="kv-key">{k}</span>
            <span class="kv-val">{val_str}</span>
        </div>
        """
        html_content += row
    return html_content

def render_detail_view():
    selected_item = next((item for item in raw_data if item['firestore_id'] == st.session_state.selected_doc_id), None)
    
    if not selected_item:
        st.error("Document not found.")
        if st.button("Back"): navigate('dashboard')
        return

    # --- VARIABLE EXTRACTION ---
    symbol = selected_item.get('symbol', 'UNKNOWN')
    ts = selected_item.get('timestamp', '')
    status = selected_item.get('trade_status', 'OPEN')
    action = selected_item.get('s_action', 'WAIT')
    
    # Info Block Vars
    macro = selected_item.get('t_macro_trend_h1', '-')
    strat = selected_item.get('s_strategy_label', '-')
    pa = selected_item.get('t_signal_candle_volume_pattern', 'NONE')

    atr1HText =  selected_item.get('t_atr_1h', '-')
    atr15MText =  selected_item.get('t_atr_m15', '-')
  
    if pa == 'NONE' or not pa: pa = selected_item.get('s_pattern', 'NONE')
    
    # Safely get float values
    def safe_get(key): 
        try: return float(selected_item.get(key, 0))
        except: return 0.0
    
    entry = safe_get('e_entry') or safe_get('s_entry_price')
    sl = safe_get('e_sl') or safe_get('s_stop_loss')
    tp = safe_get('e_tp') or safe_get('s_take_profit')
    conf = selected_item.get('s_confidence_score', 0)
    token = selected_item.get('s_llm_total_token', 0)
    
    # Result Vars
    pnl = safe_get('r_net_pnl')
    close_reason = selected_item.get('r_exit_reason', '-')
    
    # --- HEADER ---
    col_nav, col_head = st.columns([1, 10])
    with col_nav:
        if st.button("⮜ BACK"): navigate('dashboard')
    
    with col_head:
        act_badge = "bg-buy" if action == "BUY" else "bg-sell" if action == "SELL" else "bg-wait"
        status_badge = "bg-closed" if status == "CLOSED" else "bg-open"
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:15px; flex-wrap:wrap;">
            <h1 style="margin:0;">{symbol}</h1>
            <span class="badge {act_badge}">{action}</span>
            <span class="badge {status_badge}">{status}</span>
            <span style="color:#8b949e; margin-left:auto;">{ts}</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")

    # --- TABS (CHARTS) ---
    tabs = st.tabs(["📊 Analysis", "🚀 Execution", "🏁 Result"])
    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**M15 Chart**")
            st.image(load_image_hybrid(selected_item.get('s_chart_m15_url')) or "https://placehold.co/600x400?text=No+M15+Chart")
        with c2:
            st.markdown("**H1 Chart**")
            st.image(load_image_hybrid(selected_item.get('s_chart_h1_url')) or "https://placehold.co/600x400?text=No+H1+Chart")

    with tabs[1]:
        st.image(load_image_hybrid(selected_item.get('e_graph1_path')) or "https://placehold.co/800x400?text=No+Execution+Graph")

    with tabs[2]:
        st.image(load_image_hybrid(selected_item.get('r_result_m15_url')) or "https://placehold.co/800x400?text=Pending+Result")

    st.markdown("---")

    # --- INFO & REASONING SECTION ---
    c_info, c_reason, c_res = st.columns([1.2, 1.8, 1])

    # Column 1: Signal Info 
    with c_info:
        st.markdown("### 📋 Signal Data")
        st.write(f"**Macro:** {macro}")
        st.write(f"**Strategy:** {strat}")
        st.write(f"**PA:** {pa}")
        
        # Handle ATR Display Safety
        try: a15 = float(atr15MText)
        except: a15 = 0.0
        try: a1h = float(atr1HText)
        except: a1h = 0.0
        
        st.write(f"**ATR:** {a15:.5f}(15M) / {a1h:.5f}(1H)")
        st.divider()
        st.write(f"**Entry:** {entry:,.5f}")
        st.write(f"**SL:** {sl:,.5f}")
        st.write(f"**TP:** {tp:,.5f}")
        st.divider()
        st.write(f"**Confidence:** {conf}%")
        st.write(f"**Token:** {token}")

   # Column 2: Reasoning
    with c_reason:
        st.markdown("### 🧠 AI Reasoning")
        
        # --- กล่องข้อความแบบขยายขนาดตัวอักษร ---
        reason_text = selected_item.get('s_reasoning', 'No reasoning provided.')
        
        st.markdown(f"""
        <div style="
            background-color: rgba(56, 139, 253, 0.1); 
            border: 1px solid rgba(56, 139, 253, 0.4);
            border-radius: 8px;
            padding: 20px;
            font-size: 1.25rem; 
            line-height: 1.6;
            color: #e6edf3;
        ">
            {reason_text}
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="margin-top: 15px; font-size: 0.9rem; color: #8b949e;">
            <b>Ticket ID:</b> <code>{selected_item.get('r_ticket', '-')}</code><br>
            <b>Broker:</b> <code>{selected_item.get('model', '-')}</code>
        </div>
        """, unsafe_allow_html=True)

    # Column 3: Performance
    with c_res:
        st.markdown("### 💵 Performance")
        if status == "CLOSED":
            res_color = "#4ade80" if pnl > 0 else "#f87171"
            res_text = "PROFIT" if pnl > 0 else "LOSS"
            if pnl == 0: res_text = "BREAKEVEN"
            
            st.markdown(f"""
            <div style="background:{res_color}15; border:1px solid {res_color}; padding:20px; border-radius:10px; text-align:center; margin-bottom:15px;">
                <h2 style="margin:0; color:{res_color}; font-size:2.2rem;">${pnl:,.2f}</h2>
                <div style="color:{res_color}; font-weight:bold; letter-spacing:1px;">{res_text}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**Exit:** `{close_reason}`")
            st.markdown(f"**Time:** `{selected_item.get('r_close_time', '-')}`")
        else:
            st.markdown("""
            <div style="background:#58a6ff15; border:1px solid #58a6ff; padding:20px; border-radius:10px; text-align:center;">
                <h3 style="margin:0; color:#58a6ff;">RUNNING...</h3>
                <small>Result pending</small>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # --- [IMPROVED] DATA INSPECTOR (Label : Value Style) ---
    st.markdown("<div class='section-header'>💾 Data Inspector</div>", unsafe_allow_html=True)
    
    s_data = {k:v for k,v in selected_item.items() if k.startswith('s_')}
    e_data = {k:v for k,v in selected_item.items() if k.startswith('e_')}
    r_data = {k:v for k,v in selected_item.items() if k.startswith('r_')}

    d1, d2, d3 = st.columns(3)

    with d1:
        st.info(f"**📶 Signal (s_*)**")
        with st.container(height=300):
            st.markdown(render_kv_rows(s_data), unsafe_allow_html=True)

    with d2:
        st.warning(f"**⚙️ Execution (e_*)**")
        with st.container(height=300):
            st.markdown(render_kv_rows(e_data), unsafe_allow_html=True)

    with d3:
        st.success(f"**💰 Result (r_*)**")  
        with st.container(height=300):
            st.markdown(render_kv_rows(r_data), unsafe_allow_html=True)

# --- MAIN ---
if st.session_state.page == 'dashboard': render_dashboard()
else: render_detail_view()
 