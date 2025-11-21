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

# Response – để Swagger hiển thị đúng cấu trúc
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
Hãy chấm bài viết theo thang điểm 100, chia thành 5 tiêu chí sau. Mỗi tiêu chí chấm nội bộ 1–5 điểm (theo bảng chi tiết dưới đây), sau đó nhân 4 để ra 0–20 điểm. Tổng điểm = tổng 5 tiêu chí.
Nếu bài viết lạc đề một phần: trừ 10–40 điểm (tùy mức độ) từ tổng điểm.
Nếu bài lạc đề nghiêm trọng: tổng điểm tối đa chỉ được 10/100, bất kể các tiêu chí khác.

=== TIÊU CHÍ CHI TIẾT (theo chuẩn chấm HSK thực tế) ===

1. Nội dung
   • 5 điểm (Xuất sắc): Hoàn toàn bám sát chủ đề, đầy đủ mọi ý chính và ý phụ, nội dung phong phú, có chi tiết cụ thể, đúng hoàn toàn yêu cầu đề. Không lạc đề, không thiếu thông tin quan trọng.
   • 4 điểm (Tốt): Bám sát đề, có hầu hết ý cần thiết, chỉ thiếu vài chi tiết nhỏ không quan trọng, vẫn truyền tải đầy đủ thông điệp.
   • 3 điểm (Trung bình): Đúng hướng chung nhưng sơ sài, bỏ sót một số ý quan trọng hoặc chưa giải thích rõ, người đọc vẫn hiểu nhưng thấy thiếu.
   • 2 điểm (Yếu): Thiếu nhiều ý quan trọng, có phần lệch đề, thông tin mơ hồ, nghèo nàn ý tưởng.
   • 1 điểm (Kém): Lạc đề hoàn toàn hoặc nội dung cực kỳ ít ỏi (vài câu chung chung không liên quan).

2. Ngữ pháp
   • 5 điểm (Xuất sắc): Không lỗi ngữ pháp nào. Sử dụng chính xác, đa dạng các cấu trúc phức hợp phù hợp cấp độ, câu văn tự nhiên.
   • 4 điểm (Tốt): Chỉ 1-2 lỗi rất nhỏ (thiếu giới từ, trật tự nhẹ), không ảnh hưởng nghĩa.
   • 3 điểm (Trung bình): Có một số lỗi (quên “了”, nhầm vị trí “也/都”, sai thì…), vẫn hiểu được ý chính nhưng chất lượng giảm.
   • 2 điểm (Yếu): Nhiều lỗi nghiêm trọng, ảnh hưởng hiểu bài, phải đoán nghĩa.
   • 1 điểm (Kém): Sai ngữ pháp nặng nề khắp bài, hầu như không hiểu được.

3. Từ vựng
   • 5 điểm (Xuất sắc): Phong phú, chính xác tuyệt đối, dùng đủ và đúng vị trí các từ yêu cầu (nếu có từ gợi ý), không có 错别字.
   • 4 điểm (Tốt): Đa dạng, có thể 1-2 lỗi chữ hoặc chọn từ chưa chuẩn nhất nhưng không gây hiểu lầm.
   • 3 điểm (Trung bình): Vốn từ cơ bản đủ dùng, hơi đơn điệu, có vài lỗi từ vựng/chính tả nhẹ (1-3 chữ sai).
   • 2 điểm (Yếu): Từ vựng hạn chế, lặp nhiều, sai nghĩa nhiều từ hoặc sai ≥4 chữ Hán.
   • 1 điểm (Kém): Gần như không đủ từ để diễn đạt, nhiều chữ sai nghiêm trọng hoặc chèn tiếng nước ngoài.

4. Mạch lạc
   • 5 điểm (Xuất sắc): Rất mạch lạc, logic chặt chẽ, bố cục hợp lý (mở-thân-kết), dùng từ nối tự nhiên, trôi chảy như bài mẫu.
   • 4 điểm (Tốt): Nhìn chung mạch lạc, chỉ vài chỗ chuyển ý hơi đột ngột hoặc thiếu từ nối nhẹ.
   • 3 điểm (Trung bình): Có bố cục cơ bản nhưng liên kết yếu, ý sắp xếp chưa hợp lý, đọc vẫn theo dõi được nhưng không mượt.
   • 2 điểm (Yếu): Rời rạc, logic lỏng lẻo, chuyển ý đột ngột, thiếu từ nối nghiêm trọng.
   • 1 điểm (Kém): Hỗn loạn hoàn toàn, ý nhảy lung tung, không có cấu trúc.

5. Trình bày & Hình thức
   • 5 điểm (Xuất sắc): Đúng 100% độ dài yêu cầu, bố cục rõ ràng (có đoạn, có tiêu đề nếu cần), chữ sạch đẹp, không lỗi chính tả, dấu câu chuẩn.
   • 4 điểm (Tốt): Độ dài chênh ≤10%, có thể 1-2 lỗi chữ/dấu câu nhỏ, bố cục tốt.
   • 3 điểm (Trung bình): Độ dài ngắn >10% nhưng ≥50%, hoặc có 2-4 lỗi chữ/dấu câu, chưa tách đoạn rõ.
   • 2 điểm (Yếu): Quá ngắn (<50% độ dài) hoặc quá dài, sai nhiều chữ (≥5), dấu câu lộn xộn.
   • 1 điểm (Kém): Gần như bỏ giấy trắng, chỉ vài chữ hoặc viết không đọc được.

=== QUY TẮC XỬ LÝ LẠC ĐỀ ===
• Nếu bài viết lạc đề một phần:
    - Chấm từng tiêu chí bình thường.
    - Sau cùng trừ 10–40 điểm từ tổng điểm.

• Nếu bài viết lạc đề nghiêm trọng:
    - Các tiêu chí content, coherence = 0.
    - grammar, vocabulary, format vẫn chấm nhưng bị giới hạn để tổng_score ≤ 10.
    - total_score không được vượt 10 trong mọi trường hợp.

=== YÊU CẦU TRẢ VỀ JSON CHÍNH XÁC ===
{{
  "content": số (0-20),
  "grammar": số (0-20),
  "vocabulary": số (0-20),
  "coherence": số (0-20),
  "format": số (0-20),
  "total_score": số (0-100),
  "topic_matching": "Rất sát đề" | "Khá sát đề" | "Lạc đề một phần" | "Lạc đề nghiêm trọng",
  "feedback": "Nhận xét chi tiết bằng tiếng Việt, 150-350 chữ, nêu rõ điểm mạnh và điểm cần cải thiện từng tiêu chí"
}}

ĐỀ BÀI:
\"\"\"{assignment}\"\"\"

BÀI LÀM:
\"\"\"{essay}\"\"\"

Trả về đúng JSON trên, không thêm bất kỳ chữ nào ngoài JSON.
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Loại bỏ code block nếu có
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0] if "\n" in text else text
        text = text.strip()

        result = json.loads(text)

        # Đảm bảo đủ key + ép kiểu số
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