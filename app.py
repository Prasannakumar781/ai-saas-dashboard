import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from openai import OpenAI

# ---------------- SETUP ----------------
st.set_page_config(page_title="AI SaaS Dashboard", layout="wide")
st.title("🚀 AI SaaS Dashboard")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# FIX 1: Restore session on page refresh so users aren't logged out
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

    # SIGN UP
    if signup:
        if not email or not password:
            st.warning("Enter email and password")
            return
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.info("📩 Check your email to confirm your account before logging in")
        except Exception as e:
            st.error(f"Signup error: {e}")

    # LOGIN
    if login:
        if not email or not password:
            st.warning("Enter email and password")
            return
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res and res.user:
                st.session_state.user = res.user
                st.success("Login successful ✔")
                st.rerun()
        except Exception as e:
            # FIX 2: Show the actual error so the user knows what went wrong
            st.error(f"Login failed ❌: {e}")

    st.warning("Please login or sign up to continue")
    st.stop()

# 🔴 FORCE LOGIN FIRST
if st.session_state.user is None:
    auth_page()

# ---------------- LOGGED IN AREA ----------------
user_id = st.session_state.user.id  # FIX 3: Scope all queries to this user's ID

st.sidebar.success(f"Logged in as {st.session_state.user.email}")

if st.sidebar.button("Logout"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# ---------------- AI FUNCTION ----------------
def ask_ai(question: str, df: pd.DataFrame) -> str:
    sample = df.head(20).to_string()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a senior data analyst. Be concise and clear."},
            {
                "role": "user",
                "content": f"Dataset sample:\n{sample}\n\nQuestion:\n{question}"
            }
        ]
    )
    return response.choices[0].message.content

# ---------------- DATASETS ----------------
st.subheader("📂 Cloud Datasets")

file = st.file_uploader("Upload CSV")

# ---------------- UPLOAD ----------------
if file:
    try:
        df_upload = pd.read_csv(file)
        # FIX 4: Store user_id so each user only sees their own datasets
        supabase.table("datasets").insert({
            "name": file.name,
            "data": df_upload.to_dict(orient="records"),
            "user_id": user_id
        }).execute()
        st.success("✔ Uploaded successfully")
        st.rerun()
    except Exception as e:
        st.error(f"Upload failed: {e}")

# ---------------- FETCH USER'S DATASETS ----------------
def load_datasets():
    # FIX 5: Filter by user_id so users only see their own data
    result = supabase.table("datasets").select("*").eq("user_id", user_id).execute()
    return result.data or []

datasets = load_datasets()

df = None
selected = None
selected_id = None  # FIX 6: Use row ID for delete, not name (names can clash)

# FIX 7: Moved the "no datasets" warning OUTSIDE the `if datasets:` block
if not datasets:
    st.warning("No datasets found. Upload a CSV to get started.")
else:
    names = [d["name"] for d in datasets]

    selected = st.selectbox("Choose dataset", names, key="dataset_selector")

    data = next(d for d in datasets if d["name"] == selected)
    selected_id = data["id"]
    df = pd.DataFrame(data["data"])

    st.dataframe(df)

    # ---------------- DELETE ----------------
    if st.button("🗑 Delete Dataset", key="delete_btn"):
        try:
            # FIX 8: Delete by unique row ID, not by name
            supabase.table("datasets").delete().eq("id", selected_id).execute()
            st.success("Deleted ✔")
            st.rerun()
        except Exception as e:
            st.error(f"Delete failed: {e}")

    # ---------------- CHART ----------------
    st.subheader("📊 Visualization")

    if df is not None and not df.empty:
        all_cols = df.columns.tolist()
        # FIX 9: Only allow numeric columns for Y-axis to prevent broken charts
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if not numeric_cols:
            st.warning("No numeric columns found for Y-axis. Charts require at least one numeric column.")
        else:
            x = st.selectbox("X axis", all_cols, key="x_axis")
            y = st.selectbox("Y axis", numeric_cols, key="y_axis")

            chart_type = st.radio("Chart type", ["Bar", "Line", "Scatter"], horizontal=True)

            if chart_type == "Bar":
                fig = px.bar(df, x=x, y=y)
            elif chart_type == "Line":
                fig = px.line(df, x=x, y=y)
            else:
                fig = px.scatter(df, x=x, y=y)

            st.plotly_chart(fig, use_container_width=True)

# ---------------- AI CHAT ----------------
st.subheader("💬 AI Data Analyst")

# FIX 10: Guard and inform user clearly if no dataset is loaded
if df is None:
    st.info("Load a dataset above to start asking questions.")
else:
    question = st.text_input("Ask a question about your dataset")

    if question:
        with st.spinner("Thinking... 🤖"):
            try:
                answer = ask_ai(question, df)
                st.success("AI Response")
                st.write(answer)

                # FIX 11: Save chat history scoped to user_id
                supabase.table("chats").insert({
                    "question": question,
                    "answer": answer,
                    "dataset_name": selected or "unknown",
                    "user_id": user_id
                }).execute()
            except Exception as e:
                st.error(f"AI request failed: {e}")

# ---------------- CHAT HISTORY ----------------
st.subheader("📜 Chat History")

try:
    # FIX 12: Filter chat history by user_id so users only see their own history
    history = (
        supabase.table("chats")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
        .data or []
    )

    if not history:
        st.info("No chat history yet. Ask a question above!")
    else:
        for h in history:
            st.markdown(f"**Q:** {h['question']}")
            st.markdown(f"**A:** {h['answer']}")
            st.caption(f"Dataset: `{h.get('dataset_name', 'unknown')}`")
            st.divider()
except Exception as e:
    st.error(f"Could not load chat history: {e}")
