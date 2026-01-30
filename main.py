import json
import sqlite3
from typing import Any, Sequence

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

MAX_CHARS = 512

app = FastAPI(title="MCPDict API", version="1.0.0")

def _dedup(chars: str) -> list[str]:
    """Remove duplicate characters while preserving order.
    E.g. "漢漢字字" -> ["漢", "字"]
    """
    return list(dict.fromkeys(chars))

def _open_ro_conn() -> sqlite3.Connection:
    """
    Open a read-only SQLite connection using URI mode.
    We keep it short-lived per request: less shared-state, fewer surprises.
    """
    conn = sqlite3.connect(
        "file:mcpdict.db?mode=ro",
        uri=True,
        check_same_thread=False,
        isolation_level=None,  # autocommit; good for read-only
    )
    conn.row_factory = sqlite3.Row

    # Defensive pragmas for production stability.
    conn.execute("PRAGMA busy_timeout = 2000;")
    conn.execute("PRAGMA query_only = ON;")
    conn.execute("PRAGMA trusted_schema = OFF;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn

def _build_query(n: int) -> str:
    """
    Build the SQL with a VALUES list of n rows.
    Parameterized: each row contributes (?, ?) = (字頭, 字頭編號).
    """
    if n <= 0:
        # Not expected to be used; caller handles empty input.
        raise ValueError("n must be > 0")

    values_sql = ", ".join(["(?, ?)"] * n)

    return f"""
WITH q(字頭, 字頭編號) AS (
  VALUES {values_sql}
),
hits AS (
  SELECT
    q.字頭,
	q.字頭編號,
    r.語言ID,
    l.讀音,
    l.註釋
  FROM q
  JOIN langs l
    ON langs MATCH ('字組:' || q.字頭)
  JOIN info_rowid r
    ON l.語言 = r.簡稱
  ORDER BY q.字頭編號, r.語言ID
),
grouped AS (
  SELECT
    字頭,
    json_group_array(
      CASE
        WHEN 註釋 IS NULL OR 註釋 = ''
      THEN json_array(語言ID, 讀音)
        ELSE json_array(語言ID, 讀音, 註釋)
      END
    ) AS 明細
  FROM hits
  GROUP BY 字頭編號
),
payload AS (
  SELECT
    json_group_array(
      json_array(
        字頭,
        json(明細)
      )
    ) AS data
  FROM grouped
)
SELECT
  json_object(
    'version', b.version,
    'data', json(p.data)
  ) AS result
FROM build_version b
CROSS JOIN payload p;"""

def _make_params(chars_list: Sequence[str]) -> list[Any]:
    """
    Flatten params for VALUES (字頭, 字頭編號) repeated.
    字頭編號 starts at 1 to match your original.
    """
    params: list[Any] = []
    for idx, ch in enumerate(chars_list, start=1):
        params.append(ch)
        params.append(idx)
    return params

def _query_chars_sync(chars: str) -> Any:
    """
    Synchronous DB query. Returns Python object parsed from DB JSON result.
    """
    if chars is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="chars is required")

    chars = chars.strip()
    if not chars:
        return []

    chars_list = _dedup(chars)

    if len(chars_list) > MAX_CHARS:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"too many chars; max={MAX_CHARS}")

    sql = _build_query(len(chars_list))
    params = _make_params(chars_list)

    try:
        conn = _open_ro_conn()
        try:
            row = conn.execute(sql, params).fetchone()
        finally:
            conn.close()

        if row is None or row["result"] is None:
            return []

        # SQLite JSON functions return text; parse to real JSON.
        return json.loads(row["result"])

    except HTTPException:
        raise
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"database error: {e.__class__.__name__}") from e
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="database returned invalid json") from e
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="internal server error") from e

@app.get("/chars/", response_class=Response)
async def get_chars(chars: str = Query(..., description="Characters to look up")) -> Response:
    """
    Returns JSON array like:
    [
      ["是", [[語言ID, 讀音], [語言ID, 讀音, 註釋], ...]],
      ["社", [...]],
      ...
    ]
    """
    result_obj = await run_in_threadpool(_query_chars_sync, chars)
    # We emit canonical JSON (no trailing whitespace), UTF-8, and do not escape CJK.
    payload = json.dumps(result_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(content=payload, media_type="application/json; charset=utf-8")


# ...（保留你原有 import / 常量 / app / helper）...

def _list_langs_sync() -> Any:
    """
    Synchronous DB query. Returns Python object parsed from DB JSON result.
    """
    sql = """
WITH r AS (
  SELECT
    ROWID AS 語言ID,
    語言,簡稱,
    地圖集二排序,地圖集二顏色,地圖集二分區,
    音典排序,音典顏色,音典分區,
    陳邡排序,陳邡顏色,陳邡分區,經緯度
  FROM info
),
payload AS (
  SELECT json_group_array(
    json_array(
      語言ID,語言,簡稱,
      地圖集二排序,地圖集二顏色,地圖集二分區,
      音典排序,音典顏色,音典分區,
      陳邡排序,陳邡顏色,陳邡分區,經緯度
    )
  ) AS data
  FROM r
) 
SELECT
  json_object(
    'version', b.version,
    'data', json(p.data)
  ) AS result
FROM build_version b
CROSS JOIN payload p;"""
    try:
        conn = _open_ro_conn()
        try:
            row = conn.execute(sql).fetchone()
        finally:
            conn.close()

        if row is None or row["result"] is None:
            return []

        return json.loads(row["result"])

    except sqlite3.OperationalError as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"database error: {e.__class__.__name__}",
        ) from e
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database returned invalid json",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal server error",
        ) from e

# ...（保留你原有 /chars/ 路由）...

@app.get("/list-langs/", response_class=Response)
async def list_langs() -> Response:
    """
    Returns JSON array like:
    [
      [語言ID,語言,簡稱,地圖集二排序,地圖集二顏色,地圖集二分區,音典排序,音典顏色,音典分區,陳邡排序,陳邡顏色,陳邡分區],
      ...
    ]
    """
    result_obj = await run_in_threadpool(_list_langs_sync)
    payload = json.dumps(result_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(content=payload, media_type="application/json; charset=utf-8")
