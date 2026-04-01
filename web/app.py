import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st

API_BASE = os.getenv("STREAMLIT_API_URL", "http://127.0.0.1:8000").rstrip("/")
API_V1_PREFIX = os.getenv("STREAMLIT_API_V1_PREFIX", "/api/v1").rstrip("/")
GENERATE_PATH = f"{API_V1_PREFIX}/generate"
GENERATE_URL = f"{API_BASE}{GENERATE_PATH}"

st.set_page_config(
    page_title="BrainrotGen",
    layout="wide",
)

st.title("Generate Brainrot Video")

LOADING_PHRASES = [
    "Sending request...",
    "Generating script...",
    "Synthesizing voice...",
    "Mixing layers...",
    "Doing a bit of magic...",
    "Polishing final output...",
]

login = st.text_input("Login", placeholder="Your login here...")
login_ok = bool((login or "").strip())

text = st.text_area(
    "Text",
    height=200,
    placeholder="Enter your text for the video here...",
    label_visibility="collapsed",
    disabled=not login_ok,
)

if not login_ok:
    st.info("Please enter your login to continue")

_, mid, _ = st.columns([3, 2, 3])
with mid:
    submit_button = st.button(
        "Send text",
        type="primary",
        use_container_width=True,
    )

if "last_video" not in st.session_state:
    st.session_state.last_video = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None

if submit_button:
    st.session_state.last_error = None
    st.session_state.last_video = None

    if not login_ok:
        st.session_state.last_error = "Login is required"
    elif not (text or "").strip():
        st.session_state.last_error = "Please enter some text to generate a video"
    else:
        status_placeholder = st.empty()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    requests.post,
                    GENERATE_URL,
                    json={
                        "login": login.strip(),
                        "text": text.strip(),
                    },
                    timeout=300,
                )

                while not future.done():
                    phrase = random.choice(LOADING_PHRASES)
                    dots = "." * random.randint(1, 3)
                    status_placeholder.markdown(f"### {phrase}{dots}")
                    time.sleep(0.35)

                r = future.result()
        except requests.exceptions.RequestException as e:
            st.session_state.last_error = f"Error generating video: {e}"
        finally:
            status_placeholder.empty()

        if not st.session_state.last_error:
            ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
            if r.ok and ct.startswith("video/"):
                st.session_state.last_video = r.content
            elif r.ok and ct == "application/json":
                st.session_state.last_error = (
                    "Now answer is JSON, but we expected video content. Body: "
                    + r.text[:1000]
                )
            else:
                st.session_state.last_error = f"HTTP {r.status_code}: {r.text[:1000]}"

if st.session_state.last_error:
    st.error(st.session_state.last_error)

if st.session_state.last_video:
    st.subheader("Resulting video")
    st.video(st.session_state.last_video)
    st.download_button(
        label="Download video",
        data=st.session_state.last_video,
        file_name="brainrot_video.mp4",
        mime="video/mp4",
    )
