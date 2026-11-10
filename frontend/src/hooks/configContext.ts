import { createContext, useContext } from "react";

import type { AppConfig } from "../types/api";

export const DEFAULT_CONFIG: AppConfig = {
  app_env: "development",
  read_only: false,
  max_upload_size_mb: 5,
  max_log_lines: 20000,
};

export const ConfigContext = createContext<AppConfig>(DEFAULT_CONFIG);

export function useConfig(): AppConfig {
  return useContext(ConfigContext);
}
