# 단어 퀴즈 앱 이미지 설명서

# 1. 바탕: 파이썬 3.12가 미리 설치된 가벼운 리눅스
FROM python:3.12-slim

# 2. 컨테이너 안에서 작업할 폴더
WORKDIR /app

# 3. 환경변수
#    - PYTHONDONTWRITEBYTECODE: 캐시 파일(.pyc)을 만들지 않음
#    - PYTHONUNBUFFERED: 로그를 바로바로 출력
#    - DB_PATH: 단어장 파일 위치 (나중에 볼륨을 연결할 곳)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/words.db

# 4. 필요한 도구 설치 (도구 목록만 먼저 복사해서, 코드만 바뀌었을 때 재설치를 건너뛰게 함)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 앱 코드 복사
COPY app ./app

# 6. 보안: 관리자(root)가 아닌 일반 사용자로 실행, 단어장 폴더 준비
RUN useradd --create-home appuser \
    && mkdir /data \
    && chown appuser /data
USER appuser

# 7. 이 컨테이너는 8000번 포트를 사용함 (안내용 표시)
EXPOSE 8000

# 8. 컨테이너가 시작될 때 실행할 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
