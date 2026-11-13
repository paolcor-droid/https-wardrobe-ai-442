import React from "react";
import {Image,Pressable,ScrollView,Text,View} from "react-native";
import {suggestBagForWomensOutfit,rankedBagsForWomensOutfit} from "@/src/handbag-outfit-match";
export function OutfitHandbagSuggestion({garments,occasion,preferred=[],avoided=[],selectedBagId,onSelectBag}:{
 garments:Array<{colour?:string|null; colour_names?:string[]|null; name?:string; category?:string|null}>;
 occasion?:string|null;preferred?:string[];avoided?:string[];
 selectedBagId?:string;onSelectBag?:(bagId:string)=>void;
}){
 const candidates=onSelectBag
   ? rankedBagsForWomensOutfit(garments,{occasion,preferred,avoided})
   : [];
 const result=onSelectBag
   ? candidates.find(entry=>entry.bag.id===selectedBagId)||candidates[0]
   : suggestBagForWomensOutfit(garments,{occasion,preferred,avoided});
 const [showAll,setShowAll]=React.useState(false);
 if(!result)return null;
 const {bag}=result;
 return <View style={{backgroundColor:"#f5eee6",borderRadius:10,padding:12,marginVertical:8,gap:7}}>
   <Text style={{fontWeight:"700",fontSize:12,color:"#85694e",letterSpacing:1}}>COMPLETE THE LOOK · HANDBAG</Text>
   <View style={{flexDirection:"row",gap:12,alignItems:"center"}}>
     {bag.image?<Image source={bag.image} resizeMode="contain" style={{width:82,height:110,borderRadius:8,backgroundColor:"#ffffff"}}/>:
       <View style={{width:82,height:110,borderRadius:8,backgroundColor:"#e8e0d8",justifyContent:"center",padding:5}}><Text style={{fontSize:11,textAlign:"center",color:"#655b51"}}>Photo pending</Text></View>}
     <View style={{flex:1,gap:5}}>
       <Text style={{fontSize:16,fontWeight:"600",color:"#29241f"}}>{bag.name}</Text>
       <Text style={{fontSize:12,color:"#62594f"}}>{bag.colour} · Stefania P. Creations</Text>
       <Text style={{fontSize:12,color:"#62594f"}}>{result.explanation}</Text>
       <Text style={{fontSize:12,color:"#62594f"}}>Price on request · availability not confirmed</Text>
     </View>
   </View>
   {onSelectBag && candidates.length>1 ? <View style={{gap:7}}>
     <Text style={{fontSize:12,fontWeight:"600",color:"#493e34"}}>Choose a Stefania handbag · ranked by colour compatibility · no AI generation required</Text>
     <ScrollView horizontal showsHorizontalScrollIndicator accessibilityLabel="Browse ranked Stefania handbag photographs" contentContainerStyle={{gap:10,paddingVertical:5,paddingRight:12}}>
       {(showAll?candidates:candidates.slice(0,6)).map(({bag:option},index)=>(
         <Pressable key={option.id} accessibilityRole="button"
           accessibilityState={{selected:option.id===bag.id}}
           accessibilityLabel={`Select ${option.name}, ${option.colour}`}
           onPress={()=>onSelectBag(option.id)}
           style={{width:116,borderRadius:9,padding:6,borderWidth:option.id===bag.id?2:1,
             borderColor:option.id===bag.id?"#85694e":"#d4c8bc",backgroundColor:"#fff",gap:4}}>
           {option.image?<Image source={option.image} resizeMode="contain" style={{height:110,width:"100%",borderRadius:5}}/>:null}
           <Text numberOfLines={2} style={{fontWeight:option.id===bag.id?"700":"500",fontSize:12,color:"#29241f"}}>{option.name}</Text>
           <Text numberOfLines={2} style={{fontSize:11,color:"#62594f"}}>{option.colour}</Text>
           <Text style={{fontSize:10,color:"#85694e"}}>{option.id===bag.id?"Selected":index===0?"Top match":"Choose"}</Text>
         </Pressable>
       ))}
     </ScrollView>
     {candidates.length>6?<Pressable accessibilityRole="button" onPress={()=>setShowAll(value=>!value)}>
       <Text style={{fontSize:12,fontWeight:"600",color:"#65513e"}}>{showAll?`Show top 6 handbags`:`Browse all ${candidates.length} catalogue handbags`}</Text>
     </Pressable>:null}
   </View>:null}
   <Text style={{fontSize:11,color:"#786b60"}}>Styling suggestion based on colour labels, not verified fabric shades. Choosing a handbag changes the AI preview selection; image generation occurs only when you request it. Compare any AI illustration with the actual product photograph above.</Text>
 </View>;
}
