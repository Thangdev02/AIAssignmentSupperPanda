# ============================
# SUPER PANDA HSK – V8 USER INPUT + AUTO ANALYSIS
# ============================

import re
import json
import demjson3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# === DANH SÁCH KEY ===
API_KEYS = [

]

MODEL_NAME = "gemini-2.0-flash"

app = FastAPI(title="SuperPanda HSK Evaluation – V8")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# MODELS
# =============================
class EssayRequest(BaseModel):
    assignment: str
    essay: str

class EvaluationResponse(BaseModel):
    content: int
    grammar: int
    vocabulary: int
    coherence: int
    format: int
    total_score: int
    topic_matching: str
    feedback: str

# =============================
# HELPERS
# =============================
def clean(text: str) -> str:
    return re.sub(r"<[^>]*>", "", str(text)).strip()

def safe_int(value, default=10, max_val=20) -> int:
    try:
        if isinstance(value, (int, float)):
            num = int(value)
        else:
            nums = re.findall(r"\d+", str(value))
            num = int(nums[0]) if nums else default
        return max(0, min(max_val, num))
    except:
        return default

def build_prompt(assignment: str, essay: str) -> str:
    return f"""
Bạn là Super Panda – giám khảo HSK chuyên nghiệp.
Phân tích đề bài và bài làm thực tế của học sinh.

Đề bài: {assignment}
Bài làm: {essay}

Hãy chấm điểm theo các tiêu chí HSK:
- content
- grammar
- vocabulary
- coherence
- format
- topic matching

⚠️ Chỉ trả về DUY NHẤT JSON, KHÔNG MARKDOWN, KHÔNG KÝ TỰ THÊM.

Mẫu JSON:
{{
  "content": 0-20,
  "grammar": 0-20,
  "vocabulary": 0-20,
  "coherence": 0-20,
  "format": 0-20,
  "total_score": 0-100,
  "topic_matching": "Rất sát đề" | "Khá sát đề" | "Lạc đề một phần" | "Lạc đề nghiêm trọng",
  "feedback": "Chào bạn! Mình là Super Panda đây. Phân tích chi tiết bài làm và đề, đưa ra điểm mạnh, điểm cần cải thiện, có chữ Panda.\n\nBạn nên tham khảo sách HSK:\nHSK1: https://drive.google.com/drive/folders/1cpSBYKqY6mOpkSK80ZTH3DB6ZGji_JYS\nHSK2: https://drive.google.com/drive/folders/1t28iaDdLscWoEinbEMTGitmTzWZ8PHsV"
}}
"""

def generate_with_retry(prompt: str) -> str:
    for key in API_KEYS:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(MODEL_NAME)
        try:
            resp = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=1500
                )
            )
            if hasattr(resp, "text") and resp.text:
                return resp.text
            if hasattr(resp, "candidates"):
                parts = resp.candidates[0].content.parts
                return "".join(getattr(p, "text", "") for p in parts)
        except Exception as e:
            print(f"Key {key} lỗi: {str(e)}, thử key tiếp theo...")
            continue
    raise HTTPException(
        status_code=503,
        detail="Panda mệt xíu, tất cả key lỗi hoặc hết hạn!"
    )

def extract_json(raw: str) -> dict:
    raw = raw.replace("\n", "").replace("\r", "").strip()
    raw = re.sub(r".*?(\{.*\}).*", r"\1", raw)
    try:
        return json.loads(raw)
    except:
        return demjson3.decode(raw)

# =============================
# API
# =============================
@app.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_essay(data: EssayRequest):
    assignment = clean(data.assignment)
    essay = clean(data.essay)
    prompt = build_prompt(assignment, essay)

    for _ in range(5):
        try:
            raw = generate_with_retry(prompt)
            result = extract_json(raw)

            feedback = str(result.get("feedback", "")).replace("\\n", "\n").strip()
            if len(feedback) < 40 or "Panda" not in feedback:
                continue

            return EvaluationResponse(
                content=safe_int(result.get("content")),
                grammar=safe_int(result.get("grammar")),
                vocabulary=safe_int(result.get("vocabulary")),
                coherence=safe_int(result.get("coherence")),
                format=safe_int(result.get("format")),
                total_score=safe_int(result.get("total_score"), max_val=100),
                topic_matching=str(result.get("topic_matching", "Khá sát đề")),
                feedback=feedback
            )
        except:
            continue

    raise HTTPException(
        status_code=503,
        detail="Panda mệt xíu, model lười, thử lại nhé!"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
