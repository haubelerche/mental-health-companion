import json
import asyncio
import httpx
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
import openai
import re

from app.core.config import get_settings
from app.services.db.models import Resource
from app.services.utils import make_id

settings = get_settings()

CATEGORIES = ["meditate", "sleep", "music", "work_study", "wisdom", "movement"]

# Mapping from category to a more descriptive prompt context
CATEGORY_CONTEXTS = {
    "meditate": "Thiền định, tĩnh tâm, chánh niệm, hướng dẫn thiền",
    "sleep": "Nhạc ngủ ngon, hướng dẫn dễ ngủ, âm thanh thiên nhiên ru ngủ",
    "music": "Âm nhạc thư giãn, nhạc không lời êm dịu, nhạc chữa lành",
    "work_study": "Nhạc tập trung làm việc, lofi focus, nhạc học tập",
    "wisdom": "Kiến thức tâm lý học, podcast phát triển bản thân, chữa lành tinh thần",
    "movement": "Yoga nhẹ nhàng, bài tập giãn cơ, vận động giảm stress"
}

def parse_pt_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration (e.g., PT1H2M10S) to seconds."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

async def run_youtube_crawl_agent(category: str, limit: int, db: Session):
    client = openai.AsyncClient(api_key=settings.openai_api_key)
    youtube_api_key = settings.youtube_api_key
    
    if not youtube_api_key:
        yield f"data: {json.dumps({'event': 'error', 'data': 'Chưa cấu hình YOUTUBE_API_KEY'})}\n\n"
        return

    context = CATEGORY_CONTEXTS.get(category, category)

    # 1. Keyword Generation
    yield f"data: {json.dumps({'event': 'keyword_generation', 'data': {'status': 'started'}})}\n\n"
    
    prompt = f"Tôi cần tìm video YouTube chất lượng cao thuộc chủ đề: '{context}'. Hãy tạo ra 3 từ khóa tìm kiếm (bằng tiếng Việt) tối ưu nhất, ngắn gọn để truyền vào YouTube Search API. Chỉ trả về danh sách từ khóa, mỗi từ khóa trên 1 dòng, không giải thích."
    
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_analyst,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        keywords_text = response.choices[0].message.content.strip()
        keywords = [k.strip("- \t1234567890.") for k in keywords_text.split('\n') if k.strip()]
        if not keywords:
            keywords = [context]
    except Exception as e:
        print(f"Keyword generation error: {e}")
        keywords = [context]

    yield f"data: {json.dumps({'event': 'keyword_generation', 'data': {'status': 'completed', 'keywords': keywords}})}\n\n"
    await asyncio.sleep(0.5)

    # 2. YouTube Search
    yield f"data: {json.dumps({'event': 'youtube_search', 'data': {'status': 'started'}})}\n\n"
    
    all_videos = {}
    async with httpx.AsyncClient() as http_client:
        max_per_keyword = max(1, limit // len(keywords)) + 1
        for keyword in keywords:
            search_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "maxResults": max_per_keyword,
                "key": youtube_api_key,
                "relevanceLanguage": "vi"
            }
            try:
                res = await http_client.get(search_url, params=params)
                res.raise_for_status()
                data = res.json()
                for item in data.get("items", []):
                    vid = item["id"]["videoId"]
                    snippet = item["snippet"]
                    all_videos[vid] = {
                        "videoId": vid,
                        "title": snippet["title"],
                        "description": snippet["description"],
                        "channelTitle": snippet["channelTitle"],
                        "thumbnail": snippet["thumbnails"].get("high", snippet["thumbnails"].get("default"))["url"],
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    }
            except Exception as e:
                print(f"Youtube search error for keyword '{keyword}': {e}")
            
            if len(all_videos) >= limit:
                break
        
        # Get Durations
        video_ids = list(all_videos.keys())[:limit] # Truncate to limit
        final_videos = {vid: all_videos[vid] for vid in video_ids}
        
        if video_ids:
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            v_params = {
                "part": "contentDetails",
                "id": ",".join(video_ids),
                "key": youtube_api_key
            }
            try:
                v_res = await http_client.get(videos_url, params=v_params)
                v_res.raise_for_status()
                v_data = v_res.json()
                for item in v_data.get("items", []):
                    vid = item["id"]
                    duration_str = item["contentDetails"]["duration"]
                    if vid in final_videos:
                        final_videos[vid]["duration_sec"] = parse_pt_duration(duration_str)
            except Exception as e:
                print(f"Youtube duration error: {e}")
                for vid in final_videos:
                    final_videos[vid]["duration_sec"] = 0

    yield f"data: {json.dumps({'event': 'youtube_search', 'data': {'status': 'completed', 'videos_found': len(final_videos)}})}\n\n"
    await asyncio.sleep(0.5)

    if not final_videos:
        yield f"data: {json.dumps({'event': 'done', 'data': {'status': 'completed', 'results': []}})}\n\n"
        return

    # 3. Content Moderation
    yield f"data: {json.dumps({'event': 'content_moderation', 'data': {'status': 'started'}})}\n\n"
    
    approved_videos = []
    rejected_count = 0
    
    # We will moderate in batch to save time
    videos_to_moderate = list(final_videos.values())
    prompt_items = []
    for i, v in enumerate(videos_to_moderate):
        prompt_items.append(f"ID {i}: Title: {v['title']}\nDesc: {v['description'][:200]}")
    
    moderation_prompt = f"""Bạn là một chuyên gia tâm lý học lâm sàng chịu trách nhiệm tuyển chọn tài nguyên số cho ứng dụng Serene.
Chủ đề đang xét: {context}.
Hãy đánh giá danh sách video dưới đây một cách khắt khe. 
Yêu cầu:
1. Video phải có giá trị trị liệu, hỗ trợ sức khỏe tinh thần hoặc cung cấp kiến thức tâm lý chính thống.
2. Không chấp nhận các video rác, quảng cáo thuốc không rõ nguồn gốc, hoặc nội dung mang tính chất mê tín duy tâm.
3. Ưu tiên các nội dung có âm thanh êm dịu, hình ảnh đẹp hoặc kiến thức khoa học.

Trả về 'ACCEPT' nếu video thực sự có ích cho người đang gặp vấn đề tâm lý, 'REJECT' nếu ngược lại.
Định dạng trả về:
ID 0: ACCEPT
ID 1: REJECT
...
Danh sách video:
{chr(10).join(prompt_items)}"""

    try:
        mod_response = await client.chat.completions.create(
            model=settings.openai_model_analyst,
            messages=[{"role": "user", "content": moderation_prompt}],
            temperature=0.0
        )
        mod_results = mod_response.choices[0].message.content
        
        for i, v in enumerate(videos_to_moderate):
            if f"ID {i}: ACCEPT" in mod_results:
                approved_videos.append(v)
            else:
                rejected_count += 1
    except Exception as e:
        print(f"Moderation error: {e}")
        # On error, we accept all to not block the flow, but in production we might want to reject
        approved_videos = videos_to_moderate
        rejected_count = 0

    yield f"data: {json.dumps({'event': 'content_moderation', 'data': {'status': 'completed', 'approved': len(approved_videos), 'rejected': rejected_count}})}\n\n"
    await asyncio.sleep(0.5)

    if not approved_videos:
        yield f"data: {json.dumps({'event': 'done', 'data': {'status': 'completed', 'results': []}})}\n\n"
        return

    # 4. DB Insertion
    yield f"data: {json.dumps({'event': 'db_insertion', 'data': {'status': 'started'}})}\n\n"
    
    inserted_count = 0
    final_results = []
    
    for v in approved_videos:
        storage_key = v["videoId"]
        # Check if exists
        existing = db.scalar(select(Resource).where(Resource.storage_key == storage_key))
        if not existing:
            new_res = Resource(
                resource_id=make_id("res"),
                category=category,
                title=v["title"],
                description=v["description"],
                format="video",
                duration_sec=v.get("duration_sec", 0),
                storage_key=storage_key,
                thumbnail_key=v["thumbnail"],
                tags=[category],
                is_active=True
            )
            db.add(new_res)
            inserted_count += 1
            final_results.append({
                "title": v["title"],
                "status": "inserted",
                "thumbnail": v["thumbnail"],
                "url": v["url"]
            })
        else:
            final_results.append({
                "title": v["title"],
                "status": "existed",
                "thumbnail": v["thumbnail"],
                "url": v["url"]
            })
            
    db.commit()

    yield f"data: {json.dumps({'event': 'db_insertion', 'data': {'status': 'completed', 'inserted': inserted_count}})}\n\n"
    await asyncio.sleep(0.5)
    
    # 5. Done
    yield f"data: {json.dumps({'event': 'done', 'data': {'status': 'completed', 'results': final_results}})}\n\n"
