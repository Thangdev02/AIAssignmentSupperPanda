# main.py
import json
import re
import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Lấy key từ .env (khuyến khích), nếu không có thì mới dùng key mặc định (dev only)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY", "AIzaSyBRXcQXNaA-qoEjaBuBhqOf2-V3NtwIESA"))
app = FastAPI(title="HSK Essay Evaluation API – Chuẩn giám khảo SuperPanda")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request
class EssayRequest(BaseModel):
    assignment: str
    essay: str

# Response – Swagger
class EvaluationResponse(BaseModel):
    content: int
    grammar: int
    vocabulary: int
    coherence: int
    format: int
    total_score: int
    topic_matching: str
    feedback: str

def sanitize_text(text: str) -> str:
    return re.sub(r"<[^>]*>", "", text).strip()

def contains_non_chinese(text: str) -> bool:
    pattern = re.compile(r"[^\u4e00-\u9fff\u3000-\u303F，。！？；：“”‘’…\s\n\r]")
    return bool(pattern.search(text))

def evaluate_with_ai(assignment: str, essay: str):
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""
Bạn là giám khảo chấm thi HSK chính thức (HSK3–HSK6) của SuperPanda.
Hãy chấm bài viết theo thang điểm 100, chia thành 5 tiêu chí sau. Mỗi tiêu chí chấm 1–5 điểm, nhân 4 thành 0–20 điểm. Tổng điểm = tổng 5 tiêu chí.

=== QUY TẮC LẠC ĐỀ (BẮT BUỘC) ===
• Nếu bài viết **lạc đề một phần**:
    - Chấm từng tiêu chí bình thường.
    - Sau cùng trừ 10–40 điểm từ tổng.

• Nếu bài viết **lạc đề nghiêm trọng** (nội dung không liên quan tới đề, sai hoàn toàn chủ đề, hoặc viết về việc khác):
    - Tất cả 5 tiêu chí: content = 0, grammar = 0, vocabulary = 0, coherence = 0, format = 0
    - total_score = 0
    - Đây là luật bắt buộc, không được chấm bất kỳ điểm nào khác.

=== TIÊU CHÍ CHI TIẾT ===
1. Nội dung: 1–5 điểm
2. Ngữ pháp: 1–5 điểm
3. Từ vựng: 1–5 điểm
4. Mạch lạc: 1–5 điểm
5. Trình bày: 1–5 điểm

=== TRẢ VỀ JSON CHÍNH XÁC ===
{{
  "content": số (0-20),
  "grammar": số (0-20),
  "vocabulary": số (0-20),
  "coherence": số (0-20),
  "format": số (0-20),
  "total_score": số (0-100),
  "topic_matching": "Rất sát đề" | "Khá sát đề" | "Lạc đề một phần" | "Lạc đề nghiêm trọng",
  "feedback": "Nhận xét chi tiết bằng tiếng Việt, 150-350 chữ"
}}

ĐỀ BÀI:
\"\"\"{assignment}\"\"\"

BÀI LÀM:
\"\"\"{essay}\"\"\"

Chỉ trả về JSON, không giải thích thêm.
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Xử lý format
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0]

        result = json.loads(text)

        # ép kiểu
        keys = ["content","grammar","vocabulary","coherence","format","total_score"]
        for k in keys:
            result[k] = int(result.get(k, 0))

        result.setdefault("topic_matching", "Không xác định")
        result.setdefault("feedback", "Không có nhận xét")

        return result

    except Exception as e:
        return {
            "content": 0, "grammar": 0, "vocabulary": 0,
            "coherence": 0, "format": 0, "total_score": 0,
            "topic_matching": "Lỗi hệ thống",
            "feedback": f"Lỗi khi chấm bài: {str(e)[:200]}"
        }

@app.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_essay(data: EssayRequest):
    assignment = sanitize_text(data.assignment)
    essay = sanitize_text(data.essay)

    if contains_non_chinese(essay):
        return EvaluationResponse(
            content=0, grammar=0, vocabulary=0, coherence=0, format=0,
            total_score=0,
            topic_matching="Không phải tiếng Trung",
            feedback="Bài viết chứa ký tự Latin hoặc ngôn ngữ khác → chỉ chấp nhận tiếng Trung thuần túy → 0 điểm."
        )

    return evaluate_with_ai(assignment, essay)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
