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

# ================= AUTH =================
def login_page():
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    login = st.sidebar.button("Login")
    signup = st.sidebar.button("Sign Up")

    if signup:
        supabase.auth.sign_up({"email": email, "password": password})
        st.info("Check email to confirm account")

    if login:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if res and res.user:
            st.session_state.user = res.user
            st.rerun()

    st.warning("Please login to continue")
    st.stop()


# 🔴 FORCE LOGIN FIRST (CRITICAL)
if st.session_state.user is None:
    login_page()

# ================= LOGGED IN AREA =================
st.sidebar.success(f"Logged in as {st.session_state.user.email}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ================= EVERYTHING BELOW IS PROTECTED =================

st.subheader("📁 Upload Dataset")

file = st.file_uploader("Upload CSV")

df = None
selected = None

if file:
    df = pd.read_csv(file)

    supabase.table("datasets").insert({
        "name": file.name,
        "data": df.to_dict(orient="records")
    }).execute()

    st.success("Saved ✔")

# ---------------- LOAD DATASETS ----------------
st.subheader("📂 Cloud Datasets")

res = supabase.table("datasets").select("*").execute()
datasets = res.data or []

if datasets:
    names = [d["name"] for d in datasets]
    selected = st.selectbox("Choose dataset", names)

    data = next(d for d in datasets if d["name"] == selected)
    df = pd.DataFrame(data["data"])

    st.dataframe(df)

else:
    st.warning("No datasets found")
