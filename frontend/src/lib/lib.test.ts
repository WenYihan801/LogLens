import { buildQuery } from "../services/api";
import { formatBytes, formatDuration, localInputToIso } from "./format";
import { validateFileClientSide } from "./validation";

describe("buildQuery", () => {
  it("drops empty values and encodes the rest", () => {
    expect(buildQuery({ a: "1", b: "", c: undefined, d: null, q: "a b&c" })).toBe("?a=1&q=a+b%26c");
  });
  it("returns empty string when nothing is set", () => {
    expect(buildQuery({ a: "" })).toBe("");
  });
});

describe("format helpers", () => {
  it("formats bytes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.00 MB");
  });
  it("formats durations", () => {
    expect(formatDuration(45)).toBe("45s");
    expect(formatDuration(300)).toBe("5m");
    expect(formatDuration(125)).toBe("2m 5s");
    expect(formatDuration(3720)).toBe("1h 2m");
  });
  it("converts datetime-local input to UTC ISO", () => {
    const iso = localInputToIso("2026-11-03T10:00");
    expect(iso).toMatch(/Z$/);
    expect(new Date(iso!).getTime()).toBe(new Date("2026-11-03T10:00").getTime());
    expect(localInputToIso("")).toBeUndefined();
  });
});

describe("validateFileClientSide", () => {
  const f = (name: string, size: number) => new File(["x".repeat(size)], name);
  it("accepts .log and .txt", () => {
    expect(validateFileClientSide(f("a.log", 10), 5)).toBeNull();
    expect(validateFileClientSide(f("A.TXT", 10), 5)).toBeNull();
  });
  it("rejects other extensions, empty and oversized files", () => {
    expect(validateFileClientSide(f("a.exe", 10), 5)).toMatch(/Only/);
    expect(validateFileClientSide(f("a.log", 0), 5)).toMatch(/empty/);
    expect(validateFileClientSide(f("a.log", 2 * 1024 * 1024), 1)).toMatch(/limit/);
  });
});
