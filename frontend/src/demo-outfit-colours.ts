/** Visual-only demo garment colours. No inferred product photos or fabric texture. */
export const DEMO_SWATCHES: Record<string, string> = {
  navy:"#24344f",black:"#252525",white:"#f9f8f3",cream:"#f2e6cf",
  beige:"#d5c4a3",camel:"#b48655",tan:"#ba8158",brown:"#67412f",
  "dark brown":"#4e3428",grey:"#94979b","pearl grey":"#ced1d3",
  charcoal:"#50535a",olive:"#747d4c","sage green":"#a0ab94",
  "forest green":"#305f4a",red:"#ad3939",burgundy:"#74384a",
  blue:"#496e9d","light blue":"#b5cee5","dark blue":"#294c73",
  "cobalt blue":"#2655b2",sand:"#dfd0af",taupe:"#aaa092",
  mustard:"#b98c36",terracotta:"#bb6950",coral:"#e28775",
  "blush pink":"#ddadaf",lilac:"#b4a1cc"
};
export function demoSwatch(colour: string | undefined): string | null {
  return DEMO_SWATCHES[(colour || "").trim().toLowerCase()] ?? null;
}
