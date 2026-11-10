import { useEffect, useState, type FormEvent } from "react";

import { Button, Field } from "../../components/ui";
import { inputCls } from "../../lib/styles";
import { localInputToIso } from "../../lib/format";

export const EVENT_FILTER_KEYS = ["dataset", "source_ip", "source_type", "status_code", "start", "end", "q"] as const;
export type EventFilterKey = (typeof EVENT_FILTER_KEYS)[number];
type Values = Record<EventFilterKey, string>;

/** Converts a UTC ISO string to the value format of <input type="datetime-local">. */
function isoToLocalInput(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function EventFilterBar({
  values,
  onApply,
  onClear,
}: {
  values: Values;
  onApply: (v: Partial<Values>) => void;
  onClear: () => void;
}) {
  // Draft keeps start/end in <input type="datetime-local"> format (local time);
  // the URL/API always holds UTC ISO strings.
  const toDraft = (v: Values): Values => ({ ...v, start: isoToLocalInput(v.start), end: isoToLocalInput(v.end) });
  const [draft, setDraft] = useState(() => toDraft(values));
  useEffect(() => setDraft(toDraft(values)), [values]);

  const set = (k: EventFilterKey) => (e: { target: { value: string } }) => setDraft((d) => ({ ...d, [k]: e.target.value }));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onApply({
      source_ip: draft.source_ip.trim(),
      source_type: draft.source_type,
      status_code: draft.status_code.trim(),
      start: localInputToIso(draft.start) ?? "",
      end: localInputToIso(draft.end) ?? "",
      q: draft.q.trim(),
    });
  };

  return (
    <form onSubmit={submit} aria-label="Event filters" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-7 lg:items-end">
      <Field label="Source IP" htmlFor="f-ip">
        <input id="f-ip" className={inputCls} value={draft.source_ip} onChange={set("source_ip")} placeholder="203.0.113.45" />
      </Field>
      <Field label="Log source" htmlFor="f-type">
        <select id="f-type" className={inputCls} value={draft.source_type} onChange={set("source_type")}>
          <option value="">Any</option>
          <option value="NGINX">NGINX</option>
          <option value="SSH">SSH</option>
        </select>
      </Field>
      <Field label="Status code" htmlFor="f-status">
        <input
          id="f-status"
          className={inputCls}
          inputMode="numeric"
          pattern="[1-5][0-9]{2}"
          title="HTTP status code, e.g. 404"
          value={draft.status_code}
          onChange={set("status_code")}
          placeholder="404"
        />
      </Field>
      <Field label="From (local time)" htmlFor="f-start">
        <input
          id="f-start"
          type="datetime-local"
          className={inputCls}
          value={draft.start}
          onChange={set("start")}
        />
      </Field>
      <Field label="To (local time)" htmlFor="f-end">
        <input
          id="f-end"
          type="datetime-local"
          className={inputCls}
          value={draft.end}
          onChange={set("end")}
        />
      </Field>
      <Field label="Path / user contains" htmlFor="f-q">
        <input id="f-q" className={inputCls} value={draft.q} onChange={set("q")} placeholder="wp-login" />
      </Field>
      <div className="flex gap-2">
        <Button type="submit" variant="primary">
          Apply
        </Button>
        <Button variant="ghost" onClick={onClear}>
          Reset
        </Button>
      </div>
    </form>
  );
}
