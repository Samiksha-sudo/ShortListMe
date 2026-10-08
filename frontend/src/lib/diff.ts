export interface DiffPart {
  type: "same" | "add" | "del";
  text: string;
}

const tokens = (s: string) => s.split(/(\s+)/).filter(Boolean);

/** Word-level diff (longest common subsequence). Whitespace tokens travel with the words around them. */
export function diffWords(before: string, after: string): DiffPart[] {
  const a = tokens(before);
  const b = tokens(after);
  const lcs: number[][] = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i]![j] = a[i] === b[j] ? lcs[i + 1]![j + 1]! + 1 : Math.max(lcs[i + 1]![j]!, lcs[i]![j + 1]!);
    }
  }

  const parts: DiffPart[] = [];
  const push = (type: DiffPart["type"], text: string) => {
    const last = parts[parts.length - 1];
    if (last && last.type === type) last.text += text;
    else parts.push({ type, text });
  };

  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { push("same", a[i]!); i++; j++; }
    else if (lcs[i + 1]![j]! >= lcs[i]![j + 1]!) { push("del", a[i]!); i++; }
    else { push("add", b[j]!); j++; }
  }
  while (i < a.length) push("del", a[i++]!);
  while (j < b.length) push("add", b[j++]!);
  return parts;
}
