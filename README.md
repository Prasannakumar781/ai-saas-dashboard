🚀 AI SaaS Dashboard

An AI-powered SaaS dashboard that allows users to upload datasets, visualize data, and interact with an AI data analyst in real time.

✨ Features
📂 Upload and manage CSV datasets
☁️ Cloud storage with Supabase
📊 Interactive visualizations (bar, line, scatter, heatmaps)
🤖 AI-powered data analysis using OpenAI
🔐 Secure authentication (Supabase Auth)
📁 Multi-dataset user workspace
⚡ Real-time insights and chat-based analytics
🛠 Tech Stack
Frontend: Streamlit
Backend: Python
Database & Auth: Supabase
AI Engine: OpenAI API
Data Processing: Pandas
Visualization: Plotly
📸 Demo

<img width="1892" height="937" alt="image" src="https://github.com/user-attachments/assets/92c477b6-f732-48a5-baaa-08dcf74dd9dc" />


Dashboard view
AI chat analysis
Graph visualizations
⚙️ Installation
# Clone repository
git clone https://github.com/your-username/ai-saas-dashboard.git

# Enter project folder
cd ai-saas-dashboard

# Create virtual environment (optional)
python -m venv venv
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
🔑 Environment Variables

Create a .streamlit/secrets.toml file:

SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"
OPENAI_API_KEY = "your-openai-api-key"
▶️ Run the App
streamlit run app.py
📂 Project Structure
ai-saas-dashboard/
│
├── app.py
├── Styles.css
├── requirements.txt
├── .streamlit/
│   └── secrets.toml
│
└── README.md
🚀 Future Improvements
AI agent for deeper analytics
Stripe payment integration (SaaS monetization)
Multi-user team workspaces
Deployment on cloud (Vercel/Streamlit Cloud)
Advanced dashboard templates
👨‍💻 Author

Built by Arditi
