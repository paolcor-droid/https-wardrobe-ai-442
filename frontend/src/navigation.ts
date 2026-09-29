import { Platform } from "react-native";

// "unstable" is only the import path — NativeTabs is production-ready. We gate to
// iOS 26+, where it renders the native Liquid Glass tab bar; everywhere else the
// classic JS <Tabs> is used.
export const usesNativeTabs =
  Platform.OS === "ios" && parseInt(String(Platform.Version), 10) >= 26;
