import { useState, useEffect, useRef } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import paperBoatImage from "../../assets/thuyen.png";
import beachBackgroundImage from "../../assets/beach-message-bg.avif";
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

const ANIMATIONS_CSS = `
  @keyframes fadeUp     { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
  @keyframes fadeIn     { from{opacity:0} to{opacity:1} }
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
  .s-scroll::-webkit-scrollbar { display: none; }
  .s-scroll { -ms-overflow-style: none; scrollbar-width: none; }
`;

// Get UI classes based on dark mode
const getUi = (dark: boolean) => ({
  textPrimary: dark ? "text-white" : "text-slate-900",
  textSubtle: dark ? "text-white" : "text-slate-800",
  textSubtler: dark ? "text-white/50" : "text-slate-900",
  glassLight: dark
    ? "bg-slate-900/50 border-stone-50/20"
    : "bg-white/86 border-stone-950/18",
  glassBorder: dark ? "border-stone-50/20" : "border-stone-950/18",
  overlay: dark ? "bg-slate-950/74" : "bg-slate-900/26",
  inputBg: dark ? "bg-stone-50/5" : "bg-white/96",
  sendText: "text-white",
});

const LETTERS: Letter[] = [
  { id: 1, from: "Một người vô danh", time: "2 giờ trước", body: "Hôm nay tôi nhìn ra cửa sổ và thấy một chú mèo đang ngủ trên mái nhà hàng xóm. Nó trông thật bình yên đến mức tôi cũng cảm thấy nhẹ nhàng hơn. Đôi khi những điều nhỏ nhặt nhất lại chữa lành mình nhiều nhất." },
  { id: 2, from: "Người lữ hành", time: "5 giờ trước", body: "Bạn ơi, nếu hôm nay bạn đang mệt mỏi — điều đó hoàn toàn ổn. Không cần phải mạnh mẽ mọi lúc. Cứ nghỉ ngơi đi nhé, ngày mai lại bắt đầu thôi." },
  { id: 3, from: "Ẩn danh từ biển", time: "Hôm qua", body: "Tôi đang học cách chấp nhận rằng không phải mọi ngày đều phải ý nghĩa. Đôi khi chỉ cần tồn tại qua một ngày cũng đã là đủ rồi." },
];

function CinematicBg({ dark }: { dark: boolean }) {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Main background image */}
      <div
        className={`absolute inset-0 transition-all duration-500 ${dark ? "brightness-60 saturate-95" : "brightness-92 saturate-105"
          }`}
        style={{
          backgroundImage: `url(${beachBackgroundImage})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      />

      {/* Sun/glow overlay */}
      <div
        className={`absolute w-3/5 h-20 transition-all duration-1000 blur-3xl ${dark
          ? "bottom-2/5 left-1/2 -translate-x-1/2 from-blue-400/8"
          : "bottom-1/3 left-1/2 -translate-x-1/2 from-yellow-300/35"
          }`}
      />

      {/* Sun circle */}
      <div
        className={`absolute rounded-full transition-all duration-1000 ${dark
          ? "w-9 h-9 bottom-2/5 blur-sm left-1/2 -translate-x-1/2"
          : "w-14 h-14 bottom-1/3 blur-sm left-1/2 -translate-x-1/2"
          }`}
        style={{
          background: dark
            ? "radial-gradient(circle, rgba(180,210,240,0.2), transparent)"
            : "radial-gradient(circle, rgba(255,230,160,0.9) 30%, rgba(255,180,80,0.5) 70%, transparent)",
        }}
      />

      {/* Left ambient light */}
      <div
        className={`absolute bottom-1/3 left-2/5 w-1/5 h-28 transition-all duration-1000 blur-lg ${dark
          ? "bg-linear-to-b from-blue-400/6 to-transparent"
          : "bg-linear-to-b from-yellow-200/22 to-transparent"
          }`}
      />

      {/* Bottom gradient fade */}
      <div
        className={`absolute bottom-0 left-0 right-0 h-2/5 transition-all duration-1000 ${dark
          ? "bg-linear-to-b from-transparent via-slate-900/50 to-slate-950/90"
          : "bg-linear-to-b from-transparent via-blue-900/50 to-blue-950/75"
          }`}
      />

      {/* Bottom sand layer */}
      <div
        className={`absolute bottom-0 left-0 right-0 h-12 ${dark
          ? "bg-linear-to-b from-transparent to-slate-950/90"
          : ""
          }`}
      />
    </div>
  );
}

function FloatingBottle({ dark, onClick, isClicked }: { dark: boolean; onClick: () => void; isClicked: boolean }) {
  const rC = dark ? "rgba(110,170,205," : "rgba(70,140,175,";
  return (
    <div
      onClick={onClick}
      className="relative flex flex-col items-center cursor-pointer select-none"
    >
      <svg
        viewBox="0 0 340 70"
        className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-96 h-20 overflow-visible pointer-events-none z-0"
      >
        <ellipse
          cx="170"
          cy="38"
          rx="90"
          ry="12"
          fill={dark ? "rgba(0,0,0,0.30)" : "rgba(0,0,0,0.15)"}
          style={{
            animation: "bottleShadow 4.4s ease-in-out infinite",
            transformOrigin: "170px 38px",
          }}
        />
        {[
          { rx: 82, ry: 14, d: "0s" },
          { rx: 112, ry: 19, d: "0.9s" },
          { rx: 144, ry: 24, d: "1.8s" },
          { rx: 178, ry: 30, d: "2.7s" },
        ].map((r, i) => (
          <ellipse
            key={i}
            cx="170"
            cy="38"
            rx={r.rx}
            ry={r.ry}
            fill="none"
            stroke={`${rC}${0.44 - i * 0.09})`}
            strokeWidth={1.4 - i * 0.15}
            style={{
              animation: "rippleExpand 3.6s ease-out infinite",
              animationDelay: r.d,
              transformOrigin: "170px 38px",
            }}
          />
        ))}
      </svg>

      <div
        className={`relative z-10 mb-7 transition-transform duration-350 ease-out`}
        style={{
          animation: isClicked ? "none" : "bottleFloat 4.4s ease-in-out infinite",
          transform: isClicked ? "scale(0.93) translateY(5px)" : "scale(1) translateY(0)",
        }}
      >
        <img
          src={paperBoatImage}
          alt="Thuyền giấy"
          className={`w-72 h-auto display block ${dark
            ? "drop-shadow-2xl brightness-92 sepia-5"
            : "drop-shadow-2xl brightness-102"
            }`}
        />
      </div>
    </div>
  );
}

function LetterOverlay({ letter, onClose, dark }: { letter: Letter; onClose: () => void; dark: boolean }) {
  const ui = getUi(dark);
  const [replyOpen, setReplyOpen] = useState(false);
  const [reply, setReply] = useState("");
  const [sent, setSent] = useState(false);
  const areaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (replyOpen) areaRef.current?.focus();
  }, [replyOpen]);

  return (
    <div
      onClick={(e: ReactMouseEvent<HTMLDivElement>) =>
        e.target === e.currentTarget && onClose()
      }
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${ui.overlay} backdrop-blur-2xl`}
      style={{ animation: "fadeIn 0.45s ease" }}
    >
      <div
        className={`${ui.glassLight} border w-full max-w-xl rounded-2xl backdrop-blur-2xl`}
        style={{ animation: "letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both" }}
      >
        {/* Header */}
        <div className={`border-b ${ui.glassBorder} px-8 py-7 flex justify-between items-start`}>
          <div>
            <p
              className={`${ui.textSubtler} font-display text-xs font-bold uppercase tracking-wide mb-2`}
            >
              Lá thư từ biển khơi
            </p>
            <p className={`${ui.textPrimary} font-display text-lg font-semibold`}>
              {letter.from}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span className={`${ui.textSubtler} italic text-xs`}>
              {letter.time}
            </span>
            <button
              type="button"
              onClick={onClose}
              className={`${ui.textSubtle} bg-none border-none cursor-pointer p-1 flex hover:opacity-70 transition-opacity`}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-8 py-7">
          <p
            className={`${ui.textPrimary} font-display text-lg italic  leading-relaxed tracking-[.5px]`}
          >
            {letter.body}
          </p>
        </div>

        {/* Footer */}
        <div className={`px-8 py-7 border-t ${ui.glassBorder}`}>
          {!sent ? (
            !replyOpen ? (
              <div className="mt-5 flex gap-3">
                <button
                  type="button"
                  onClick={() => setReplyOpen(true)}
                  className={`flex-1 bg-none border rounded-xl py-2.5 px-0 font-display tracking-wide cursor-pointer transition-all`}
                  style={{
                    borderColor: dark ? "rgba(242,235,224,0.13)" : "rgba(18,30,40,0.18)",
                    color: dark ? "rgba(242,235,224,0.45)" : "rgba(20,26,33,0.7)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = dark
                      ? "rgba(242,235,224,0.92)"
                      : "rgba(20,26,33,0.92)";
                    e.currentTarget.style.borderColor = "rgba(111,190,214,0.68)";
                    e.currentTarget.style.background = "rgba(111,190,214,0.12)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = dark
                      ? "rgba(242,235,224,0.45)"
                      : "rgba(20,26,33,0.45)";
                    e.currentTarget.style.borderColor = dark
                      ? "rgba(242,235,224,0.13)"
                      : "rgba(18,30,40,0.18)";
                    e.currentTarget.style.background = "none";
                  }}
                >
                  Trả lời thư
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className={`flex-1 bg-none border rounded-xl py-2.5 px-0 font-display  font-semibold tracking-wide cursor-pointer transition-all`}
                  style={{
                    borderColor: dark ? "rgba(242,235,224,0.13)" : "rgba(18,30,40,0.18)",
                    color: dark ? "rgba(242,235,224,0.45)" : "rgba(20,26,33,0.7)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = dark
                      ? "rgba(242,235,224,0.92)"
                      : "rgba(20,26,33,0.92)";
                    e.currentTarget.style.borderColor = "rgba(111,190,214,0.68)";
                    e.currentTarget.style.background = "rgba(111,190,214,0.12)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = dark
                      ? "rgba(242,235,224,0.45)"
                      : "rgba(20,26,33,0.45)";
                    e.currentTarget.style.borderColor = dark
                      ? "rgba(242,235,224,0.13)"
                      : "rgba(18,30,40,0.18)";
                    e.currentTarget.style.background = "none";
                  }}
                >
                  Đẩy thuyền trôi đi
                </button>
              </div>
            ) : (
              <div
                className="mt-5"
                style={{ animation: "fadeUpCard 0.35s ease" }}
              >
                <textarea
                  ref={areaRef}
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="Viết hồi âm của bạn..."
                  rows={3}
                  className={`w-full rounded-xl p-4 font-display text-lg italic font-light leading-relaxed resize-none outline-none transition-colors`}
                  style={{
                    backgroundColor: dark ? "rgba(242,235,224,0.05)" : "rgb(255,255,255)",
                    borderColor: dark ? "rgba(242,235,224,0.13)" : "rgba(18,30,40,0.18)",
                    color: dark ? "rgb(255,255,255)" : "rgb(15,23,42)",
                    border: `1px solid ${dark ? "rgba(242,235,224,0.13)" : "rgba(18,30,40,0.18)"}`,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = dark
                      ? "rgba(242,235,224,0.92)"
                      : "rgba(20,26,33,0.92)";
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = dark
                      ? "rgba(242,235,224,0.13)"
                      : "rgba(18,30,40,0.18)";
                  }}
                />
                <div className="flex justify-between items-center mt-2.5">
                  <button
                    type="button"
                    onClick={() => {
                      setReplyOpen(false);
                      setReply("");
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: dark ? "rgba(242,235,224,0.55)" : "rgba(20,26,33,0.56)",
                    }}
                    className={` text-xs cursor-pointer tracking-wide`}
                  >
                    Huỷ
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (reply.trim()) {
                        setSent(true);
                        setTimeout(onClose, 2000);
                      }
                    }}
                    disabled={!reply.trim()}
                    style={{
                      background: reply.trim()
                        ? "linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)"
                        : "none",
                      border: `1px solid ${reply.trim()
                        ? "rgba(111,190,214,0.68)"
                        : dark
                          ? "rgba(242,235,224,0.13)"
                          : "rgba(18,30,40,0.18)"
                        }`,
                      color: reply.trim()
                        ? "#ffffff"
                        : dark
                          ? "rgba(242,235,224,0.45)"
                          : "rgba(20,26,33,0.45)",
                      cursor: reply.trim() ? "pointer" : "default",
                    }}
                    className={`px-6 py-2 rounded-lg font-display text-sm italic transition-all`}
                    onMouseEnter={(e) => {
                      if (reply.trim()) {
                        e.currentTarget.style.background =
                          "linear-gradient(135deg,#77e0ce 0%,#67afd9 100%)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (reply.trim()) {
                        e.currentTarget.style.background =
                          "linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)";
                      }
                    }}
                  >
                    Thả về biển
                  </button>
                </div>
              </div>
            )
          ) : (
            <div
              className="mt-5 text-center py-3"
              style={{ animation: "fadeUpCard 0.5s ease" }}
            >
              <p className={`${ui.textSubtle} font-display text-base italic font-light`}>
                Hồi âm đã trôi ra biển khơi...
              </p>
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
    <div
      onClick={(e: ReactMouseEvent<HTMLDivElement>) =>
        e.target === e.currentTarget && onClose()
      }
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${ui.overlay} backdrop-blur-2xl`}
      style={{ animation: "fadeIn 0.45s ease" }}
    >
      <div
        className={`${ui.glassLight} border w-full max-w-xl rounded-2xl backdrop-blur-2xl`}
        style={{ animation: "letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both" }}
      >
        {/* Header */}
        <div className={`border-b ${ui.glassBorder} px-8 py-7 flex justify-between items-start`}>
          <div>
            <p
              className={`${ui.textSubtler} text-lg font-light uppercase tracking-wider mb-2`}
            >
              Viết lá thư của bạn
            </p>
            <p className={`${ui.textSubtle} font-display text-base italic font-light`}>
              Lá thư sẽ trôi đến tay một người xa lạ
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: dark ? "rgba(242,235,224,0.45)" : "rgba(20,26,33,0.45)",
            }}
            className={`p-1 flex hover:opacity-70 transition-opacity`}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-8 py-7">
          {!sent ? (
            <>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Hôm nay bạn muốn chia sẻ điều gì..."
                rows={6}
                autoFocus
                className={`w-full rounded-3xl p-4 font-display text-lg italic font-light leading-relaxed resize-none outline-none transition-colors`}
                style={{
                  backgroundColor: dark ? "rgba(242,235,224,0.05)" : "rgb(255,255,255)",
                  borderColor: dark ? "rgba(242,235,224,0.13)" : "rgba(18,30,40,0.18)",
                  color: dark ? "rgb(255,255,255)" : "rgb(15,23,42)",
                  border: `1px solid ${dark ? "rgba(242,235,224,0.13)" : "rgba(18,30,40,0.18)"}`,
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = dark
                    ? "rgba(242,235,224,0.92)"
                    : "rgba(20,26,33,0.92)";
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = dark
                    ? "rgba(242,235,224,0.13)"
                    : "rgba(18,30,40,0.18)";
                }}
              />
              <div className="flex justify-end mt-3.5">
                <button
                  type="button"
                  onClick={() => {
                    if (text.trim()) {
                      setSent(true);
                      setTimeout(onClose, 2200);
                    }
                  }}
                  disabled={!text.trim()}
                  style={{
                    background: text.trim()
                      ? "linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)"
                      : "none",
                    border: `1px solid ${text.trim()
                      ? "rgba(111,190,214,0.68)"
                      : dark
                        ? "rgba(242,235,224,0.13)"
                        : "rgba(18,30,40,0.18)"
                      }`,
                    color: text.trim()
                      ? "#ffffff"
                      : dark
                        ? "rgba(242,235,224,0.45)"
                        : "rgba(20,26,33,0.45)",
                    cursor: text.trim() ? "pointer" : "default",
                  }}
                  className={`px-8 py-2.5 rounded-3xl font-display text-base italic transition-all`}
                  onMouseEnter={(e) => {
                    if (text.trim()) {
                      e.currentTarget.style.background =
                        "linear-gradient(135deg,#77e0ce 0%,#67afd9 100%)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (text.trim()) {
                      e.currentTarget.style.background =
                        "linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)";
                    }
                  }}
                >
                  Thả ra biển
                </button>
              </div>
            </>
          ) : (
            <div
              className="text-center py-6"
              style={{ animation: "fadeUpCard 0.6s ease" }}
            >
              <p className={`${ui.textSubtle} font-display text-lg italic font-light leading-relaxed`}>
                Lá thư đã trôi ra biển khơi...
                <br />
                <span className={`${ui.textSubtler} text-xs font-normal uppercase tracking-wide`}>
                  Ai đó sẽ nhận được tâm tình của bạn
                </span>
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

  return (
    <div className="h-screen overflow-hidden ">
      <style>{ANIMATIONS_CSS}</style>
      <FontLink />
      <CinematicBg dark={dark} />

      {/* Navigation */}
      <nav
        className={`relative z-10 flex items-center justify-center px-8 py-4.5  ${ui.glassBorder} backdrop-blur-md`}
      >
        <div className="flex gap-24">
          {[
            { id: "beach", label: "Bến thư" },
            { id: "community", label: "Kho thư" },
          ].map((t) => (
            <button
              type="button"
              key={t.id}
              onClick={() => setTab(t.id as TabId)}
              style={{
                background: "none",
                border: "none",
                borderBottom: `2px solid ${tab === t.id
                  ? dark
                    ? "rgb(255,255,255)"
                    : "rgb(15,23,42)"
                  : dark
                    ? "rgba(242,235,224,0.45)"
                    : "rgba(20,26,33,0.45)"
                  }`,
                color:
                  tab === t.id
                    ? dark
                      ? "rgb(255,255,255)"
                      : "rgb(15,23,42)"
                    : dark
                      ? "rgba(242,235,224,0.45)"
                      : "rgba(20,26,33,0.45)",
                marginBottom: "-1px",
              }}
              className={`py-1.5 px-4 text-lg font-display font-semibold tracking-wide cursor-pointer transition-all`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Beach Tab */}
      {tab === "beach" && (
        <div className="relative z-10 flex flex-col items-center min-h-[calc(100vh-64px)] pt-20 pb-16">
          <div
            className="text-center mb-16"
            style={{ animation: "fadeUp 1s ease 0.1s both" }}
          >
            <h1
              className={`${ui.textPrimary} font-display text-5xl italic font-normal leading-snug drop-shadow-xl`}
              style={{
                textShadow: dark
                  ? "0 2px 18px rgba(0,0,0,0.45)"
                  : "0 2px 12px rgba(255,255,255,0.38)",
              }}
            >
              {hasBottle ? "Có một lá thư đang chờ bạn" : "Chưa có thư mới"}
            </h1>
          </div>

          {hasBottle ? (
            <div
              className="flex flex-col items-center gap-6"
              style={{ animation: "fadeUp 1s ease 0.3s both" }}
            >
              <FloatingBottle dark={dark} onClick={handleBottle} isClicked={ripple} />
              <p
                className={`text-white font-display font-semibold tracking-widest uppercase mt-2 animate-pulse`}
              >
                Chạm để xem
              </p>
            </div>
          ) : (
            <div
              className="text-center"
              style={{ animation: "fadeUp 1s ease 0.3s both" }}
            >
              <p
                className={`${ui.textPrimary} font-display text-2xl italic font-normal leading-relaxed`}
                style={{ opacity: dark ? 0.78 : 0.88 }}
              >
                Biển đang lặng, chưa có thư trôi đến.
              </p>
            </div>
          )}

          <div
            className="flex flex-col items-center gap-4 mt-16"
            style={{ animation: "fadeUp 1s ease 0.5s both" }}
          >
            <button
              type="button"
              onClick={() => setShowWrite(true)}
              className={`
                border rounded-full px-10 py-3 font-display text-2xl font-semibold cursor-pointer transition-all
                ${dark
                  ? "bg-white/10 border-white/45 text-white/95 shadow-[0_10px_24px_rgba(0,0,0,0.28)]"
                  : "bg-white/80 border-slate-900/30 text-slate-900/90 shadow-[0_8px_20px_rgba(20,40,56,0.18)]"
                }
                hover:bg-cyan-400/25 hover:border-cyan-400/85 hover:text-white hover:shadow-[0_12px_28px_rgba(66,153,180,0.42)] hover:-translate-y-px
              `}
            >
              Viết lá thư của bạn
            </button>
          </div>
        </div>
      )}

      {/* Community Tab */}
      {tab === "community" && (
        <div
          className="relative z-10 max-w-2xl mx-auto px-6 py-16 pb-20"
          style={{ animation: "fadeUp 0.8s ease both" }}
        >
          <div className="mb-10">
            <h2
              className={`${ui.textPrimary} font-display text-4xl italic font-normal`}
              style={{
                textShadow: dark
                  ? "0 2px 16px rgba(0,0,0,0.36)"
                  : "0 2px 10px rgba(255,255,255,0.35)",
              }}
            >
              Kho thư cộng đồng
            </h2>
          </div>

          <div className="flex flex-col gap-4">
            {LETTERS.map((l, i) => (
              <div
                key={l.id}
                onClick={() => setOpenLetter(l)}
                className={`${ui.glassLight} border rounded-2xl p-6 cursor-pointer transition-all hover:bg-opacity-70 hover:border-opacity-80`}
                style={{ animation: `fadeUpCard 0.6s ease ${i * 0.1}s both` }}
              >
                <div className="flex justify-between items-start mb-3">
                  <p className={`${ui.textSubtle} font-display text-sm font-semibold tracking-wide`}>
                    {l.from}
                  </p>
                  <p className={`${ui.textSubtler}  text-xs`}>
                    {l.time}
                  </p>
                </div>
                <p
                  className={`${ui.textSubtle} font-display text-lg italic leading-relaxed mb-3 line-clamp-3`}
                >
                  {l.body}
                </p>
                <p className={`${ui.textSubtler} text-xs tracking-wider `}>
                  Nhấn để đọc & hồi âm →
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Overlays */}
      {openLetter && (
        <LetterOverlay letter={openLetter} onClose={() => setOpenLetter(null)} dark={dark} />
      )}
      {showWrite && <WriteOverlay onClose={() => setShowWrite(false)} dark={dark} />}
    </div>
  );
}
