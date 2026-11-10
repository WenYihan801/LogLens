import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { emptyPage, mockFetch, renderWithRouter } from "../test/utils";
import type { Alert, AlertDetail, DashboardSummary, LogEvent } from "../types/api";
import { AlertDetailPage } from "./AlertDetailPage";
import { DashboardPage } from "./DashboardPage";
import { DatasetsPage } from "./DatasetsPage";
import { EventsPage } from "./EventsPage";

afterEach(() => vi.unstubAllGlobals());

const emptySummary: DashboardSummary = {
  dataset_id: null,
  total_events: 0,
  total_alerts: 0,
  high_alerts: 0,
  medium_alerts: 0,
  low_alerts: 0,
  open_alerts: 0,
  unique_source_ips: 0,
  dataset_count: 0,
  severity_distribution: [],
  alert_status_distribution: [],
  status_code_distribution: [],
  source_type_distribution: [],
  top_source_ips: [],
  trend_bucket: "hour",
  activity_trend: [],
  recent_alerts: [],
};

const alert: Alert = {
  id: "a1",
  dataset_id: "d1",
  rule_code: "SSH_BRUTE_FORCE",
  rule_name: "Possible SSH Brute Force",
  source_ip: "203.0.113.99",
  severity: "HIGH",
  status: "OPEN",
  occurrence_count: 7,
  first_seen: "2026-11-03T09:30:00Z",
  last_seen: "2026-11-03T09:32:00Z",
  summary: "x",
  created_at: "2026-11-03T09:40:00Z",
  updated_at: "2026-11-03T09:40:00Z",
};

const samples = [
  { key: "ssh-bruteforce", name: "SSH – brute force", source_type: "SSH", filename: "ssh/b.log", description: "d" },
];

describe("DashboardPage", () => {
  it("shows the empty state with sample loading when there is no data (FR-17)", async () => {
    mockFetch({
      "/api/v1/dashboard/summary": () => emptySummary,
      "/api/v1/datasets/samples": () => samples,
    });
    renderWithRouter(<DashboardPage />);
    expect(await screen.findByText("No logs imported yet")).toBeInTheDocument();
    expect(await screen.findByText("SSH – brute force")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load" })).toBeEnabled();
  });

  it("disables sample loading in read-only demo mode", async () => {
    mockFetch({
      "/api/v1/dashboard/summary": () => emptySummary,
      "/api/v1/datasets/samples": () => samples,
    });
    renderWithRouter(<DashboardPage />, { config: { read_only: true } });
    expect(await screen.findByRole("button", { name: "Load" })).toBeDisabled();
  });

  it("renders stat cards and passes the dataset scope to the API (FR-16)", async () => {
    const { calls } = mockFetch({
      "/api/v1/dashboard/summary": () => ({
        ...emptySummary,
        dataset_id: "d1",
        dataset_count: 1,
        total_events: 1234,
        total_alerts: 3,
        high_alerts: 1,
        medium_alerts: 2,
        recent_alerts: [alert],
      }),
      "/api/v1/datasets": () => [],
    });
    renderWithRouter(<DashboardPage />, { route: "/?dataset=d1" });
    expect(await screen.findByTestId("stat-Log events")).toHaveTextContent("1,234");
    expect(screen.getByTestId("stat-High")).toHaveTextContent("1");
    expect(screen.getByText("Possible SSH Brute Force")).toBeInTheDocument();
    const dash = calls.find((c) => c.url.pathname === "/api/v1/dashboard/summary")!;
    expect(dash.url.searchParams.get("dataset_id")).toBe("d1");
  });

  it("shows an actionable error when the API is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    renderWithRouter(<DashboardPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the LogLens API");
  });
});

describe("EventsPage", () => {
  const ev = (i: number): LogEvent => ({
    id: i,
    dataset_id: "d1",
    event_timestamp: "2026-11-03T10:00:00Z",
    source_type: "NGINX",
    source_ip: "203.0.113.45",
    http_method: "GET",
    request_path: `/p${i}`,
    status_code: 404,
    user_agent: null,
    username: null,
    auth_result: null,
    line_number: i,
  });

  it("requests a server-side page and navigates pages (FR-20)", async () => {
    const { calls } = mockFetch({
      "/api/v1/datasets": () => [],
      "/api/v1/events": (url) => {
        const page = Number(url.searchParams.get("page"));
        return { items: [ev(page)], total: 120, page, page_size: 50, pages: 3 };
      },
    });
    renderWithRouter(<EventsPage />, { route: "/events?dataset=d1" });
    expect(await screen.findByText("/p1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("/p2")).toBeInTheDocument();
    const last = calls.filter((c) => c.url.pathname === "/api/v1/events").at(-1)!;
    expect(last.url.searchParams.get("page")).toBe("2");
    expect(last.url.searchParams.get("page_size")).toBe("50");
    expect(last.url.searchParams.get("dataset_id")).toBe("d1");
  });

  it("applies filters to the URL, the API call and the CSV export link (FR-19, FR-30)", async () => {
    const { calls } = mockFetch({ "/api/v1/datasets": () => [], "/api/v1/events": () => emptyPage });
    renderWithRouter(<EventsPage />, { route: "/events" });
    await screen.findByText("No events match these filters");
    await userEvent.type(screen.getByLabelText("Source IP"), "203.0.113.45");
    await userEvent.type(screen.getByLabelText("Status code"), "404");
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("source_ip=203.0.113.45"));
    const last = calls.filter((c) => c.url.pathname === "/api/v1/events").at(-1)!;
    expect(last.url.searchParams.get("source_ip")).toBe("203.0.113.45");
    expect(last.url.searchParams.get("status_code")).toBe("404");
    const link = screen.getByRole("link", { name: /Export CSV/ });
    expect(link.getAttribute("href")).toContain("source_ip=203.0.113.45");
    expect(link.getAttribute("href")).toContain("status_code=404");
  });
});

describe("AlertDetailPage", () => {
  const detail: AlertDetail = {
    ...alert,
    dataset_name: "SSH – brute force",
    rule: {
      id: "r1",
      rule_code: "SSH_BRUTE_FORCE",
      name: "Possible SSH Brute Force",
      description: "desc",
      source_type: "SSH",
      threshold: 5,
      window_seconds: 300,
      severity: "HIGH",
      enabled: true,
      version: 1,
    },
    explanation: "This is a suspicious-behaviour indicator — it is not a confirmed attack.",
    observed_window_seconds: 120,
    evidence: [
      {
        id: 11,
        dataset_id: "d1",
        event_timestamp: "2026-11-03T09:30:00Z",
        source_type: "SSH",
        source_ip: "203.0.113.99",
        http_method: null,
        request_path: null,
        status_code: null,
        user_agent: null,
        username: "<b>root</b>",
        auth_result: "FAILURE",
        line_number: 4,
        raw_message: "Failed password for <b>root</b>",
      },
    ],
    evidence_total: 1,
    notes: [],
  };

  it("explains the rule, lists evidence and updates status (FR-13, FR-24, FR-25)", async () => {
    let status = "OPEN";
    const { calls } = mockFetch({
      "GET /api/v1/alerts/a1": () => ({ ...detail, status }),
      "PATCH /api/v1/alerts/a1/status": (_u, init) => {
        status = JSON.parse(String(init?.body)).status;
        return { ...alert, status };
      },
    });
    renderWithRouter(<AlertDetailPage />, { route: "/alerts/a1", path: "/alerts/:id" });
    expect(await screen.findByText(/not a confirmed attack/)).toBeInTheDocument();
    expect(screen.getByText(/≥ 5 matching events from one IP within 5m/)).toBeInTheDocument();
    expect(screen.getByText("user <b>root</b>")).toBeInTheDocument(); // text, not markup

    const group = screen.getByRole("group", { name: "Alert status" });
    await userEvent.click(within(group).getByRole("button", { name: "ACKNOWLEDGED" }));
    await waitFor(() =>
      expect(within(group).getByRole("button", { name: "ACKNOWLEDGED" })).toHaveAttribute("aria-pressed", "true"),
    );
    const patch = calls.find((c) => c.init?.method === "PATCH")!;
    expect(JSON.parse(String(patch.init!.body))).toEqual({ status: "ACKNOWLEDGED" });
  });

  it("hides write controls in read-only mode (FR-33)", async () => {
    mockFetch({ "GET /api/v1/alerts/a1": () => detail });
    renderWithRouter(<AlertDetailPage />, { route: "/alerts/a1", path: "/alerts/:id", config: { read_only: true } });
    await screen.findByText(/not a confirmed attack/);
    const group = screen.getByRole("group", { name: "Alert status" });
    within(group)
      .getAllByRole("button")
      .forEach((b) => expect(b).toBeDisabled());
    expect(screen.queryByRole("button", { name: "Add note" })).toBeNull();
  });
});

describe("DatasetsPage", () => {
  it("surfaces server-side validation errors from upload (NFR-15)", async () => {
    mockFetch({
      "/api/v1/datasets": () => [],
      "/api/v1/datasets/samples": () => [],
      "POST /api/v1/datasets/upload": () =>
        new Response(
          JSON.stringify({ error_code: "FORMAT_MISMATCH", message: "Only 0 of the first 3 lines look like NGINX log entries." }),
          { status: 422 },
        ),
    });
    renderWithRouter(<DatasetsPage />);
    const input = await screen.findByLabelText("Log file (.log / .txt)");
    await userEvent.upload(input, new File(["hello\n"], "a.log", { type: "text/plain" }));
    await userEvent.click(screen.getByRole("button", { name: "Upload & analyse" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("look like NGINX");
    expect(screen.getByText("FORMAT_MISMATCH")).toBeInTheDocument();
  });

  it("rejects unsupported files before uploading", async () => {
    const { calls } = mockFetch({ "/api/v1/datasets": () => [], "/api/v1/datasets/samples": () => [] });
    renderWithRouter(<DatasetsPage />);
    const input = await screen.findByLabelText("Log file (.log / .txt)");
    await userEvent.upload(input, new File(["x"], "a.exe"), { applyAccept: false });
    await userEvent.click(screen.getByRole("button", { name: "Upload & analyse" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Only .log and .txt");
    expect(calls.some((c) => c.url.pathname.endsWith("/upload"))).toBe(false);
  });
});
