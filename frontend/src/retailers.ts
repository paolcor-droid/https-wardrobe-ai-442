export type Retailer = {
  id: string;
  name: string;
  homeUrl: string;
  searchUrl?: (query: string) => string;
  kind?: "retail" | "wholesale";
};

export const RETAILERS: Retailer[] = [
  { id: "zara", name: "Zara", homeUrl: "https://www.zara.com/au/", searchUrl: (q) => `https://www.zara.com/au/en/search?searchTerm=${encodeURIComponent(q)}` },
  { id: "hm", name: "H&M", homeUrl: "https://www2.hm.com/en_au/index.html", searchUrl: (q) => `https://www2.hm.com/en_au/search-results.html?q=${encodeURIComponent(q)}` },
  { id: "uniqlo", name: "UNIQLO", homeUrl: "https://www.uniqlo.com/au/en/", searchUrl: (q) => `https://www.uniqlo.com/au/en/search?q=${encodeURIComponent(q)}` },
  { id: "the-iconic", name: "THE ICONIC", homeUrl: "https://www.theiconic.com.au/" },
  { id: "david-jones", name: "David Jones", homeUrl: "https://www.davidjones.com/" },
  { id: "myer", name: "Myer", homeUrl: "https://www.myer.com.au/" },
  { id: "asos", name: "ASOS", homeUrl: "https://www.asos.com/au/" },
  { id: "country-road", name: "Country Road", homeUrl: "https://www.countryroad.com.au/" },
  { id: "massimo-dutti", name: "Massimo Dutti", homeUrl: "https://www.massimodutti.com/au/" },
  { id: "romanelli-b2b", name: "Romanelli B2B", homeUrl: "https://www.romanellib2b.com/en/catalog", kind: "wholesale" },
  { id: "loro-piana", name: "Loro Piana", homeUrl: "https://www.loropiana.com/en-au/" },
  { id: "armani", name: "Armani", homeUrl: "https://www.armani.com/en-au/" },
];

export const DEFAULT_RETAILERS = ["zara", "hm", "uniqlo"];

export function retailerUrl(retailer: Retailer, query: string) {
  return retailer.searchUrl ? retailer.searchUrl(query) : retailer.homeUrl;
}
