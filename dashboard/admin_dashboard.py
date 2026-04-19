"""Admin Dashboard for LLM Observability.

Streamlit-based dashboard for monitoring and management.

Run with:
    streamlit run dashboard/admin_dashboard.py
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="LLM Observability Admin",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-healthy {
        color: #28a745;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Authentication
if "token" not in st.session_state:
    st.session_state.token = None

if "username" not in st.session_state:
    st.session_state.username = None


def login(username: str, password: str) -> bool:
    """Authenticate user."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            params={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.username = username
            return True
    except:
        pass
    return False


def get_headers():
    """Get auth headers."""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def logout():
    """Logout user."""
    st.session_state.token = None
    st.session_state.username = None


# Login page
if not st.session_state.token:
    st.markdown('<div class="main-header">🎯 LLM Observability Admin</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Login")
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", value="admin123")
        
        if st.button("Login", use_container_width=True):
            if login(username, password):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
        
        st.info("💡 Default credentials: admin / admin123")
    
    st.stop()


# Main dashboard
st.markdown(f'<div class="main-header">🎯 LLM Observability Dashboard</div>', unsafe_allow_html=True)
st.markdown(f"**Logged in as:** {st.session_state.username}")

if st.sidebar.button("Logout"):
    logout()
    st.rerun()

st.markdown("---")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "📊 Overview",
        "👥 User Management",
        "🔍 Detection Monitor",
        "📈 Policy & Governance",
        "⚙️ System Settings",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Stats")

# Fetch stats
try:
    health_response = requests.get(
        f"{API_BASE_URL}/api/monitoring/health",
        headers=get_headers()
    )
    if health_response.status_code == 200:
        health_data = health_response.json()
        status = health_data.get("status", "unknown")
        
        if status == "healthy":
            st.sidebar.success(f"✅ System: {status.upper()}")
        else:
            st.sidebar.warning(f"⚠️ System: {status.upper()}")
except:
    st.sidebar.error("❌ API Unavailable")


# Page: Overview
if page == "📊 Overview":
    st.header("System Overview")
    
    # Fetch tier stats
    try:
        tier_response = requests.get(
            f"{API_BASE_URL}/api/monitoring/tier_stats",
            headers=get_headers()
        )
        
        if tier_response.status_code == 200:
            tier_data = tier_response.json()
            distribution = tier_data.get("distribution", {})
            health = tier_data.get("health", {})
            
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Tier 1 (Regex)",
                    f"{distribution.get('tier1_pct', 0):.1f}%",
                    delta="Target: 95%"
                )
            
            with col2:
                st.metric(
                    "Tier 2 (Semantic)",
                    f"{distribution.get('tier2_pct', 0):.1f}%",
                    delta="Target: 4%"
                )
            
            with col3:
                st.metric(
                    "Tier 3 (LLM)",
                    f"{distribution.get('tier3_pct', 0):.1f}%",
                    delta="Target: 1%"
                )
            
            with col4:
                st.metric(
                    "Total Checks",
                    tier_data.get("total_checks", 0)
                )
            
            # Tier distribution chart
            st.subheader("Tier Distribution")
            
            fig = go.Figure(data=[
                go.Bar(
                    x=["Tier 1\n(Regex)", "Tier 2\n(Semantic)", "Tier 3\n(LLM)"],
                    y=[
                        distribution.get("tier1_pct", 0),
                        distribution.get("tier2_pct", 0),
                        distribution.get("tier3_pct", 0)
                    ],
                    marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"],
                    text=[
                        f"{distribution.get('tier1_pct', 0):.1f}%",
                        f"{distribution.get('tier2_pct', 0):.1f}%",
                        f"{distribution.get('tier3_pct', 0):.1f}%"
                    ],
                    textposition="outside"
                )
            ])
            
            # Add target lines
            fig.add_hline(y=95, line_dash="dash", line_color="blue", annotation_text="Target: 95%")
            fig.add_hline(y=4, line_dash="dash", line_color="orange", annotation_text="Target: 4%")
            fig.add_hline(y=1, line_dash="dash", line_color="green", annotation_text="Target: 1%")
            
            fig.update_layout(
                title="Tier Distribution vs Targets",
                yaxis_title="Percentage (%)",
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Health status
            st.subheader("System Health")
            is_healthy = health.get("is_healthy", False)
            message = health.get("message", "Unknown")
            
            if is_healthy:
                st.success(f"✅ {message}")
            else:
                st.warning(f"⚠️ {message}")
        
        else:
            st.error("Failed to fetch tier stats")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")


# Page: User Management
elif page == "👥 User Management":
    st.header("User Management")
    
    try:
        users_response = requests.get(
            f"{API_BASE_URL}/api/admin/users",
            headers=get_headers()
        )
        
        if users_response.status_code == 200:
            users = users_response.json()
            
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Users", len(users))
            with col2:
                active_users = sum(1 for u in users if not u.get("disabled", False))
                st.metric("Active Users", active_users)
            with col3:
                admin_users = sum(1 for u in users if u.get("role") == "admin")
                st.metric("Admin Users", admin_users)
            
            st.markdown("---")
            
            # Users table
            st.subheader("All Users")
            
            df = pd.DataFrame(users)
            st.dataframe(
                df[["username", "email", "role", "rate_limit_tier", "disabled"]],
                use_container_width=True
            )
            
            # User management
            st.markdown("---")
            st.subheader("Manage User")
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_user = st.selectbox(
                    "Select User",
                    [u["username"] for u in users]
                )
                
                new_role = st.selectbox(
                    "Change Role",
                    ["admin", "user", "viewer"]
                )
                
                if st.button("Update Role"):
                    try:
                        response = requests.put(
                            f"{API_BASE_URL}/api/admin/users/{selected_user}/role",
                            params={"role": new_role},
                            headers=get_headers()
                        )
                        if response.status_code == 200:
                            st.success(f"Role updated for {selected_user}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to update role")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            with col2:
                new_tier = st.selectbox(
                    "Change Rate Limit Tier",
                    ["free", "pro", "enterprise"]
                )
                
                if st.button("Update Tier"):
                    try:
                        response = requests.put(
                            f"{API_BASE_URL}/api/admin/users/{selected_user}/tier",
                            params={"tier": new_tier},
                            headers=get_headers()
                        )
                        if response.status_code == 200:
                            st.success(f"Tier updated for {selected_user}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to update tier")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        else:
            st.error("Failed to fetch users")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")


# Page: Detection Monitor
elif page == "🔍 Detection Monitor":
    st.header("Detection Monitor")
    
    st.subheader("Test Detection")
    
    test_text = st.text_area(
        "Enter text to test",
        height=150,
        placeholder="Enter LLM response to analyze..."
    )
    
    if st.button("Analyze", type="primary"):
        if test_text:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/detect",
                    json={"text": test_text},
                    headers=get_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Results
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        tier = result.get("tier_used", 1)
                        st.metric("Tier Used", f"Tier {tier}")
                    
                    with col2:
                        confidence = result.get("confidence", 0)
                        st.metric("Confidence", f"{confidence:.2%}")
                    
                    with col3:
                        time_ms = result.get("processing_time_ms", 0)
                        st.metric("Processing Time", f"{time_ms:.2f}ms")
                    
                    # Action
                    should_block = result.get("should_block", False)
                    action = result.get("action", "allow")
                    
                    if should_block:
                        st.error(f"❌ Action: {action.upper()}")
                    else:
                        st.success(f"✅ Action: {action.upper()}")
                    
                    # Details
                    if result.get("reason"):
                        st.info(f"**Reason:** {result['reason']}")
                    
                    # Rate limit info
                    rate_limit = result.get("rate_limit", {})
                    st.caption(f"Rate limit: {rate_limit.get('remaining', 0)}/{rate_limit.get('limit', 0)} remaining")
                
                else:
                    st.error(f"Detection failed: {response.status_code}")
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter text to analyze")


# Page: Policy & Governance
elif page == "📈 Policy & Governance":
    st.header("Policy routing, PII, drift, and defense-in-depth (Pro-style console)")

    col_def, col_pii = st.columns(2)

    with col_def:
        st.subheader("External moderation fusion (env)")
        try:
            ms = requests.get(
                f"{API_BASE_URL}/api/monitoring/moderation_status",
                headers=get_headers(),
            )
            if ms.status_code == 200:
                st.json(ms.json())
            else:
                st.warning(f"moderation_status: {ms.status_code}")
        except Exception as e:
            st.error(str(e))

        st.subheader("Drift alert (Tier 3 share in compliance window)")
        try:
            drift = requests.get(
                f"{API_BASE_URL}/api/monitoring/drift_signals?window=200",
                headers=get_headers(),
            )
            if drift.status_code == 200:
                dj = drift.json()
                if dj.get("drift_alert"):
                    st.error(
                        f"DRIFT ALERT: Tier-3 fraction in recent window is {dj.get('tier3_fraction_recent_compliance_window')} "
                        f"(threshold {dj.get('drift_threshold_tier3_fraction')}, min samples {dj.get('min_samples_for_alert')})."
                    )
                else:
                    st.success("No drift alert on current window (heuristic).")
                st.json(dj)
            else:
                st.warning(f"drift_signals: {drift.status_code}")
        except Exception as e:
            st.error(str(e))

    with col_pii:
        st.subheader("PII entity heatmap (demo corpus)")
        try:
            ph = requests.get(
                f"{API_BASE_URL}/api/governance/pii-heatmap-demo",
                headers=get_headers(),
            )
            if ph.status_code == 200:
                pj = ph.json()
                ec = pj.get("entity_counts") or {}
                if ec:
                    df_pii = pd.DataFrame(
                        [{"entity": k, "hits": v} for k, v in sorted(ec.items(), key=lambda x: -x[1])]
                    )
                    fig_h = px.bar(
                        df_pii,
                        x="entity",
                        y="hits",
                        color="hits",
                        color_continuous_scale="Viridis",
                        title=f"PII-like hits across {pj.get('samples_scanned', 0)} synthetic lines",
                    )
                    st.plotly_chart(fig_h, use_container_width=True)
                else:
                    st.info("No PII-like entities in demo corpus.")
            else:
                st.warning(f"pii-heatmap-demo: {ph.status_code}")
        except Exception as e:
            st.error(str(e))

    st.subheader("Policy effectiveness (live routing + recent compliance mix)")
    try:
        pe = requests.get(
            f"{API_BASE_URL}/api/monitoring/policy_effectiveness",
            headers=get_headers(),
        )
        if pe.status_code == 200:
            data = pe.json()
            rows = data.get("heatmap_rows", [])
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)
                fig = px.bar(df, x="tier", y="pct", title="Live routing % by tier")
                st.plotly_chart(fig, use_container_width=True)
            am = data.get("recent_action_mix") or {}
            if am:
                df_a = pd.DataFrame([{"action": k, "count": v} for k, v in am.items()])
                fig_a = px.bar(
                    df_a,
                    x="action",
                    y="count",
                    color="count",
                    color_continuous_scale="Blues",
                    title=f"Recent actions (last {data.get('recent_compliance_window', 0)} compliance rows)",
                )
                st.plotly_chart(fig_a, use_container_width=True)
            fm = data.get("recent_failure_class_mix") or {}
            if fm:
                df_f = pd.DataFrame([{"failure_class": k, "count": v} for k, v in fm.items()])
                fig_f = px.bar(df_f, x="failure_class", y="count", title="Failure class mix (recent window)")
                st.plotly_chart(fig_f, use_container_width=True)
            st.caption(data.get("drift_note", ""))
        else:
            st.error(f"policy_effectiveness failed: {pe.status_code}")
    except Exception as e:
        st.error(str(e))

    st.subheader("Agentic / tool-use guard simulator")
    ag_text = st.text_area("Agent or user text", height=100, key="ag_text")
    ag_tool = st.text_input("Tool name (optional)", "", key="ag_tool")
    ag_allowed = st.text_input("Allowed tools (comma-separated, optional)", "read_file,list_dir", key="ag_allowed")
    if st.button("Run agentic-check"):
        try:
            allowed = [x.strip() for x in ag_allowed.split(",") if x.strip()] if ag_allowed.strip() else []
            payload = {"text": ag_text or " "}
            if ag_tool.strip():
                payload["tool_name"] = ag_tool.strip()
            if allowed:
                payload["allowed_tools"] = allowed
            ar = requests.post(
                f"{API_BASE_URL}/api/governance/agentic-check",
                json=payload,
                headers={**get_headers(), "Content-Type": "application/json"},
            )
            if ar.status_code == 200:
                st.json(ar.json())
            else:
                st.error(ar.text[:500])
        except Exception as e:
            st.error(str(e))

    st.subheader("Prometheus scrape (/metrics)")
    st.caption("Same host as API; use Grafana or Prometheus server to scrape this text endpoint.")
    if st.button("Fetch raw /metrics"):
        try:
            mr = requests.get(f"{API_BASE_URL}/metrics", timeout=10)
            st.text(mr.text[:8000] if mr.status_code == 200 else mr.text[:2000])
        except Exception as e:
            st.error(str(e))

    st.subheader("Output self-correction history")
    if st.button("Load correction-history"):
        try:
            cr = requests.get(
                f"{API_BASE_URL}/api/governance/correction-history?limit=80",
                headers=get_headers(),
            )
            if cr.status_code == 200:
                st.json(cr.json())
            else:
                st.error(cr.text[:500])
        except Exception as e:
            st.error(str(e))

    st.subheader("India PII redaction (sample)")
    sample = st.text_area("Text to redact", value="PAN ABCDE1234F phone +91 9876543210")
    if st.button("Redact via API"):
        try:
            r = requests.post(
                f"{API_BASE_URL}/api/governance/redact",
                json={"text": sample},
                headers={**get_headers(), "Content-Type": "application/json"},
            )
            if r.status_code == 200:
                st.json(r.json())
            else:
                st.error(r.text[:500])
        except Exception as e:
            st.error(str(e))

    st.subheader("Compliance JSONL export (admin)")
    st.caption("Downloads append-only audit rows (hashed by default).")
    if st.button("Fetch export preview"):
        try:
            r = requests.get(
                f"{API_BASE_URL}/api/governance/compliance/export?max_lines=50",
                headers=get_headers(),
            )
            if r.status_code == 200:
                st.download_button(
                    "Download JSONL",
                    data=r.content,
                    file_name="compliance_audit.jsonl",
                    mime="application/x-ndjson",
                )
                st.text(r.text[:4000])
            else:
                st.error(f"{r.status_code}: {r.text[:500]}")
        except Exception as e:
            st.error(str(e))


# Page: System Settings
elif page == "⚙️ System Settings":
    st.header("System Settings")
    
    st.subheader("Rate Limiting Configuration")
    
    st.code("""
# Rate Limits (requests/hour)
Free Tier:       100
Pro Tier:        1000
Enterprise:      10000

# Detection Tier Limits
Tier 1 (Regex):  No limit
Tier 2 (Semantic): 50/hour
Tier 3 (LLM):    10/hour
    """, language="yaml")
    
    st.subheader("Detection Thresholds")
    
    st.code("""
# Confidence Thresholds
Strong Match:    >= 0.80
Gray Zone:       0.30 - 0.80
Weak Match:      < 0.30

# Target Distribution
Tier 1: 95%
Tier 2: 4%
Tier 3: 1%
    """, language="yaml")
    
    st.info("💡 Configuration is managed through YAML files in the config/ directory")