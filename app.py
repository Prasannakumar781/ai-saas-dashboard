import math
import hashlib
import pathlib
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from openai import OpenAI

# ---------------- SETUP ----------------
st.set_page_config(page_title="AI SaaS Dashboard", layout="wide", page_icon="🚀")

# ---------------- LOAD STYLES ----------------
def load_css(filename: str) -> None:
    """Read a .css file (relative to this script) and inject it into the Streamlit app."""
    css_path = pathlib.Path(__file__).parent / filename
    css = css_path.read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css("Styles.css")

st.title("🚀 AI SaaS Dashboard")

# ---------------- COLOUR PALETTES ----------------
PALETTES = [
    # Each palette = list of hex colours for chart series / bars / points
    ["#f953c6", "#b91d73", "#ff6b6b", "#feca57", "#48dbfb"],   # magenta-pink
    ["#43e97b", "#38f9d7", "#4facfe", "#00f2fe", "#a8edea"],   # mint-cyan
    ["#f9a825", "#ff6f00", "#ff8f00", "#ffd54f", "#ffe082"],   # amber-fire
    ["#a18cd1", "#fbc2eb", "#8fd3f4", "#c2e9fb", "#d4fc79"],   # lavender-blush
    ["#fd746c", "#ff9068", "#ffd194", "#70e1f5", "#00d2ff"],   # sunset-ocean
    ["#6a3093", "#a044ff", "#e96c7c", "#ffc75f", "#f9f871"],   # galaxy
    ["#11998e", "#38ef7d", "#1cb5e0", "#000851", "#373b44"],   # deep-sea
    ["#fc5c7d", "#6a82fb", "#a8ff78", "#78ffd6", "#f7971e"],   # candy-pop
]

def palette_for(name: str) -> list:
    """Deterministically pick a palette based on dataset name."""
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(PALETTES)
    return PALETTES[idx]

def primary_color(name: str) -> str:
    return palette_for(name)[0]

PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(255,255,255,0.03)",
        "font": {"color": "#e0e0e0", "family": "Space Grotesk"},
        "xaxis": {"gridcolor": "rgba(255,255,255,0.08)", "zerolinecolor": "rgba(255,255,255,0.08)"},
        "yaxis": {"gridcolor": "rgba(255,255,255,0.08)", "zerolinecolor": "rgba(255,255,255,0.08)"},
    }
}

def styled_fig(fig, dataset_name: str):
    """Apply dark theme + dataset palette to any Plotly figure."""
    pal = palette_for(dataset_name)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        font=dict(color="#e0e0e0", family="Space Grotesk"),
        colorway=pal,
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.1)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.1)"),
        legend=dict(bgcolor="rgba(255,255,255,0.05)", bordercolor="rgba(255,255,255,0.1)"),
        margin=dict(t=40, b=40, l=40, r=20),
    )
    # For single-trace bar/line/scatter, force the first palette colour
    for trace in fig.data:
        if hasattr(trace, "marker") and trace.marker.color is None:
            trace.marker.color = pal[0]
        if hasattr(trace, "line") and trace.line.color is None:
            trace.line.color = pal[0]
    return fig

# ---------------- NaN SANITIZER ----------------
def sanitize_records(records):
    clean = []
    for row in records:
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean_row[k] = None
            else:
                clean_row[k] = v
        clean.append(clean_row)
    return clean

# ---------------- SECRETS ----------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state.user = session.user
    except Exception:
        pass

st.sidebar.title("🔐 Account")

# ---------------- AUTH PAGE ----------------
def auth_page():
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    login = st.sidebar.button("Login")
    signup = st.sidebar.button("Sign Up")

    if signup:
        if not email or not password:
            st.warning("Enter email and password")
            return
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.info("📩 Check your email to confirm your account before logging in")
        except Exception as e:
            st.error(f"Signup error: {e}")

    if login:
        if not email or not password:
            st.warning("Enter email and password")
            return
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res and res.user:
                st.session_state.user = res.user
                st.success("Login successful")
                st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")

    st.warning("Please login or sign up to continue")
    st.stop()

if st.session_state.user is None:
    auth_page()

# ---------------- LOGGED IN ----------------
user_id = st.session_state.user.id
st.sidebar.success(f"✅ {st.session_state.user.email}")

if st.sidebar.button("Logout"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# Sidebar palette legend
st.sidebar.markdown("---")
st.sidebar.markdown("**🎨 Dataset Colours**")

# ---------------- AI FUNCTION ----------------
def ask_ai(question, df):
    sample = df.head(20).to_string()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a senior data analyst. Be concise and clear."},
            {"role": "user", "content": f"Dataset sample:\n{sample}\n\nQuestion:\n{question}"}
        ]
    )
    return response.choices[0].message.content

# ---------------- DATASETS ----------------
st.markdown('<div class="section-header"><span>📂</span><h2 style="margin:0">Cloud Datasets</h2></div>', unsafe_allow_html=True)

file = st.file_uploader("Upload CSV", type=["csv"])

if file:
    try:
        df_upload = pd.read_csv(file)
        records = sanitize_records(df_upload.to_dict(orient="records"))
        supabase.table("datasets").insert({
            "name": file.name,
            "data": records,
            "user_id": user_id
        }).execute()
        st.success("✅ Uploaded successfully")
        st.rerun()
    except Exception as e:
        st.error(f"Upload failed: {e}")

# ---------------- FETCH DATASETS ----------------
def load_datasets():
    result = supabase.table("datasets").select("*").eq("user_id", user_id).execute()
    return result.data or []

datasets = load_datasets()

df = None
selected = None
selected_id = None

if not datasets:
    st.warning("No datasets found. Upload a CSV to get started.")
else:
    # Show colour swatches in sidebar for all datasets
    for d in datasets:
        col = primary_color(d["name"])
        st.sidebar.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
            f'<div style="width:14px;height:14px;border-radius:50%;background:{col};flex-shrink:0"></div>'
            f'<span style="font-size:0.8rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{d["name"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    names = [d["name"] for d in datasets]
    selected = st.selectbox("Choose dataset", names, key="dataset_selector")

    data = next(d for d in datasets if d["name"] == selected)
    selected_id = data["id"]
    df = pd.DataFrame(data["data"])

    # Dataset colour accent bar
    accent = primary_color(selected)
    pal = palette_for(selected)
    st.markdown(
        f'<div style="height:4px;border-radius:2px;background:linear-gradient(90deg,{",".join(pal[:4])});margin-bottom:12px"></div>',
        unsafe_allow_html=True
    )

    # Quick stats
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        cols = st.columns(min(len(num_cols), 4))
        for i, col_name in enumerate(num_cols[:4]):
            with cols[i]:
                val = df[col_name].mean()
                st.metric(f"avg {col_name}", f"{val:,.2f}")

    st.dataframe(df, use_container_width=True)

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🗑 Delete Dataset", key="delete_btn"):
            try:
                supabase.table("datasets").delete().eq("id", selected_id).execute()
                st.success("Deleted")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")

    # ---------------- CHART ----------------
    st.markdown('<div class="section-header"><span>📊</span><h2 style="margin:0">Visualization</h2></div>', unsafe_allow_html=True)

    if not df.empty:
        all_cols = df.columns.tolist()
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if not numeric_cols:
            st.warning("No numeric columns found for Y-axis.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                x = st.selectbox("X axis", all_cols, key="x_axis")
            with c2:
                y = st.selectbox("Y axis", numeric_cols, key="y_axis")
            with c3:
                chart_type = st.radio("Chart type", ["Bar", "Line", "Scatter", "Area"], horizontal=False)

            pal = palette_for(selected)

            if chart_type == "Bar":
                fig = px.bar(df, x=x, y=y, color_discrete_sequence=pal)
            elif chart_type == "Line":
                fig = px.line(df, x=x, y=y, color_discrete_sequence=pal)
            elif chart_type == "Area":
                fig = px.area(df, x=x, y=y, color_discrete_sequence=pal)
            else:
                fig = px.scatter(
                    df, x=x, y=y,
                    color_discrete_sequence=pal,
                    opacity=0.85,
                    size_max=14
                )

            fig = styled_fig(fig, selected)
            # Gradient fill for bar
            if chart_type == "Bar":
                fig.update_traces(marker=dict(
                    color=df[y] if y in df else None,
                    colorscale=[[0, pal[-1]], [1, pal[0]]],
                    showscale=False,
                ))
            # Smooth lines
            if chart_type in ("Line", "Area"):
                fig.update_traces(line=dict(width=3))

            st.plotly_chart(fig, use_container_width=True)

            # Extra: distribution histogram
            with st.expander("📈 Distribution View"):
                fig2 = px.histogram(df, x=y, nbins=30, color_discrete_sequence=pal)
                fig2 = styled_fig(fig2, selected)
                fig2.update_traces(marker_color=pal[0], opacity=0.85)
                st.plotly_chart(fig2, use_container_width=True)

            # Extra: correlation heatmap if multiple numeric cols
            if len(numeric_cols) > 1:
                with st.expander("🔥 Correlation Heatmap"):
                    corr = df[numeric_cols].corr()
                    fig3 = px.imshow(
                        corr,
                        color_continuous_scale=[[0, pal[-1]], [0.5, "#1a1a2e"], [1, pal[0]]],
                        zmin=-1, zmax=1,
                        text_auto=True
                    )
                    fig3 = styled_fig(fig3, selected)
                    st.plotly_chart(fig3, use_container_width=True)

# ---------------- AI CHAT ----------------
st.markdown('<div class="section-header"><span>💬</span><h2 style="margin:0">AI Data Analyst</h2></div>', unsafe_allow_html=True)

if df is None:
    st.info("Load a dataset above to start asking questions.")
else:
    question = st.text_input("Ask a question about your dataset", placeholder="e.g. What trends do you see? Which column has the most variance?")

    if question:
        with st.spinner("🤖 Thinking..."):
            try:
                answer = ask_ai(question, df)
                st.markdown(
                    f'<div class="chat-q"><strong>Q:</strong> {question}</div>'
                    f'<div class="chat-a"><strong>A:</strong> {answer}</div>',
                    unsafe_allow_html=True
                )
                supabase.table("chats").insert({
                    "question": question,
                    "answer": answer,
                    "dataset_name": selected or "unknown",
                    "user_id": user_id
                }).execute()
            except Exception as e:
                st.error(f"AI request failed: {e}")

# ---------------- CHAT HISTORY ----------------
st.markdown('<div class="section-header"><span>📜</span><h2 style="margin:0">Chat History</h2></div>', unsafe_allow_html=True)

try:
    history = (
        supabase.table("chats")
        .select("*")
        .eq("user_id", user_id)
        .limit(10)
        .execute()
        .data or []
    )

    if not history:
        st.info("No chat history yet. Ask a question above!")
    else:
        for h in reversed(history):
            ds_name = h.get("dataset_name", "unknown")
            col = primary_color(ds_name)
            st.markdown(
                f'<div style="border-left:3px solid {col};padding-left:12px;margin:8px 0">'
                f'<div class="chat-q"><strong>Q:</strong> {h["question"]}</div>'
                f'<div class="chat-a"><strong>A:</strong> {h["answer"]}</div>'
                f'<small style="opacity:0.5">Dataset: <code>{ds_name}</code></small>'
                f'</div>',
                unsafe_allow_html=True
            )
            st.divider()
except Exception as e:
    st.error(f"Could not load chat history: {e}")
