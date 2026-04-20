from __future__ import annotations

import logging
import time

from app.services.proactive_voice import run_voice_worker_once

logger = logging.getLogger(__name__)


def run_forever(*, poll_seconds: int = 2, batch_size: int = 20) -> None:
    logger.info("voice tts worker started (poll=%ss, batch=%s)", poll_seconds, batch_size)
    while True:
        try:
            processed = run_voice_worker_once(batch_size=batch_size)
            if processed:
                logger.info("voice tts worker processed %s jobs", processed)
        except Exception as exc:
            logger.warning("voice tts worker error: %s", exc)
        time.sleep(max(1, poll_seconds))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
