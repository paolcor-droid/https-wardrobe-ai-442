/** Explain eligible demo looks without inventing verified skin/colour/stock claims. */
export type StylingPrefs = { climate?: string | null; style?: string | null; occasion?: string | null; preferred_colours?: string[] } | null | undefined;
export type DemoLook = { occasion?: string; style?: string; reason?: string; garments: Array<{name:string; colour_names:string[]}> };
export function explainDemoLook(look: DemoLook, prefs: StylingPrefs): string[] {
  const colours = [...new Set(look.garments.map(x => x.colour_names[0]).filter(Boolean))];
  const statements: string[] = [];
  if (colours.length) statements.push("Colour palette: " + colours.join(", ") + ". Each garment passed the saved eligibility rules; the photographs are illustrative, not a new colour-analysis measurement.");
  if (prefs?.style) statements.push("Style preference: " + prefs.style + ". " + ((look.occasion || "").toLowerCase() === (prefs.occasion || "").toLowerCase() ? "The occasion label matches your preference." : "Review the styling details to judge whether this look suits your usual style."));
  if (prefs?.climate === "hot") statements.push("Hot-climate preference: the outfit has passed the configured seasonal screening; fabric weight and comfort have not been physically verified.");
  else if (prefs?.climate === "cold") statements.push("Cold-climate preference: the configured seasonal rules have been applied; check garment warmth before use.");
  else if (prefs?.climate) statements.push("Climate preference: " + prefs.climate + ". The recommendations respect configured seasonal rules, not a live forecast.");
  if (look.occasion) statements.push("Suggested occasion: " + look.occasion + " (a heuristic classification, not a dress-code guarantee).");
  return statements;
}
export type DemoInventoryReadiness = { mode: "synthetic_demo" | "verified_supplier"; purchasable: false; requires: string[] };
export const DEMO_INVENTORY_READINESS: DemoInventoryReadiness = {
  mode:"synthetic_demo", purchasable:false,
  requires:["Provider authorization and API credentials","Variant-specific rights-cleared product imagery","Live stock/price timestamps and currency","Per-user access controls","Supplier test orders and checkout security checks"]
};
