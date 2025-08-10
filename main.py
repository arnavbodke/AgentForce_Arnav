import streamlit as st
import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ANALYSIS_AUTH_TOKEN = os.getenv("GEMINI_API_KEY")

def fetch_pr_data(repo_owner: str, repo_name: str, pr_id: int) -> dict:
    if not GITHUB_TOKEN:
        st.error("GitHub Token Not Connected")
        return None

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        pr_details = response.json()
        return {
            "title": pr_details.get('title', ''),
            "body": pr_details.get('body', '')
        }
    except requests.exceptions.RequestException as e:
        st.error(f"Error Fetching PR Details: {e}")
        return None

def fetch_pr_diff(repo_owner: str, repo_name: str, pr_id: int) -> str:
    if not GITHUB_TOKEN:
        st.error("GitHub Token Not Connected")
        return None

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.diff"
    }
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        st.error(f"Fetching Error: {e}")
        return None

def generate_review(pr_title: str, pr_body: str, pr_diff: str) -> str:
    if not ANALYSIS_AUTH_TOKEN:
        st.error("Gemini Key Not Connected")
        return "API Key Error"

    prompt = f"""
    You are a code review assistant. Your task is to provide a brief code review for the following pull request.

    Pull Request Details:
    Title: {pr_title}
    Body: {pr_body}

    Code Changes:
    ```diff
    {pr_diff}
    ```

    Please provide a concise review in a conversational tone.
    """

    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            headers = { "Content-Type": "application/json" }
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            }
            
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={ANALYSIS_AUTH_TOKEN}"
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            if result.get('candidates'):
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return "Failed to get review: No content from API."
        except requests.exceptions.RequestException as e:
            st.warning(f"API call failed, retrying... ({retries+1}/{max_retries})")
            retries += 1
            time.sleep(2 ** retries)

    return "Failed to get review after multiple retries."


st.set_page_config(page_title="AFH")

st.title("AI PR Manager")
st.markdown("Markdown")

with st.form("pr_form"):
    repo_owner = st.text_input("Owner")
    repo_name = st.text_input("Repository Name")
    pr_id = st.number_input("PR Number", min_value=1, value=42, step=1)
    
    run_button_clicked = st.form_submit_button("Review")

    if run_button_clicked:
        if not repo_owner or not repo_name or not pr_id:
            st.error("Incomplete Fields")
        else:
            with st.spinner("Request Initiated"):
                pr_data = fetch_pr_data(repo_owner, repo_name, pr_id)
                pr_changes = fetch_pr_diff(repo_owner, repo_name, pr_id)

                if pr_data and pr_changes:
                    review = generate_review(pr_data["title"], pr_data["body"], pr_changes)
                    
                    st.divider()
                    st.success("Review")
                    st.subheader("Report")
                    st.code(review)
                else:
                    st.error("Error")
