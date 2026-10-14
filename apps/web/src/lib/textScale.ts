/**
 * The text-size setting. The stored choice stays 1 (standard) or 2 (larger text), because the layout switches (one column, fewer chart
 * labels, `[data-ts='2']` rules) key off it. "Larger text" is 1.5 times the standard sizes (it was twice until 2026-10-14): big enough to
 * read comfortably, and small enough that every screen still fits a phone. Use `textFactor` wherever a size is worked out in code.
 */
export const LARGER_TEXT = 1.5

export const textFactor = (textScale: 1 | 2): number => (textScale === 2 ? LARGER_TEXT : 1)
