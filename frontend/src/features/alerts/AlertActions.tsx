import { useState, type FormEvent } from "react";

import { Button, ErrorMessage } from "../../components/ui";
import { inputCls } from "../../lib/styles";
import { useConfig } from "../../hooks/configContext";
import { formatDateTime } from "../../lib/format";
import { api } from "../../services/api";
import type { AlertStatus, Note } from "../../types/api";

const STATUSES: AlertStatus[] = ["OPEN", "ACKNOWLEDGED", "RESOLVED"];

export function StatusControl({
  alertId,
  status,
  onChanged,
}: {
  alertId: string;
  status: AlertStatus;
  onChanged: () => void;
}) {
  const { read_only } = useConfig();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();

  const change = async (s: AlertStatus) => {
    setBusy(true);
    setError(undefined);
    try {
      await api.setAlertStatus(alertId, s);
      onChanged();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5" role="group" aria-label="Alert status">
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            disabled={busy || read_only || s === status}
            aria-pressed={s === status}
            onClick={() => change(s)}
            title={read_only ? "Disabled in the read-only demo" : undefined}
            className={
              s === status
                ? "rounded-md bg-slate-900 px-3 py-1 text-xs font-semibold text-white"
                : "rounded-md px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400 disabled:hover:bg-transparent"
            }
          >
            {s}
          </button>
        ))}
      </div>
      {error != null && <ErrorMessage error={error} />}
    </div>
  );
}

export function Notes({ alertId, notes, onAdded }: { alertId: string; notes: Note[]; onAdded: () => void }) {
  const { read_only } = useConfig();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(undefined);
    try {
      await api.addNote(alertId, text.trim());
      setText("");
      onAdded();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      {notes.length === 0 ? (
        <p className="text-sm text-slate-500">No investigation notes yet.</p>
      ) : (
        <ol className="space-y-3">
          {notes.map((n) => (
            <li key={n.id} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <div className="text-xs text-slate-500">{formatDateTime(n.created_at)}</div>
              {/* Rendered as plain text — never as HTML (NFR-06). */}
              <p className="mt-0.5 whitespace-pre-wrap break-words text-sm text-slate-800">{n.note}</p>
            </li>
          ))}
        </ol>
      )}
      {!read_only && (
        <form onSubmit={submit} className="space-y-2" aria-label="Add investigation note">
          <label htmlFor="note" className="sr-only">
            Investigation note
          </label>
          <textarea
            id="note"
            rows={3}
            maxLength={5000}
            className={`${inputCls} w-full`}
            placeholder="e.g. Source belongs to an external scanner; no successful login afterwards."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <Button type="submit" variant="primary" disabled={busy || !text.trim()}>
            {busy ? "Saving…" : "Add note"}
          </Button>
          {error != null && <ErrorMessage error={error} />}
        </form>
      )}
    </div>
  );
}
