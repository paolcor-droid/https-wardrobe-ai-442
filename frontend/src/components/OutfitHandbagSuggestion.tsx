import React from "react";
import {Image,Text,View} from "react-native";
import {suggestBagForWomensOutfit} from "@/src/handbag-outfit-match";
export function OutfitHandbagSuggestion({garments,occasion,preferred=[],avoided=[]}:{
 garments:Array<{colour?:string|null; colour_names?:string[]|null; name?:string; category?:string}>;
 occasion?:string|null;preferred?:string[];avoided?:string[];
}){
 const result=suggestBagForWomensOutfit(garments,{occasion,preferred,avoided});
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
   <Text style={{fontSize:11,color:"#786b60"}}>Styling suggestion based on colour labels, not verified fabric shades. Handbag shown separately from AI-generated outfit previews.</Text>
 </View>;
}
