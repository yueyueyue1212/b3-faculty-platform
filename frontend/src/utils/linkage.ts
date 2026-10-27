export type CollegeDisciplineMap = Record<string, string[]>

/**
 * Disciplines that belong to the selected college.
 *
 * Before a college is chosen the dependent select is intentionally empty; the
 * current value is kept only when editing an older record whose pair is not in
 * the current option mapping yet.
 */
export function disciplinesForCollege(
  mapping: CollegeDisciplineMap | undefined,
  college: string,
  current = '',
): string[] {
  if (!college) return []
  const values = mapping?.[college] ?? []
  if (current && !values.includes(current)) return [current, ...values]
  return values
}
