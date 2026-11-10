import { Link, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { EmptyState } from "./components/ui";
import { ConfigProvider } from "./hooks/useConfig";
import { AlertDetailPage } from "./pages/AlertDetailPage";
import { AlertsPage } from "./pages/AlertsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DatasetsPage } from "./pages/DatasetsPage";
import { EventsPage } from "./pages/EventsPage";

function NotFound() {
  return (
    <EmptyState title="Page not found" icon="?">
      <Link to="/" className="font-medium text-sky-700 underline">
        Back to the dashboard
      </Link>
    </EmptyState>
  );
}

export default function App() {
  return (
    <ConfigProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="events" element={<EventsPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="alerts/:id" element={<AlertDetailPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ConfigProvider>
  );
}
