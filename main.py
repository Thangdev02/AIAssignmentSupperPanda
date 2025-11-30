# ============================
# SUPER PANDA HSK – V6 ULTRA FAST & NO 503 (Với Key Dự Phòng)
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
    "AIzaSyBpgXEWQbMdQU1c-65Qkl0wYBT_oMsSqno",             # key dự phòng
    "AIzaSyBQtTCihN0VVQS2jfYNoKRl4yKaMmBKCiI",  # key chính

]

MODEL_NAME = "gemini-2.0-flash"

app = FastAPI(title="SuperPanda HSK Evaluation – V6 Ultra Fast")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def clean(text):
    return re.sub(r"<[^>]*>", "", str(text)).strip()

def safe_int(value, default=10, max_val=20):
    try:
        if isinstance(value, (int, float)):
            num = int(value)
        else:
            nums = re.findall(r"\d+", str(value))
            num = int(nums[0]) if nums else default
        return max(0, min(max_val, num))
    except:
        return default

# === PROMPT CHÍNH ===
def build_prompt(assignment, essay):
    return f"""
Bạn là Super Panda – giám khảo HSK chuyên nghiệp.

Đề: {assignment}
Bài: {essay}

Hãy phân tích bài với các tiêu chí HSK:
- nội dung
- ngữ pháp
- từ vựng
- mạch lạc
- bố cục
- mức bám sát đề

⚠️ Chỉ trả về đúng 1 JSON duy nhất, KHÔNG có ký tự ngoài JSON.

Mẫu JSON:
{{
  "content": 0-20,
  "grammar": 0-20,
  "vocabulary": 0-20,
  "coherence": 0-20,
  "format": 0-20,
  "total_score": 0-100,
  "topic_matching": "Rất sát đề" hoặc "Khá sát đề" hoặc "Lạc đề một phần" hoặc "Lạc đề nghiêm trọng",
  "feedback": "Chào bạn! Mình là Super Panda đây\\n\\nSo với đề bài \\\"{assignment}\\\" thì bài của bạn đã [phân tích cụ thể, không chung chung]...\\n\\nĐiểm mạnh:\\n- [ít nhất 2 điểm]\\n\\nĐiểm cần cải thiện:\\n- [ít nhất 2 lỗi]\\n\\nSửa lỗi cụ thể:\\n- \\\"[câu sai]\\\" → \\\"[câu đúng]\\\"\\n\\nBạn nên tham khảo Bài [số] ([chủ đề]) trong sách HSK1 hoặc HSK2 nhé!\\n\\nSách tham khảo:\\nHSK Standard Course 1 → https://drive.google.com/drive/folders/1cpSBYKqY6mOpkSK80ZTH3DB6ZGji_JYS\\nHSK Standard Course2 → https://drive.google.com/drive/folders/1t28iaDdLscWoEinbEMTGitmTzWZ8PHsV\\n\\nCố lên nào, Panda tin bạn làm được mà!"
}}
"""

# === HÀM GENERATE VỚI KEY DỰ PHÒNG ===
def generate_with_retry(prompt):
    for key in API_KEYS:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(MODEL_NAME)
        try:
            resp = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=1400
                )
            )
            return resp.text
        except Exception as e:
            print(f"Key {key} fail: {str(e)} – thử key tiếp theo...")
            continue
    raise HTTPException(
        status_code=503,
        detail="Panda mệt xíu, tất cả key đều hết hạn hoặc lỗi, gửi lại giúp Panda nha!"
    )

@app.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_essay(data: EssayRequest):
    assignment = clean(data.assignment)
    essay = clean(data.essay)

    prompt = build_prompt(assignment, essay)

    for _ in range(7):  # 7 lần retry cực khó fail
        try:
            raw = generate_with_retry(prompt)
            raw = raw.replace("\n", "").replace("\r", "").strip()
            raw = re.sub(r".*?(\{.*\}).*", r"\1", raw)

            try:
                result = json.loads(raw)
            except:
                result = demjson3.decode(raw)

            feedback = str(result.get("feedback", "")).replace("\\n", "\n").strip()

            # BẮT BUỘC: feedback phải đủ tâm + có chữ Panda
            if len(feedback) < 60 or "Panda" not in feedback:
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
        detail="Panda mệt xíu, gửi lại giùm Panda với nha!"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
