import json
import re
import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai

# 🔹 Load biến môi trường
load_dotenv()

# 🔹 Cấu hình Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY", "AIzaSyCs1UDQyjMEQ2mL86hTw8GAAQLZuQW4Wdw"))

# 🔹 Khởi tạo FastAPI
app = FastAPI(title="IELTS Essay Evaluation API")

# 🔹 Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Model dữ liệu request
class EssayRequest(BaseModel):
    assignment: str
    essay: str

# 🔹 Hàm làm sạch HTML
def sanitize_text(text: str) -> str:
    text = re.sub(r"<[^>]*>", "", text)
    return text.strip()

# 🔹 Hàm gọi Gemini để phân tích và chấm điểm bài viết theo IELTS
def evaluate_with_ai(assignment: str, essay: str):
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""
    You are an IELTS Writing examiner. Please evaluate the candidate's essay strictly following the official IELTS Writing Band Descriptors.

    The evaluation must be based on the following four criteria:
    1️⃣ Task Achievement (TA): Does the essay fully address all parts of the task and develop ideas logically and relevantly to the question?
    2️⃣ Coherence and Cohesion (CC): Is the essay well organized with clear paragraphing, logical flow, and appropriate cohesive devices?
    3️⃣ Lexical Resource (LR): Is there a wide range of vocabulary used accurately, naturally, and appropriately?
    4️⃣ Grammatical Range and Accuracy (GRA): Does the essay use a range of sentence structures accurately and effectively with minimal errors?

    You must:
    - Give a separate band score (0–9, may include .5) for each of the 4 criteria above.
    - Provide an "overall_score" that is the average of the 4 criteria.
    - Include a short "task_relevance" field commenting on how well the essay answers the given assignment.

    Return the result strictly as valid JSON only:
    {{
      "task_achievement": number,
      "coherence_and_cohesion": number,
      "lexical_resource": number,
      "grammatical_range_and_accuracy": number,
      "overall_score": number,
      "task_relevance": string,
      "feedback": string
    }}

    IELTS Band Descriptors summary:
    - Band 9: Expert user, fully addresses all task parts, fluent and precise.
    - Band 8: Very good user, rare inaccuracies, well-developed arguments.
    - Band 7: Good user, occasional inaccuracy, clear progression of ideas.
    - Band 6: Competent user, some errors but generally effective.
    - Band 5: Modest user, limited flexibility, frequent errors.
    - Band 4–1: Basic or minimal ability in written English.

    IELTS Writing Task Assignment:
    \"\"\"{assignment}\"\"\"

    Candidate's Essay:
    \"\"\"{essay}\"\"\"
    """

    try:
        response = model.generate_content(prompt)
        reply_text = response.text.strip()

        try:
            result = json.loads(reply_text)
        except json.JSONDecodeError:
            start = reply_text.find("{")
            end = reply_text.rfind("}")
            if start != -1 and end != -1:
                json_text = reply_text[start:end + 1]
                result = json.loads(json_text)
            else:
                raise ValueError("Model did not return valid JSON.")

        required_keys = [
            "task_achievement",
            "coherence_and_cohesion",
            "lexical_resource",
            "grammatical_range_and_accuracy",
            "overall_score",
            "task_relevance",
            "feedback"
        ]
        for key in required_keys:
            result.setdefault(key, "Missing")

        return result

    except Exception as e:
        return {
            "task_achievement": 0,
            "coherence_and_cohesion": 0,
            "lexical_resource": 0,
            "grammatical_range_and_accuracy": 0,
            "overall_score": 0,
            "task_relevance": f"❌ Error during evaluation: {str(e)}",
            "feedback": "Evaluation failed."
        }

# 🔹 API endpoint chính
@app.post("/api/evaluate")
async def evaluate_essay(data: EssayRequest):
    try:
        assignment = sanitize_text(data.assignment)
        essay = sanitize_text(data.essay)
        result = evaluate_with_ai(assignment, essay)
        return result
    except Exception as e:
        return {
            "task_achievement": 0,
            "coherence_and_cohesion": 0,
            "lexical_resource": 0,
            "grammatical_range_and_accuracy": 0,
            "overall_score": 0,
            "task_relevance": f"❌ Internal Server Error: {str(e)}",
            "feedback": "Evaluation failed."
        }

# 🔹 Cho phép chạy local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
