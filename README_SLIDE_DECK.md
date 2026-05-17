# README Slide Deck Du An Serene

## Context

Tai lieu nay la bo noi dung thuyet trinh theo chuan 12 slide trong Sequoia Framework, duoc dieu chinh cho du an Serene: he thong AI ho tro sang loc va cham soc suc khoe tinh than bang tieng Viet. Muc tieu cua file la giup nhom nhanh chong tao slide, thuyet trinh demo, va bao ve cac quyet dinh san pham - ky thuat mot cach mach lac.

Serene khong duoc dinh vi la bac si AI, khong chan doan benh, va khong thay the chuyen gia tam ly. He thong duoc dinh vi la mot lop ho tro dau tien: rieng tu, it phan xet, co kha nang lang nghe, sang loc dau hieu ban dau, dua ra hanh dong nho co the lam ngay, va chuyen nguoi dung sang nguon luc thuc te khi rui ro vuot nguong tu ho tro.

## Problem Statement

Nguoi tre 18-24 tuoi thuong gap ap luc hoc tap, cong viec, tai chinh, gia dinh, quan he va cam giac co don, nhung khong de dang tim den ho tro chuyen mon do ky thi, chi phi, thoi gian, so bi danh gia, hoac khong biet van de cua minh co nghiem trong hay khong. Cac giai phap hien tai bi phan manh: bai test online kho cung, chatbot pho thong thieu safety guardrail, ung dung self-care thieu ca nhan hoa, va dich vu chuyen gia co nhieu rao can tiep can.

Bai toan cot loi cua Serene la xay dung mot he thong du tin cay de nguoi dung dam noi that, du thong minh de nhan dien pattern cam xuc ban dau, du thuc te de dua ra buoc tiep theo, va du an toan de khong bo mac nguoi dung trong tinh huong rui ro cao.

## Technical Deep-Dive

Kien truc hien tai cua Serene la lightweight multi-agent voi 3 vai tro runtime chinh:

| Vai tro | Ten san pham | Dinh danh ky thuat | Chuc nang |
|---|---|---|---|
| Agent 1 | Serene Conversation Agent | `FriendNode` | Tra loi nguoi dung trong luong binh thuong, giu mot danh tinh Serene on dinh, ap dung persona nhu style mode. |
| Agent 2 | Internal Analyst Agent | `AnalystNode` | Phan tich pattern, trigger, coping, resource context; chi xuat `AnalystBundle`, khong noi truc tiep voi nguoi dung. |
| Agent 3 | Safety Agent | `SafetyFinalizer` | Xu ly high-risk turn bang payload co kiem soat: lam diu, micro-action, hotline/referral, crisis/audit log. |

Nguon du lieu chinh la PostgreSQL/Supabase. Redis chi dung cho cache, rate limit, idempotency va guest state ngan han. pgvector dung cho semantic recall tren noi dung da mask hoac tom tat. Neo4j chi la lop tri thuc/pattern da lam sach, khong luu raw messages, PII, crisis logs, cau tra loi screening tho, hay quan he chan doan truc tiep. Outbox/Celery xu ly cac side effect bat dong bo nhu memory, dashboard insight, TTS va graph sync.

## Strategic Recommendations

Slide deck nen trinh bay Serene nhu mot san pham co loi the o 4 diem: privacy-first, Vietnamese-native emotional support, safety-first architecture, va continuous insight loop. Khong nen nhan manh "co nhieu chatbot" nhu loi the chinh, vi thi truong chatbot tong quat da bao hoa va kho tao niem tin. Loi the phong thu can nam o data boundary, clinical-adjacent safety design, dashboard insight, memory co quyen kiem soat, va he sinh thai ho tro lien tuc.

## Cau Truc Slide Deck

### 01. Purpose

**Tieu de slide:** Serene: Noi an toan de ban noi that, hieu minh hon, va biet buoc tiep theo.

**One-liner dinh vi:** Serene la AI mental-health companion bang tieng Viet, giup nguoi tre chia se rieng tu, sang loc dau hieu cam xuc ban dau, nhan ho tro tuc thoi, va ket noi nguon luc thuc te khi can.

**Noi dung dua len slide:**

| Thanh phan | Noi dung |
|---|---|
| San pham | Ung dung AI ho tro suc khoe tinh than cho nguoi tre Viet Nam. |
| Dinh vi | Emotional first-aid, private screening, guided support. |
| Khong phai | Khong chan doan, khong thay the bac si, khong dua ra quyet dinh lam sang tu dong. |
| Vong lap gia tri | Talk -> Understand -> Act -> Reflect. |

**Loi thoai trinh bay:** Serene duoc xay dung tu mot su that don gian: phan lon nguoi tre khong bat dau bang cau "toi can dieu tri", ma bat dau bang "toi khong on nhung khong biet noi voi ai". Vi vay, san pham khong co gang dong vai bac si AI, ma dong vai mot diem cham dau tien an toan, rieng tu va co kha nang dan nguoi dung den buoc tiep theo phu hop.

**Goi y hinh anh:** Man hinh landing Serene, khung chat voi loi chao bang tieng Viet, va vong lap 4 buoc Talk - Understand - Act - Reflect.

### 02. Problem

**Tieu de slide:** Khoang trong ho tro tam ly dau tien cho nguoi tre.

**Noi dung dua len slide:**

| Van de | Tac dong den nguoi dung |
|---|---|
| So bi danh gia | Khong dam chia se voi gia dinh, ban be, giao vien hoac dong nghiep. |
| Khong biet muc do nghiem trong | Tri hoan tim kiem ho tro chuyen mon. |
| Chi phi va thoi gian | Dich vu tam ly chuyen nghiep khong phai luc nao cung de tiep can. |
| Cong cu hien tai phan manh | Chatbot thieu safety, bai test kho cung, self-care app thieu ca nhan hoa. |
| Thieu ban dia hoa | Nhieu ung dung khong hieu cach nguoi Viet noi giam, noi vong, noi dua, hoac ne tranh cam xuc. |

**Loi thoai trinh bay:** Bai toan khong chi la thieu noi dung self-care. Bai toan that su la thieu mot co che dau tien du kin dao de nguoi dung bat dau noi that, du co cau truc de khong bien thanh mot chatbot chung chung, va du an toan de xu ly truong hop rui ro cao.

**Goi y hinh anh:** Funnel mo ta khoang cach tu "co van de" den "tim duoc ho tro", voi cac diem roi: stigma, cost, uncertainty, availability.

### 03. Customer

**Tieu de slide:** Nguoi dung muc tieu: 18-24 tuoi, ap luc cao, can rieng tu.

**Noi dung dua len slide:**

| Nhom nguoi dung | Dac diem | Nhu cau cot loi |
|---|---|---|
| Sinh vien | Ap luc hoc tap, thi cu, gia dinh, tuong lai nghe nghiep. | Noi ra dieu kho noi, duoc lang nghe, co hanh dong nho de lam ngay. |
| Nguoi moi di lam | Stress cong viec, tai chinh, quan he, thich nghi moi truong moi. | Hieu pattern cang thang, quan sat tien trien, nhan goi y thuc te. |
| Nguoi da dung self-care app | Co y thuc theo doi cam xuc nhung thieu lien tuc. | Dashboard, trigger map, coping history, resource ca nhan hoa. |

**Customer insight:** Nguoi dung khong tim mot "AI therapist" de gan nhan benh; ho can mot khong gian rieng tu, it phan xet, noi dung dung ngu canh Viet Nam, va mot buoc tiep theo ro rang.

**Loi thoai trinh bay:** Nhom 18-24 rat quen voi AI va nen tang so, nhung dieu do khong dong nghia ho se tin bat ky chatbot nao. Niem tin den tu ranh gioi ro rang: noi nao luu du lieu, khi nao he thong can thiep, va vi sao Serene khong vuot qua vai tro ho tro ban dau.

**Goi y hinh anh:** 2 persona card: "Sinh vien ap luc thi cu" va "Nguoi moi di lam bi burnout".

### 04. Solution

**Tieu de slide:** Mot companion an toan, ca nhan hoa, va co luong escalation.

**Noi dung dua len slide:**

| Thanh phan giai phap | Gia tri |
|---|---|
| Chat cam xuc bang tieng Viet | Lang nghe tu nhien, xac nhan cam xuc, tranh chan doan. |
| SafetyGate truoc moi luot | Phat hien high-risk signal truoc khi vao luong LLM thong thuong. |
| Internal Analyst | Tong hop pattern tu chat, check-in, screening va hanh vi su dung resource. |
| Dashboard insight | Hien thi xu huong mood, trigger, coping effectiveness va next step. |
| Resource recommendation | Goi y breathing, grounding, journaling, sleep routine, exercise, knowledge cards. |
| Privacy controls | Cho phep quan ly memory, lich su chat, delete data va opt-out personalization. |

**Loi thoai trinh bay:** Giai phap cua Serene khong phai them mot chatbot vao thi truong. Diem khac biet la chat duoc dat trong mot he thong co safety gate, memory co kiem soat, analyst pipeline khong chan doan, dashboard insight an toan, va escalation flow khi rui ro vuot nguong.

**Goi y hinh anh:** So do luong: User Message -> SafetyGate -> Normal Chat hoac SafetyFinalizer -> Persistence -> Outbox -> Analyst/Dashboard.

### 05. Product/Demo

**Tieu de slide:** Trai nghiem san pham: tu chia se rieng tu den insight co hanh dong.

**Demo flow de trinh bay:**

| Buoc demo | Man hinh | Noi dung can noi |
|---|---|---|
| 1 | Landing/onboarding | Serene giai thich vai tro ho tro, privacy va disclaimer. |
| 2 | Chat | Nguoi dung noi "dao nay ap luc qua, khong ngu duoc". Serene phan hoi bang cam xuc, khong phan xet, khong chan doan. |
| 3 | Quick check-in | Ghi nhan mood, emotion, trigger, sleep/energy. |
| 4 | Resource | Goi y breathing, grounding, bai tap nho hoac noi dung YouTube/resource phu hop. |
| 5 | Dashboard | Hien thi mood trend, trigger-emotion heatmap, coping effectiveness, next step. |
| 6 | Safety path | Khi co high-risk phrase, he thong dung SafetyFinalizer, hien micro-action va hotline/referral thay vi chat binh thuong. |

**Tinh nang hien co trong repository:**

| Nhom tinh nang | Thanh phan code/tai lieu lien quan |
|---|---|
| Frontend app | React, Vite, Tailwind, `frontend/src/components/pages/*`. |
| Chat | `frontend/src/components/pages/chat/Chat.tsx`, `backend/app/api/v1/routers/chat.py`. |
| Safety/SOS | `backend/app/safety/*`, `backend/app/services/sos_handler.py`, crisis components frontend. |
| Dashboard | `frontend/src/components/dashboard/*`, `backend/app/dashboard/*`. |
| Screening | `frontend/src/components/pages/ScreeningFlow.tsx`, `backend/app/api/v1/routers/screening.py`. |
| Memory | `backend/app/memory/*`, `backend/app/services/memory_*`. |
| Rewards/persona | `frontend/src/components/pages/rewards/*`, `backend/app/rewards/*`, `backend/app/personas/*`. |
| Admin | `frontend/src/components/admin/*`, `backend/app/api/v1/routers/admin/*`. |

**Loi thoai trinh bay:** Demo nen bat dau bang mot tinh huong rat doi thuong, vi gia tri cua Serene nam o kha nang bien chia se mo ho thanh mot duong ho tro co cau truc: phan hoi cam xuc, hanh dong nho, luu memory co kiem soat, va dashboard phan anh tien trien.

**Goi y hinh anh:** 4 anh chup man hinh: Chat, Check-in, Dashboard, SOS popup.

### 06. Market

**Tieu de slide:** Co hoi thi truong: digital mental wellness cho nguoi tre Viet Nam.

**Noi dung dua len slide:**

| Tang thi truong | Mo ta | Ham y chien luoc |
|---|---|---|
| TAM | Digital mental health va AI wellness toan cau. | Thi truong lon, dang duoc AI tai cau truc. |
| SAM | Nguoi dung tre su dung smartphone, quen voi AI, co nhu cau self-care va emotional support. | Can product-led adoption, onboarding thap ma sat. |
| SOM | Sinh vien, nguoi moi di lam, cong dong hoc tap va to chuc giao duc/doanh nghiep tai Viet Nam. | Bat dau bang B2C freemium, mo rong B2B/B2B2C cho truong hoc va to chuc. |

**Phan tich co hoi:** Thi truong khong nen duoc nhin nhu "ban chatbot". Co hoi nam o lop trust infrastructure cho mental-health support: data governance, safety orchestration, user-facing insight, va workflow ket noi nguon luc ho tro.

**Loi thoai trinh bay:** Neu chi can mot chatbot, nguoi dung co the dung cong cu tong quat. Thi truong cua Serene la nhom nguoi can mot san pham duoc thiet ke rieng cho cam xuc, privacy, ngon ngu Viet Nam, va cac tinh huong safety nhay cam.

**Goi y hinh anh:** Market funnel hoac 3 vong tron TAM/SAM/SOM.

### 07. Business Model

**Tieu de slide:** Mo hinh doanh thu ket hop B2C va B2B2C.

**Noi dung dua len slide:**

| Dong doanh thu | Mo ta | Gia tri | Rui ro can kiem soat |
|---|---|---|---|
| Freemium B2C | Chat co gioi han, check-in, mot so resources mien phi. | Tang adoption va du lieu hanh vi an toan. | Chi phi LLM tren moi user. |
| Premium B2C | Unlimited insight, dashboard nang cao, memory controls, voice/TTS, guided programs. | Gia tri ca nhan hoa va lien tuc. | Khong tao phu thuoc tam ly. |
| B2B2C | Goi cho truong hoc, trung tam dao tao, doanh nghiep tre. | Dashboard tong hop an danh, resource curation, early support channel. | Phai tach du lieu ca nhan va analytics tong hop. |
| Referral/resource partnership | Noi dung, clinic/referral, knowledge packs co kiem duyet. | Mo rong nguon luc thuc te. | Khong thuong mai hoa tinh huong khung hoang. |

**Cost-to-serve can quan tri:**

| Hang muc chi phi | Chien luoc giam chi phi |
|---|---|
| LLM chat | Routing theo risk, cache context, gioi han Analyst khi khong can, fallback template. |
| TTS | Async job, deduplication theo content hash, khong chan text response. |
| Database/graph | PostgreSQL source-of-truth, Neo4j chi cho taxonomy/derived aggregate, outbox bat dong bo. |
| Safety review | Rule-based gate, audit log co cau truc, admin workflow. |

**Loi thoai trinh bay:** Business model phai ton trong dac thu mental health: khong the toi uu retention bang thao tung cam xuc. Gia tri tra phi phai nam o insight, continuity, privacy control va content/chat quality, khong nam o viec lam nguoi dung phu thuoc.

**Goi y hinh anh:** Bang 2 truc: user value vs cost-to-serve.

### 08. Traction

**Tieu de slide:** Bang chung hien tai: MVP da co nen tang san pham va ky thuat.

**Noi dung dua len slide:**

| Loai bang chung | Hien trang trong repository |
|---|---|
| Frontend MVP | Landing, chat, reflect/check-in, screening, dashboard, resource, rewards, profile, admin screens. |
| Backend API | Auth, chat, safety, screening, dashboard, memory, resources, rewards, notifications, admin routes. |
| Safety architecture | SafetyGate, SOS handler, distress router, crisis payload, hotline/referral components. |
| Data architecture | Alembic migrations, PostgreSQL ownership contract, SQLite local dev, pgvector/Neo4j boundary docs. |
| Evaluation | Golden conversations, guardrails, judge scripts, AI security eval, backend regression tests. |
| Observability | Langfuse tracing hooks, latency metrics, audit logs, outbox worker, eval reports. |

**Metrics nen dua vao slide neu co so lieu thuc te:**

| Metric | Y nghia |
|---|---|
| P95 chat latency | Do he thong co du nhanh cho hoi thoai cam xuc hay khong. |
| Safety high-risk recall | Do an toan cua SafetyGate/SafetyFinalizer. |
| D1/D7 retention | Do san pham co tao gia tri lap lai hay khong. |
| Helpful rating | Do nguoi dung thay phan hoi co huu ich hay khong. |
| Insight usefulness | Do dashboard co giup nguoi dung hieu pattern hay khong. |
| Cost per meaningful session | Do tinh ben vung cua business model. |

**Loi thoai trinh bay:** Traction hien tai nen duoc trinh bay nhu bang chung ve kha nang thuc thi, khong phong dai thanh product-market fit neu chua co du lieu nguoi dung that. Diem manh cua du an la da co day du cac lop can thiet cho MVP nghiem tuc: UX, API, safety, data, evaluation va admin operation.

**Goi y hinh anh:** Checklist milestone hoac pipeline CI/eval/report.

### 09. Competition

**Tieu de slide:** Loi the canh tranh: trust, safety, Vietnamese context, continuous insight.

**Bang so sanh:**

| Nhom doi thu | Diem manh | Diem yeu | Loi the cua Serene |
|---|---|---|---|
| Chatbot AI tong quat | Linh hoat, manh ve ngon ngu, de tiep can. | Khong thiet ke rieng cho mental-health safety, memory/privacy boundary khong ro voi nguoi dung. | Safety-first orchestration, non-diagnostic policy, Vietnamese emotional UX. |
| Ung dung thien/self-care | Noi dung de dung, chi phi thap. | It hoi thoai, it ca nhan hoa, kho xu ly distress real-time. | Chat + check-in + analyst insight + resource matching. |
| Bai test tam ly online | Co cau truc, nhanh. | Kho cung, de gay hieu nham chan doan, thieu hanh dong tiep theo. | Screening duoc dat trong luong ho tro va disclaimer ro rang. |
| Dich vu chuyen gia | Chuyen mon cao. | Chi phi, lich hen, stigma, khong phai luc nao cung san sang. | Lop dau vao rieng tu, co escalation sang nguon luc thuc te khi can. |

**Moat ky thuat va san pham:**

| Moat | Mo ta |
|---|---|
| Safety moat | SafetyGate truoc orchestration, high-risk bypass normal flow, deterministic SafetyFinalizer, crisis/audit logs. |
| Data moat | PostgreSQL source-of-truth, memory co consent, Neo4j khong luu raw sensitive data. |
| Context moat | Tieng Viet doi thuong, persona la style mode, khong tao nhieu identity gay roi. |
| Insight moat | Analyst pipeline bien chat/check-in/resource usage thanh dashboard insight khong chan doan. |
| Operational moat | Evaluation suite, guardrails, admin audit, outbox async, graceful degradation. |

**Loi thoai trinh bay:** Loi the cua Serene khong nam o viec mo hinh AI thong minh hon tat ca. Loi the nam o cach he thong dong goi AI trong mot san pham co ranh gioi an toan, quyen rieng tu, ngon ngu ban dia va vong lap insight lien tuc.

**Goi y hinh anh:** Ma tran 2x2: General AI vs Mental-health-specific, Low safety vs High safety.

### 10. Team

**Tieu de slide:** Doi ngu thuc thi: product, AI architecture, full-stack, safety, evaluation.

**Noi dung dua len slide:**

| Vai tro | Trach nhiem |
|---|---|
| Product Lead | Dinh vi san pham, user journey, go-to-market, metrics, scope MVP. |
| AI Architect | Runtime flow, multi-agent boundary, prompt/contracts, evaluation, safety invariant. |
| Backend Engineer | FastAPI, auth, data model, outbox, workers, API contracts, observability. |
| Frontend Engineer | React/Vite UI, chat UX, dashboard, crisis UI, admin views, accessibility. |
| Data/Infra Engineer | PostgreSQL, Alembic, Redis, pgvector, Neo4j boundary, deployment. |
| Safety/Clinical Advisor | Non-diagnostic framing, escalation policy, hotline/referral review, content safety. |

**Neu day la slide lop/nhom:** thay bang ten thanh vien that va gan voi cac module da lam trong repo.

**Loi thoai trinh bay:** Du an nay can nang luc lien nganh. Mot chatbot co the duoc xay nhanh, nhung mot he thong mental-health companion can product judgment, safety policy, data governance, backend reliability va UX tinh te.

**Goi y hinh anh:** Org chart nho hoac bang mapping thanh vien -> module.

### 11. Roadmap

**Tieu de slide:** Roadmap: tu MVP an toan den nen tang ho tro lien tuc.

**Roadmap de xuat:**

| Giai doan | Muc tieu | Deliverables |
|---|---|---|
| Phase A: Safety + Core Chat | MVP co the demo va test an toan. | Guest/auth, chat, SafetyGate, SafetyFinalizer, basic persona, crisis payload, logging. |
| Phase B: Insight + Screening | Hieu pattern khong chan doan. | Screening flow, AnalystBundle, dashboard insight, resource recommendation. |
| Phase C: Memory + Dashboard | Ca nhan hoa lien tuc. | Memory cards, session summary, mood trend, trigger map, coping effectiveness. |
| Phase D: Resource + Engagement | Tang gia tri su dung lap lai. | Rewards, knowledge packs, TTS dedup, resource curation, notifications. |
| Phase E: Hardening + Pilot | San sang pilot voi nguoi dung that. | PII masking, deletion/export, monitoring, eval thresholds, admin review, legal/safety review. |

**Milestone uu tien tiep theo:**

| Uu tien | Ly do |
|---|---|
| Chuan hoa API response giua spec va code | Giam loi frontend/backend contract. |
| Bo sung real metrics cho traction | Bien slide 08 tu engineering evidence thanh market evidence. |
| Kiem thu crisis flow end-to-end | Safety la invariant quan trong nhat cua san pham. |
| Hoan thien dashboard safe insight | Gia tri khac biet cua Serene nam o pattern understanding. |
| Chuan bi pilot nho | Can du lieu nguoi dung that de validate retention va helpfulness. |

**Loi thoai trinh bay:** Roadmap nen uu tien an toan va niem tin truoc cac tinh nang tang engagement. Trong linh vuc nay, reliability va safety khong phai phan phu; chung la dieu kien de san pham duoc phep mo rong.

**Goi y hinh anh:** Timeline 5 phase.

### 12. Ask / Financials

**Tieu de slide:** Can nguon luc de chuyen tu MVP ky thuat sang pilot co do luong.

**Neu thuyet trinh trong lop/hackathon, Ask nen la:**

| Nhu cau | Muc dich |
|---|---|
| Feedback san pham | Kiem tra thong diep, onboarding, chat UX, dashboard insight. |
| Nguoi dung pilot | Thu nghiem voi nhom sinh vien/nguoi moi di lam trong pham vi an toan. |
| Mentor safety/clinical | Ranh gioi ngon ngu, escalation policy, noi dung resource. |
| Ho tro infrastructure | LLM credits, database hosting, observability, TTS budget. |

**Neu thuyet trinh voi nha dau tu/doi tac, Ask nen la:**

| Hang muc | Muc dich |
|---|---|
| Seed/pilot budget | Chay pilot 3-6 thang, do retention, helpfulness, safety metrics. |
| Clinical/safety review | Kiem dinh policy, crisis flow, disclaimer, hotline/referral data. |
| Partnership | Truong hoc, trung tam tu van, cong dong sinh vien, to chuc tre. |
| Engineering capacity | Hardening API, eval automation, production monitoring, data deletion/export. |

**Financial logic can trinh bay:**

| Bien so | Cach do |
|---|---|
| CAC | Chi phi co duoc mot user kich hoat chat dau tien. |
| Activation rate | Ty le hoan thanh onboarding va gui tin nhan dau tien. |
| Retention | D1, D7, D30. |
| Cost per session | LLM + database + TTS + observability tren mot meaningful session. |
| Conversion | Freemium sang premium hoac B2B2C seat activation. |
| Safety operations cost | Chi phi review crisis logs, content moderation, compliance. |

**Loi thoai trinh bay:** Ask cua Serene khong chi la tien de build them feature. Ask dung la nguon luc de validate niem tin, safety va gia tri lap lai trong moi truong that, vi day la ba dieu kien quyet dinh san pham co the mo rong hay khong.

**Goi y hinh anh:** Bang "What we need / What it unlocks".

## Slide Design Standard

| Tieu chi | Chuan thiet ke |
|---|---|
| Bo cuc | Moi slide mot thong diep chinh, toi da 3-5 bullet hoac 1 bang ngan. |
| Tone | Nghiem tuc, an toan, tin cay; tranh mau sac qua kich thich hoac gam mau mot chieu. |
| Visual | Uu tien screenshot san pham, flow diagram, dashboard snapshot, safety pipeline. |
| Text | Tieu de ngan, noi dung slide gon, loi thoai chi tiet dat trong speaker notes. |
| Ngon ngu | Tieng Viet ro rang, tranh thuat ngu lam sang qua muc, nhan manh "khong chan doan". |
| Mau goi y | Xanh la/xanh ngoc cho calm, navy/xam cho trust, diem nhan vang nhe cho action. |

## Appendix: He Thong Can Noi Trong Phan Q&A

### Kien truc runtime

| Cau hoi | Cau tra loi de xuat |
|---|---|
| Day co phai multi-agent khong? | Co, nhung la lightweight multi-agent voi 3 vai tro runtime: Conversation, Analyst va Safety. Personas khong phai agent rieng. |
| Vi sao khong dung 5 agent rieng? | Nhieu agent user-facing lam tang latency, chi phi, do phuc tap orchestration va rui ro identity/safety drift. |
| High-risk message di dau? | SafetyGate chay truoc. Neu high-risk, normal flow bi bypass va SafetyFinalizer tra payload co kiem soat. |
| Analyst co noi voi nguoi dung khong? | Khong. Analyst chi tao structured bundle cho insight/dashboard, khong sinh final user text. |

### Data, privacy, security

| Cau hoi | Cau tra loi de xuat |
|---|---|
| Du lieu nguoi dung luu o dau? | PostgreSQL/Supabase la source of truth cho user, messages, screening, crisis logs, rewards, memory va dashboard state. |
| Neo4j co luu tin nhan nguoi dung khong? | Khong. Neo4j chi dung cho taxonomy/pattern graph da lam sach; khong luu raw message, PII hay crisis logs. |
| Nguoi dung co xoa memory duoc khong? | Co. Memory la tinh nang co kiem soat; nguoi dung co the xem, xoa hoac opt-out long-term personalization. |
| Neu LLM/TTS/Neo4j loi thi sao? | He thong degrade an toan: text chat khong bi chan boi TTS, normal chat khong phu thuoc Neo4j write, safety co template fallback. |

### Product risk

| Rui ro | Cach giam thieu |
|---|---|
| Nguoi dung hieu nham la chan doan | Disclaimer, non-diagnostic copy, cam disease probability, screening framing. |
| High-risk false negative | SafetyGate rule + classifier, crisis eval set, audit logs, regression tests. |
| Chi phi LLM cao | Routing theo risk/context, chi goi Analyst khi can, cache, async workers, fallback template. |
| Phu thuoc tam ly vao app | Khong toi uu engagement bang thao tung; day nguoi dung sang real-world support khi can. |
| Lo ngai rieng tu | Data minimization, PII masking, delete/export, Neo4j boundary, admin audit. |

## Final Narrative

Serene la mot AI mental-health companion duoc thiet ke cho nguoi tre Viet Nam, nhung tham vong cua du an khong phai tao ra mot chatbot biet an ui. Gia tri that su nam o viec dong goi AI trong mot he thong co ranh gioi ro rang: safety truoc orchestration, privacy truoc personalization, insight truoc chan doan, va hanh dong nho truoc loi khuyen dai dong.

Neu trinh bay trong 5 phut, hay giu mach noi nhu sau: nguoi tre can noi that nhung so bi danh gia; Serene tao mot diem cham rieng tu va an toan; he thong ket hop chat, safety, analyst insight, dashboard va resource; kien truc da co source-of-truth data boundary va eval guardrails; buoc tiep theo la pilot co do luong de chung minh helpfulness, retention va safety.
