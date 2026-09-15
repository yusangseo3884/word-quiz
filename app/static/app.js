// 화면 동작 담당 파일.
// 버튼을 누르면 서버(FastAPI)에 HTTP 요청을 보내고, 받은 결과로 화면을 바꿉니다.

const $ = (id) => document.getElementById(id);

const state = {
  currentWordId: null,
  correct: 0,
  total: 0,
  streak: 0,
};

// ---------- 서버 요청 공통 함수 ----------

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) {
    const error = new Error(typeof data.detail === "string" ? data.detail : "요청을 처리하지 못했습니다.");
    error.status = res.status;
    throw error;
  }
  return data;
}

// ---------- 탭 전환 ----------

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    $("tab-quiz").hidden = tab.dataset.tab !== "quiz";
    $("tab-words").hidden = tab.dataset.tab !== "words";
    if (tab.dataset.tab === "quiz") loadQuiz();
    if (tab.dataset.tab === "words") loadWords();
  });
});

// ---------- 단어장 ----------

async function loadWords() {
  const words = await api("GET", "/api/words");
  $("word-count").textContent = words.length;
  $("words-empty").hidden = words.length > 0;

  const tbody = $("word-list");
  tbody.innerHTML = "";
  for (const w of words) {
    const tr = document.createElement("tr");
    for (const [value, cls] of [[w.word, ""], [w.meaning, ""], [w.correct_count, "num"], [w.wrong_count, "num"]]) {
      const td = document.createElement("td");
      td.textContent = value; // textContent: 입력값을 글자로만 표시 (보안상 안전)
      if (cls) td.className = cls;
      tr.appendChild(td);
    }
    const tdDelete = document.createElement("td");
    const btn = document.createElement("button");
    btn.className = "delete";
    btn.textContent = "삭제";
    btn.addEventListener("click", async () => {
      if (!confirm(`'${w.word}'를 삭제할까요?`)) return;
      await api("DELETE", `/api/words/${w.id}`);
      loadWords();
    });
    tdDelete.appendChild(btn);
    tr.appendChild(tdDelete);
    tbody.appendChild(tr);
  }
}

$("word-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("word-error").hidden = true;
  try {
    await api("POST", "/api/words", {
      word: $("word-input").value,
      meaning: $("meaning-input").value,
    });
    $("word-form").reset();
    $("word-input").focus();
    loadWords();
  } catch (err) {
    $("word-error").textContent = err.message;
    $("word-error").hidden = false;
  }
});

// ---------- 퀴즈 ----------

async function loadQuiz() {
  const query = state.currentWordId ? `?exclude_id=${state.currentWordId}` : "";
  try {
    const quiz = await api("GET", `/api/quiz${query}`);
    state.currentWordId = quiz.id;
    $("quiz-word").textContent = quiz.word;
    $("quiz-empty").hidden = true;
    $("quiz-box").hidden = false;
    $("answer-form").reset();
    $("answer-input").disabled = false;
    $("quiz-result").hidden = true;
    $("next-btn").hidden = true;
    $("answer-input").focus();
  } catch (err) {
    if (err.status !== 404) throw err;
    $("quiz-empty").hidden = false;
    $("quiz-box").hidden = true;
  }
}

$("answer-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if ($("answer-input").disabled) return;

  const result = await api("POST", `/api/quiz/${state.currentWordId}/answer`, {
    answer: $("answer-input").value,
  });

  state.total += 1;
  if (result.correct) {
    state.correct += 1;
    state.streak += 1;
  } else {
    state.streak = 0;
  }
  $("score-correct").textContent = state.correct;
  $("score-total").textContent = state.total;
  $("score-streak").textContent = state.streak;

  const box = $("quiz-result");
  box.textContent = result.correct ? `⭕ 정답! (${result.meaning})` : `❌ 오답. 정답은 "${result.meaning}"`;
  box.className = `result ${result.correct ? "correct" : "wrong"}`;
  box.hidden = false;
  $("answer-input").disabled = true;
  $("next-btn").hidden = false;
  $("next-btn").focus(); // Enter를 한 번 더 누르면 다음 문제로
});

$("next-btn").addEventListener("click", loadQuiz);

// ---------- 처음 열었을 때 ----------

loadQuiz();
api("GET", "/api/words").then((words) => ($("word-count").textContent = words.length));
