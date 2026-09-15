"""웹 서버(FastAPI) 담당 파일.

브라우저가 보내는 HTTP 요청을 받아서 처리하고 응답을 돌려줍니다.
실행 방법: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import database

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()  # 서버가 켜질 때 DB 준비
    yield


app = FastAPI(title="단어 퀴즈", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------- 요청으로 받을 데이터 모양 ----------

class WordCreate(BaseModel):
    word: str = Field(min_length=1, max_length=100)
    meaning: str = Field(min_length=1, max_length=200)


class AnswerSubmit(BaseModel):
    answer: str = Field(max_length=200)


# ---------- 정답 채점 ----------

def normalize(text: str) -> str:
    """대소문자와 띄어쓰기 차이는 무시합니다."""
    return "".join(text.lower().split())


def is_correct(answer: str, meaning: str) -> bool:
    """뜻이 여러 개면(예: '사과, 능금') 그중 하나만 맞혀도 정답입니다."""
    user = normalize(answer)
    candidates = [normalize(m) for m in meaning.replace("/", ",").split(",")]
    return bool(user) and user in candidates


# ---------- 화면 ----------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


# ---------- API: 단어장 ----------

@app.get("/api/words")
def list_words():
    return database.list_words()


@app.post("/api/words", status_code=201)
def add_word(body: WordCreate):
    word, meaning = body.word.strip(), body.meaning.strip()
    if not word or not meaning:
        raise HTTPException(status_code=400, detail="단어와 뜻을 모두 입력해주세요.")
    created = database.add_word(word, meaning)
    if created is None:
        raise HTTPException(status_code=409, detail=f"'{word}'는 이미 등록된 단어입니다.")
    return created


@app.delete("/api/words/{word_id}", status_code=204)
def delete_word(word_id: int):
    if not database.delete_word(word_id):
        raise HTTPException(status_code=404, detail="단어를 찾을 수 없습니다.")


# ---------- API: 퀴즈 ----------

@app.get("/api/quiz")
def next_quiz(exclude_id: int | None = None):
    word = database.get_random_word(exclude_id)
    if word is None:
        raise HTTPException(status_code=404, detail="등록된 단어가 없습니다. 먼저 단어를 추가해주세요.")
    return {"id": word["id"], "word": word["word"]}  # 정답(뜻)은 보내지 않음


@app.post("/api/quiz/{word_id}/answer")
def submit_answer(word_id: int, body: AnswerSubmit):
    word = database.get_word(word_id)
    if word is None:
        raise HTTPException(status_code=404, detail="단어를 찾을 수 없습니다.")
    correct = is_correct(body.answer, word["meaning"])
    database.record_answer(word_id, correct)
    return {"correct": correct, "meaning": word["meaning"]}


# ---------- 상태 확인 (쿠버네티스가 앱이 살아있는지 확인할 때 사용) ----------

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
