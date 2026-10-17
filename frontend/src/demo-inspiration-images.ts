/** Curated illustrative photography: source-specific CC licences, NOT demo SKUs. */
export type DemoInspiration = { uri: string; page: string; author: string; licence: string; match: string };
const MEDIA = {
  shirtWhite: {
    uri: "https://commons.wikimedia.org/wiki/Special:FilePath/Button_up_%28Unsplash%29.jpg?width=500",
    page: "https://commons.wikimedia.org/wiki/File:Button_up_(Unsplash).jpg",
    author: "michael m_minimal", licence: "CC0 1.0", match: "White shirt, representative photo",
  },
  chinoNeutral: {
    uri: "https://commons.wikimedia.org/wiki/Special:FilePath/Chino_pants.jpg?width=500",
    page: "https://commons.wikimedia.org/wiki/File:Chino_pants.jpg",
    author: "Kuha455405", licence: "CC BY-SA 3.0", match: "Neutral chino trousers, representative photo",
  },
} as const;
export function demoInspiration(name: string, selectedColour: string): DemoInspiration | null {
  const item = name.toLowerCase();
  const colour = selectedColour.toLowerCase().trim();
  if (/shirt oxford|oxford shirt|button.down shirt/.test(item) && colour === "white") return MEDIA.shirtWhite;
  // Chino reference image is light khaki; do not claim it depicts cream, grey or navy.
  if (/chino/.test(item) && /trouser|pants/.test(item) && (colour === "beige" || colour === "sand")) return MEDIA.chinoNeutral;
  return null;
}
