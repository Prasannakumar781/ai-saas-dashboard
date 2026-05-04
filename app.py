import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI


# ---------------- SETUP ----------------
st.set_page_config(page_title="AI SaaS Dashboard", layout="wide")
st.title("🚀 AI SaaS Dashboard (GPT + Supabase)")

load_dotenv()

# ---------------- SUPABASE ----------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase credentials missing in .env")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
st.sidebar.title("🔐 Account")

if "user" not in st.session_state:
    st.session_state.user = None

email = ""
password = ""
login = False
signup = False

# ---------------- NOT LOGGED IN ----------------
if st.session_state.user is None:

    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    login = st.sidebar.button("Login")
    signup = st.sidebar.button("Sign Up")

    if login:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if res and res.user:
            st.session_state.user = res.user
            st.rerun()

    if signup:
        supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        st.success("Signup success ✔")

# ---------------- LOGGED IN ----------------
else:
    st.sidebar.success(f"Logged in as {st.session_state.user.email}")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

if login:
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if res and res.user:
            st.session_state.user = res.user
            st.success(f"Welcome {res.user.email} ✔")
        else:
            st.error("Login failed: Invalid credentials")

    except Exception as e:
        st.error(f"Login error: {e}")
if signup:
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        st.success("Signup success ✔ Check Supabase users table")

    except Exception as e:
        st.error(f"Signup failed: {e}")

# ---------------- OPENAI ----------------
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("❌ OPENAI_API_KEY missing in .env")
    st.stop()

client = OpenAI(api_key=api_key)

def ask_ai(question, df):
    sample = df.head(20).to_string()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a senior data analyst."},
            {"role": "user", "content": f"""
Dataset:
{sample}

Question:
{question}
"""}
        ]
    )

    return response.choices[0].message.content

# ---------------- UPLOAD ----------------
st.subheader("📁 Upload Dataset")

file = st.file_uploader("Upload CSV")

df = None

if file:
    df = pd.read_csv(file)

    st.dataframe(df.head())

    supabase.table("datasets").insert({
        "name": file.name,
        "data": json.loads(df.to_json(orient="records"))
    }).execute()

    st.success("✔ Saved to cloud")

# ---------------- LOAD DATASETS ----------------
res = supabase.table("datasets").select("*").execute()
datasets = res.data or []

df = None

if datasets:
    st.subheader("📂 Cloud Datasets")

    names = [d["name"] for d in datasets]
    selected = st.selectbox("Choose dataset", names)

    data = next(d for d in datasets if d["name"] == selected)
    df = pd.DataFrame(data["data"])

    st.dataframe(df)

    # ---------------- CHART ----------------
    st.subheader("📊 Visualization")

    cols = df.columns.tolist()

    x = st.selectbox("X axis", cols)
    y = st.selectbox("Y axis", cols)

    fig = px.bar(df, x=x, y=y)
    st.plotly_chart(fig)

else:
    st.warning("Upload dataset first")

# ---------------- GPT CHAT ----------------
st.subheader("💬 AI Data Analyst")

question = st.text_input("Ask a question about your data")

if question:
    if df is None:
        st.warning("No dataset loaded")
    else:
        with st.spinner("Thinking like a data analyst... 🤖"):
            answer = ask_ai(question, df)

        st.success("AI Response")
        st.write(answer)

        # OPTIONAL: save chat to Supabase (SAAS FEATURE)
        supabase.table("chats").insert({
            "question": question,
            "answer": answer,
            "dataset_name": selected if "selected" in locals() else "unknown"
        }).execute()
st.subheader("📜 Chat History")

history = supabase.table("chats").select("*").execute().data or []

for h in reversed(history[-10:]):
    st.markdown(f"**Q:** {h['question']}")
    st.markdown(f"**A:** {h['answer']}")
    st.divider()