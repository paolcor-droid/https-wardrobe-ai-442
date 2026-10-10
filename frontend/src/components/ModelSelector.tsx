import { View, Text, Pressable } from "react-native";
import { useQuery } from "@tanstack/react-query";

import { getModels, type ChatProvider, type ProviderInfo } from "@/src/api";
import { useModel } from "@/src/model-provider";
import { makeStyles, fonts } from "@/src/theme";

// Compact dev/testing selector to compare AI providers (Claude vs ChatGPT).
// Intentionally small and unobtrusive — not a redesign of the app.

const FALLBACK: ProviderInfo[] = [
  { id: "claude", label: "Claude", model: "claude-sonnet-5" },
  { id: "openai", label: "ChatGPT", model: "gpt-5.6-sol" },
];

function shortLabel(p: ProviderInfo): string {
  if (p.id === "openai") return "ChatGPT";
  if (p.id === "claude") return "Claude";
  return p.label;
}

export function ModelSelector({ compact = false }: { compact?: boolean }) {
  const styles = useStyles();
  const { provider, setProvider } = useModel();
  const { data } = useQuery({ queryKey: ["models"], queryFn: getModels, staleTime: 60_000 });
  const providers = data?.providers?.length ? data.providers : FALLBACK;
  const active = providers.find((p) => p.id === provider) ?? providers[0];

  return (
    <View style={styles.wrap} testID="model-selector">
      <Text style={styles.kicker}>AI MODEL · DEV</Text>
      <View style={styles.segment}>
        {providers.map((p) => {
          const isActive = p.id === provider;
          return (
            <Pressable
              key={p.id}
              testID={`model-option-${p.id}`}
              onPress={() => setProvider(p.id as ChatProvider)}
              style={[styles.option, isActive && styles.optionActive]}
            >
              <Text style={[styles.optionText, isActive && styles.optionTextActive]}>
                {shortLabel(p)}
              </Text>
            </Pressable>
          );
        })}
      </View>
      {!compact && active ? <Text style={styles.model}>{active.model}</Text> : null}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  wrap: { gap: 6 },
  kicker: { fontFamily: fonts.text, fontSize: 10, letterSpacing: 1.5, color: c.muted },
  segment: {
    flexDirection: "row",
    borderWidth: 1,
    borderColor: c.border,
    borderRadius: 6,
    overflow: "hidden",
    alignSelf: "flex-start",
  },
  option: { paddingVertical: 8, paddingHorizontal: 16, minHeight: 36, justifyContent: "center" },
  optionActive: { backgroundColor: c.brandPrimary },
  optionText: { fontFamily: fonts.text, fontSize: 13, fontWeight: "600", color: c.onSurface },
  optionTextActive: { color: c.onBrandPrimary },
  model: { fontFamily: fonts.text, fontSize: 11, color: c.muted },
}));
