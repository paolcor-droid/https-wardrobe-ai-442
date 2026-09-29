import * as ImagePicker from "expo-image-picker";

export type PickResult = { uri: string; name: string; type: string };
export type PermState = { granted: boolean; canAskAgain: boolean };

export async function ensureCameraPermission(): Promise<PermState> {
  const cur = await ImagePicker.getCameraPermissionsAsync();
  if (cur.granted) return { granted: true, canAskAgain: true };
  if (cur.canAskAgain) {
    const req = await ImagePicker.requestCameraPermissionsAsync();
    return { granted: req.granted, canAskAgain: req.canAskAgain };
  }
  return { granted: false, canAskAgain: false };
}

export async function ensureLibraryPermission(): Promise<PermState> {
  const cur = await ImagePicker.getMediaLibraryPermissionsAsync();
  if (cur.granted) return { granted: true, canAskAgain: true };
  if (cur.canAskAgain) {
    const req = await ImagePicker.requestMediaLibraryPermissionsAsync();
    return { granted: req.granted, canAskAgain: req.canAskAgain };
  }
  return { granted: false, canAskAgain: false };
}

function toResult(r: ImagePicker.ImagePickerResult): PickResult | null {
  if (r.canceled || !r.assets?.length) return null;
  const a = r.assets[0];
  const name = a.fileName || a.uri.split("/").pop() || "photo.jpg";
  const type = a.mimeType || "image/jpeg";
  return { uri: a.uri, name, type };
}

export async function takePhoto(): Promise<PickResult | null> {
  const r = await ImagePicker.launchCameraAsync({
    mediaTypes: ["images"],
    quality: 0.7,
    allowsEditing: false,
  });
  return toResult(r);
}

export async function pickFromLibrary(): Promise<PickResult | null> {
  const r = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ["images"],
    quality: 0.7,
    allowsEditing: false,
  });
  return toResult(r);
}

export type PickFlow = { status: "ok" | "blocked" | "cancelled"; asset?: PickResult };

export async function pickWithPermission(kind: "camera" | "library"): Promise<PickFlow> {
  const perm = kind === "camera" ? await ensureCameraPermission() : await ensureLibraryPermission();
  if (!perm.granted) return { status: perm.canAskAgain ? "cancelled" : "blocked" };
  const asset = kind === "camera" ? await takePhoto() : await pickFromLibrary();
  return asset ? { status: "ok", asset } : { status: "cancelled" };
}
