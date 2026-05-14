"""Report non-canonical mem0 cache quality metrics.

This command is read-only. It helps decide whether legacy mem0 rows are safe to
ignore, delete, or manually migrate into canonical memory_cards.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.db.session import get_session_factory


QUERY = """
WITH rows AS (
  SELECT
    id::text AS id,
    payload,
    payload->>'source' AS source,
    payload->>'fallback_reason' AS fallback_reason,
    NULLIF(payload->>'session_id', '') AS session_id,
    NULLIF(payload->>'data', '') AS data,
    vector IS NULL AS vector_is_null
  FROM app.mem0_memories
),
normalized AS (
  SELECT
    *,
    lower(regexp_replace(coalesce(data, ''), '\\s+', ' ', 'g')) AS normalized_data
  FROM rows
)
SELECT
  (SELECT count(*) FROM rows) AS total_rows,
  (SELECT count(*) FROM rows WHERE vector_is_null) AS vector_null_rows,
  (SELECT count(*) FROM rows WHERE session_id IS NULL) AS missing_session_id_rows,
  coalesce((SELECT jsonb_object_agg(coalesce(source, '<null>'), n) FROM (
    SELECT source, count(*) AS n FROM rows GROUP BY source ORDER BY source
  ) s), '{}'::jsonb) AS by_source,
  coalesce((SELECT jsonb_object_agg(coalesce(fallback_reason, '<null>'), n) FROM (
    SELECT fallback_reason, count(*) AS n FROM rows GROUP BY fallback_reason ORDER BY fallback_reason
  ) f), '{}'::jsonb) AS by_fallback_reason,
  (SELECT count(*) FROM (
    SELECT normalized_data FROM normalized
    WHERE normalized_data <> ''
    GROUP BY normalized_data HAVING count(*) > 1
  ) d) AS duplicate_groups,
  (SELECT coalesce(sum(n), 0) FROM (
    SELECT count(*) AS n FROM normalized
    WHERE normalized_data <> ''
    GROUP BY normalized_data HAVING count(*) > 1
  ) d) AS rows_in_duplicate_groups
"""


def main() -> None:
    db = get_session_factory()()
    try:
        row = db.execute(text(QUERY)).mappings().one()
        for key, value in row.items():
            print(f"{key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
