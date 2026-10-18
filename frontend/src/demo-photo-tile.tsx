import { useEffect, useState } from "react";
import { View, Image, Text } from "react-native";
import type { DemoInspiration } from "./demo-inspiration-images";
import { demoSwatch } from "./demo-outfit-colours";

/** Representative image only. Always fall back to the actual selected colour label. */
export function DemoPhotoTile({ photo, colour, height = 120 }: {
  photo: DemoInspiration | null; colour: string; height?: number;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [photo?.id]);
  const swatch = demoSwatch(colour);
  return <View style={{ height, width: "100%", borderRadius: 7, backgroundColor: "#f5f5f2", justifyContent: "center", alignItems: "center", overflow: "hidden" }}>
    {photo && !failed ?
      <Image accessibilityLabel={photo.match + "; not the actual demo product"}
        source={{ uri: photo.uri }} resizeMode="cover" onError={() => setFailed(true)}
        style={{ width: "100%", height }} /> :
      <View style={{ alignItems: "center", gap: 6 }}>
        <View accessibilityLabel={"Indicative " + colour + " colour"}
          style={{ height: Math.min(52,height-25), width: 54, borderRadius: 5, borderWidth: 1, borderColor: "#c7c7c7", backgroundColor: swatch || "#ddd" }}/>
        <Text style={{ fontSize: 10, color: "#555" }}>{photo && failed ? "Photo unavailable" : "Colour preview"}</Text>
      </View>}
    {photo && !failed && photo.kind === "ai_generated_demo" ? <View style={{ position: "absolute", bottom: 0, left: 0, right: 0, backgroundColor: "#ffffffeb", paddingVertical: 3 }}>
      <Text style={{ fontSize: 9, color: "#333", textAlign: "center" }}>AI-generated demo image · Not actual product</Text>
    </View> : null}
    {photo && !failed && !photo.colourAccurate && photo.kind !== "ai_generated_demo" ? <View style={{ position: "absolute", bottom: 0, left: 0, right: 0, backgroundColor: "#ffffffeb", paddingVertical: 3, paddingHorizontal: 5 }}>
      <Text style={{ fontSize: 9, color: "#333", textAlign: "center" }}>Style reference · Colour differs</Text>
    </View> : null}
  </View>;
}
