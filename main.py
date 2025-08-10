import streamlit as st
import os
import requests
import json
import time
from dotenv import load_dotenv

st.set_page_config(page_title="AFH", layout="wide")
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ANALYSIS_AUTH_TOKEN = os.getenv("GEMINI_API_KEY")
ANALYSIS_ENGINE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

def fetch_pr_data(repo_owner: str, repo_name: str, pr_id: int) -> dict | None:

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

def fetch_pr_diff(repo_owner: str, repo_name: str, pr_id: int) -> str | None:
    if not GITHUB_TOKEN:
        st.error("GitHub Token Not Connected.")
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
        st.error(f"Error Fetching PR Diff: {e}")
        return None


def generate_structured_review(pr_title: str, pr_body: str, pr_diff: str) -> dict | None:
    
    if not ANALYSIS_AUTH_TOKEN:
        st.error("Gemini API Key Not Connected")
        return None

    prompt = f"""
    You are an expert software engineer performing a detailed code review.
    Your task is to analyze the following pull request and provide a structured JSON response.

    **Pull Request Details:**
    Title: {pr_title}
    Body: {pr_body}

    **Code Changes:**
    ```diff
    {pr_diff}
    ```

    **Instructions:**
    Return a single, valid JSON object with three top-level keys: 'summary', 'review_report', and 'full_corrected_code'.
    1.  **summary**: A concise, high-level summary of your findings.
    2.  **review_report**: An array of objects. For every issue you find (no matter how small), you MUST create a corresponding object in this array. Each object must include: 'file_path', 'severity' (CRITICAL, MAJOR, or MINOR), 'description', and a 'fix_suggestion_code' snippet showing how to fix the issue.
    3.  **full_corrected_code**: A string containing the complete, corrected code for the file, with all your suggestions applied. This should be a ready-to-use code block that the user can copy and paste.
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    api_url = f"{ANALYSIS_ENGINE_URL}?key={ANALYSIS_AUTH_TOKEN}"

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        st.error(f"Failed Review: {e}")
        return None


def display_review_report(review_data: dict):
 
    try:
        report_content_str = review_data['candidates'][0]['content']['parts'][0]['text']
        report = json.loads(report_content_str)
    except (KeyError, IndexError, json.JSONDecodeError):
        st.error("Failed AI Response. Format Error.")
        st.json(review_data)
        return

    summary = report.get("summary", "No summary provided.")
    issues = report.get("review_report", [])
    full_code = report.get("full_corrected_code")

    st.subheader("Review Summary")
    st.markdown(summary)

    if not issues:
        st.success("No Specific Issues Found.")
        return

    critical_issues = [i for i in issues if i.get("severity") == "CRITICAL"]
    major_issues = [i for i in issues if i.get("severity") == "MAJOR"]
    minor_issues = [i for i in issues if i.get("severity") == "MINOR"]

    st.markdown("---")

    if critical_issues:
        with st.expander(f"Critical Issues ({len(critical_issues)})", expanded=True):
            for issue in critical_issues:
                st.markdown(f"**Description:** {issue.get('description', 'N/A')}")
                st.code(issue.get('fix_suggestion_code', '# No suggestion provided'), language='python')
                st.markdown("---")

    if major_issues:
        with st.expander(f"Major Issues ({len(major_issues)})"):
            for issue in major_issues:
                st.markdown(f"**Description:** {issue.get('description', 'N/A')}")
                st.code(issue.get('fix_suggestion_code', '# No suggestion provided'), language='python')
                st.markdown("---")

    if minor_issues:
        with st.expander(f"Minor Issues ({len(minor_issues)})"):
            for issue in minor_issues:
                st.markdown(f"**Description:** {issue.get('description', 'N/A')}")
                st.code(issue.get('fix_suggestion_code', '# No suggestion provided'), language='python')
                st.markdown("---")

    if full_code:
        st.markdown("---")
        st.subheader("Complete Suggested Code")
        st.markdown("The following code block contains all suggested fixes and can be used to replace the original file.")
        st.code(full_code, language='python')

st.title("AI PR Manager")
st.markdown("Enter the details of a public GitHub pull request to get a detailed automated code review.")

with st.form("pr_form"):
    repo_owner = st.text_input("Repository Owner")
    repo_name = st.text_input("Repository Name")
    pr_id = st.number_input("PR Number", min_value=1, step=1)
    
    run_button_clicked = st.form_submit_button("Generate Review")

    if run_button_clicked:
        if not repo_owner or not repo_name or not pr_id:
            st.error("Please Fill all the Fields")
        else:
            with st.spinner("Analyzing the Pull Request"):
                pr_data = fetch_pr_data(repo_owner, repo_name, pr_id)
                pr_changes = fetch_pr_diff(repo_owner, repo_name, pr_id)

                if pr_data and pr_changes:
                    review_data = generate_structured_review(pr_data["title"], pr_data["body"], pr_changes)
                    
                    st.divider()
                    st.success("Analysis Complete")
                    
                    if review_data:
                        display_review_report(review_data)
                    else:
                        st.error("Could not generate the Review Report.")
                else:
                    st.error("Failed to Fetch Request Data. Please check the Details.")
