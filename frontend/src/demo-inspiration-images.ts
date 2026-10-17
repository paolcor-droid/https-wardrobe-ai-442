/** Licensed representative demo references. Never treated as photographs of demo SKUs. */
export type DemoPhotoAsset = {
 id: string; category: "shirt" | "trousers" | "sneakers" | "loafers";
 colourFamilies: string[]; uri: string; page: string;
 author: string; licence: string; match: string; attributionRequired: boolean;
};
export type DemoInspiration = DemoPhotoAsset;
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
 if(/shirt|oxford|blouse/.test(t))return "shirt";
 return null;
}
/** Conservative exact-colour matching: never replace missing imagery with a wrong-colour photo. */
export function demoInspiration(name:string, selectedColour:string):DemoInspiration|null {
 const category=demoCategory(name);
 const colour=COLOUR_FAMILY_MAP[selectedColour.trim().toLowerCase()];
 if(!category||!colour)return null;
 return DEMO_PHOTO_LIBRARY.find(p=>p.category===category&&p.colourFamilies.includes(colour))||null;
}
