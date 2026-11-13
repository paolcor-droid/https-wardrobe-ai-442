import {SPC_BAGS, type SPCBag} from "./spc-handbags";

/** Label-based coordinating accessories. This is styling guidance, not a verified fabric or exact-shade match. */
const colourGroups:Record<string,string[]>={
 neutral:["black","white","cream","grey","gray","taupe","beige","sand","ivory","charcoal","silver"],
 blue:["navy","blue","denim","cobalt"],
 green:["green","khaki","olive","sage","forest"],
 rose:["pink","rose","blush","burgundy","red","dusty"],
 warm:["gold","caramel","camel","brown","tan","turmeric","mustard","orange"],
};
const tokens=(x:string)=>(x||"").toLowerCase().replace(/[^a-z ]/g," ").split(/\s+/).filter(Boolean);
const groups=(name:string)=>new Set(Object.entries(colourGroups).filter(([,words])=>words.some(w=>tokens(name).includes(w))).map(([group])=>group));
const neutrals=["black","cream","beige","white","grey","taupe","brown","silver"];
const hasNeutral=(name:string)=>neutrals.some(c=>tokens(name).includes(c));

export type OutfitBagMatch={bag:SPCBag; explanation:string; confidence:"high"|"moderate"|"low"; score:number};
export function suggestBagForWomensOutfit(
 garments: Array<{colour?:string|null; colour_names?:string[]|null; name?:string; category?:string|null}>,
 opts:{occasion?:string|null; preferred?:string[]; avoided?:string[]; excludedIds?:string[]}={}
):OutfitBagMatch|null{
 if(!SPC_BAGS.length)return null;
 const colours=garments.flatMap(g=>g.colour_names?.length?g.colour_names:[g.colour||""]).filter(Boolean);
 const garmentGroups=colours.map(groups);
 const occasion=(opts.occasion||"").toLowerCase();
 const formal=/formal|evening|wedding|party|ceremony|gala|dressy/.test(occasion);
 const avoided=(opts.avoided||[]).map(c=>c.toLowerCase());
 const preferred=(opts.preferred||[]).map(c=>c.toLowerCase());
 const candidates=SPC_BAGS.filter(b=>!opts.excludedIds?.includes(b.id) && !avoided.some(c=>tokens(b.colour).some(bt=>tokens(c).includes(bt)))).map(b=>{
   const bgroup=groups(b.colour);
   const related=garmentGroups.filter(g=>[...bgroup].some(group=>g.has(group))).length;
   const exact=colours.filter(c=>tokens(b.colour).some(bt=>tokens(c).includes(bt))).length;
   const neutral=hasNeutral(b.colour);
   const clashes=0;
   const prefs=preferred.some(c=>tokens(b.colour).some(bt=>tokens(c).includes(bt)))?8:0;
   const name=b.name.toLowerCase();
   const occasionScore=formal?(/aura sposa|doreé|diamante|rosa d|notte|velvet/.test(name)?6:0):(/aurea|perla|blue night|ambra|velvet/.test(name)?3:0);
   const score=exact*20+related*9+(neutral?10:0)+prefs+occasionScore-clashes;
   return {bag:b,score,related,exact,neutral,clashes};
 }).sort((a,b)=>b.score-a.score||a.bag.id.localeCompare(b.bag.id));
 const best=candidates[0];
 if(!best)return null;
 const confidence:OutfitBagMatch["confidence"]=best.exact>0||best.related>1?"high":best.related>0||best.neutral?"moderate":"low";
 const explanation=best.exact>0?"Shares a named colour with pieces in your outfit."
  :best.related>0?"Coordinates with the outfit's broad colour family."
  :best.neutral?"Neutral accessory intended to complement the outfit."
  :"Closest available handbag; colour harmony is uncertain. Review the photos and shades.";
 return {bag:best.bag,confidence,explanation,score:best.score};
}
