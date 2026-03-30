import requests
import streamlit as st
from backend.config import settings

API_BASE = settings.api_base_url.rstrip("/")
GENERATE_PATH = f"{settings.api_v1_prefix}/generate"
GENERATE_URL = f"{API_BASE}{GENERATE_PATH}"

st.set_page_config(
    page_title="BrainrotGen",
    layout="wide",
)

st.title("Generate Brainrot Video")

text = st.text_area(
    "Text",
    height=200,
    placeholder="Enter your text for the video here...",
    label_visibility="collapsed",
)

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

    if not (text or "").strip():
        st.session_state.last_error = "Please enter some text to generate a video"
    else:
        with st.spinner("Sending text and generating video..."):
            try:
                r = requests.post(
                    GENERATE_URL,
                    json={"text": text},
                    timeout=300,
                )
            except requests.exceptions.RequestException as e:
                st.session_state.last_error = f"Error generating video: {e}"
            else:
                ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
                if r.ok and ct.startswith("video/"):
                    st.session_state.last_video = r.content
                elif r.ok and ct == "application/json":
                    st.session_state.last_error = (
                        "Now answer is JSON, but we expected video content. Body: "
                        + r.text[:1000]
                    )
                else:
                    st.session_state.last_error = (
                        f"HTTP {r.status_code}: {r.text[:1000]}"
                    )

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
