import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
import openai
from app.core.config import get_settings
from app.services.db.models import TherapyLetter, MoodCheckin, ClinicalProfile, User
from app.services.utils import make_id, make_anon_name, get_now

settings = get_settings()

AI_SERENE_USER_ID = "ai_serene_agent"

async def generate_ai_reply(letter_content: str, mood_info: str = None, clinical_info: str = None) -> str:
    """Calls LLM to generate a healing response based on user context."""
    client = openai.AsyncClient(api_key=settings.openai_api_key)
    
    system_prompt = (
        "Bạn là Tiến sĩ Serene - một nhà tâm lý học lâm sàng với hơn 15 năm kinh nghiệm trong trị liệu tâm hồn. "
        "Phong cách của bạn là sự kết hợp giữa sự thấu cảm sâu sắc của một người bạn và tri thức chuyên môn của một chuyên gia tâm lý. "
        "Nhiệm vụ của bạn là phản hồi những lá thư tâm sự của người dùng một cách chân thành, chữa lành và mang tính nâng đỡ cao. "
        "Hãy xưng 'mình' hoặc 'tôi' tùy ngữ cảnh (nhưng 'mình' sẽ thân thiện hơn) và gọi người dùng là 'bạn'. "
        "Ngôn ngữ: Tiếng Việt. Phong cách: Điềm tĩnh, thấu cảm, không máy móc, mang tính khích lệ, sử dụng ngôn từ có sức mạnh chữa lành. "
        "Hãy dựa vào thông tin tâm trạng và tình trạng lâm sàng (nếu có) để đưa ra những phân tích và lời khuyên phù hợp với tâm thế của một bác sĩ tâm lý thấu hiểu. "
        "Độ dài: Khoảng 100-150 từ."
    )
    
    user_context = f"Nội dung thư của người dùng gửi: \"{letter_content}\"\n"
    if mood_info:
        user_context += f"Tâm trạng hiện tại của người dùng: {mood_info}\n"
    if clinical_info:
        user_context += f"Chỉ số sức khỏe tinh thần: {clinical_info}\n"
        
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_friend,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context}
            ],
            temperature=0.8,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI Letter Reply Error: {e}")
        return "Mình đã đọc được tâm sự của bạn. Dù thế nào, mình vẫn ở đây lắng nghe và ủng hộ bạn. Chúc bạn một ngày bình yên nhé."

async def generate_multi_reply_suggestions(letter_content: str, mood_info: str = None, clinical_info: str = None) -> list[dict]:
    """Generates 3 different reply styles for Admin to choose."""
    client = openai.AsyncClient(api_key=settings.openai_api_key)
    
    system_prompt = (
        "Bạn là trợ lý ảo Serene - chuyên hỗ trợ Admin phản hồi thư của người dùng. "
        "Dựa trên nội dung thư, hãy sinh ra 3 phương án trả lời khác nhau theo các phong cách: "
        "1. 'Trang trọng' (Formal): Chuyên nghiệp, lịch sự, đúng chuẩn chuyên gia. "
        "2. 'Thân thiện' (Casual): Gần gũi như một người bạn, nhẹ nhàng, thấu cảm. "
        "3. 'Ngắn gọn' (Brief): Đi thẳng vào vấn đề, súc tích nhưng vẫn chân thành. "
        "Kết quả trả về dưới dạng JSON với trường 'suggestions' là một danh sách các object, "
        "mỗi object có: 'style' (tên phong cách), 'content' (nội dung câu trả lời)."
    )
    
    user_context = f"Nội dung thư: \"{letter_content}\"\n"
    if mood_info:
        user_context += f"Tâm trạng: {mood_info}\n"
    if clinical_info:
        user_context += f"Sức khỏe tinh thần: {clinical_info}\n"
        
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_friend,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        import json
        data = json.loads(response.choices[0].message.content.strip())
        return data.get("suggestions", [])
    except Exception as e:
        print(f"AI Suggestion Error: {e}")
        return [
            {"style": "Thân thiện", "content": "Cảm ơn bạn đã chia sẻ tâm sự này với mình. Mình luôn ở đây để lắng nghe bạn."},
            {"style": "Trang trọng", "content": "Chúng tôi đã nhận được thông tin từ bạn và rất thấu hiểu tình huống này. Hãy cùng nhau tìm giải pháp nhé."},
            {"style": "Ngắn gọn", "content": "Cố gắng lên bạn nhé, mọi chuyện rồi sẽ ổn thôi!"}
        ]


async def analyze_reported_letter(letter_content: str, report_reason: str = None) -> dict:
    """Analyze a reported letter to help admin decide the action."""
    client = openai.AsyncClient(api_key=settings.openai_api_key)
    
    system_prompt = (
        "Bạn là chuyên gia kiểm duyệt nội dung của hệ thống Serene. "
        "Nhiệm vụ của bạn là phân tích một lá thư bị báo cáo và đưa ra đánh giá khách quan. "
        "Hãy xác định xem lá thư có thực sự vi phạm (nội dung độc hại, quấy rối, tự hại, v.v.) hay đây là một báo cáo sai sự thật. "
        "Kết quả trả về dưới dạng JSON với các trường: "
        "'category' (loại vi phạm hoặc 'safe'), "
        "'severity' (thấp/trung bình/cao), "
        "'reason' (giải thích ngắn gọn), "
        "'action' (đề xuất: 'keep' hoặc 'delete')."
    )
    
    user_context = f"Nội dung thư bị báo cáo: \"{letter_content}\"\n"
    if report_reason:
        user_context += f"Lý do người dùng báo cáo: {report_reason}\n"
        
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_friend,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        import json
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"AI Content Moderation Error: {e}")
        return {
            "category": "unknown",
            "severity": "unknown",
            "reason": f"Lỗi phân tích AI: {str(e)}",
            "action": "keep"
        }

async def run_ai_reply_worker(db: Session, hours_threshold: int = 6):
    """
    Finds letters older than threshold with no replies, 
    generates AI response, and handles the original letter.
    """
    import time
    start_time = time.time()
    
    # Ensure AI user exists (simplified check/create)
    ai_user = db.get(User, AI_SERENE_USER_ID)
    if not ai_user:
        ai_user = User(
            user_id=AI_SERENE_USER_ID,
            email="healer.friend@serene.app",
            display_name="Người bạn chữa lành",
            is_active=True
        )
        db.add(ai_user)
        db.flush()

    threshold_time = get_now().replace(tzinfo=None) - timedelta(hours=hours_threshold)
    
    # Find active public letters older than threshold
    stmt = (
        select(TherapyLetter)
        .where(
            TherapyLetter.letter_type == "public",
            TherapyLetter.status == "active",
            TherapyLetter.created_at <= threshold_time
        )
    )
    
    letters = db.scalars(stmt).all()
    processed_count = 0
    replied_details = []
    
    for letter in letters:
        # Check if already replied by someone else
        exists_reply = db.scalar(
            select(func.count(TherapyLetter.letter_id))
            .where(TherapyLetter.reply_to_id == letter.letter_id)
        )
        if exists_reply:
            continue
            
        # Get context
        sender_id = letter.user_id
        latest_mood = db.scalar(
            select(MoodCheckin)
            .where(MoodCheckin.user_id == sender_id)
            .order_by(MoodCheckin.logged_at.desc())
            .limit(1)
        )
        clinical = db.scalar(
            select(ClinicalProfile).where(ClinicalProfile.user_id == sender_id)
        )
        
        mood_str = f"{latest_mood.mood} ({latest_mood.emoji})" if latest_mood else "Chưa ghi nhận"
        clin_str = f"PHQ-9: {clinical.phq9_score}, GAD-7: {clinical.gad7_score}" if clinical else "N/A"
        
        # Generate and save
        reply_content = await generate_ai_reply(letter.content, mood_str, clin_str)
        
        reply = TherapyLetter(
            letter_id=make_id("lrep_ai"),
            user_id=AI_SERENE_USER_ID,
            receiver_id=letter.user_id, # Set receiver so user sees it in inbox
            reply_to_id=letter.letter_id,
            anonymous_name=make_anon_name(),
            content=reply_content,
            letter_type="reply",
            status="active",
            created_at=get_now().replace(tzinfo=None)
        )
        
        # Remove from recipient's inbox
        letter.receiver_id = None
        
        db.add(reply)
        db.add(letter)
        
        # Send notification to the user
        try:
            from app.services.notification_service import send_instant_notification
            send_instant_notification(
                db, 
                user_id=letter.user_id, 
                event_type="letter.replied", 
                payload={
                    "letter_id": letter.letter_id,
                    "reply_id": reply.letter_id,
                    "message": f"Ai đó vừa phản hồi lá thư tâm sự của bạn."
                }
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")

        replied_details.append({
            "letter_id": letter.letter_id,
            "user_id": letter.user_id,
            "content_brief": letter.content[:100] + "..." if len(letter.content) > 100 else letter.content,
            "reply_brief": reply_content[:100] + "..." if len(reply_content) > 100 else reply_content
        })
        processed_count += 1
        
    db.commit()
    duration = time.time() - start_time
    return {
        "count": processed_count,
        "details": replied_details,
        "duration_sec": round(duration, 2)
    }
