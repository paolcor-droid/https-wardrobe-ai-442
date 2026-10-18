import { DEMO_AI_ASSETS } from "./demo-ai-assets";
/** Licensed representative demo references. Never treated as photographs of demo SKUs. */
export type DemoPhotoAsset = {
 id: string; category: "shirt" | "polo" | "tshirt" | "trousers" | "sneakers" | "loafers";
 colourFamilies: string[]; uri: string; page: string;
 kind?: "licensed_reference" | "ai_generated_demo";
 author: string; licence: string; match: string; attributionRequired: boolean;
};
export type DemoInspiration = DemoPhotoAsset & { colourAccurate: boolean };
export const COLOUR_FAMILY_MAP: Record<string,string> = {
 white:"white",cream:"cream",beige:"beige",sand:"sand",
 "pearl grey":"grey",grey:"grey",navy:"navy",olive:"olive",
 camel:"camel",brown:"brown",tan:"tan",taupe:"taupe","light blue":"blue"
};
export const DEMO_PHOTO_LIBRARY: DemoPhotoAsset[] = [
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
function demoCategory(name:string): DemoPhotoAsset["category"] | null {
 const t=name.toLowerCase();
 if(/loafer|mocassin/.test(t))return "loafers";
 if(/sneaker|trainer/.test(t))return "sneakers";
 if(/chino|trouser|pants/.test(t))return "trousers";
 if(/polo|maglia/.test(t))return "polo";
 if(/t-shirt|tee|tshirt/.test(t))return "tshirt";
 if(/shirt|oxford|blouse/.test(t))return "shirt";
 return null;
}
/** Exact-colour first; a clearly marked chino photo can illustrate style in other shades. */
export function demoInspiration(name:string, selectedColour:string):DemoInspiration|null {
 const category=demoCategory(name);
 const colour=COLOUR_FAMILY_MAP[selectedColour.trim().toLowerCase()];
 if(!category||!colour)return null;
 const exact = DEMO_PHOTO_LIBRARY.find(p => p.category === category && p.colourFamilies.includes(colour));
 if (exact) {
   // A colour family match does not prove an exact fabric shade.
   const shadeVerified = !["tshirt-grey", "chino-sand"].includes(exact.id);
   return { ...exact, colourAccurate: shadeVerified,
     match: shadeVerified ? exact.match : exact.match + "; photographed shade is an approximate reference" };
 }
 return null;
}
