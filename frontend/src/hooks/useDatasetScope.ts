import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

/** The selected dataset lives in the URL (?dataset=...) so it survives reloads
 *  and is shared by Dashboard, Events and Alerts (FR-16, BR-09). */
export function useDatasetScope(): [string, (id: string) => void] {
  const [params, setParams] = useSearchParams();
  const datasetId = params.get("dataset") ?? "";
  const setDatasetId = useCallback(
    (id: string) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (id) next.set("dataset", id);
          else next.delete("dataset");
          next.delete("page");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );
  return [datasetId, setDatasetId];
}
