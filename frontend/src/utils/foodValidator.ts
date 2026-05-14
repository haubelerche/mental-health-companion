/**
 * Food input validator v2 – HARDENED.
 *
 * Previous version used naive substring matching which caused false positives:
 *   - "khô" matched inside "không"
 *   - "hành" matched inside "thành"
 *   - Any long Vietnamese paragraph would pass.
 *
 * New strategy (defense-in-depth):
 *   1. WORD-BOUNDARY matching: split text → words, check exact word matches
 *   2. Separate STRONG vs WEAK keywords (ambiguous words need extra evidence)
 *   3. Multi-word phrases use phrase matching (still OK for multi-word)
 *   4. Length-based heuristics: long text = stricter food density requirement
 *   5. Non-food content detection: diary/emotional vent patterns → block
 *   6. Spam/injection/profanity filters remain
 */

// ─── STRONG food keywords (unambiguous – one match is enough) ─────────────────
// These words almost always mean food when used as a standalone word.
const STRONG_FOOD_WORDS = new Set([
  // Staples
  'cơm', 'xôi', 'phở', 'bún', 'mì', 'miến', 'cháo', 'nui', 'mỳ',
  'gạo',
  // Proteins
  'thịt', 'tôm', 'cua', 'mực', 'trứng', 'giò', 'nem', 'sườn',
  'protein', 'whey', 'chicken', 'beef', 'pork', 'fish', 'tofu',
  'sushi', 'sashimi', 'steak',
  // Vegetables
  'salad', 'khoai', 'nấm',
  // Fruits
  'chuối', 'xoài', 'smoothie',
  // Dairy
  'yogurt', 'cheese',
  // Snacks
  'pudding', 'cookie', 'chocolate', 'granola',
  // International
  'pizza', 'burger', 'pasta', 'sandwich', 'taco', 'hotdog',
  'kebab', 'curry', 'bibimbap', 'ramen', 'udon', 'dumpling',
])

// ─── WEAK food keywords (ambiguous – need ≥2 matches or short text) ───────────
// These words CAN mean food but also commonly appear in non-food contexts.
// "hành" = onion OR action; "nước" = water OR country; "khô" = jerky OR dry; etc.
const WEAK_FOOD_WORDS = new Set([
  'gà', 'bò', 'heo', 'lợn', 'cá', 'ốc',
  'chả', 'gan', 'tim', 'lòng', 'xương',
  'egg',
  'rau', 'canh', 'cải', 'bí', 'mướp', 'đậu',
  'hành', 'tỏi', 'ớt', 'gừng',
  'táo', 'cam', 'bưởi', 'dưa', 'nho', 'dâu', 'lê', 'ổi', 'vải',
  'berry', 'apple', 'banana', 'mango', 'orange', 'fruit',
  'sữa', 'milk', 'trà', 'nước', 'tea', 'coffee', 'juice',
  'kem', 'chè', 'kẹo', 'snack', 'hạt', 'khô', 'mứt', 'cake',
  'chiên', 'xào', 'hấp', 'nướng', 'luộc', 'kho', 'rim', 'om',
  'soup', 'lẩu', 'nấu', 'rang',
  'ăn', 'món', 'đĩa', 'tô', 'bát', 'chén', 'ly', 'cốc',
  'phần', 'suất', 'set', 'combo', 'menu',
  'muối', 'đường', 'dầu', 'mỡ', 'bơ', 'tương',
  'sauce', 'mayo', 'rice', 'noodle', 'wrap',
  'oat', 'bread',
])

// ─── Multi-word FOOD PHRASES (use phrase matching – unambiguous) ───────────────
const FOOD_PHRASES: string[] = [
  'bánh mì', 'bánh cuốn', 'bánh xèo', 'bánh canh', 'bánh tráng',
  'bánh ngọt', 'bánh bao', 'bánh chưng', 'bánh tét',
  'hủ tiếu', 'bún bò', 'bún chả', 'bún riêu', 'bún đậu',
  'yến mạch', 'ngũ cốc',
  'đậu hũ', 'đậu phụ', 'tàu hũ', 'thịt kho',
  'xà lách', 'rau muống', 'rau cải', 'bắp cải', 'súp lơ',
  'cà rốt', 'cà chua',
  'trái cây', 'thanh long', 'sầu riêng', 'sinh tố',
  'phô mai', 'sữa chua', 'sữa đậu nành', 'sữa hạt',
  'nước ép', 'nước dừa', 'nước mắm', 'cà phê',
  'tráng miệng', 'dim sum',
  'canh rau', 'cơm gà', 'cơm tấm', 'cơm sườn',
  'bữa sáng', 'bữa trưa', 'bữa tối', 'bữa ăn',
]

// ─── Single word "bánh" – strong when standalone ──────────────────────────────
// "bánh" by itself almost always means food
const SEMI_STRONG_WORDS = new Set(['bánh', 'bữa', 'lẩu'])

// ─── Spam patterns ────────────────────────────────────────────────────────────
const SPAM_PATTERNS: RegExp[] = [
  /https?:\/\//i,
  /www\./i,
  /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/,
  /(.)\1{4,}/,
  /^[\d\s.,]+$/,
  /[{}<>\\|`~]/,
  /\b(select|insert|update|delete|drop|alter)\b.*\b(from|into|table|where)\b/i,
  /<\s*script/i,
  /javascript:/i,
  /on\w+\s*=/i,
]

// ─── Profanity patterns ───────────────────────────────────────────────────────
const PROFANITY_PATTERNS: RegExp[] = [
  /\b(đ[éè]o|đ[ủu] m[áa]|đ[ịi]t|c[ặặ]c|l[ồô]n|đ[éè]o m[ẹe]|v[ãã]i|ngu|chó|đ[ồô] ng[ốo]c)\b/i,
  /\b(fuck|shit|bitch|ass|dick|cunt|damn|bastard|idiot|stupid|retard)\b/i,
]

// ─── Diary / emotional vent patterns (Vietnamese) ─────────────────────────────
// If the text matches multiple of these, it's likely a diary entry, not food.
const DIARY_PATTERNS: RegExp[] = [
  /cảm giác/i,
  /mệt mỏi/i,
  /áp lực/i,
  /buồn/i,
  /tủi thân/i,
  /chịu đựng/i,
  /cô đơn/i,
  /stress/i,
  /lo lắng/i,
  /suy nghĩ/i,
  /cố gắng/i,
  /cuộc sống/i,
  /khó khăn/i,
  /than thở/i,
  /im lặng/i,
  /một mình/i,
  /người khác/i,
  /thất bại/i,
  /đau khổ/i,
  /kiệt sức/i,
  /không thể/i,
  /chẳng thể/i,
  /tâm sự/i,
  /nỗi đau/i,
  /mất ngủ/i,
  /thức khuya/i,
]

// ═══════════════════════════════════════════════════════════════════════════════
export interface FoodValidationResult {
  isValid: boolean
  errorMessage: string | null
}

/**
 * Split Vietnamese text into a Set of individual word tokens (lowercase).
 * Vietnamese words are space-separated syllables.
 */
function textToWords(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .split(/[\s,;.!?:…\-–—/()"']+/)
      .map((w) => w.trim())
      .filter((w) => w.length > 0)
  )
}

/**
 * Count how many diary/emotional patterns the text matches.
 */
function countDiaryPatterns(text: string): number {
  return DIARY_PATTERNS.reduce((count, pattern) => count + (pattern.test(text) ? 1 : 0), 0)
}

/**
 * Count total food evidence (strong words + weak words + phrases).
 * Returns { strong, weak, phrase, total }.
 */
function countFoodEvidence(text: string, words: Set<string>) {
  const lower = text.toLowerCase()

  let strong = 0
  for (const w of words) {
    if (STRONG_FOOD_WORDS.has(w)) strong++
    if (SEMI_STRONG_WORDS.has(w)) strong++
  }

  let weak = 0
  for (const w of words) {
    if (WEAK_FOOD_WORDS.has(w)) weak++
  }

  let phrase = 0
  for (const p of FOOD_PHRASES) {
    if (lower.includes(p)) phrase++
  }

  return { strong, weak, phrase, total: strong + phrase }
}

// ─── Main validator ───────────────────────────────────────────────────────────
export function validateFoodInput(text: string): FoodValidationResult {
  const trimmed = text.trim()

  // 1. Length checks
  if (trimmed.length < 2) {
    return { isValid: false, errorMessage: 'Vui lòng nhập nội dung bữa ăn (ít nhất 2 ký tự).' }
  }
  if (trimmed.length > 2000) {
    return { isValid: false, errorMessage: 'Nội dung quá dài (tối đa 2000 ký tự).' }
  }

  // 2. Profanity
  if (PROFANITY_PATTERNS.some((p) => p.test(trimmed))) {
    return { isValid: false, errorMessage: 'Nội dung không phù hợp. Vui lòng chỉ ghi nhận thông tin bữa ăn.' }
  }

  // 3. Spam / injection
  if (SPAM_PATTERNS.some((p) => p.test(trimmed))) {
    return { isValid: false, errorMessage: 'Nội dung có vẻ không phải mô tả bữa ăn. Vui lòng nhập lại.' }
  }

  // 4. Diary / emotional vent detection
  const diaryScore = countDiaryPatterns(trimmed)
  if (diaryScore >= 3) {
    return {
      isValid: false,
      errorMessage: 'Đây có vẻ là tâm sự cá nhân chứ không phải mô tả bữa ăn 💙 Hãy nhập nội dung bữa ăn nhé! Ví dụ: "cơm gà, canh rau"',
    }
  }

  // 5. Word-boundary food keyword matching
  const words = textToWords(trimmed)
  const evidence = countFoodEvidence(trimmed, words)

  // 5a. At least one STRONG keyword or food PHRASE → pass (for short texts)
  if (evidence.total >= 1 && trimmed.length <= 300) {
    return { isValid: true, errorMessage: null }
  }

  // 5b. For longer texts (>300 chars): need stronger evidence
  if (trimmed.length > 300) {
    // Long text with strong food evidence → still need high density
    if (evidence.total >= 3) {
      return { isValid: true, errorMessage: null }
    }
    // Long text but weak evidence → suspicious
    if (evidence.total >= 1 && evidence.weak >= 2) {
      // Has some food words but text is very long — likely not a meal description
      return {
        isValid: false,
        errorMessage: 'Nội dung quá dài cho mô tả bữa ăn. Hãy ghi ngắn gọn: "cơm, canh, rau, trái cây"',
      }
    }
    return {
      isValid: false,
      errorMessage: 'Nội dung quá dài và không rõ là bữa ăn. Hãy mô tả ngắn gọn bữa ăn nhé!',
    }
  }

  // 5c. Short text but only WEAK keywords → need at least 2
  if (evidence.weak >= 2 && evidence.total === 0) {
    return { isValid: true, errorMessage: null }
  }

  // 5d. No food keywords at all
  return {
    isValid: false,
    errorMessage: 'Hmm, mình không nhận ra đây là đồ ăn 🤔 Hãy mô tả bữa ăn cụ thể hơn nhé! Ví dụ: "cơm gà, canh rau, trái cây"',
  }
}

// ─── Real-time typing hint ────────────────────────────────────────────────────
export function looksLikeFood(text: string): boolean {
  const trimmed = text.trim()
  if (trimmed.length < 2) return true
  if (SPAM_PATTERNS.some((p) => p.test(trimmed))) return false
  if (PROFANITY_PATTERNS.some((p) => p.test(trimmed))) return false

  // Warn early if it looks like a diary entry
  if (countDiaryPatterns(trimmed) >= 2) return false

  // Warn if text is getting long with no food words
  if (trimmed.length > 80) {
    const words = textToWords(trimmed)
    const evidence = countFoodEvidence(trimmed, words)
    if (evidence.total === 0 && evidence.weak < 2) return false
  }

  return true
}
