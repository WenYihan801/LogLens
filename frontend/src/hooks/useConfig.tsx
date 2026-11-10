import type { ReactNode } from "react";

import { api } from "../services/api";
import { ConfigContext, DEFAULT_CONFIG } from "./configContext";
import { useAsync } from "./useAsync";

export function ConfigProvider({ children }: { children: ReactNode }) {
  const { data } = useAsync(() => api.config(), []);
  return <ConfigContext.Provider value={data ?? DEFAULT_CONFIG}>{children}</ConfigContext.Provider>;
}
