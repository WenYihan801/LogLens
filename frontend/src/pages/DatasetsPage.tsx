import { useState } from "react";
import { Link } from "react-router-dom";

import { Card, Drawer, EmptyState, ErrorMessage, NeutralBadge, PageHeader, Spinner } from "../components/ui";
import { cx } from "../lib/cx";
import { DatasetDetailPanel } from "../features/datasets/DatasetDetailPanel";
import { SampleLoader } from "../features/datasets/SampleLoader";
import { UploadForm } from "../features/datasets/UploadForm";
import { useAsync } from "../hooks/useAsync";
import { formatBytes, formatDateTime } from "../lib/format";
import { api } from "../services/api";
import type { DatasetStatus, UploadResult } from "../types/api";

const statusTone: Record<DatasetStatus, string> = {
  COMPLETED: "text-emerald-700",
  PROCESSING: "text-sky-700",
  PENDING: "text-slate-500",
  FAILED: "text-red-700",
};

export function DatasetsPage() {
  const { data, error, loading, reload } = useAsync(() => api.datasets(), []);
  const [selected, setSelected] = useState<string>();
  const [last, setLast] = useState<UploadResult>();

  const onImported = (r: UploadResult) => {
    setLast(r);
    reload();
  };

  return (
    <>
      <PageHeader title="Datasets" description="Each import becomes a dataset with its own processing summary, events and alerts." />
      <div className="space-y-6">
        <Card title="Import a log file">
          <UploadForm onUploaded={onImported} />
        </Card>

        {last && (
          <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-3 text-sm text-emerald-900">
            <strong>Import {last.status.toLowerCase()}</strong> — {last.source_type}: {last.total_lines.toLocaleString()} lines,{" "}
            {last.parsed_lines.toLocaleString()} parsed, {last.failed_lines.toLocaleString()} failed,{" "}
            <strong>{last.alerts_generated} alerts</strong> generated in {(last.processing_ms / 1000).toFixed(2)}s.
            {last.duplicate_of && " This file was imported before (same SHA-256)."}{" "}
            <Link className="font-medium underline" to={`/?dataset=${last.dataset_id}`}>
              Open dashboard
            </Link>
          </div>
        )}

        <Card title="Load a synthetic sample" subtitle="Generated data using documentation-only IP ranges (RFC 5737 / RFC 3849).">
          <SampleLoader onLoaded={onImported} />
        </Card>

        <Card title="Imported datasets" subtitle={data ? `${data.length} total` : undefined}>
          {error && <ErrorMessage error={error} onRetry={reload} />}
          {loading && !data && <Spinner />}
          {data && data.length === 0 && <EmptyState title="No datasets yet">Upload a file or load a sample above.</EmptyState>}
          {data && data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Name</th>
                    <th className="py-2 pr-4 font-medium">Type</th>
                    <th className="py-2 pr-4 text-right font-medium">Lines</th>
                    <th className="py-2 pr-4 text-right font-medium">Parsed</th>
                    <th className="py-2 pr-4 text-right font-medium">Failed</th>
                    <th className="py-2 pr-4 text-right font-medium">Alerts</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 pr-4 font-medium">Imported</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.map((d) => (
                    <tr key={d.id} className="hover:bg-slate-50">
                      <td className="py-2 pr-4">
                        <button type="button" className="text-left font-medium text-sky-700 hover:underline" onClick={() => setSelected(d.id)}>
                          {d.name}
                        </button>
                        <div className="text-xs text-slate-400">
                          {d.original_filename} · {formatBytes(d.size_bytes)}
                        </div>
                      </td>
                      <td className="py-2 pr-4">
                        <NeutralBadge>{d.source_type}</NeutralBadge>
                      </td>
                      <td className="py-2 pr-4 text-right tabular-nums">{d.total_lines.toLocaleString()}</td>
                      <td className="py-2 pr-4 text-right tabular-nums">{d.parsed_lines.toLocaleString()}</td>
                      <td className={cx("py-2 pr-4 text-right tabular-nums", d.failed_lines > 0 && "text-amber-700")}>
                        {d.failed_lines.toLocaleString()}
                      </td>
                      <td className="py-2 pr-4 text-right tabular-nums">
                        <Link to={`/alerts?dataset=${d.id}`} className="hover:underline">
                          {d.alert_count}
                        </Link>
                      </td>
                      <td className={cx("py-2 pr-4 text-xs font-semibold", statusTone[d.status])}>{d.status}</td>
                      <td className="whitespace-nowrap py-2 pr-4 text-slate-600">{formatDateTime(d.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Drawer open={!!selected} onClose={() => setSelected(undefined)} title="Dataset details">
        {selected && (
          <DatasetDetailPanel
            id={selected}
            onChanged={reload}
            onDeleted={() => {
              setSelected(undefined);
              setLast(undefined);
              reload();
            }}
          />
        )}
      </Drawer>
    </>
  );
}
