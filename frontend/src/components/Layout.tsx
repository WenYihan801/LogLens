import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useConfig } from "../hooks/configContext";
import { cx } from "../lib/cx";

const NAV = [
  { to: "/", label: "Dashboard", icon: "▦" },
  { to: "/datasets", label: "Datasets", icon: "⬆" },
  { to: "/events", label: "Events", icon: "≡" },
  { to: "/alerts", label: "Alerts", icon: "⚑" },
];

export function Layout() {
  const { read_only } = useConfig();
  const { search } = useLocation();
  // Keep the selected dataset when moving between pages.
  const dataset = new URLSearchParams(search).get("dataset");
  const keep = dataset ? `?dataset=${encodeURIComponent(dataset)}` : "";

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col bg-slate-900 px-3 py-5 text-slate-300 md:flex">
        <div className="mb-8 flex items-center gap-2 px-2">
          <img src="/favicon.svg" alt="" className="h-7 w-7" />
          <div>
            <div className="text-base font-semibold text-white">LogLens</div>
            <div className="text-[11px] text-slate-400">Log analysis &amp; detection</div>
          </div>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to + (n.to === "/datasets" ? "" : keep)}
              end={n.to === "/"}
              className={({ isActive }) =>
                cx(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-slate-800 text-white" : "hover:bg-slate-800/60 hover:text-white",
                )
              }
            >
              <span aria-hidden className="w-4 text-center">
                {n.icon}
              </span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-2 text-[11px] leading-relaxed text-slate-500">
          Alerts indicate suspicious behaviour that needs review — not confirmed attacks.
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <nav className="flex gap-1 overflow-x-auto bg-slate-900 px-3 py-2 md:hidden">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to + (n.to === "/datasets" ? "" : keep)}
              end={n.to === "/"}
              className={({ isActive }) =>
                cx("rounded-md px-3 py-1.5 text-sm", isActive ? "bg-slate-700 text-white" : "text-slate-300")
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        {read_only && (
          <div role="note" className="border-b border-amber-200 bg-amber-50 px-6 py-2 text-sm text-amber-900">
            <strong>Public read-only demo.</strong> You are viewing synthetic sample data with pre-computed alerts.
            Uploading, deleting and changing alerts are disabled — run LogLens locally for the full workflow.
          </div>
        )}
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
