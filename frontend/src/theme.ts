// Design tokens for StyleScan (Wardrobe AI). Editorial light + a matching dark.
//
// Keys match the "color" block of /app/design_guidelines.json. Use a background
// key together with its `on` partner for text/icons.
//   const useStyles = makeStyles((c) => ({ box: { backgroundColor: c.surface } }));
// For non-style color props (icon color, placeholderTextColor) read
// useTheme().colors inside the component.

import { useMemo } from "react";
import { Appearance, StyleSheet, useColorScheme } from "react-native";

export type ColorScheme = "light" | "dark";

const light = {
  surface: "#F9F9F8",
  onSurface: "#111111",
  surfaceSecondary: "#FFFFFF",
  onSurfaceSecondary: "#111111",
  surfaceTertiary: "#F0F0EE",
  onSurfaceTertiary: "#333333",
  surfaceInverse: "#111111",
  onSurfaceInverse: "#F9F9F8",
  muted: "#7E7E7A",

  brand: "#2B2B2B",
  onBrand: "#FFFFFF",
  brandPrimary: "#1C1C1C",
  onBrandPrimary: "#FFFFFF",
  brandSecondary: "#5A5A5A",
  onBrandSecondary: "#FFFFFF",
  brandTertiary: "#EBEBEB",
  onBrandTertiary: "#111111",

  success: "#4A5D4E",
  onSuccess: "#FFFFFF",
  warning: "#C29367",
  onWarning: "#111111",
  error: "#964B4B",
  onError: "#FFFFFF",
  info: "#7E7E7A",
  onInfo: "#FFFFFF",

  border: "#E5E5E3",
  borderStrong: "#111111",
  divider: "#E5E5E3",
};

const dark: typeof light = {
  surface: "#111111",
  onSurface: "#F5F4F1",
  surfaceSecondary: "#1B1B1A",
  onSurfaceSecondary: "#F5F4F1",
  surfaceTertiary: "#242423",
  onSurfaceTertiary: "#D8D6D1",
  surfaceInverse: "#F5F4F1",
  onSurfaceInverse: "#111111",
  muted: "#9C9A94",

  brand: "#E9E7E2",
  onBrand: "#111111",
  brandPrimary: "#F5F4F1",
  onBrandPrimary: "#111111",
  brandSecondary: "#A7A49D",
  onBrandSecondary: "#111111",
  brandTertiary: "#2E2E2C",
  onBrandTertiary: "#F5F4F1",

  success: "#8FA893",
  onSuccess: "#111111",
  warning: "#D6A97C",
  onWarning: "#111111",
  error: "#C98E8E",
  onError: "#111111",
  info: "#9C9A94",
  onInfo: "#111111",

  border: "#2E2E2C",
  borderStrong: "#F5F4F1",
  divider: "#2E2E2C",
};

export type ThemeColors = typeof light;

// Editorial typography — variable TTFs loaded in app/_layout.tsx.
export const fonts = {
  display: "PlayfairDisplay",
  text: "DMSans",
};

export const defaultScheme = "light" satisfies ColorScheme;

export const themes: { light: ThemeColors; dark?: ThemeColors } = { light, dark };

export function setColorScheme(scheme: ColorScheme | null) {
  Appearance.setColorScheme?.(scheme ?? "unspecified");
}

setColorScheme?.(themes.dark ? null : defaultScheme);

export function useTheme(): { scheme: ColorScheme; colors: ThemeColors } {
  const system = useColorScheme();
  const scheme: ColorScheme =
    (system === "light" || system === "dark") && themes[system] ? system : defaultScheme;
  return { scheme, colors: themes[scheme] ?? themes.light };
}

export function makeStyles<T extends StyleSheet.NamedStyles<T> | StyleSheet.NamedStyles<any>>(
  factory: (colors: ThemeColors) => T & StyleSheet.NamedStyles<any>,
): () => T {
  return function useStyles(): T {
    const { colors } = useTheme();
    return useMemo(() => StyleSheet.create(factory(colors)), [colors]);
  };
}
