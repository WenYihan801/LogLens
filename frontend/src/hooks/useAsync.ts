import { useCallback, useEffect, useRef, useState } from "react";

export interface AsyncState<T> {
  data: T | undefined;
  error: Error | undefined;
  loading: boolean;
  reload: () => void;
}

/**
 * Minimal data-fetching hook: runs `fn` whenever `deps` change, ignores stale
 * responses, and exposes `reload` for manual refresh after mutations.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const callId = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  useEffect(() => {
    const id = ++callId.current;
    setLoading(true);
    setError(undefined);
    run()
      .then((d) => {
        if (id === callId.current) setData(d);
      })
      .catch((e: Error) => {
        if (id === callId.current) setError(e);
      })
      .finally(() => {
        if (id === callId.current) setLoading(false);
      });
  }, [run, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}
