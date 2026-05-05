"""Sovereign AI — Governance & compliance console (Streamlit).

Uses the same FastAPI + JWT flow as admin_dashboard. Run:
  streamlit run dashboard/governance_dashboard.py

API paths match this repo: ``/api/governance/*``, ``/api/monitoring/*``.
"""

from __future__ import annotations

import os
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# --- Config ---
API_BASE_URL = os.getenv("SOVEREIGN_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Sovereign AI — Governance",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    div.block-container { padding-top: 1.2rem; }
    .gov-title { font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; }
    .muted { color: #6c757d; font-size: 0.95rem; }
</style>
""",
    unsafe_allow_html=True,
)

if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "api_url" not in st.session_state:
    st.session_state.api_url = API_BASE_URL


def login(username: str, password: str) -> bool:
    try:
        base = (st.session_state.api_url or API_BASE_URL).rstrip("/")
        r = requests.post(
            f"{base}/api/auth/login",
            params={"username": username, "password": password},
            timeout=15,
        )
        if r.status_code == 200:
            st.session_state.token = r.json()["access_token"]
            st.session_state.username = username
            return True
    except Exception:
        pass
    return False


def headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


# --- Login ---
if not st.session_state.token:
    st.markdown('<p class="gov-title">🛡️ Sovereign AI Governance</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="muted">Production LLM safety & compliance monitoring · All Rights Reserved © 2026 Pranay Mathur</p>',
        unsafe_allow_html=True,
    )
    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.subheader("Sign in")
        st.session_state.api_url = st.text_input(
            "API base URL",
            value=st.session_state.api_url,
            help="Must match your FastAPI server (e.g. http://localhost:8000)",
        )
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if login(u, p):
                st.success("Signed in.")
                time.sleep(0.3)
                st.rerun()
            else:
                st.error("Invalid credentials")
        st.caption("Use the same accounts as the main API (`/api/auth/login`).")
    st.stop()

# --- Main UI ---
st.markdown('<p class="gov-title">🛡️ Sovereign AI Governance Dashboard</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="muted"><b>Production LLM safety & compliance monitoring</b> · All Rights Reserved © 2026 Pranay Mathur</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.caption(f"Signed in as **{st.session_state.username}**")
    st.session_state.api_url = st.text_input(
        "API base URL",
        value=st.session_state.api_url,
        help="FastAPI root, e.g. http://localhost:8000",
    )
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.username = None
        st.rerun()
    st.divider()
    st.subheader("Filters")
    st.date_input("Date range (UI only)", [datetime.now().date(), datetime.now().date()])
    refresh = st.button("🔄 Refresh all")


if refresh:
    try:
        st.cache_data.clear()
    except Exception:
        pass


def fetch(path: str) -> dict:
    base = st.session_state.api_url.rstrip("/")
    r = requests.get(f"{base}{path}", headers=headers(), timeout=20)
    if r.status_code != 200:
        return {"_error": r.status_code, "_body": r.text[:300]}
    return r.json()


# --- Row 1: moderation + drift ---
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("External moderation fusion")
    try:
        ms = fetch("/api/monitoring/moderation_status")
        if "_error" in ms:
            st.error(ms)
        else:
            st.json(ms)
    except Exception as e:
        st.error(str(e))

with c_right:
    st.subheader("Drift signals (Tier 3 share)")
    try:
        drift = fetch("/api/monitoring/drift_signals?window=200")
        if "_error" in drift:
            st.error(drift)
        else:
            if drift.get("drift_alert"):
                st.error(
                    f"**Drift alert:** Tier-3 fraction in recent compliance window = "
                    f"{drift.get('tier3_fraction_recent_compliance_window')} "
                    f"(threshold {drift.get('drift_threshold_tier3_fraction')}, "
                    f"min samples {drift.get('min_samples_for_alert')})."
                )
            else:
                st.success("No drift alert on current window (heuristic).")
            t3 = drift.get("tier3_fraction_recent_compliance_window") or 0
            thr = drift.get("drift_threshold_tier3_fraction") or 0.12
            fig_g = go.Figure(
                go.Bar(
                    x=["Recent window Tier-3 fraction", "Alert threshold"],
                    y=[float(t3), float(thr)],
                    marker_color=["#fd7e14", "#dc3545"],
                )
            )
            fig_g.update_layout(title="Tier 3 share vs threshold", height=320)
            st.plotly_chart(fig_g, use_container_width=True)
            st.json(drift)
    except Exception as e:
        st.error(str(e))

# --- PII heatmap (demo corpus) ---
st.subheader("PII redaction heatmap (DPDP-oriented demo corpus)")
try:
    pii = fetch("/api/governance/pii-heatmap-demo")
    if "_error" in pii:
        st.error(pii)
    else:
        ec = pii.get("entity_counts") or {}
        if ec:
            types = list(ec.keys())
            vals = [ec[k] for k in types]
            fig_h = px.imshow(
                [vals],
                x=types,
                y=["Detections"],
                text_auto=True,
                aspect="auto",
                color_continuous_scale="Reds",
                title=f"Synthetic sample hits (n={pii.get('samples_scanned', 0)})",
            )
            st.plotly_chart(fig_h, use_container_width=True)
            st.dataframe(pd.DataFrame(pii.get("per_sample", [])), use_container_width=True)
        else:
            st.info("No PII-like entities in demo corpus.")
except Exception as e:
    st.error(str(e))

# --- Policy effectiveness ---
st.subheader("Policy effectiveness")
try:
    pol = fetch("/api/monitoring/policy_effectiveness")
    if "_error" in pol:
        st.error(pol)
    else:
        rows = pol.get("heatmap_rows") or []
        if rows:
            df = pd.DataFrame(rows)
            c1, c2 = st.columns(2)
            with c1:
                fig_b = px.bar(
                    df,
                    x="tier",
                    y="pct",
                    color="pct",
                    color_continuous_scale="Viridis",
                    title="Live routing % by tier",
                )
                st.plotly_chart(fig_b, use_container_width=True)
            with c2:
                am = pol.get("recent_action_mix") or {}
                if am:
                    df_a = pd.DataFrame([{"action": k, "count": v} for k, v in am.items()])
                    fig_a = px.bar(
                        df_a,
                        x="action",
                        y="count",
                        color="count",
                        color_continuous_scale="Blues",
                        title=f"Recent actions (n={pol.get('recent_compliance_window', 0)})",
                    )
                    st.plotly_chart(fig_a, use_container_width=True)
            fm = pol.get("recent_failure_class_mix") or {}
            if fm:
                df_f = pd.DataFrame([{"failure_class": k, "count": v} for k, v in fm.items()])
                fig_f = px.pie(df_f, names="failure_class", values="count", title="Failure class mix (recent)")
                st.plotly_chart(fig_f, use_container_width=True)
        st.caption(pol.get("drift_note", ""))
except Exception as e:
    st.error(str(e))

st.caption("Dashboard uses Sovereign AI Governance & monitoring APIs · Data refreshes on each load or when you click Refresh.")
