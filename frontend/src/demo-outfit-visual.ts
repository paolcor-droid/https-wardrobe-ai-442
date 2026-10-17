/** Generic category illustrations only; NEVER product photographs. */
export function demoGarmentSymbol(name: string, category?: string): string {
  const text = ((name || "") + " " + (category || "")).toLowerCase();
  if (/sandal|loafer|sneaker|boot|shoe|footwear|mocassin/.test(text)) return "👞";
  if (/trouser|chino|jeans|pants|short|bottom/.test(text)) return "👖";
  if (/skirt/.test(text)) return "👗";
  if (/dress|jumpsuit|abito/.test(text)) return "👗";
  if (/blazer|jacket|coat|cardigan|outerwear/.test(text)) return "🧥";
  if (/shirt|t-shirt|tee|blouse|sweater|sweatshirt|polo|top/.test(text)) return "👕";
  return "◇";
}
