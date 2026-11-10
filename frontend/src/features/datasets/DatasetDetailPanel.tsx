import { useState } from "react";
import { Link } from "react-router-dom";

import { Button, EmptyState, ErrorMessage, KeyValue, NeutralBadge, Spinner } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { useConfig } from "../../hooks/configContext";
import { formatBytes, formatDateTime } from "../../lib/format";
import { api } from "../../services/api";
import type { DetectionRunResult } from "../../types/api";

export function DatasetDetailPanel({ id, onChanged, onDeleted }: { id: string; onChanged: () => void; onDeleted: () => void }) {
  const { read_only } = useConfig();
  const { data: d, error, loading, reload } = useAsync(() => api.dataset(id), [id]);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<unknown>();
  const [rerun, setRerun] = useState<DetectionRunResult>();

  if (loading && !d) return <Spinner />;
  if (error) return <ErrorMessage error={error} onRetry={reload} />;
  if (!d) return null;

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setActionError(undefined);
    try {
      await fn();
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <KeyValue
        items={[
          ["Name", d.name],
          ["Source type", <NeutralBadge key="t">{d.source_type}</NeutralBadge>],
          ["Original file", d.original_filename],
          ["Size", formatBytes(d.size_bytes)],
          ["SHA-256", <span key="h" className="font-mono text-xs">{d.file_sha256}</span>],
          ["Imported", formatDateTime(d.created_at)],
          ["Status", d.status + (d.status_message ? ` — ${d.status_message}` : "")],
          ["Lines (non-blank)", d.total_lines.toLocaleString()],
          ["Parsed", d.parsed_lines.toLocaleString()],
          ["Failed", d.failed_lines.toLocaleString()],
          ["Ignored by rules", `${d.detection_skipped} (no source IP)`],
          ["Alerts", d.alert_count],
        ]}
      />

      <div className="flex flex-wrap gap-2">
        <Link to={`/events?dataset=${d.id}`} className="text-sm font-medium text-sky-700 hover:underline">
          Browse events →
        </Link>
        <Link to={`/alerts?dataset=${d.id}`} className="text-sm font-medium text-sky-700 hover:underline">
          View alerts →
        </Link>
      </div>

      {!read_only && (
        <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
          <Button
            disabled={busy}
            onClick={() =>
              run(async () => {
                setRerun(await api.rerunDetection(d.id));
                reload();
                onChanged();
              })
            }
          >
            Re-run detection
          </Button>
          {!confirming ? (
            <Button variant="danger" disabled={busy} onClick={() => setConfirming(true)}>
              Delete dataset
            </Button>
          ) : (
            <>
              <span className="text-sm text-red-700">Delete events, alerts, notes and errors?</span>
              <Button
                variant="danger"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    await api.deleteDataset(d.id);
                    onDeleted();
                  })
                }
              >
                Confirm delete
              </Button>
              <Button variant="ghost" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
            </>
          )}
        </div>
      )}
      {rerun && (
        <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Detection re-run: {rerun.alerts_total} alerts ({rerun.created} new, {rerun.updated} unchanged/updated,{" "}
          {rerun.removed} removed). Existing alert status and notes are preserved.
        </p>
      )}
      {actionError != null && <ErrorMessage error={actionError} />}

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-800">Import errors</h3>
        {Object.keys(d.error_summary).length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {Object.entries(d.error_summary).map(([code, n]) => (
              <NeutralBadge key={code}>
                {code}: {n}
              </NeutralBadge>
            ))}
          </div>
        )}
        {d.import_errors.length === 0 ? (
          <EmptyState title="No import errors" icon="✓">
            Every non-blank line was parsed successfully.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="text-slate-500">
                <tr>
                  <th className="py-1.5 pr-3 font-medium">Line</th>
                  <th className="py-1.5 pr-3 font-medium">Code</th>
                  <th className="py-1.5 pr-3 font-medium">Reason / preview</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 align-top">
                {d.import_errors.map((e) => (
                  <tr key={e.id}>
                    <td className="py-1.5 pr-3 tabular-nums">{e.line_number}</td>
                    <td className="py-1.5 pr-3 font-mono">{e.error_code}</td>
                    <td className="py-1.5 pr-3">
                      <div className="text-slate-700">{e.error_message}</div>
                      <code className="mt-0.5 block break-all text-slate-500">{e.raw_preview}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {d.import_errors_truncated && (
              <p className="mt-2 text-xs text-slate-500">Showing the first {d.import_errors.length} errors.</p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
