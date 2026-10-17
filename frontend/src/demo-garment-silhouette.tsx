import { View } from "react-native";

/** Simple single-colour geometric outlines, not product photos or exact cuts. */
export function DemoGarmentSilhouette({ name, category, colour }: { name: string; category?: string; colour: string }) {
  const words = (name + " " + (category || "")).toLowerCase();
  const edge = "#777";
  const shape = { backgroundColor: colour, borderWidth: 1, borderColor: edge };
  if (/shoe|loafer|sneaker|sandal|boot|footwear|mocassin/.test(words)) {
    return <View style={{ width: 82, height: 64, justifyContent: "flex-end", alignItems: "center" }}>
      <View style={[shape, { width: 66, height: 23, borderTopLeftRadius: 21, borderTopRightRadius: 12, borderBottomLeftRadius: 9, borderBottomRightRadius: 14, transform: [{ rotate: "-9deg" }] }]} />
      <View style={{ width: 67, height: 3, backgroundColor: edge, borderRadius: 3 }} />
    </View>;
  }
  if (/trouser|chino|pants|jeans|short|bottom/.test(words)) {
    const shorts = /short/.test(words);
    return <View style={{ width: 72, height: 68, alignItems: "center" }}>
      <View style={[shape, { width: 49, height: 15, borderTopLeftRadius: 4, borderTopRightRadius: 4 }]} />
      <View style={{ flexDirection: "row", gap: 4 }}>
        <View style={[shape, { width: 22, height: shorts ? 25 : 49, transform: [{ rotate: "3deg" }] }]} />
        <View style={[shape, { width: 22, height: shorts ? 25 : 49, transform: [{ rotate: "-3deg" }] }]} />
      </View>
    </View>;
  }
  if (/dress|skirt|jumpsuit|abito/.test(words)) {
    return <View style={{ width: 78, height: 68, alignItems: "center" }}>
      <View style={[shape, { width: 27, height: 24, borderTopLeftRadius: 8, borderTopRightRadius: 8 }]} />
      <View style={[shape, { width: 64, height: 42, borderTopLeftRadius: 7, borderTopRightRadius: 7, borderBottomLeftRadius: 3, borderBottomRightRadius: 3 }]} />
    </View>;
  }
  return <View style={{ width: 86, height: 68, flexDirection: "row", justifyContent: "center", alignItems: "flex-start" }}>
    <View style={[shape, { width: 19, height: 32, transform: [{ rotate: "19deg" }], marginTop: 8, marginRight: -2, borderRadius: 4 }]} />
    <View style={[shape, { width: 42, height: 61, borderTopLeftRadius: 12, borderTopRightRadius: 12, borderBottomLeftRadius: 3, borderBottomRightRadius: 3 }]} />
    <View style={[shape, { width: 19, height: 32, transform: [{ rotate: "-19deg" }], marginTop: 8, marginLeft: -2, borderRadius: 4 }]} />
  </View>;
}
