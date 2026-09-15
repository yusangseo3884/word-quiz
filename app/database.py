"""데이터베이스(SQLite) 담당 파일.

단어장 데이터를 저장하고 꺼내는 일만 여기서 합니다.
나중에 DB를 PostgreSQL 등으로 바꾸더라도 이 파일만 고치면 됩니다.
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# DB 파일 위치. 환경변수 DB_PATH가 있으면 그 경로를 쓰고, 없으면 프로젝트의 data 폴더에 저장합니다.
# (컨테이너/쿠버네티스 단계에서 볼륨 경로로 바꿀 때 코드 수정 없이 환경변수만 바꾸면 됩니다.)
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "words.db"
DB_PATH = Path(os.getenv("DB_PATH", DEFAULT_DB_PATH))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """DB 연결을 열고, 작업이 끝나면 저장(commit)한 뒤 닫습니다."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 결과를 row["word"]처럼 이름으로 꺼낼 수 있게 함
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """앱이 시작될 때 한 번 실행: 폴더와 단어장 표가 없으면 만듭니다."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS words (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                word          TEXT NOT NULL UNIQUE COLLATE NOCASE,
                meaning       TEXT NOT NULL,
                correct_count INTEGER NOT NULL DEFAULT 0,
                wrong_count   INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def list_words() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM words ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def add_word(word: str, meaning: str) -> dict | None:
    """단어를 추가합니다. 이미 있는 단어면 None을 돌려줍니다."""
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO words (word, meaning) VALUES (?, ?)", (word, meaning)
            )
            row = conn.execute("SELECT * FROM words WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        return None
    return dict(row)


def delete_word(word_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
        return cur.rowcount > 0


def get_word(word_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
    return dict(row) if row else None


def get_random_word(exclude_id: int | None = None) -> dict | None:
    """퀴즈용 단어를 무작위로 하나 고릅니다.

    - 방금 나온 단어(exclude_id)는 가능하면 피합니다.
    - 틀린 횟수가 많은 단어일수록 더 자주 나옵니다.
    """
    weighted_random = "(ABS(RANDOM()) % 1000000) / (1.0 + wrong_count)"
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT * FROM words WHERE id != ? ORDER BY {weighted_random} LIMIT 1",
            (exclude_id if exclude_id is not None else -1,),
        ).fetchone()
        if row is None:
            # 단어가 1개뿐이라 제외하면 남는 게 없을 때
            row = conn.execute("SELECT * FROM words ORDER BY RANDOM() LIMIT 1").fetchone()
    return dict(row) if row else None


def record_answer(word_id: int, correct: bool) -> None:
    column = "correct_count" if correct else "wrong_count"
    with get_connection() as conn:
        conn.execute(f"UPDATE words SET {column} = {column} + 1 WHERE id = ?", (word_id,))
