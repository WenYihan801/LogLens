import { formatBytes } from "./format";

export function validateFileClientSide(file: File, maxMb: number): string | null {
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (![".log", ".txt"].includes(ext)) return "Only .log and .txt files are supported.";
  if (file.size === 0) return "The selected file is empty.";
  if (file.size > maxMb * 1024 * 1024) return `The file is ${formatBytes(file.size)}; the limit is ${maxMb} MB.`;
  return null;
}
