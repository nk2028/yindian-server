from contextlib import asynccontextmanager
import json
import sqlite3
from typing import Any, Sequence
import pandas as pd

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

MAX_CHARS = 128

BUILD_VERSION: str | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global BUILD_VERSION
    try:
        conn = _open_ro_conn()
        try:
            row = conn.execute("SELECT CAST(version AS TEXT) AS version FROM build_version;").fetchone()
            if row and row["version"]:
                BUILD_VERSION = row["version"]
            else:
                raise RuntimeError("No version found in build_version table.")
        finally:
            conn.close()
    except Exception as e:
        raise RuntimeError(f"Failed to load build version during lifespan startup: {e}")

    yield

    # No shutdown logic needed — leave empty or add logging/cleanup if desired

app = FastAPI(title="MCPDict API", version="1.0.0", lifespan=lifespan)

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
)
SELECT
  r.語言ID,
  q.字頭,
  CASE
    WHEN COUNT(*) = 1 AND (MAX(l.註釋)  IS NULL OR MAX(l.註釋) = '')
    THEN MAX(l.讀音)
    ELSE json_group_array(
      CASE
        WHEN l.註釋 IS NULL OR l.註釋 = ''
        THEN json_array(l.讀音)
        ELSE json_array(l.讀音,l.註釋)
      END
    )
  END AS 讀音
FROM q
JOIN langs l
  ON langs MATCH ('字組:' || q.字頭)
JOIN info_rowid r
  ON l.語言 = r.簡稱
GROUP BY q.字頭編號, r.語言ID
ORDER BY r.語言ID;"""

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

    if BUILD_VERSION is None:
        raise HTTPException(status_code=500, detail="Build version not initialized")

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
            df = pd.read_sql_query(sql, conn, params=params)
        finally:
            conn.close()

        pivot_df = df.pivot(index='語言ID', columns='字頭', values='讀音')
        pivot_df.columns.name = None
        pivot_df = pivot_df.reset_index().fillna('')
        # Reorder columns to have 'id' first, then the characters in the order they were queried.
        pivot_df = pivot_df[['語言ID', *chars_list]]
        data_2d = [pivot_df.columns.tolist()] + pivot_df.values.tolist()

        return {
            'version': BUILD_VERSION,
            'data': data_2d,
        }

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
    陳邡排序,陳邡顏色,陳邡分區,
    地點,經緯度
  FROM info
  WHERE 簡稱<>'漢字'
),
payload AS (
  SELECT json_group_array(
    json_array(
      語言ID,語言,簡稱,
      地圖集二排序,地圖集二顏色,地圖集二分區,
      音典排序,音典顏色,音典分區,
      陳邡排序,陳邡顏色,陳邡分區,
      地點,經緯度
    )
  ) AS data
  FROM r
) 
SELECT
  json_object(
    'version', CAST(b.version AS TEXT),
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

@app.get("/list-langs/", response_class=Response)
async def list_langs() -> Response:
    """
    Returns JSON array like:
    [
        [
            語言ID,語言,簡稱,
            地圖集二排序,地圖集二顏色,地圖集二分區,
            音典排序,音典顏色,音典分區,
            陳邡排序,陳邡顏色,陳邡分區,
            地點,經緯度
        ],
        ...
    ]
    """
    result_obj = await run_in_threadpool(_list_langs_sync)
    payload = json.dumps(result_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(content=payload, media_type="application/json; charset=utf-8")
