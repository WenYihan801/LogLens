import { useState } from "react";

import { Button, ErrorMessage, NeutralBadge } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { useConfig } from "../../hooks/configContext";
import { api } from "../../services/api";
import type { UploadResult } from "../../types/api";

export function SampleLoader({ onLoaded }: { onLoaded: (r: UploadResult) => void }) {
  const { read_only } = useConfig();
  const { data: samples, error } = useAsync(() => api.samples(), []);
  const [busy, setBusy] = useState<string>();
  const [loadError, setLoadError] = useState<unknown>();

  if (error) return <ErrorMessage error={error} />;
  if (!samples?.length) return null;

  const load = async (key: string) => {
    setBusy(key);
    setLoadError(undefined);
    try {
      onLoaded(await api.loadSample(key));
    } catch (e) {
      setLoadError(e);
    } finally {
      setBusy(undefined);
    }
  };

  return (
    <div className="space-y-3">
      {loadError != null && <ErrorMessage error={loadError} />}
      <ul className="grid gap-3 sm:grid-cols-2">
        {samples.map((s) => (
          <li key={s.key} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
                {s.name} <NeutralBadge>{s.source_type}</NeutralBadge>
              </div>
              <p className="mt-0.5 text-xs text-slate-500">{s.description}</p>
            </div>
            <Button
              variant="primary"
              onClick={() => load(s.key)}
              disabled={read_only || busy !== undefined}
              title={read_only ? "Disabled in the read-only demo" : undefined}
            >
              {busy === s.key ? "Loading…" : "Load"}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
