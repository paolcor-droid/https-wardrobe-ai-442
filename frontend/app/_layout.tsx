import { QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { LogBox, View } from "react-native";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { useFonts } from "expo-font";
import { StatusBar } from "expo-status-bar";

import { ErrorBoundary } from "@/src/components/error-boundary";
import { queryClient } from "@/src/query-client";
import { useTheme } from "@/src/theme";

// Disable logbox errors etc so that users can see the app
// and agent works as expected.
LogBox.ignoreAllLogs(true);

export default function RootLayout() {
  const { scheme, colors } = useTheme();
  const [fontsLoaded, fontError] = useFonts({
    PlayfairDisplay: require("../assets/fonts/PlayfairDisplay.ttf"),
    DMSans: require("../assets/fonts/DMSans.ttf"),
  });

  const ready = fontsLoaded || !!fontError;

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <KeyboardProvider>
          <StatusBar style={scheme === "dark" ? "light" : "dark"} />
          {ready ? (
            <Stack screenOptions={{ headerShown: false }} />
          ) : (
            <View style={{ flex: 1, backgroundColor: colors.surface }} />
          )}
        </KeyboardProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
