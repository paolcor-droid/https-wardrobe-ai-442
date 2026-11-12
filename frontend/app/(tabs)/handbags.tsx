import React, {useMemo,useState} from "react";
import {ScrollView,View,Text,Pressable,Image,useWindowDimensions} from "react-native";
import {useSafeAreaInsets} from "react-native-safe-area-context";
import {useQuery} from "@tanstack/react-query";
import {getProfile} from "@/src/api";
import {SPC_BAGS,matchingSPCBags, type SPCBag} from "@/src/spc-handbags";
const ink="#29241f", muted="#72665a", cream="#fdfbf8", gold="#987b5d";
const filters=["All","Colour matches","Black","Blue","Neutral","Pink","Gold"] as const;
type Filter=typeof filters[number];
const neutral=["beige","white","brown","khaki","caramel","grey"];
export default function HandbagsScreen(){
 const insets=useSafeAreaInsets(), {width}=useWindowDimensions();
 const {data:profile}=useQuery({queryKey:["profile"],queryFn:getProfile});
 const [filter,setFilter]=useState<Filter>("All"),[expanded,setExpanded]=useState<string|null>(null);
 const p=profile?.preferences||{};
 const preferred=Array.isArray(p.preferred_colours)?p.preferred_colours.filter((c:unknown):c is string=>typeof c==="string"):[];
 const avoided=Array.isArray(p.avoided_colours)?p.avoided_colours.filter((c:unknown):c is string=>typeof c==="string"):[];
 const ordered=useMemo(()=>matchingSPCBags(preferred,avoided),[JSON.stringify(preferred),JSON.stringify(avoided)]);
 const items=filter==="All"?SPC_BAGS:filter==="Colour matches"?ordered.filter(b=>preferred.some(c=>b.colour.toLowerCase().includes(c.toLowerCase()))):SPC_BAGS.filter(b=>filter==="Neutral"?neutral.some(c=>b.colour.toLowerCase().includes(c)):b.colour.toLowerCase().includes(filter.toLowerCase()));
 const cardWidth=width>950?Math.min(280,(width-115)/3):width>620?(width-66)/2:width-36;
 return <ScrollView style={{flex:1,backgroundColor:cream}} contentContainerStyle={{paddingTop:Math.max(insets.top,16)+16,paddingHorizontal:18,paddingBottom:90}}>
  <Text style={{fontSize:11,letterSpacing:2.2,color:gold,fontWeight:"700"}}>LUMIÈRE × STEFANIA P. CREATIONS</Text>
  <Text style={{fontSize:34,color:ink,marginTop:12,marginBottom:10,fontFamily:"Georgia"}}>Handmade Italian handbags</Text>
  <Text style={{color:muted,lineHeight:23,maxWidth:680}}>Explore 18 authorised designs to complement your outfits. This early catalogue preview is not a shopping checkout.</Text>
  <View style={{backgroundColor:"#f1e9e0",padding:12,borderRadius:9,marginTop:18}}><Text style={{color:muted}}>Prices coming soon · Stock availability unconfirmed · No purchasing enabled</Text></View>
  <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{gap:8,paddingVertical:16}}>
  {filters.map(f=><Pressable key={f} onPress={()=>setFilter(f)} style={{borderColor:"#d5c8bb",borderWidth:1,borderRadius:24,paddingHorizontal:14,paddingVertical:8,backgroundColor:f===filter?ink:"white"}}><Text style={{color:f===filter?"white":ink}}>{f}</Text></Pressable>)}
  </ScrollView>
  {filter==="Colour matches"&&preferred.length===0&&<Text style={{color:muted,marginBottom:12}}>Choose preferred colours in your profile to see personalised suggestions.</Text>}
  <View style={{flexDirection:"row",flexWrap:"wrap",gap:14}}>
  {items.map(b=><Pressable accessibilityRole="button" accessibilityLabel={b.name+" view details"} key={b.id} onPress={()=>setExpanded(expanded===b.id?null:b.id)} style={{width:cardWidth,backgroundColor:"white",borderWidth:1,borderColor:"#e9e1d7",borderRadius:10,overflow:"hidden"}}>
    {b.image ? <Image source={b.image} resizeMode="contain" style={{width:"100%",height:Math.min(300,cardWidth*1.1)}}/> : <View style={{height:Math.min(300,cardWidth*1.1),backgroundColor:"#f1ebe4",alignItems:"center",justifyContent:"center",padding:25}}><Text style={{color:muted,textAlign:"center"}}>Supplier image awaiting repository transfer</Text></View>}
    <View style={{padding:15}}>
      <Text style={{fontSize:10,letterSpacing:1.1,color:gold}}>{b.brand.toUpperCase()}</Text>
      <Text style={{fontFamily:"Georgia",fontSize:20,color:ink,marginTop:6}}>{b.name}</Text>
      <View style={{flexDirection:"row",alignItems:"center",gap:8,marginTop:10}}><View style={{width:15,height:15,borderRadius:8,backgroundColor:b.colourHex,borderColor:"#ccc",borderWidth:1}}/><Text style={{color:muted,fontSize:12,flexShrink:1}}>{b.colour}</Text></View>
      <Text style={{marginTop:14,color:ink,fontWeight:"600"}}>Price on request</Text>
      {expanded===b.id&&<View style={{borderTopWidth:1,borderTopColor:"#e9e1d7",marginTop:12,paddingTop:12,gap:4}}>
        <Text style={{color:muted,fontSize:12}}>Code: {b.sku}</Text>
        <Text style={{color:muted,fontSize:12}}>Materials: {b.materials.join(", ")}</Text>
        <Text style={{color:muted,fontSize:12}}>Dimensions: {b.dimensions}</Text>
        <Text style={{color:muted,fontSize:12}}>Made in {b.origin}</Text>
      </View>}
      <Text style={{color:gold,marginTop:14,fontSize:12}}>{expanded===b.id?"Hide details −":"View details +"}</Text>
    </View>
   </Pressable>)}
  </View>
  {items.length===0&&<Text style={{color:muted,marginTop:16}}>No handbags match this filter.</Text>}
  <Text style={{color:muted,fontSize:11,marginTop:28}}>Authorised supplier catalogue preview. No price, live inventory or product checkout has been verified.</Text>
 </ScrollView>
}
