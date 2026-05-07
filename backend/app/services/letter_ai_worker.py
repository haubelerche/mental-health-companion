import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
import openai
from app.core.config import get_settings
from app.services.db.models import TherapyLetter, MoodCheckin, ClinicalProfile, User
from app.services.utils import make_id

settings = get_settings()

AI_SERENE_USER_ID = "ai_serene_agent"

async def generate_ai_reply(letter_content: str, mood_info: str = None, clinical_info: str = None) -> str:
    """Calls LLM to generate a healing response based on user context."""
    client = openai.AsyncClient(api_key=settings.openai_api_key)
    
    system_prompt = (
        "Bạn là Serene - một người bạn tâm giao ẩn danh. Bạn có khả năng thấu hiểu và xoa dịu tâm hồn. "
        "Nhiệm vụ của bạn là phản hồi những lá thư tâm sự của người dùng một cách chân thành, "
        "chữa lành và gần gũi. Hãy xưng 'mình' và gọi người dùng là 'bạn'. "
        "Ngôn ngữ: Tiếng Việt. Phong cách: Nhẹ nhàng, thấu cảm, không máy móc, mang tính khích lệ, đời thường. "
        "Hãy dựa vào thông tin tâm trạng và tình trạng lâm sàng (nếu có) để đưa ra lời khuyên phù hợp. "
        "Độ dài: Khoảng 80-120 từ."
    )
    
    user_context = f"Nội dung thư của người dùng gửi: \"{letter_content}\"\n"
    if mood_info:
        user_context += f"Tâm trạng hiện tại của người dùng: {mood_info}\n"
    if clinical_info:
        user_context += f"Chỉ số sức khỏe tinh thần: {clinical_info}\n"
        
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_chat,
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

async def run_ai_reply_worker(db: Session, hours_threshold: int = 6):
    """
    Finds letters older than threshold with no replies, 
    generates AI response, and handles the original letter.
    """
    # Ensure AI user exists (simplified check/create)
    ai_user = db.get(User, AI_SERENE_USER_ID)
    if not ai_user:
        ai_user = User(
            user_id=AI_SERENE_USER_ID,
            email="ai@serene.app",
            display_name="Serene AI",
            is_active=True
        )
        db.add(ai_user)
        db.commit()

    threshold_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours_threshold)
    
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
            reply_to_id=letter.letter_id,
            anonymous_name="Serene AI 🌿",
            content=reply_content,
            letter_type="reply",
            status="active",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        
        # Remove from recipient's inbox
        letter.receiver_id = None
        
        db.add(reply)
        db.add(letter)
        processed_count += 1
        
    db.commit()
    return processed_count
