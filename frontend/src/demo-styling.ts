/** Explain eligible demo looks without inventing verified skin/colour/stock claims. */
export type StylingPrefs = { climate?: string | null; style?: string | null; occasion?: string | null; preferred_colours?: string[] } | null | undefined;
export type DemoLook = { occasion?: string; style?: string; reason?: string; garments: Array<{name:string; colour_names:string[]}> };
export function explainDemoLook(look: DemoLook, prefs: StylingPrefs): string[] {
 const garments=look.garments.map(g=>g.name);
 const colours=[...new Set(look.garments.map(g=>g.colour_names?.[0]).filter(Boolean))];
 const detail=garments.length ? "Pieces: " + garments.join(" + ") + "." : "Coordinated garments.";
 const lines:string[]=[detail];
 if(colours.length) lines.push("Colour combination: "+colours.join(" / ")+". This mix was selected by the recommendation filters, not independently checked against a new colour analysis.");
 if(prefs?.style) lines.push("Your saved style is "+prefs.style+". "+(look.style && look.style.toLowerCase()===prefs.style.toLowerCase() ? "The look's style label agrees." : "Assess whether these silhouettes feel consistent with that preference."));
 if(prefs?.climate==="hot") {
   const seasonal=/shorts|sandali|sandals|t-shirt|tee|blouse|linen/i.test(garments.join(" "));
   lines.push(seasonal ? "Warm-weather styling: the included shorts, light top or open footwear can support a less layered look; confirm actual fabric weight and comfort." : "Hot-climate filter has been applied. Check material and layering before wearing in heat.");
 } else if(prefs?.climate==="cold") lines.push("Cold-climate preference: assess insulating layers and materials; a seasonal screen is not a warmth guarantee.");
 else if(prefs?.climate) lines.push("Climate preference: "+prefs.climate+". This is not based on live weather.");
 if(look.occasion)lines.push("Suggested occasion: "+look.occasion+". This is styling guidance, not a verified dress code.");
 return lines;
}
export type DemoInventoryReadiness = { mode: "synthetic_demo" | "verified_supplier"; purchasable: false; requires: string[] };
export const DEMO_INVENTORY_READINESS: DemoInventoryReadiness = {
  mode:"synthetic_demo", purchasable:false,
  requires:["Provider authorization and API credentials","Variant-specific rights-cleared product imagery","Live stock/price timestamps and currency","Per-user access controls","Supplier test orders and checkout security checks"]
};
