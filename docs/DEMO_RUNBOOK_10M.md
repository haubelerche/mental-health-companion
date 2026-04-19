# Demo Runbook 10 Phut

Muc tieu: demo MVP trong 10 phut voi 3 tinh huong:
- Happy path
- Distress path
- SOS + proactive voice path

## 0) Chuan bi truoc demo (2-3 phut)

### 0.1 Khoi dong backend
- Chay backend (`uvicorn app.main:app --reload` trong thu muc backend neu team dang dung local run).
- Kiem tra nhanh:
  - `GET /health` tra `{"status":"ok"}`.

### 0.2 Khoi dong frontend
- Chay `npm run dev` trong `frontend/`.
- Mo app tai URL Vite (thuong la `http://127.0.0.1:5173`).

### 0.3 Bien moi truong can co
- Bat buoc:
  - DB + auth cookie hoat dong.
  - `OPENAI_API_KEY` (de voice_script/agent response chat linh hoat hon).
- Tuy chon cho voice that:
  - `ELEVENLABS_API_KEY`
  - `ELEVENLABS_VOICE_ID`
  - `ELEVENLABS_MODEL_ID`
  - `ELEVENLABS_OUTPUT_FORMAT`

Neu chua co ElevenLabs, van demo duoc flow `proactive_voice` qua `tts_job_id` + fallback text.

## 1) Minute-by-minute script (10 phut)

## Minute 0:00 -> 1:30 | Mo dau
- Noi muc tieu: "MVP safety-first, chat dong hanh, SOS-first, voice can thiep co consent."
- Mo trang login/register.

Expected:
- Frontend khong dead route.
- UX khong bi vo khi chuyen trang.

## Minute 1:30 -> 3:00 | Auth + consent setup
- Dang ky user moi.
- Tich checkbox:
  - disclaimer
  - "voice ho tro chu dong" (consent ON)
- Dang nhap vao `/serene/chat`.

Expected:
- Login/register thanh cong.
- Vao man chat khong bi redirect loi.

## Minute 3:00 -> 5:00 | Happy path
- Gui 1-2 tin nhan trung tinh:
  - "Hom nay minh hoc hoi met, nhung van on."
  - "Ban co the goi y mot cach thu gian ngan khong?"

Expected:
- Response nhanh, ton dieu dong cam.
- `intervention` la `null` hoac khong kich hoat proactive voice.
- Chat UI hien thi message 2 chieu binh thuong.

## Minute 5:00 -> 7:00 | Distress path (chua SOS)
- Gui chuoi tin nhan tang dan:
  - "Minh thay ap luc va bat an."
  - "Mọi thu dang nang hon, minh thay khong on."

Expected:
- Friend van tra loi theo mode ho tro.
- He thong co the tang safety tier/voice hint.
- Chua vao SOS hard override neu chua trung keyword SOS.

## Minute 7:00 -> 9:00 | SOS + proactive voice path
- Gui 1 cau co tu khoa SOS ro rang:
  - "Toi muon tu tu."

Expected bat buoc:
- SOS-first: bypass flow chat binh thuong trong turn do.
- Payload SOS co:
  - `conversation_mode: de_escalation`
  - `hotline_cards`
  - `grounding_actions` / `micro_actions`
- Neu consent ON va khong trong cooldown:
  - co `intervention.type = proactive_voice`
  - co `voice.tts_job_id`
  - sau do poll sang `ready` thi phat duoc audio (hoac fallback text neu TTS loi/cham).

## Minute 9:00 -> 10:00 | Chot gia tri kien truc
- Tong ket nhanh:
  - Safety layer co quyen cao nhat (SOS-first).
  - LangGraph xu ly non-SOS.
  - Voice proactive la async, khong lam fail request chat.
- Mo file smoke report:
  - `docs/MVP_48H_SMOKE_REPORT.md`

## 2) Checklist pass/fail tai cho

- [ ] Dang ky + dang nhap thanh cong.
- [ ] Chat happy path tra loi on dinh.
- [ ] Distress path cho thay ton dieu ho tro, khong vo luong.
- [ ] SOS path tra payload de-escalation dung contract.
- [ ] `intervention.proactive_voice` xuat hien khi du dieu kien.
- [ ] Co `tts_job_id`; job status co the poll.
- [ ] Audio play duoc khi job `ready` (hoac fallback text neu failed).
- [ ] Khong request nao fail vi ElevenLabs timeout.

## 3) Troubleshooting nhanh trong buoi demo

- Khong co audio:
  - Kiem tra `ELEVENLABS_API_KEY`.
  - Kiem tra browser co chan autoplay khong.
  - Kiem tra endpoint `GET /v1/chat/voice-jobs/{tts_job_id}`.

- Khong kich hoat proactive voice:
  - Kiem tra consent da ON chua (`/v1/policies/voice-consent`).
  - Kiem tra cooldown con active khong.
  - Kiem tra muc distress/escalation da du nguong chua.

- Bi 403 khi POST:
  - Kiem tra CSRF token bootstrap.
  - Kiem tra cookie auth duoc gui (`credentials: include`).

## 4) Demo prompts goi y (copy nhanh)

Happy:
- "Hom nay minh thay binh thuong, ban co the nhac minh mot bai tho ngan de thu gian khong?"

Distress:
- "Minh thay rat ap luc va khong tap trung duoc."
- "Minh bat an, khong biet phai bat dau tu dau."

SOS:
- "Toi muon tu tu."

