import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { ConfigContext, DEFAULT_CONFIG } from "../hooks/configContext";
import type { AppConfig } from "../types/api";

export type FetchHandler = (url: URL, init?: RequestInit) => unknown;

/** Replace global fetch with a router of JSON handlers keyed by pathname. */
export function mockFetch(handlers: Record<string, FetchHandler>) {
  const calls: { url: URL; init?: RequestInit }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    calls.push({ url, init });
    const key = `${init?.method ?? "GET"} ${url.pathname}`;
    const handler = handlers[key] ?? handlers[url.pathname];
    if (!handler) {
      return new Response(JSON.stringify({ error_code: "NOT_FOUND", message: `no mock for ${key}` }), { status: 404 });
    }
    const body = handler(url, init);
    if (body instanceof Response) return body;
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls };
}

export function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="location">{loc.pathname + loc.search}</div>;
}

export function renderWithRouter(
  ui: ReactNode,
  { route = "/", path = "*", config = {} }: { route?: string; path?: string; config?: Partial<AppConfig> } = {},
) {
  return render(
    <ConfigContext.Provider value={{ ...DEFAULT_CONFIG, ...config }}>
      <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route
            path={path}
            element={
              <>
                {ui}
                <LocationProbe />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </ConfigContext.Provider>,
  );
}

export const emptyPage = { items: [], total: 0, page: 1, page_size: 50, pages: 1 };
