import json
import logging
import time
from pathlib import Path
from typing import Optional, Union

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


_retry_logger = logging.getLogger(__name__)


def get_with_retry(
    url: str,
    params: dict = None,
    headers: dict = None,
    max_retries: int = 3,
    backoff: float = 1.5,
    timeout: int = 15,
) -> requests.Response:
    """GET with exponential backoff and Retry-After support. Raises on final failure."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                x_ratelimit = {
                    k: v for k, v in response.headers.items()
                    if k.lower().startswith(("x-ratelimit", "ratelimit", "retry"))
                }
                _retry_logger.warning(
                    "429 rate-limited: %s | Retry-After: %s | headers: %s",
                    url, retry_after, x_ratelimit,
                )
                if attempt < max_retries - 1:
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff ** (attempt + 2)
                    _retry_logger.info("Waiting %.1fs before retry %d/%d", wait, attempt + 1, max_retries)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                sleep_time = backoff ** attempt
                time.sleep(sleep_time)
    raise last_exc


def save_raw(data: Union[dict, list], subdir: Path, filename: str) -> Path:
    """Save data as JSON to a raw data subdirectory."""
    subdir.mkdir(parents=True, exist_ok=True)
    path = subdir / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_json(path: Path) -> Optional[Union[dict, list]]:
    """Load JSON from a file, returning None if the file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def strip_jsonp(text: str) -> Union[dict, list]:
    """Strip JSONP wrapper (e.g. '?(...);\n') and parse JSON."""
    start = text.index("(") + 1
    end = text.rindex(")")
    return json.loads(text[start:end])
