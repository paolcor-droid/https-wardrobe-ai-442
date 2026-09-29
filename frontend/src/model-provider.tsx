import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

import type { ChatProvider } from "@/src/api";

// Lightweight, dev/testing-oriented store for the selected chat/analysis
// provider. Defaults to "claude" so existing behaviour is preserved. The
// choice is persisted so it survives reloads while comparing models.

const STORAGE_KEY = "stylescan.chatProvider";
const DEFAULT_PROVIDER: ChatProvider = "claude";

type ModelContextValue = {
  provider: ChatProvider;
  setProvider: (p: ChatProvider) => void;
  ready: boolean;
};

const ModelContext = createContext<ModelContextValue>({
  provider: DEFAULT_PROVIDER,
  setProvider: () => {},
  ready: false,
});

export function ModelProvider({ children }: { children: React.ReactNode }) {
  const [provider, setProviderState] = useState<ChatProvider>(DEFAULT_PROVIDER);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    AsyncStorage.getItem(STORAGE_KEY)
      .then((val) => {
        if (active && (val === "claude" || val === "openai")) {
          setProviderState(val);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const setProvider = (p: ChatProvider) => {
    setProviderState(p);
    AsyncStorage.setItem(STORAGE_KEY, p).catch(() => {});
  };

  const value = useMemo(() => ({ provider, setProvider, ready }), [provider, ready]);

  return <ModelContext.Provider value={value}>{children}</ModelContext.Provider>;
}

export function useModel(): ModelContextValue {
  return useContext(ModelContext);
}
