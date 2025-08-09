import streamlit as st
import os

def fetch_pr_data(repo_owner: str, repo_name: str, pr_id: int) -> dict:
    return {
        "title": "Pull Request",
        "body": "Change."
    }

def fetch_pr_diff(repo_owner: str, repo_name: str, pr_id: int) -> str:
    return "Simulated"

def generate_review(pr_title: str, pr_body: str, pr_diff: str) -> str:
    return "Simulated Report"


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
