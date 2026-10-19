import { DEMO_AI_ASSETS } from "./demo-ai-assets";
/** Licensed representative demo references. Never treated as photographs of demo SKUs. */
export type DemoPhotoAsset = {
 id: string; segment?: "women" | "men" | "unisex"; subtype?: string; category: "shirt" | "polo" | "tshirt" | "trousers" | "shorts" | "tailored" | "sneakers" | "loafers" | "belt" | "blouse" | "bodysuit" | "knit" | "culotte" | "palazzo" | "fluid-trousers" | "straight-trousers" | "pleated-trousers" | "summer-trousers" | "flats" | "sandals" | "cropped-tshirt" | "platform-sneakers" | "horsebit-loafers";
 colourFamilies: string[]; uri: string; page: string;
 kind?: "licensed_reference" | "ai_generated_demo";
 author: string; licence: string; match: string; attributionRequired: boolean;
};
export type DemoInspiration = DemoPhotoAsset & { colourAccurate: boolean; matchKind?: "exact" | "style-reference" };
export const COLOUR_FAMILY_MAP: Record<string,string> = {
 white:"white",cream:"cream",beige:"beige",sand:"sand",ivory:"cream",ecru:"cream",
 "pearl grey":"grey",grey:"grey",navy:"navy",olive:"olive",
 camel:"camel",brown:"brown",tan:"tan",taupe:"taupe",coral:"coral",salmon:"coral","light blue":"blue"
};
export const DEMO_PHOTO_LIBRARY: DemoPhotoAsset[] = [
 ...(DEMO_AI_ASSETS["sand-shirt"] ? [{ id:"ai-sand-shirt", category:"shirt" as const, colourFamilies:["sand"], uri:DEMO_AI_ASSETS["sand-shirt"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated sand dress shirt; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["grey-polo"] ? [{ id:"ai-grey-polo", category:"polo" as const, colourFamilies:["grey"], uri:DEMO_AI_ASSETS["grey-polo"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated grey knitted polo; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["beige-polo"] ? [{ id:"ai-beige-polo", category:"polo" as const, colourFamilies:["beige"], uri:DEMO_AI_ASSETS["beige-polo"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated beige piqué polo; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["olive-tshirt"] ? [{ id:"ai-olive-tshirt", category:"tshirt" as const, colourFamilies:["olive"], uri:DEMO_AI_ASSETS["olive-tshirt"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated olive T-shirt; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["taupe-chinos"] ? [{ id:"ai-taupe-chinos", category:"trousers" as const, colourFamilies:["taupe"], uri:DEMO_AI_ASSETS["taupe-chinos"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated taupe chino trousers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["navy-shorts"] ? [{ id:"ai-navy-shorts", category:"shorts" as const, colourFamilies:["navy"], uri:DEMO_AI_ASSETS["navy-shorts"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated navy chino shorts; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["grey-tailored"] ? [{ id:"ai-grey-tailored", category:"tailored" as const, colourFamilies:["grey"], uri:DEMO_AI_ASSETS["grey-tailored"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated grey tailored trousers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["camel-tailored"] ? [{ id:"ai-camel-tailored", category:"tailored" as const, colourFamilies:["camel"], uri:DEMO_AI_ASSETS["camel-tailored"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated camel tailored trousers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["cream-sneakers"] ? [{ id:"ai-cream-sneakers", category:"sneakers" as const, colourFamilies:["cream"], uri:DEMO_AI_ASSETS["cream-sneakers"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated cream sneakers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["navy-sneakers"] ? [{ id:"ai-navy-sneakers", category:"sneakers" as const, colourFamilies:["navy"], uri:DEMO_AI_ASSETS["navy-sneakers"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated navy sneakers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["beige-sneakers"] ? [{ id:"ai-beige-sneakers", category:"sneakers" as const, colourFamilies:["beige"], uri:DEMO_AI_ASSETS["beige-sneakers"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated beige sneakers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["pearl-grey-sneakers"] ? [{ id:"ai-pearl-grey-sneakers", category:"sneakers" as const, colourFamilies:["grey"], uri:DEMO_AI_ASSETS["pearl-grey-sneakers"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated pearl-grey sneakers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["tan-loafers"] ? [{ id:"ai-tan-loafers", category:"loafers" as const, colourFamilies:["tan"], uri:DEMO_AI_ASSETS["tan-loafers"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated tan penny loafers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["taupe-polo-new"] ? [{ id:"ai-taupe-polo-new", category:"polo" as const, colourFamilies:["taupe"], uri:DEMO_AI_ASSETS["taupe-polo-new"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated taupe knitted polo; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["pearl-grey-oxford"] ? [{ id:"ai-pearl-grey-oxford", category:"shirt" as const, colourFamilies:["grey"], uri:DEMO_AI_ASSETS["pearl-grey-oxford"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated pearl grey Oxford shirt; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["beige-tshirt"] ? [{ id:"ai-beige-tshirt", category:"tshirt" as const, colourFamilies:["beige"], uri:DEMO_AI_ASSETS["beige-tshirt"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated beige T-shirt; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["navy-tshirt"] ? [{ id:"ai-navy-tshirt", category:"tshirt" as const, colourFamilies:["navy"], uri:DEMO_AI_ASSETS["navy-tshirt"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated navy T-shirt; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["sand-chinos"] ? [{ id:"ai-sand-chinos", category:"trousers" as const, colourFamilies:["sand"], uri:DEMO_AI_ASSETS["sand-chinos"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated sand chino trousers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["olive-chinos"] ? [{ id:"ai-olive-chinos", category:"trousers" as const, colourFamilies:["olive"], uri:DEMO_AI_ASSETS["olive-chinos"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated olive chino trousers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["navy-chinos"] ? [{ id:"ai-navy-chinos", category:"trousers" as const, colourFamilies:["navy"], uri:DEMO_AI_ASSETS["navy-chinos"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated navy chino trousers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["camel-loafers"] ? [{ id:"ai-camel-loafers", category:"loafers" as const, colourFamilies:["camel"], uri:DEMO_AI_ASSETS["camel-loafers"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated camel penny loafers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["taupe-polo"] ? [{ id:"ai-taupe-polo", category:"polo" as const, colourFamilies:["taupe"], uri:DEMO_AI_ASSETS["taupe-polo"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated taupe knitted polo; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["cream-chinos"] ? [{ id:"ai-cream-chinos", category:"trousers" as const, colourFamilies:["cream"], uri:DEMO_AI_ASSETS["cream-chinos"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated cream chino trousers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 ...(DEMO_AI_ASSETS["navy-loafers"] ? [{ id:"ai-navy-loafers", category:"loafers" as const, colourFamilies:["navy"], uri:DEMO_AI_ASSETS["navy-loafers"], page:"", author:"AI-generated", licence:"Synthetic AI-generated demo illustration", match:"AI-generated navy penny loafers; not actual product", attributionRequired:false, kind:"ai_generated_demo" as const }] : []),
 { id:"oxford-white",category:"shirt",colourFamilies:["white"],
   uri:"https://commons.wikimedia.org/wiki/Special:FilePath/Button_up_%28Unsplash%29.jpg?width=500",
   page:"https://commons.wikimedia.org/wiki/File:Button_up_(Unsplash).jpg",
   author:"michael m_minimal",licence:"CC0 1.0",
   match:"White button-up shirt, representative photo",attributionRequired:false },
 { id:"polo-white-knit",category:"polo",colourFamilies:[],
   uri:"https://commons.wikimedia.org/wiki/Special:FilePath/Classical_polo_shirt.jpg?width=500",
   page:"https://commons.wikimedia.org/wiki/File:Classical_polo_shirt.jpg",
   author:"Elkagye",licence:"CC BY-SA 3.0",
   match:"Classic knitted polo shirt style; photographed shade differs from selected colour",attributionRequired:true },
 { id:"tshirt-white",category:"tshirt",colourFamilies:["white"],
   uri:"https://commons.wikimedia.org/wiki/Special:FilePath/White-tshirt.jpg?width=500",
   page:"https://commons.wikimedia.org/wiki/File:White-tshirt.jpg",
   author:"Paulinaela",licence:"CC0 1.0",
   match:"White T-shirt, representative photo",attributionRequired:false },
 { id:"tshirt-grey",category:"tshirt",colourFamilies:["grey"],
   uri:"https://commons.wikimedia.org/wiki/Special:FilePath/Grey_Tshirt.jpg?width=500",
   page:"https://commons.wikimedia.org/wiki/File:Grey_Tshirt.jpg",
   author:"Camisetas",licence:"CC BY-SA 3.0",
   match:"Grey T-shirt representative photograph",attributionRequired:true },
 { id:"sneakers-white",category:"sneakers",colourFamilies:["white"],
   uri:"https://commons.wikimedia.org/wiki/Special:FilePath/Fashion-shoes-white-snickers_%2823699823403%29.jpg?width=500",
   page:"https://commons.wikimedia.org/wiki/File:Fashion-shoes-white-snickers_(23699823403).jpg",
   author:"www.Pixel.la Free Stock Photos",licence:"CC0 1.0",
   match:"White sneakers, representative photograph",attributionRequired:false },
 { id:"penny-loafer-brown",category:"loafers",colourFamilies:[],
   uri:"https://commons.wikimedia.org/wiki/Special:FilePath/A_Penny_Loafer.jpg?width=500",
   page:"https://commons.wikimedia.org/wiki/File:A_Penny_Loafer.jpg",
   author:"Wikipedia-ce",licence:"CC0 1.0",
   match:"Penny loafer style reference; photographed colour may differ",attributionRequired:false },
 { id:"chino-sand",category:"trousers",colourFamilies:["sand","beige"],
   uri:"https://commons.wikimedia.org/wiki/Special:FilePath/Chino_pants.jpg?width=500",
   page:"https://commons.wikimedia.org/wiki/File:Chino_pants.jpg",
   author:"Kuha455405",licence:"CC BY-SA 3.0",
   match:"Light khaki chino trousers, representative photo",attributionRequired:true }
];
/** Canonical Italian/English subtype normalisation: most specific rules precede generic ones. */
export function canonicalDemoSubtype(name:string):string {
 const t=name.toLowerCase().trim();
 const patterns: Array<[RegExp,string]> = [
 [/blouse.*seta/,"blouse_fluid_silk"],[/blouse|blusa/,"blouse_fluid"],
 [/body|bodysuit/,"bodysuit"],[/pullover.*v.neck/,"vneck_knit"],
 [/t.shirt.*cropp/,"tshirt_cropped"],
 [/pantalone.*pince/,"trousers_pleated"],[/pantalone.*culotte/,"trousers_culotte"],
 [/pantalone.*palazzo/,"trousers_palazzo"],[/pantalone.*fluido/,"trousers_fluid"],
 [/pantalone.*gamba.dritta/,"trousers_straight"],[/pantalone.*estivo/,"trousers_summer"],
 [/shorts.*cargo/,"shorts_cargo"],[/shorts/,"shorts_classic"],
 [/ballerine.*punta/,"flats_pointed"],[/ballerine.*cinturino/,"flats_strap"],
 [/sandali.*tacco/,"sandals_heel"],[/sandali.*intrecciat/,"sandals_woven"],
 [/sandali/,"sandals_flat"],[/loafer.*morsetto/,"loafers_horsebit"],
 [/sneaker.*plateau/,"sneakers_platform"],[/sneaker.*alte/,"sneakers_low"],
 [/tailored|sartorial/,"trousers_tailored"],[/chino|trouser|pants/,"trousers_chino"],
 [/v.neck.*t.shirt/,"tshirt_vneck"],[/t.shirt|tshirt|tee/,"tshirt_basic"],
 [/polo|maglia|piqu[eé]/,"polo"],[/shirt|oxford|camicia/,"shirt"],[/loafer/,"loafers"],[/sneaker/,"sneakers"],
 ];
 return patterns.find(([re])=>re.test(t))?.[1] ?? "unknown";
}
const WOMEN_KEYS: Array<[string,string,string]> = [["blouse_fluid_navy","blouse_fluid","navy"],["blouse_fluid_cream","blouse_fluid","cream"],["blouse_fluid_silk_beige","blouse_fluid_silk","beige"],["bodysuit_coral","bodysuit","coral"],["vneck_knit_camel","vneck_knit","camel"],["tshirt_cropped_grey","tshirt_cropped","grey"],["tshirt_basic_cream","tshirt_basic","cream"],["tshirt_crew_coral","tshirt_basic","coral"],["tshirt_vneck_navy","tshirt_vneck","navy"],["trousers_pleated_cream","trousers_pleated","cream"],["trousers_culotte_navy","trousers_culotte","navy"],["trousers_palazzo_beige","trousers_palazzo","beige"],["trousers_palazzo_navy","trousers_palazzo","navy"],["trousers_fluid_coral","trousers_fluid","coral"],["trousers_straight_navy","trousers_straight","navy"],["trousers_summer_beige","trousers_summer","beige"],["shorts_classic_white","shorts_classic","white"],["shorts_classic_navy","shorts_classic","navy"],["shorts_cargo_navy","shorts_cargo","navy"],["flats_pointed_beige","flats_pointed","beige"],["flats_strap_navy","flats_strap","navy"],["sandals_flat_brown","sandals_flat","brown"],["sandals_flat_navy","sandals_flat","navy"],["sandals_heel_brown","sandals_heel","brown"],["sandals_heel_camel","sandals_heel","camel"],["sandals_heel_navy","sandals_heel","navy"],["sandals_woven_camel","sandals_woven","camel"],["loafers_horsebit_tan","loafers_horsebit","tan"],["sneakers_platform_beige","sneakers_platform","beige"],["tshirt_crew_white","tshirt_basic","white"],["tshirt_crew_navy","tshirt_basic","navy"],["tshirt_vneck_coral","tshirt_vneck","coral"],["trousers_tailored_camel","trousers_tailored","camel"],["trousers_tailored_grey","trousers_tailored","grey"],["shorts_classic_sand","shorts_classic","sand"],["loafers_navy","loafers","navy"],["loafers_camel","loafers","camel"],["loafers_horsebit_navy","loafers_horsebit","navy"],["loafers_horsebit_camel","loafers_horsebit","camel"],["sneakers_platform_white","sneakers_platform","white"],["sneakers_low_cream","sneakers_low","cream"]];
export const WOMENS_DEMO_PHOTOS:DemoPhotoAsset[] = WOMEN_KEYS.flatMap(([key,subtype,colour]) => DEMO_AI_ASSETS["women_"+key] ? [{
 id:"women_"+key,segment:"women" as const,subtype,category:"shirt" as const,colourFamilies:[colour],
 uri:DEMO_AI_ASSETS["women_"+key],page:"",kind:"ai_generated_demo" as const,author:"AI-generated",licence:"Synthetic AI illustration",match:"Women's "+subtype+" in "+colour+"; illustrative, not actual product",attributionRequired:false
}] : []);
/** Default remains legacy for menswear; women's items cannot borrow male imagery. */
export function demoInspiration(name:string, selectedColour:string, segment:"women"|"men"|"unisex"="men"):DemoInspiration|null {
 const colour=COLOUR_FAMILY_MAP[selectedColour.trim().toLowerCase()];
 if(!colour)return null;
 if(segment==="women") {
   const subtype=canonicalDemoSubtype(name);
   const exact=WOMENS_DEMO_PHOTOS.find(p=>p.subtype===subtype&&p.colourFamilies.includes(colour));
   if(exact)return {...exact,colourAccurate:true,matchKind:"exact"};
   // Only accept a visibly correct cut. Nearby colours can mislead users, so retain selected-colour swatches instead.
   return null;
 }
 // Prefer a garment-specific menswear image to the broad category matcher.
 // Never use a photograph of a different subtype or an unverified colour as exact.
 const subtype=canonicalDemoSubtype(name);
 const subtypeCategory: Record<string, DemoPhotoAsset["category"]> = {
   trousers_tailored:"tailored", trousers_chino:"trousers",
   shorts_classic:"shorts", shorts_cargo:"shorts", shirt:"shirt",
   polo:"polo", tshirt_basic:"tshirt", tshirt_vneck:"tshirt",
   sneakers:"sneakers", sneakers_low:"sneakers", loafers:"loafers"
 };
 const expected=subtypeCategory[subtype];
 const matching=expected ? DEMO_PHOTO_LIBRARY.find(p=>p.category===expected && p.colourFamilies.includes(colour) && p.kind==="ai_generated_demo") : undefined;
 if(matching)return {...matching,colourAccurate:true,matchKind:"exact"};
 // A colour-family fallback is an illustrative style reference, NEVER an exact-colour claim.
 // For neutral shades only; avoid showing a misleading vivid or unrelated colour.
 const neutralFamily:Record<string,string[]> = {
   white:["cream","beige","sand"], cream:["white","beige","sand"],
   beige:["sand","cream","white"], sand:["beige","cream","white"],
   grey:["grey"], navy:["navy"], olive:["olive"], camel:["tan","brown"],
   tan:["camel","brown"], brown:["tan","camel"]
 };
 const family=(neutralFamily[colour]||[]).filter(c=>c!==colour);
 const familyMatch=expected ? DEMO_PHOTO_LIBRARY.find(p=>p.category===expected && p.kind==="ai_generated_demo" && p.colourFamilies.some(c=>family.includes(c))) : undefined;
 if(familyMatch)return {...familyMatch,colourAccurate:false,matchKind:"style-reference",match:familyMatch.match+"; neutral-colour reference only, not the selected "+selectedColour};

 const category=demoCategory(name);
 if(!category)return null;
 const exact=DEMO_PHOTO_LIBRARY.find(p=>p.category===category&&p.colourFamilies.includes(colour));
 if(!exact)return null;
 const accurate=exact.kind==="ai_generated_demo"||!["tshirt-grey","chino-sand"].includes(exact.id);
 return {...exact,colourAccurate:accurate,matchKind:accurate?"exact":"style-reference",match:accurate?exact.match:exact.match+"; approximate reference"};
}
function demoCategory(name:string):DemoPhotoAsset["category"]|null {
 const t=name.toLowerCase();
 if(/belt|cintura/.test(t))return "belt";
 if(/loafer|mocassin/.test(t))return "loafers";
 if(/sneaker|trainer/.test(t))return "sneakers";
 if(/shorts|bermuda/.test(t))return "shorts";
 if(/tailored|sartorial/.test(t))return "tailored";
 if(/chino|trouser|pants/.test(t))return "trousers";
 if(/polo|maglia|piqu[eé]/.test(t))return "polo";
 if(/t-shirt|tee|tshirt/.test(t))return "tshirt";
 if(/shirt|oxford|blouse/.test(t))return "shirt";
 return null;
}
