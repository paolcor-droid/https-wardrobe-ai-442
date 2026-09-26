// Image picker wrapper — returns base64 (no data URI prefix)
import * as ImagePicker from "expo-image-picker";

export async function pickImageBase64(): Promise<string | null> {
  const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!perm.granted) return null;

  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    allowsEditing: false,
    quality: 0.7,
    base64: true,
  });

  if (result.canceled || !result.assets?.[0]) return null;
  return result.assets[0].base64 ?? null;
}

export async function captureImageBase64(): Promise<string | null> {
  const perm = await ImagePicker.requestCameraPermissionsAsync();
  if (!perm.granted) return null;

  const result = await ImagePicker.launchCameraAsync({
    allowsEditing: false,
    quality: 0.7,
    base64: true,
  });

  if (result.canceled || !result.assets?.[0]) return null;
  return result.assets[0].base64 ?? null;
}
