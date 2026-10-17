/** Licensed representative demo references. Never treated as photographs of demo SKUs. */
export type DemoPhotoAsset = {
 id: string; category: "shirt" | "tshirt" | "trousers" | "sneakers" | "loafers";
 colourFamilies: string[]; uri: string; page: string;
 author: string; licence: string; match: string; attributionRequired: boolean;
};
export type DemoInspiration = DemoPhotoAsset & { colourAccurate: boolean };
export const COLOUR_FAMILY_MAP: Record<string,string> = {
 white:"white",cream:"cream",beige:"beige",sand:"sand",
 "pearl grey":"grey",grey:"grey",navy:"navy",olive:"olive",
 camel:"camel",brown:"brown",tan:"tan","light blue":"blue"
};
export const DEMO_PHOTO_LIBRARY: DemoPhotoAsset[] = [
 { id:"oxford-white",category:"shirt",colourFamilies:["white"],
   uri:"https://commons.wikimedia.org/wiki/Special:FilePath/Button_up_%28Unsplash%29.jpg?width=500",
   page:"https://commons.wikimedia.org/wiki/File:Button_up_(Unsplash).jpg",
   author:"michael m_minimal",licence:"CC0 1.0",
   match:"White button-up shirt, representative photo",attributionRequired:false },
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
 if (category === "shirt" && /oxford|shirt/i.test(name)) {
   const photo = DEMO_PHOTO_LIBRARY.find(p => p.id === "oxford-white");
   if (photo) return { ...photo, colourAccurate: false,
     match: "Representative Oxford-style shirt; pictured white differs from selected " + selectedColour };
 }
 if (category === "tshirt") {
   const photo = DEMO_PHOTO_LIBRARY.find(p => p.id === "tshirt-white");
   if (photo) return { ...photo, colourAccurate: false,
     match: "Representative T-shirt design; pictured white differs from selected " + selectedColour };
 }
 if (category === "sneakers") {
   const photo = DEMO_PHOTO_LIBRARY.find(p => p.id === "sneakers-white");
   if (photo) return { ...photo, colourAccurate: false,
     match: "Representative sneaker style; pictured white differs from selected " + selectedColour };
 }
 if (category === "loafers") {
   const photo = DEMO_PHOTO_LIBRARY.find(p => p.id === "penny-loafer-brown");
   if (photo) return { ...photo, colourAccurate: false,
     match: "Representative loafer design, not a photo of selected " + selectedColour + " loafers" };
 }
 if (category === "trousers" && /chino/i.test(name)) {
   const reference = DEMO_PHOTO_LIBRARY.find(p => p.id === "chino-sand");
   if (reference) return { ...reference, colourAccurate: false,
     match: "Representative chino style, not the selected " + selectedColour + " colour" };
 }
 return null;
}
