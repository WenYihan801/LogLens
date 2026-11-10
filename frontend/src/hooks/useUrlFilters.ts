import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * Filters + page number stored in the URL query string, so a filtered view can
 * be bookmarked/shared and exports use exactly what is on screen (FR-30).
 */
export function useUrlFilters<K extends string>(keys: readonly K[]) {
  const [params, setParams] = useSearchParams();

  const filters = useMemo(() => {
    const f = {} as Record<K, string>;
    for (const k of keys) f[k] = params.get(k) ?? "";
    return f;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, keys.join(",")]);

  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);

  const setFilters = useCallback(
    (next: Partial<Record<K, string>>) => {
      setParams((prev) => {
        const p = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(next) as [K, string | undefined][]) {
          if (v) p.set(k, v);
          else p.delete(k);
        }
        p.delete("page");
        return p;
      });
    },
    [setParams],
  );

  const setPage = useCallback(
    (n: number) =>
      setParams((prev) => {
        const p = new URLSearchParams(prev);
        if (n > 1) p.set("page", String(n));
        else p.delete("page");
        return p;
      }),
    [setParams],
  );

  const clear = useCallback(() => {
    setParams((prev) => {
      const p = new URLSearchParams();
      const ds = prev.get("dataset");
      if (ds) p.set("dataset", ds);
      return p;
    });
  }, [setParams]);

  return { filters, setFilters, page, setPage, clear };
}
