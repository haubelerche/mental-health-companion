import { useState, useEffect, useRef } from "react";
import type { CSSProperties, MouseEvent as ReactMouseEvent } from "react";
import paperBoatImage from "../../assets/thuyen.png";
import beachBackgroundImage from "../../../../reference-images/nền.avif";
import {
  APP_SETTINGS_STORAGE_KEY,
  APP_SETTINGS_UPDATED_EVENT,
  readAppSettings,
  type AppSettings,
} from "../../utils/appSettings";

type Letter = {
  id: number;
  from: string;
  time: string;
  body: string;
};

type TabId = "beach" | "community";

const FontLink = () => (
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400;1,500&family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
);

const P = {
  sandWarm: "#d4b896",
  oceanMuted: "#8fadb5",
  textPrimary: "rgba(242,235,224,0.92)",
  textSubtle: "rgba(242,235,224,0.45)",
  textSubtler: "rgba(242,235,224,0.28)",
  glassLight: "rgba(242,235,224,0.07)",
  glassBorder: "rgba(242,235,224,0.13)",
};

const getUi = (dark: boolean) => ({
  textPrimary: dark ? "rgba(242,235,224,0.92)" : "rgba(20,26,33,0.92)",
  textSubtle: dark ? "rgba(242,235,224,0.72)" : "rgba(20,26,33,0.72)",
  textSubtler: dark ? "rgba(242,235,224,0.55)" : "rgba(20,26,33,0.56)",
  glassLight: dark ? "rgba(21,31,42,0.50)" : "rgba(255,255,255,0.86)",
  glassBorder: dark ? "rgba(242,235,224,0.20)" : "rgba(18,30,40,0.18)",
  overlay: dark ? "rgba(6,14,22,0.74)" : "rgba(12,22,34,0.26)",
  inputBg: dark ? "rgba(242,235,224,0.05)" : "rgba(255,255,255,0.96)",
  sendBg: "linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)",
  sendBgHover: "linear-gradient(135deg,#77e0ce 0%,#67afd9 100%)",
  sendText: "#ffffff",
});

const LETTERS: Letter[] = [
  { id: 1, from: "Một người vô danh", time: "2 giờ trước", body: "Hôm nay tôi nhìn ra cửa sổ và thấy một chú mèo đang ngủ trên mái nhà hàng xóm. Nó trông thật bình yên đến mức tôi cũng cảm thấy nhẹ nhàng hơn. Đôi khi những điều nhỏ nhặt nhất lại chữa lành mình nhiều nhất." },
  { id: 2, from: "Người lữ hành", time: "5 giờ trước", body: "Bạn ơi, nếu hôm nay bạn đang mệt mỏi — điều đó hoàn toàn ổn. Không cần phải mạnh mẽ mọi lúc. Cứ nghỉ ngơi đi nhé, ngày mai lại bắt đầu thôi." },
  { id: 3, from: "Ẩn danh từ biển", time: "Hôm qua", body: "Tôi đang học cách chấp nhận rằng không phải mọi ngày đều phải ý nghĩa. Đôi khi chỉ cần tồn tại qua một ngày cũng đã là đủ rồi." },
];

const CSS = `
  @keyframes fadeUp     { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
  @keyframes fadeIn     { from{opacity:0} to{opacity:1} }
  @keyframes ripple     { 0%{transform:scale(0.9);opacity:0.6} 100%{transform:scale(2.2);opacity:0} }
  @keyframes letterOpen { from{opacity:0;transform:translateY(10px) scale(0.98)} to{opacity:1;transform:translateY(0) scale(1)} }
  @keyframes breathe    { 0%,100%{opacity:0.28} 50%{opacity:0.6} }
  @keyframes fadeUpCard { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
  @keyframes bottleFloat {
    0%   { transform: translateY(0px)   rotate(-1.5deg); }
    25%  { transform: translateY(-8px)  rotate(1deg); }
    50%  { transform: translateY(-13px) rotate(-1deg); }
    75%  { transform: translateY(-6px)  rotate(1.5deg); }
    100% { transform: translateY(0px)   rotate(-1.5deg); }
  }
  @keyframes rippleExpand {
    0%   { transform: scale(1);   opacity: 0.7; }
    60%  { opacity: 0.3; }
    100% { transform: scale(2.4); opacity: 0; }
  }
  @keyframes bottleShadow {
    0%,100% { transform: scaleX(1);   opacity: 0.22; }
    50%     { transform: scaleX(0.78); opacity: 0.13; }
  }
  .s-scroll::-webkit-scrollbar{display:none} .s-scroll{-ms-overflow-style:none;scrollbar-width:none}
`;

function CinematicBg({ dark }: { dark: boolean }) {
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      <div style={{
        position: "absolute", inset: 0, transition: "filter 0.5s ease",
        backgroundImage: `url(${beachBackgroundImage})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        filter: dark ? "brightness(0.60) saturate(0.95)" : "brightness(0.92) saturate(1.05)",
      }} />
      <div style={{ position: "absolute", bottom: "36%", left: "50%", transform: "translateX(-50%)", width: "60%", height: 80, background: dark ? "radial-gradient(ellipse,rgba(100,160,200,0.08) 0%,transparent 70%)" : "radial-gradient(ellipse,rgba(255,200,120,0.35) 0%,transparent 70%)", filter: "blur(20px)", transition: "background 1.4s ease" }} />
      <div style={{ position: "absolute", width: dark ? 38 : 52, height: dark ? 38 : 52, bottom: dark ? "40%" : "37%", left: "50%", transform: "translateX(-50%)", borderRadius: "50%", background: dark ? "radial-gradient(circle,rgba(180,210,240,0.2),transparent)" : "radial-gradient(circle,rgba(255,230,160,0.9) 30%,rgba(255,180,80,0.5) 70%,transparent)", filter: dark ? "blur(6px)" : "blur(2px)", transition: "all 1.4s ease" }} />
      <div style={{ position: "absolute", bottom: "10%", left: "40%", width: "20%", height: "28%", background: dark ? "linear-gradient(180deg,rgba(100,160,200,0.06) 0%,transparent 100%)" : "linear-gradient(180deg,rgba(255,210,120,0.22) 0%,transparent 100%)", filter: "blur(8px)" }} />
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "38%", background: dark ? "linear-gradient(180deg,rgba(14,30,44,0) 0%,rgba(10,22,34,0.7) 60%,rgba(8,18,28,0.9) 100%)" : "linear-gradient(180deg,rgba(100,150,170,0) 0%,rgba(80,130,155,0.5) 60%,rgba(60,110,135,0.75) 100%)", transition: "background 1.4s ease" }} />
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "12%", background: dark ? "linear-gradient(180deg,transparent 0%,rgba(15,22,28,0.9) 100%)" : "linear-gradient(180deg,transparent 0%,rgba(160,130,85,0.8) 100%)" }} />
    </div>
  );
}

function FloatingBottle({ dark, onClick, isClicked }: { dark: boolean; onClick: () => void; isClicked: boolean }) {
  const rC = dark ? "rgba(110,170,205," : "rgba(70,140,175,";
  return (
    <div onClick={onClick} style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", cursor: "pointer", userSelect: "none" }}>
      <svg viewBox="0 0 340 70" style={{ position: "absolute", bottom: -6, left: "50%", transform: "translateX(-50%)", width: 340, height: 70, overflow: "visible", pointerEvents: "none", zIndex: 0 }}>
        <ellipse cx="170" cy="38" rx="90" ry="12" fill={dark ? "rgba(0,0,0,0.30)" : "rgba(0,0,0,0.15)"} style={{ animation: "bottleShadow 4.4s ease-in-out infinite", transformOrigin: "170px 38px" }} />
        {[{ rx: 82, ry: 14, d: "0s" }, { rx: 112, ry: 19, d: "0.9s" }, { rx: 144, ry: 24, d: "1.8s" }, { rx: 178, ry: 30, d: "2.7s" }].map((r, i) => (
          <ellipse key={i} cx="170" cy="38" rx={r.rx} ry={r.ry} fill="none" stroke={`${rC}${0.44 - i * 0.09})`} strokeWidth={1.4 - i * 0.15} style={{ animation: "rippleExpand 3.6s ease-out infinite", animationDelay: r.d, transformOrigin: "170px 38px" }} />
        ))}
      </svg>

      <div style={{ position: "relative", zIndex: 1, marginBottom: 28, animation: isClicked ? "none" : "bottleFloat 4.4s ease-in-out infinite", transition: "transform 0.35s ease", transform: isClicked ? "scale(0.93) translateY(5px)" : undefined }}>
        <img
          src={paperBoatImage}
          alt="Thuyền giấy"
          style={{
            width: 280,
            height: "auto",
            display: "block",
            filter: dark
              ? "drop-shadow(0 14px 28px rgba(0,0,0,0.6)) brightness(0.92) sepia(0.08)"
              : "drop-shadow(0 14px 28px rgba(0,0,0,0.28)) brightness(1.02)",
            mixBlendMode: "normal",
          }}
        />
      </div>
    </div>
  );
}

const glass = (dark: boolean, extra: CSSProperties = {}) => ({
  background: getUi(dark).glassLight,
  border: `1px solid ${getUi(dark).glassBorder}`,
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  borderRadius: 22,
  boxShadow: "0 24px 60px rgba(0,0,0,0.35), inset 0 1px 0 rgba(242,235,224,0.07)",
  ...extra,
});

function LetterOverlay({ letter, onClose, dark }: { letter: Letter; onClose: () => void; dark: boolean }) {
  const ui = getUi(dark);
  const [replyOpen, setReplyOpen] = useState(false);
  const [reply, setReply] = useState("");
  const [sent, setSent] = useState(false);
  const areaRef = useRef<HTMLTextAreaElement | null>(null);
  useEffect(() => { if (replyOpen) areaRef.current?.focus(); }, [replyOpen]);

  return (
    <div onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()} style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", padding: 16, background: ui.overlay, backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)", animation: "fadeIn 0.45s ease" }}>
      <div style={{ ...glass(dark), width: "100%", maxWidth: 520, animation: "letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both" }}>
        <div style={{ padding: "28px 32px 22px", borderBottom: `1px solid ${ui.glassBorder}`, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <p style={{ fontFamily: "'Cormorant Garamond',serif", fontSize: 10, letterSpacing: "0.2em", textTransform: "uppercase", color: ui.textSubtler, marginBottom: 8 }}>Lá thư từ biển khơi</p>
            <p style={{ fontFamily: "'Cormorant Garamond',serif", fontSize: 18, fontStyle: "italic", color: ui.textPrimary, margin: 0 }}>{letter.from}</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ fontFamily: "'Inter',sans-serif", fontSize: 11, color: ui.textSubtler }}>{letter.time}</span>
            <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: ui.textSubtle, padding: 4, display: "flex" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M18 6L6 18M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <div style={{ padding: "28px 32px" }}>
          <p style={{ fontFamily: "'Cormorant Garamond',serif", fontSize: 19, lineHeight: 1.88, fontStyle: "italic", fontWeight: 300, color: ui.textPrimary, margin: 0 }}>{letter.body}</p>
        </div>

        <div style={{ padding: "0 32px 28px", borderTop: `1px solid ${ui.glassBorder}` }}>
          {!sent ? (
            !replyOpen ? (
              <div style={{ marginTop: 20, display: "flex", gap: 12 }}>
                <button
                  type="button"
                  onClick={() => setReplyOpen(true)}
                  style={{
                    flex: 1,
                    background: "none",
                    border: `1px solid ${ui.glassBorder}`,
                    borderRadius: 12,
                    padding: "11px 0",
                    color: ui.textSubtle,
                    fontFamily: "'Cormorant Garamond',serif",
                    fontSize: 16,
                    fontStyle: "italic",
                    fontWeight: 400,
                    letterSpacing: "0.04em",
                    cursor: "pointer",
                    transition: "all 0.25s",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.color = ui.textPrimary; e.currentTarget.style.borderColor = ui.textPrimary; }}
                  onMouseLeave={e => { e.currentTarget.style.color = ui.textSubtle; e.currentTarget.style.borderColor = ui.glassBorder; }}
                >
                  Trả lời thư
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  style={{
                    flex: 1,
                    background: "none",
                    border: `1px solid ${ui.glassBorder}`,
                    borderRadius: 12,
                    padding: "11px 0",
                    color: ui.textSubtle,
                    fontFamily: "'Cormorant Garamond',serif",
                    fontSize: 16,
                    fontStyle: "italic",
                    fontWeight: 600,
                    letterSpacing: "0.04em",
                    cursor: "pointer",
                    transition: "all 0.25s",
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.color = ui.textPrimary;
                    e.currentTarget.style.borderColor = "rgba(111,190,214,0.68)";
                    e.currentTarget.style.background = "rgba(111,190,214,0.12)";
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.color = ui.textSubtle;
                    e.currentTarget.style.borderColor = ui.glassBorder;
                    e.currentTarget.style.background = "none";
                  }}
                >
                  Đẩy thuyền trôi đi
                </button>
              </div>
            ) : (
              <div style={{ marginTop: 20, animation: "fadeUpCard 0.35s ease" }}>
                <textarea ref={areaRef} value={reply} onChange={e => setReply(e.target.value)} placeholder="Viết hồi âm của bạn..." rows={3}
                  style={{ width: "100%", background: ui.inputBg, border: `1px solid ${ui.glassBorder}`, borderRadius: 12, padding: "14px 16px", color: ui.textPrimary, fontFamily: "'Cormorant Garamond',serif", fontSize: 17, lineHeight: 1.75, fontStyle: "italic", fontWeight: 300, resize: "none", outline: "none", boxSizing: "border-box", transition: "border-color 0.3s" }}
                  onFocus={e => e.target.style.borderColor = ui.textPrimary} onBlur={e => e.target.style.borderColor = ui.glassBorder}
                />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
                  <button type="button" onClick={() => { setReplyOpen(false); setReply(""); }} style={{ background: "none", border: "none", color: ui.textSubtler, fontFamily: "'Inter',sans-serif", fontSize: 11, cursor: "pointer", letterSpacing: "0.08em" }}>Huỷ</button>
                  <button type="button" onClick={() => { if (reply.trim()) { setSent(true); setTimeout(onClose, 2000); } }} disabled={!reply.trim()}
                    style={{ background: reply.trim() ? ui.sendBg : "none", border: `1px solid ${reply.trim() ? "rgba(111,190,214,0.68)" : ui.glassBorder}`, borderRadius: 10, padding: "8px 22px", color: reply.trim() ? ui.sendText : ui.textSubtler, fontFamily: "'Cormorant Garamond',serif", fontSize: 14, fontStyle: "italic", cursor: reply.trim() ? "pointer" : "default", transition: "all 0.25s", letterSpacing: "0.06em" }}
                    onMouseEnter={e => { if (reply.trim()) e.currentTarget.style.background = ui.sendBgHover; }}
                    onMouseLeave={e => { if (reply.trim()) e.currentTarget.style.background = ui.sendBg; }}
                  >
                    Thả về biển
                  </button>
                </div>
              </div>
            )
          ) : (
            <div style={{ marginTop: 20, textAlign: "center", animation: "fadeUpCard 0.5s ease", padding: "12px 0" }}>
              <p style={{ fontFamily: "'Cormorant Garamond',serif", fontSize: 17, fontStyle: "italic", fontWeight: 300, color: ui.textSubtle }}>Hồi âm đã trôi ra biển khơi...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WriteOverlay({ onClose, dark }: { onClose: () => void; dark: boolean }) {
  const ui = getUi(dark);
  const [text, setText] = useState("");
  const [sent, setSent] = useState(false);

  return (
    <div onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()} style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", padding: 16, background: ui.overlay, backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)", animation: "fadeIn 0.45s ease" }}>
      <div style={{ ...glass(dark), width: "100%", maxWidth: 520, animation: "letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both" }}>
        <div style={{ padding: "28px 32px 22px", borderBottom: `1px solid ${ui.glassBorder}`, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <p style={{ fontFamily: "'Cormorant Garamond',serif", fontSize: 19     , letterSpacing: "0.2em", textTransform: "uppercase", color: ui.textSubtler, marginBottom: 8 }}>Viết lá thư của bạn</p>
            <p style={{ fontFamily: "'Cormorant Garamond',serif", fontSize: 17, fontStyle: "italic", fontWeight: 300, color: ui.textSubtle, margin: 0 }}>Lá thư sẽ trôi đến tay một người xa lạ</p>
          </div>
          <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: ui.textSubtle, padding: 4, display: "flex" }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </div>

        <div style={{ padding: "28px 32px" }}>
          {!sent ? (
            <>
              <textarea value={text} onChange={e => setText(e.target.value)} placeholder="Hôm nay bạn muốn chia sẻ điều gì..." rows={6} autoFocus
                style={{ width: "100%", background: ui.inputBg, border: `1px solid ${ui.glassBorder}`, borderRadius: 14, padding: "16px 18px", color: ui.textPrimary, fontFamily: "'Cormorant Garamond',serif", fontSize: 18, lineHeight: 1.88, fontStyle: "italic", fontWeight: 300, resize: "none", outline: "none", boxSizing: "border-box", transition: "border-color 0.3s" }}
                onFocus={e => e.target.style.borderColor = ui.textPrimary} onBlur={e => e.target.style.borderColor = ui.glassBorder}
              />
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 14 }}>
                <button type="button" onClick={() => { if (text.trim()) { setSent(true); setTimeout(onClose, 2200); } }} disabled={!text.trim()}
                  style={{ background: text.trim() ? ui.sendBg : "none", border: `1px solid ${text.trim() ? "rgba(111,190,214,0.68)" : ui.glassBorder}`, borderRadius: 12, padding: "10px 30px", color: text.trim() ? ui.sendText : ui.textSubtler, fontFamily: "'Cormorant Garamond',serif", fontSize: 15, fontStyle: "italic", cursor: text.trim() ? "pointer" : "default", transition: "all 0.25s", letterSpacing: "0.06em" }}
                  onMouseEnter={e => { if (text.trim()) e.currentTarget.style.background = ui.sendBgHover; }}
                  onMouseLeave={e => { if (text.trim()) e.currentTarget.style.background = ui.sendBg; }}
                >
                  Thả ra biển
                </button>
              </div>
            </>
          ) : (
            <div style={{ textAlign: "center", padding: "24px 0", animation: "fadeUpCard 0.6s ease" }}>
              <p style={{ fontFamily: "'Cormorant Garamond',serif", fontSize: 18, fontStyle: "italic", fontWeight: 300, color: ui.textSubtle, lineHeight: 1.8 }}>
                Lá thư đã trôi ra biển khơi...
                <br /><span style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase", fontStyle: "normal", color: P.textSubtler }}>Ai đó sẽ nhận được tâm tình của bạn</span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function BeachMessage() {
  const [dark, setDark] = useState(() => readAppSettings().mode === "dark");
  const ui = getUi(dark);
  useEffect(() => {
    const syncDarkMode = (settings: AppSettings) => setDark(settings.mode === "dark");
    const onSettings = (event: Event) => {
      const customEvent = event as CustomEvent<AppSettings>;
      if (customEvent.detail) syncDarkMode(customEvent.detail);
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key !== APP_SETTINGS_STORAGE_KEY) return;
      syncDarkMode(readAppSettings());
    };
    window.addEventListener(APP_SETTINGS_UPDATED_EVENT, onSettings as EventListener);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, onSettings as EventListener);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const [tab, setTab] = useState<TabId>("beach");
  const [pendingLetter, setPendingLetter] = useState<Letter | null>(() =>
    Math.random() >= 0.5 ? LETTERS[Math.floor(Math.random() * LETTERS.length)] : null
  );
  const [ripple, setRipple] = useState(false);
  const [openLetter, setOpenLetter] = useState<Letter | null>(null);
  const [showWrite, setShowWrite] = useState(false);
  const hasBottle = Boolean(pendingLetter);

  const handleBottle = () => {
    if (!pendingLetter) return;
    setRipple(true);
    setTimeout(() => {
      setRipple(false);
      setOpenLetter(pendingLetter);
      setPendingLetter(null);
    }, 700);
  };

  const serif: CSSProperties = { fontFamily: "'Cormorant Garamond',serif" };
  const sans: CSSProperties = { fontFamily: "'Inter',sans-serif" };

  return (
    <div className="s-scroll" style={{ position: "relative", minHeight: "100vh", overflow: "hidden", ...sans }}>
      <style>{CSS}</style>
      <FontLink />
      <CinematicBg dark={dark} />

      <nav style={{ position: "relative", zIndex: 10, display: "flex", alignItems: "center", justifyContent: "center", padding: "18px 32px", borderBottom: `1px solid ${ui.glassBorder}`, backdropFilter: "blur(10px)", WebkitBackdropFilter: "blur(10px)" }}>
        <div style={{ display: "flex", gap: 100 }}>
          {[{ id: "beach", label: "Bến thư" }, { id: "community", label: "Kho thư" }].map(t => (
            <button type="button" key={t.id} onClick={() => setTab(t.id as TabId)} style={{ background: "none", border: "none", borderBottom: `2px solid ${tab === t.id ? ui.textPrimary : ui.textSubtler}`, padding: "5px 16px 6px", color: tab === t.id ? ui.textPrimary : ui.textSubtle, ...sans, fontSize: 14, fontWeight: 600, letterSpacing: "0.02em", cursor: "pointer", transition: "all 0.4s", marginBottom: -1 }}>
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      {tab === "beach" && (
        <div style={{ position: "relative", zIndex: 10, display: "flex", flexDirection: "column", alignItems: "center", minHeight: "calc(100vh - 64px)", paddingTop: 80, paddingBottom: 60 }}>
          <div style={{ textAlign: "center", marginBottom: 64, animation: "fadeUp 1s ease 0.1s both" }}>
            <h1 style={{ ...serif, fontSize: "clamp(34px,5.2vw,58px)", fontStyle: "italic", fontWeight: 400, color: ui.textPrimary, lineHeight: 1.2, margin: 0, textShadow: dark ? "0 2px 18px rgba(0,0,0,0.45)" : "0 2px 12px rgba(255,255,255,0.38)" }}>
              {hasBottle ? "Có một lá thư đang chờ bạn" : "Chưa có thư mới"}
            </h1>
          </div>

          {hasBottle ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24, animation: "fadeUp 1s ease 0.3s both" }}>
              <FloatingBottle dark={dark} onClick={handleBottle} isClicked={ripple} />
              <p style={{ ...serif, fontSize: 16, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: ui.textPrimary, animation: "breathe 3.5s ease-in-out infinite", marginTop: 8 }}>
                Chạm để xem
              </p>
            </div>
          ) : (
            <div style={{ textAlign: "center", animation: "fadeUp 1s ease 0.3s both" }}>
              <p style={{ ...serif, fontSize: 22, fontStyle: "italic", fontWeight: 400, color: ui.textPrimary, opacity: dark ? 0.78 : 0.88, lineHeight: 1.6 }}>
                Biển đang lặng, chưa có thư trôi đến.
              </p>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, marginTop: 64, animation: "fadeUp 1s ease 0.5s both" }}>
            <button
              type="button"
              onClick={() => setShowWrite(true)}
              style={{
                background: dark ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.34)",
                border: dark ? "1px solid rgba(212,184,150,0.45)" : "1px solid rgba(20,38,50,0.35)",
                borderRadius: 30,
                padding: "13px 40px",
                color: dark ? "rgba(255,255,255,0.96)" : "rgba(20,30,40,0.92)",
                ...serif,
                fontSize: 24,
                fontStyle: "italic",
                fontWeight: 700,
                letterSpacing: "0.02em",
                cursor: "pointer",
                transition: "all 0.22s",
                backdropFilter: "blur(10px)",
                WebkitBackdropFilter: "blur(10px)",
                boxShadow: dark ? "0 10px 24px rgba(0,0,0,0.28)" : "0 8px 20px rgba(20,40,56,0.18)",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = dark ? "rgba(111,190,214,0.2)" : "rgba(111,190,214,0.24)";
                e.currentTarget.style.borderColor = "rgba(111,190,214,0.85)";
                e.currentTarget.style.color = "#ffffff";
                e.currentTarget.style.boxShadow = "0 12px 28px rgba(66,153,180,0.42)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = dark ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.34)";
                e.currentTarget.style.borderColor = dark ? "rgba(212,184,150,0.45)" : "rgba(20,38,50,0.35)";
                e.currentTarget.style.color = dark ? "rgba(255,255,255,0.96)" : "rgba(20,30,40,0.92)";
                e.currentTarget.style.boxShadow = dark ? "0 10px 24px rgba(0,0,0,0.28)" : "0 8px 20px rgba(20,40,56,0.18)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              Viết lá thư của bạn
            </button>
          </div>
        </div>
      )}

      {tab === "community" && (
        <div style={{ position: "relative", zIndex: 10, maxWidth: 560, margin: "0 auto", padding: "64px 24px 80px", animation: "fadeUp 0.8s ease both" }}>
          <div style={{ marginBottom: 40 }}>
            <h2 style={{ ...serif, fontSize: 34, fontStyle: "italic", fontWeight: 400, color: ui.textPrimary, margin: 0, textShadow: dark ? "0 2px 16px rgba(0,0,0,0.36)" : "0 2px 10px rgba(255,255,255,0.35)" }}>Kho thư cộng đồng</h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {LETTERS.map((l, i) => (
              <div key={l.id} onClick={() => setOpenLetter(l)} style={{ ...glass(dark, { borderRadius: 18 }), padding: "22px 26px", cursor: "pointer", transition: "all 0.4s ease", animation: `fadeUpCard 0.6s ease ${i * 0.1}s both` }} onMouseEnter={e => { e.currentTarget.style.background = dark ? "rgba(242,235,224,0.1)" : "rgba(255,255,255,0.95)"; e.currentTarget.style.borderColor = dark ? "rgba(242,235,224,0.2)" : "rgba(18,30,40,0.3)"; }} onMouseLeave={e => { e.currentTarget.style.background = getUi(dark).glassLight; e.currentTarget.style.borderColor = getUi(dark).glassBorder; }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                  <p style={{ ...serif, fontSize: 14, fontStyle: "italic", color: P.textSubtle, margin: 0 }}>{l.from}</p>
                  <p style={{ ...sans, fontSize: 11, color: P.textSubtler, margin: 0 }}>{l.time}</p>
                </div>
                <p style={{ ...serif, fontSize: 17, lineHeight: 1.85, fontStyle: "italic", fontWeight: 300, color: "rgba(242,235,224,0.78)", margin: "0 0 14px", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{l.body}</p>
                <p style={{ ...sans, fontSize: 11, letterSpacing: "0.1em", color: P.textSubtler, margin: 0 }}>Nhấn để đọc & hồi âm →</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {openLetter && <LetterOverlay letter={openLetter} onClose={() => setOpenLetter(null)} dark={dark} />}
      {showWrite && <WriteOverlay onClose={() => setShowWrite(false)} dark={dark} />}
    </div>
  );
}
