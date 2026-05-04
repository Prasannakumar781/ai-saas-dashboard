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
            supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            st.info("📩 Check your email to confirm your account before logging in")

        except Exception as e:
            st.error(f"Signup error: {e}")

    # LOGIN
    if login:
        if not email or not password:
            st.warning("Enter email and password")
            return

        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if res and res.user:
                st.session_state.user = res.user
                st.success("Login successful ✔")
                st.rerun()

        except Exception:
            st.error("Login failed ❌ (check email confirmation or credentials)")

    st.warning("Please login to continue")
    st.stop()

# 🔴 FORCE LOGIN FIRST
if st.session_state.user is None:
    auth_page()

# ---------------- LOGGED IN AREA ----------------
st.sidebar.success(f"Logged in as {st.session_state.user.email}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ---------------- AI FUNCTION ----------------
def ask_ai(question, df):
    sample = df.head(20).to_string()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a senior data analyst."},
            {
                "role": "user",
                "content": f"""
Dataset:
{sample}

Question:
{question}
"""
            }
        ]
    )

    return response.choices[0].message.content

st.subheader("📂 Cloud Datasets")

# ---------------- UPLOAD ----------------
file = st.file_uploader("Upload CSV")

if file:
    df_upload = pd.read_csv(file)

    try:
        supabase.table("datasets").insert({
            "name": file.name,
            "data": df_upload.to_dict(orient="records")
        }).execute()

        st.success("✔ Uploaded successfully")
        st.rerun()

    except Exception as e:
        st.error(f"Upload error: {e}")

# ---------------- REFRESH DATA ----------------
try:
    res = supabase.table("datasets").select("*").execute()
    datasets = res.data or []
except Exception:
    datasets = []

df = None
selected = None

if datasets:
    names = [d["name"] for d in datasets]
    selected = st.selectbox("Choose dataset", names)

    data = next(d for d in datasets if d["name"] == selected)
    df = pd.DataFrame(data["data"])

    st.dataframe(df)

    # ---------------- DELETE ----------------
    if st.button("🗑 Delete Dataset"):
        try:
            supabase.table("datasets") \
                .delete() \
                .eq("name", selected) \
                .execute()

            st.success("Deleted ✔")
            st.rerun()

        except Exception as e:
            st.error(f"Delete failed: {e}")

    # ---------------- CHART ----------------
    st.subheader("📊 Visualization")

    if df is not None and not df.empty:
        x = st.selectbox("X axis", df.columns, key="x_axis")
        y = st.selectbox("Y axis", df.columns, key="y_axis")

        fig = px.bar(df, x=x, y=y)
        st.plotly_chart(fig)

else:
    st.warning("No datasets found")
    # ---------------- CHART ----------------
    st.subheader("📊 Visualization")

    if not df.empty:
        x = st.selectbox("X axis", df.columns)
        y = st.selectbox("Y axis", df.columns)

        fig = px.bar(df, x=x, y=y)
        st.plotly_chart(fig)

else:
    st.warning("No datasets found")
# ---------------- AI CHAT ----------------
st.subheader("💬 AI Data Analyst")

question = st.text_input("Ask a question")

if question and df is not None:
    with st.spinner("Thinking... 🤖"):
        answer = ask_ai(question, df)

    st.success("AI Response")
    st.write(answer)

    try:
        supabase.table("chats").insert({
            "question": question,
            "answer": answer,
            "dataset_name": selected or "unknown"
        }).execute()
    except:
        pass

# ---------------- CHAT HISTORY ----------------
st.subheader("📜 Chat History")

try:
    history = supabase.table("chats").select("*").execute().data or []

    for h in reversed(history[-10:]):
        st.markdown(f"**Q:** {h['question']}")
        st.markdown(f"**A:** {h['answer']}")
        st.divider()
except:
    st.info("No chat history yet")
