from backend.service.poller import RequestPoller

_request_poller: RequestPoller | None = None


def get_request_poller() -> RequestPoller:
    global _request_poller
    if _request_poller is None:
        _request_poller = RequestPoller()
    return _request_poller


def start_request_poller() -> RequestPoller:
    poller = get_request_poller()
    poller.start_in_background()
    return poller


def stop_request_poller(timeout: float = 5.0) -> None:
    if _request_poller is None:
        return
    _request_poller.stop()
    _request_poller.join(timeout)
