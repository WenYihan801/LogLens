import { useRef, useState, type FormEvent } from "react";

import { Button, ErrorMessage, Field } from "../../components/ui";
import { inputCls } from "../../lib/styles";
import { useConfig } from "../../hooks/configContext";
import { validateFileClientSide } from "../../lib/validation";
import { api } from "../../services/api";
import type { UploadResult } from "../../types/api";

export function UploadForm({ onUploaded }: { onUploaded: (r: UploadResult) => void }) {
  const { read_only, max_upload_size_mb, max_log_lines } = useConfig();
  const [file, setFile] = useState<File | null>(null);
  const [sourceType, setSourceType] = useState("AUTO");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    const problem = validateFileClientSide(file, max_upload_size_mb);
    if (problem) {
      setError(new Error(problem));
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      const r = await api.upload(file, sourceType, name.trim() || undefined);
      setFile(null);
      setName("");
      if (inputRef.current) inputRef.current.value = "";
      onUploaded(r);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  if (read_only) {
    return (
      <p className="text-sm text-slate-500">
        Uploads are disabled in the public read-only demo. Clone the repository and run it locally to import your own logs.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4" aria-label="Upload log file">
      <div className="grid gap-4 md:grid-cols-[2fr_1fr_1.5fr_auto] md:items-end">
        <Field label="Log file (.log / .txt)" htmlFor="upload-file">
          <input
            id="upload-file"
            ref={inputRef}
            type="file"
            accept=".log,.txt,text/plain"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setError(undefined);
            }}
            className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
          />
        </Field>
        <Field label="Log type" htmlFor="upload-type">
          <select id="upload-type" className={inputCls} value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
            <option value="AUTO">Auto-detect</option>
            <option value="NGINX">Nginx access log</option>
            <option value="SSH">SSH auth log</option>
          </select>
        </Field>
        <Field label="Display name (optional)" htmlFor="upload-name">
          <input
            id="upload-name"
            className={inputCls}
            value={name}
            maxLength={150}
            onChange={(e) => setName(e.target.value)}
            placeholder={file?.name ?? "e.g. web-01 access log"}
          />
        </Field>
        <Button type="submit" variant="primary" disabled={!file || busy}>
          {busy ? "Processing…" : "Upload & analyse"}
        </Button>
      </div>
      <p className="text-xs text-slate-500">
        Max {max_upload_size_mb} MB and {max_log_lines.toLocaleString()} lines. The file is validated, parsed and
        discarded — only the parsed events are stored. Use synthetic or properly anonymised data.
      </p>
      {error != null && <ErrorMessage error={error} />}
    </form>
  );
}
