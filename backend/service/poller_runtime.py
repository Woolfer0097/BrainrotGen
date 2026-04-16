"""Poller lifecycle management module.

Provides functions to start, stop, and access the background request poller.
Supports both real video generation and static video modes for testing.
"""

from backend.config import settings
from backend.service.poller import RequestPoller
from backend.service.video import VideoGenerationService
from backend.service.video_static import StaticExampleVideoService

_request_poller: RequestPoller | None = None


def _build_request_poller() -> RequestPoller:
    """Build a RequestPoller with appropriate video service.

    Returns:
        Configured RequestPoller instance.
    """
    if settings.use_static_example_video:
        video_service = StaticExampleVideoService(
            settings.static_example_video_file,
        )
    else:
        video_service = VideoGenerationService()
    return RequestPoller(video_service=video_service)


def get_request_poller() -> RequestPoller:
    """Get or create the singleton RequestPoller instance.

    Returns:
        The global RequestPoller instance.
    """
    global _request_poller
    if _request_poller is None:
        _request_poller = _build_request_poller()
    return _request_poller


def start_request_poller() -> RequestPoller:
    """Start the background request poller.

    Creates the poller if needed and starts it in a background thread.

    Returns:
        The running RequestPoller instance.
    """
    poller = get_request_poller()
    poller.start_in_background()
    return poller


def stop_request_poller(timeout: float = 5.0) -> None:
    """Stop the background request poller gracefully.

    Args:
        timeout: Seconds to wait for the poller thread to finish.
    """
    if _request_poller is None:
        return
    _request_poller.stop()
    _request_poller.join(timeout)
