export interface SignEntry {
  /** The word/phrase to match in transcript text (lowercase) */
  word: string;
  /** ASL sign label displayed in the UI */
  label: string;
  /** Path to the video clip relative to /signs/ */
  videoFile: string;
}

export const SIGN_VOCABULARY: SignEntry[] = [
  { word: "hello", label: "HELLO", videoFile: "hello.mp4" },
  { word: "thank you", label: "THANK-YOU", videoFile: "thank-you.mp4" },
  { word: "please", label: "PLEASE", videoFile: "please.mp4" },
  { word: "yes", label: "YES", videoFile: "yes.mp4" },
  { word: "no", label: "NO", videoFile: "no.mp4" },
  { word: "help", label: "HELP", videoFile: "help.mp4" },
  { word: "sorry", label: "SORRY", videoFile: "sorry.mp4" },
  { word: "my name", label: "MY-NAME", videoFile: "my-name.mp4" },
  { word: "how are you", label: "HOW-ARE-YOU", videoFile: "how-are-you.mp4" },
  { word: "good", label: "GOOD", videoFile: "good.mp4" },
  { word: "bad", label: "BAD", videoFile: "bad.mp4" },
  { word: "understand", label: "UNDERSTAND", videoFile: "understand.mp4" },
  { word: "goodbye", label: "GOODBYE", videoFile: "goodbye.mp4" },
];

// Sort by word length descending so multi-word phrases match before single words
// e.g. "don't understand" matches before "understand"
const SORTED_VOCAB = [...SIGN_VOCABULARY].sort((a, b) => b.word.length - a.word.length);

/**
 * Scan text for known ASL vocabulary words.
 * Returns matching SignEntry items in the order they appear in the text.
 * Multi-word phrases are matched first to avoid partial matches.
 */
export function matchSigns(text: string): SignEntry[] {
  const lower = text.toLowerCase();
  const matches: { index: number; entry: SignEntry }[] = [];

  for (const entry of SORTED_VOCAB) {
    let searchFrom = 0;
    while (true) {
      const idx = lower.indexOf(entry.word, searchFrom);
      if (idx === -1) break;
      // Check word boundary: not preceded/followed by a letter
      const before = idx === 0 || !/[a-z]/.test(lower[idx - 1]);
      const after =
        idx + entry.word.length >= lower.length ||
        !/[a-z]/.test(lower[idx + entry.word.length]);
      if (before && after) {
        matches.push({ index: idx, entry });
      }
      searchFrom = idx + entry.word.length;
    }
  }

  // Deduplicate overlapping matches (longer phrase wins)
  matches.sort((a, b) => a.index - b.index);
  const result: SignEntry[] = [];
  let lastEnd = -1;
  for (const m of matches) {
    if (m.index >= lastEnd) {
      result.push(m.entry);
      lastEnd = m.index + m.entry.word.length;
    }
  }
  return result;
}
