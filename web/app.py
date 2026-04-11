import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests  # noqa: E402
import streamlit as st  # noqa: E402

from backend.config import settings  # noqa: E402
from backend.service.quota import DAILY_QUOTA_SECONDS  # noqa: E402

API_BASE = settings.api_base_url.rstrip("/")
GENERATE_PATH = f"{settings.api_v1_prefix}/generate"
API_V1_PREFIX = settings.api_v1_prefix.rstrip("/")
GENERATE_URL = f"{API_BASE}{GENERATE_PATH}"

API_DAILY_QUOTA_EXCEEDED_DETAIL = (
    f"Daily quota exceeded ({DAILY_QUOTA_SECONDS}s limit)"
)
DAILY_QUOTA_USER_MESSAGE = "Bruh, you're hitting the daily quota, buddy"

VIDEO_DISPLAY_WIDTH_PX = 640

st.set_page_config(
    page_title="BrainrotGen",
    layout="wide",
)

st.title("Generate Brainrot Video")

if "last_video" not in st.session_state:
    st.session_state.last_video = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None

LOADING_PHRASES = [
    "Crafting text-to-brainrot pipeline",
    "Loading another lore dump",
    "Cooked / uncooked — deciding",
    "Touch grass later — first this",
    "Wait for the plot twist",
    "Sigma grindset",
    "How about six seven",
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

if submit_button:
    st.session_state.last_error = None
    st.session_state.last_video = None

    if not login_ok:
        st.session_state.last_error = "Login is required"
    elif not (text or "").strip():
        st.session_state.last_error = (
            "Please enter some text to generate a video"
        )
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

                _phrase_pool = LOADING_PHRASES.copy()
                random.shuffle(_phrase_pool)
                _phrase_i = 0
                while not future.done():
                    if _phrase_i >= len(_phrase_pool):
                        _phrase_pool = LOADING_PHRASES.copy()
                        random.shuffle(_phrase_pool)
                        _phrase_i = 0
                    phrase = _phrase_pool[_phrase_i]
                    _phrase_i += 1
                    dots = "." * random.randint(1, 3)
                    status_placeholder.markdown(f"### {phrase}{dots}")
                    time.sleep(2)

                r = future.result()
        except requests.exceptions.RequestException as e:
            st.session_state.last_error = f"Error generating video: {e}"
        finally:
            status_placeholder.empty()

        if not st.session_state.last_error:
            ct = (
                (r.headers.get("content-type") or "")
                .split(";")[0]
                .strip()
                .lower()
            )
            if r.ok and ct.startswith("video/"):
                st.session_state.last_video = r.content
            elif r.ok and ct == "application/json":
                st.session_state.last_error = (
                    "Now answer is JSON, but we expected video content. Body: "
                    + r.text[:1000]
                )
            elif r.status_code == 429:
                detail = None
                try:
                    payload = r.json()
                    if isinstance(payload, dict):
                        d = payload.get("detail")
                        detail = d if isinstance(d, str) else None
                except ValueError:
                    pass
                if detail == API_DAILY_QUOTA_EXCEEDED_DETAIL:
                    st.session_state.last_error = DAILY_QUOTA_USER_MESSAGE
                else:
                    st.session_state.last_error = f"HTTP 429: {r.text[:1000]}"
            else:
                st.session_state.last_error = (
                    f"HTTP {r.status_code}: {r.text[:1000]}"
                )

if st.session_state.last_error:
    st.error(st.session_state.last_error)

if st.session_state.last_video:
    st.subheader("Resulting video")
    _, vid_col, _ = st.columns([2, 2, 2])
    with vid_col:
        st.video(
            st.session_state.last_video,
            width=VIDEO_DISPLAY_WIDTH_PX,
        )
    _, dl_col, _ = st.columns([2, 2, 2])
    with dl_col:
        st.download_button(
            label="Download video",
            data=st.session_state.last_video,
            file_name="brainrot_video.mp4",
            mime="video/mp4",
            use_container_width=True,
        )
