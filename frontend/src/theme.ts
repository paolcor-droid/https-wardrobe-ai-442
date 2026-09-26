// Design tokens — Lumière Editorial Mobile LIGHT (from /app/design_guidelines.json)

import { useMemo } from "react";
import { Appearance, StyleSheet, useColorScheme } from "react-native";

export type ColorScheme = "light" | "dark";

const light = {
  surface: "#FDFBF7",
  onSurface: "#1A1A18",
  surfaceSecondary: "#F4F2EC",
  onSurfaceSecondary: "#1A1A18",
  surfaceTertiary: "#EAE7DF",
  onSurfaceTertiary: "#1A1A18",
  surfaceInverse: "#1A1A18",
  onSurfaceInverse: "#FDFBF7",
  muted: "#7D7A73",

  brand: "#A85B4B",
  onBrand: "#FDFBF7",
  brandPrimary: "#A85B4B",
  onBrandPrimary: "#FDFBF7",
  brandSecondary: "#D29584",
  onBrandSecondary: "#1A1A18",
  brandTertiary: "#F1E3DF",
  onBrandTertiary: "#1A1A18",

  success: "#4B6653",
  onSuccess: "#FDFBF7",
  warning: "#C28B44",
  onWarning: "#1A1A18",
  error: "#8F3D3D",
  onError: "#FDFBF7",
  info: "#4B6653",
  onInfo: "#FDFBF7",

  border: "#EAE7DF",
  borderStrong: "#D1CCC3",
  divider: "#EAE7DF",
};

export type ThemeColors = typeof light;

export const defaultScheme = "light" satisfies ColorScheme;

export const themes: { light: ThemeColors; dark?: ThemeColors } = { light };

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  "2xl": 32,
  "3xl": 48,
};

export const fonts = {
  display: "PlayfairDisplay",
  displayItalic: "PlayfairDisplay-Italic",
  text: "Satoshi",
  textMedium: "Satoshi-Medium",
};

export function setColorScheme(scheme: ColorScheme | null) {
  Appearance.setColorScheme?.(scheme ?? "unspecified");
}

setColorScheme?.(themes.dark ? null : defaultScheme);

export function useTheme(): { scheme: ColorScheme; colors: ThemeColors } {
  const system = useColorScheme();
  const scheme: ColorScheme = system && themes[system] ? system : defaultScheme;
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

export const colors = light;
