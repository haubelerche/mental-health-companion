from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError

from app.advisors.base import BaseAdvisor
from app.services.schemas.contracts import AdvisorAdvice


class AdvisorPool:
    def __init__(self, advisors: list[BaseAdvisor], *, timeout_ms: int = 1200) -> None:
        self._advisors = advisors
        self._timeout = timeout_ms / 1000.0

    def run(self, *, user_message: str, context_summary: str = "") -> list[AdvisorAdvice]:
        results: list[AdvisorAdvice] = []
        with ThreadPoolExecutor(max_workers=max(1, len(self._advisors))) as ex:
            futures = [ex.submit(a.run, user_message=user_message, context_summary=context_summary) for a in self._advisors]
            for fut in futures:
                try:
                    out = fut.result(timeout=self._timeout)
                except TimeoutError:
                    continue
                if hasattr(out, "final_text"):
                    continue
                if not isinstance(out, AdvisorAdvice):
                    continue
                if not out.advisor_id:
                    continue
                results.append(out)
        ranked = sorted(results, key=lambda x: float(x.confidence or 0.0), reverse=True)
        return ranked[:2]
