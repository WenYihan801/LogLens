import type {
  Alert,
  AlertDetail,
  AlertFilters,
  AlertStatus,
  ApiErrorBody,
  AppConfig,
  DashboardSummary,
  Dataset,
  DatasetDetail,
  DetectionRunResult,
  EventDetail,
  EventFilters,
  LogEvent,
  Note,
  Page,
  Rule,
  SampleInfo,
  UploadResult,
} from "../types/api";

/**
 * Base URL of the API. Empty in development (Vite proxies /api) and in the
 * Docker image (Nginx proxies /api). Set VITE_API_BASE_URL when the frontend
 * is hosted separately from the backend (e.g. a static site + API service).
 */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.error_code;
    this.details = body.details;
  }
}

type Query = Record<string, string | number | undefined | null>;

export function buildQuery(params: Query = {}): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export function apiUrl(path: string, params?: Query): string {
  return `${API_BASE}${path}${buildQuery(params)}`;
}

async function request<T>(path: string, init: RequestInit = {}, params?: Query): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path, params), {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(0, {
      error_code: "NETWORK_ERROR",
      message: "Cannot reach the LogLens API. Check that the backend is running and try again.",
    });
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!res.ok) {
    const b = body as Partial<ApiErrorBody> | null;
    throw new ApiError(res.status, {
      error_code: b?.error_code ?? `HTTP_${res.status}`,
      message: b?.message ?? `Request failed with status ${res.status}.`,
      details: b?.details,
    });
  }
  return body as T;
}

const toQuery = (f: object): Query => ({ ...(f as Query) });

export const api = {
  config: () => request<AppConfig>("/api/v1/config"),

  // datasets
  datasets: () => request<Dataset[]>("/api/v1/datasets"),
  dataset: (id: string) => request<DatasetDetail>(`/api/v1/datasets/${id}`),
  deleteDataset: (id: string) => request<void>(`/api/v1/datasets/${id}`, { method: "DELETE" }),
  rerunDetection: (id: string) =>
    request<DetectionRunResult>(`/api/v1/datasets/${id}/detect`, { method: "POST" }),
  samples: () => request<SampleInfo[]>("/api/v1/datasets/samples"),
  loadSample: (key: string) =>
    request<UploadResult>(`/api/v1/datasets/samples/${encodeURIComponent(key)}`, { method: "POST" }),
  upload: (file: File, sourceType: string, name?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("source_type", sourceType);
    if (name) fd.append("name", name);
    return request<UploadResult>("/api/v1/datasets/upload", { method: "POST", body: fd });
  },

  // events
  events: (f: EventFilters, page: number, pageSize: number) =>
    request<Page<LogEvent>>("/api/v1/events", {}, { ...toQuery(f), page, page_size: pageSize }),
  event: (id: number) => request<EventDetail>(`/api/v1/events/${id}`),

  // alerts
  alerts: (f: AlertFilters, page: number, pageSize: number) =>
    request<Page<Alert>>("/api/v1/alerts", {}, { ...toQuery(f), page, page_size: pageSize }),
  alert: (id: string) => request<AlertDetail>(`/api/v1/alerts/${id}`),
  setAlertStatus: (id: string, status: AlertStatus) =>
    request<Alert>(`/api/v1/alerts/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  addNote: (id: string, note: string) =>
    request<Note>(`/api/v1/alerts/${id}/notes`, { method: "POST", body: JSON.stringify({ note }) }),
  rules: () => request<Rule[]>("/api/v1/rules"),

  // dashboard
  dashboard: (datasetId?: string) =>
    request<DashboardSummary>("/api/v1/dashboard/summary", {}, { dataset_id: datasetId }),

  // exports (plain links so the browser handles the download)
  eventsCsvUrl: (f: EventFilters) => apiUrl("/api/v1/exports/events.csv", toQuery(f)),
  alertsJsonUrl: (f: AlertFilters) => apiUrl("/api/v1/exports/alerts.json", toQuery(f)),
};
