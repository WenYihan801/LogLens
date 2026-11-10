import { api } from "../services/api";
import { useAsync } from "../hooks/useAsync";
import { inputCls } from "../lib/styles";

export function DatasetSelect({
  value,
  onChange,
  id = "dataset-select",
}: {
  value: string;
  onChange: (id: string) => void;
  id?: string;
}) {
  const { data } = useAsync(() => api.datasets(), []);
  return (
    <label htmlFor={id} className="flex items-center gap-2 text-sm text-slate-600">
      <span className="font-medium">Dataset</span>
      <select id={id} className={inputCls} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">All datasets</option>
        {data?.map((d) => (
          <option key={d.id} value={d.id}>
            {d.name} ({d.source_type})
          </option>
        ))}
      </select>
    </label>
  );
}
