import React, { createContext, useContext } from "react";
import type { ChatProvider } from "@/src/api";

// Customer-facing selection is retired. All requests use ChatGPT.
// The backend owns actual provider and model configuration.
type ModelContextValue = { provider: ChatProvider; setProvider: (p: ChatProvider) => void; ready: boolean };
const value: ModelContextValue = { provider: "openai", setProvider: () => {}, ready: true };
const ModelContext = createContext<ModelContextValue>(value);
export function ModelProvider({ children }: { children: React.ReactNode }) {
  return <ModelContext.Provider value={value}>{children}</ModelContext.Provider>;
}
export function useModel(): ModelContextValue { return useContext(ModelContext); }
