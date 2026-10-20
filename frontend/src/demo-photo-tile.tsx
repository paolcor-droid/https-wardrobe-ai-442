import { useEffect, useState } from "react";
import { View, Image, Text } from "react-native";
import type { DemoInspiration } from "./demo-inspiration-images";
import { demoSwatch } from "./demo-outfit-colours";

/** Representative demo imagery; show disclosures BELOW, never on top of garments. */
export function DemoPhotoTile({ photo, colour, height = 120 }: {
  photo: DemoInspiration | null; colour: string; height?: number;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [photo?.id, photo?.uri]);
  const swatch = demoSwatch(colour);
  const caption = photo && !failed
    ? !photo.colourAccurate
      ? "Silhouette reference · Colour may differ · Not actual product"
      : photo.kind === "ai_generated_demo"
        ? "AI-generated demo image · Not actual product"
        : "Representative photo · Not actual product"
    : null;
  return (
    <View style={{ width: "100%", borderRadius: 7, overflow: "hidden", backgroundColor: "#f5f5f2" }}>
      <View style={{ height, width: "100%", justifyContent: "center", alignItems: "center" }}>
        {photo && !failed ? (
          <Image
            accessibilityLabel={photo.match + "; not the actual demo product"}
            source={{ uri: photo.uri }}
            resizeMode="contain"
            onError={() => setFailed(true)}
            style={{ width: "100%", height }}
          />
        ) : (
          <View style={{ alignItems: "center", gap: 6 }}>
            <View accessibilityLabel={"Indicative " + colour + " colour"}
              style={{ height: Math.min(52, height - 25), width: 54, borderRadius: 5, borderWidth: 1, borderColor: "#c7c7c7", backgroundColor: swatch || "#ddd" }} />
            <Text style={{ fontSize: 10, color: "#555" }}>
              {photo && failed ? "Photo unavailable" : "Colour preview"}
            </Text>
          </View>
        )}
      </View>
      {caption ? (
        <View style={{ minHeight: 28, justifyContent: "center", paddingHorizontal: 5, paddingVertical: 4, backgroundColor: "#fff" }}>
          <Text style={{ fontSize: 10, lineHeight: 13, color: "#444", textAlign: "center" }}>{caption}</Text>
        </View>
      ) : null}
    </View>
  );
}
