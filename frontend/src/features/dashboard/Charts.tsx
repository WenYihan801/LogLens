import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "../../components/ui";
import { formatBucket, formatDateTime } from "../../lib/format";
import type { CountItem, DashboardSummary } from "../../types/api";

const SEVERITY_COLORS: Record<string, string> = { HIGH: "#dc2626", MEDIUM: "#d97706", LOW: "#0284c7" };
const AXIS = { fontSize: 11, fill: "#64748b" };
const LEGEND = { fontSize: 12, paddingTop: 4 };

function statusColor(code: string): string {
  const n = Number(code);
  if (n >= 500) return "#b91c1c";
  if (n >= 400) return "#d97706";
  if (n >= 300) return "#0284c7";
  return "#059669";
}

function NoData() {
  return <EmptyState title="No data for this selection" icon="∅" />;
}

export function SeverityChart({ data }: { data: CountItem[] }) {
  if (data.every((d) => d.count === 0)) return <NoData />;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey="key" tick={AXIS} />
        <YAxis allowDecimals={false} tick={AXIS} />
        <Tooltip />
        <Legend wrapperStyle={LEGEND} payload={data.map((d) => ({ value: d.key, type: "square", color: SEVERITY_COLORS[d.key] }))} />
        <Bar dataKey="count" name="Alerts" radius={[4, 4, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.key} fill={SEVERITY_COLORS[d.key]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function StatusCodeChart({ data }: { data: CountItem[] }) {
  if (!data.length) return <NoData />;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey="key" tick={AXIS} />
        <YAxis allowDecimals={false} tick={AXIS} />
        <Tooltip />
        <Legend
          wrapperStyle={LEGEND}
          payload={[
            { value: "2xx", type: "square", color: "#059669" },
            { value: "3xx", type: "square", color: "#0284c7" },
            { value: "4xx", type: "square", color: "#d97706" },
            { value: "5xx", type: "square", color: "#b91c1c" },
          ]}
        />
        <Bar dataKey="count" name="Requests" radius={[4, 4, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.key} fill={statusColor(d.key)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TrendChart({ summary }: { summary: DashboardSummary }) {
  const data = summary.activity_trend;
  if (!data.length) return <NoData />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis
          dataKey="bucket"
          tick={AXIS}
          tickFormatter={(v: string) => formatBucket(v, summary.trend_bucket)}
          minTickGap={24}
        />
        <YAxis yAxisId="events" allowDecimals={false} tick={AXIS} />
        <YAxis yAxisId="alerts" orientation="right" allowDecimals={false} tick={AXIS} />
        <Tooltip labelFormatter={(v: string) => formatDateTime(v)} />
        <Legend wrapperStyle={LEGEND} />
        <Line yAxisId="events" type="linear" dataKey="events" name="Log events" stroke="#0284c7" strokeWidth={2} dot={data.length <= 48 ? { r: 2 } : false} />
        <Line yAxisId="alerts" type="stepAfter" dataKey="alerts" name="Alerts (first seen)" stroke="#dc2626" strokeWidth={2} dot={{ r: 2 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function TopIpChart({ data }: { data: CountItem[] }) {
  if (!data.length) return <NoData />;
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 28)}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
        <XAxis type="number" allowDecimals={false} tick={AXIS} />
        <YAxis type="category" dataKey="key" width={170} tick={{ ...AXIS, fontFamily: "ui-monospace, monospace" }} />
        <Tooltip />
        <Legend wrapperStyle={LEGEND} />
        <Bar dataKey="count" name="Events" fill="#475569" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
