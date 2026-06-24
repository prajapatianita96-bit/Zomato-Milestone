# Zomato AI Recommendation System - Deployment Plan

This document outlines the strategy for deploying the Zomato AI Restaurant Recommendation system to the cloud.

## ⚠️ Important Note Regarding "Streamlit Cloud"

You requested to deploy this project on **Streamlit**. However, during our recent development, we pivoted the frontend architecture from Streamlit to a **React UI served by a FastAPI backend** to achieve the "Nocturnal Epicure" design system.

**Streamlit Community Cloud** *only* hosts native Python Streamlit scripts (e.g., `app.py` using `import streamlit`). It **cannot** host a FastAPI server or a custom React/HTML frontend. 

Therefore, you have two deployment paths depending on your goal:

---

## Path 1: Deploy the Current React + FastAPI App (Recommended)

To keep the beautiful, ultra-high-quality UI we just built, you need a generic cloud provider that supports Python web servers (FastAPI). The easiest and most popular free option is **Render**.

### Steps to Deploy on Render.com:
1. **Prepare GitHub:**
   - Push your entire `Zomato-Milestone` folder to a GitHub repository.
   - Ensure `requirements.txt` contains `fastapi`, `uvicorn`, `python-dotenv`, `groq`, `pandas`, `pyyaml`.
2. **Create Web Service:**
   - Go to [Render.com](https://render.com/) and sign in with GitHub.
   - Click **New +** and select **Web Service**.
   - Connect the GitHub repository you just created.
3. **Configure the Service:**
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python -m src.api` (or `uvicorn src.api:app --host 0.0.0.0 --port 10000`)
4. **Environment Variables:**
   - Go to the **Environment** tab on Render.
   - Add your secret `GROQ_API_KEY`.
5. **Deploy:**
   - Click **Save / Deploy**. Render will spin up the server, and you'll get a public URL (e.g., `https://zomato-ai.onrender.com`) where your React UI will be live!

---

## Path 2: Deploy on Streamlit Community Cloud (Reverting the UI)

If you strictly *must* deploy to Streamlit Cloud (perhaps for a school project or strict requirement), you will not be able to use the React UI we built. You must revert to or recreate a native `app.py` Streamlit frontend.

### Steps to Deploy on Streamlit Cloud:
1. **Restore Streamlit App:**
   - You must have an `app.py` in the root directory that contains your Streamlit UI code (`import streamlit as st`).
2. **Prepare GitHub:**
   - Push the code to a public GitHub repository. 
   - Ensure `streamlit` is in your `requirements.txt`.
3. **Deploy:**
   - Go to [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
   - Click **New app**.
   - Select your repository, branch, and specify the **Main file path** as `app.py`.
4. **Secrets:**
   - Before hitting deploy, click **Advanced settings**.
   - Under "Secrets", paste your `GROQ_API_KEY`:
     ```toml
     GROQ_API_KEY = "your-actual-api-key"
     ```
5. **Launch:**
   - Click **Deploy!** 

## Summary
To preserve the gorgeous, ultra-clear React UI with the AI-generated fallback images, follow **Path 1 (Render)**. If you are required to use Streamlit Cloud, you must follow **Path 2** and revert the frontend.
