/** Authorised Stefania P. Creations catalogue; source photos are not yet stored in this branch. No invented price or stock. */
export type SPCBag = {id:string; sku:string; name:string; brand:string; colour:string; colourHex:string; materials:string[]; dimensions:string; season:string; origin:"Italy"; price:null; availability:"unconfirmed"; image?:number};
const HERO_IMAGES: number[] = [
  require("../assets/spc-handbags/SPC-FW2627-01_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-02_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-03_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-04_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-05_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-06_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-07_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-08_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-09_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-10_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-11_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-12_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-13_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-14_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-15_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-16_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-17_hero.jpg"),
  require("../assets/spc-handbags/SPC-FW2627-18_hero.jpg"),
];
const data = [["01","Velvet Black & Grey","Black / Medium Grey","#242323","chenille, cotton-polyester, cotton, satin","21 × 17 cm"],["02","Blue Night","Midnight Blue","#172640","chenille, cotton-polyester, cotton, satin","24 × 16 cm"],["03","Petali Dorati","Dusty Rose / Gold","#A96D69","chenille, cotton-polyester, lurex, satin","24 × 16 cm"],["04","Double Queen","Deep Sea Green","#17413F","chenille, cotton-polyester, cotton, satin","24 × 16 cm"],["05","Diva Noir","Black","#171717","chenille, cotton-polyester, cotton, satin","24 × 16 cm"],["06","Velvet Black Diamonds","Black / Medium Grey","#242323","chenille, cotton-polyester, cotton, satin","21 × 17 cm"],["07","Notte di Cristallo","Black","#171717","chenille, cotton-polyester, cotton, satin","24 × 16 cm"],["08","Diamond Blue","Midnight Blue / Olive Green","#253550","chenille, cotton-polyester, cotton, satin","21 × 17 cm"],["09","Perla D'Oro","Beige","#D8BD95","chenille, cotton-polyester, cotton, satin","24 × 16 cm"],["10","Velvet Golden Jewel","Turmeric / Gold","#B57735","chenille, cotton-polyester, lurex, satin","24 × 16 cm"],["11","Occhio di Tigre","Turmeric / Caramel","#9A5C30","chenille, cotton-polyester, cotton, satin","21 × 17 cm"],["12","Notte Stellata","Khaki / Caramel / Gold","#80613E","chenille, cotton-polyester, lurex, satin","24 × 16 cm"],["13","Ambra","Khaki / Caramel","#77593E","chenille, cotton-polyester, cotton, satin","21 × 17 cm"],["14","Aurea","Dark Brown","#4A342C","duplex leather, satin","23 × 14 × 3 cm"],["15","Aura Sposa","Silk White","#E9E5DD","satin","21 × 14 × 3 cm"],["16","Rosa D’argento","Antique Rose / Silver","#B48682","cotton, lurex, satin","23 × 16 × 4 cm"],["17","Doreé","Gold","#B59865","lurex, satin","23 × 16 × 4 cm"],["18","Diamante Rosa","Antique Rose / Silver","#B48682","cotton, lurex, satin","23 × 16 × 4 cm"]];
export const SPC_BAGS: SPCBag[] = data.map(([n,name,colour,colourHex,materials,dimensions])=>({
 id:"SPC-FW2627-"+n, sku:"SPC-FW2627-"+n, name, brand:"Stefania P. Creations", colour, colourHex,
 materials:materials.split(", "), dimensions, season:"Autumn / Winter 2026–2027", origin:"Italy",
 price:null, availability:"unconfirmed", image:HERO_IMAGES[Number(n)-1],
}));
const norm=(s:string)=>s.toLowerCase().replace(/[^a-z0-9]/g," ").trim();
const similar=(a:string,b:string)=>a.split(/[\/ ,]+/).some(piece=>piece.length>2&&norm(b).includes(norm(piece)));
export function matchingSPCBags(preferred:string[]=[],avoided:string[]=[]):SPCBag[]{
 const candidates=SPC_BAGS.filter(bag=>!avoided.some(c=>c&&similar(c,bag.colour)));
 return candidates.sort((a,b)=>Number(preferred.some(c=>c&&similar(c,b.colour)))-Number(preferred.some(c=>c&&similar(c,a.colour))));
}
