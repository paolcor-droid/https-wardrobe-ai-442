import { useEffect, useState } from "react";
import { Image } from "expo-image";
import { accountAccessToken } from "@/src/account-api";
import { fileUrl } from "@/src/api";

// Private pictures are fetched with the customer's bearer token; the opaque
// photo identifier is never transformed into a public or permanent signed link.
export function AccountPhoto({
  path, style, contentFit = "cover",
}: {
  path: string;
  style: any;
  contentFit?: "cover" | "contain";
}) {
  const [token, setToken] = useState<string | null>(null);
  const privatePhoto = path.startsWith("private:");
  useEffect(() => {
    let active = true;
    setToken(null);
    if (privatePhoto) {
      void accountAccessToken()
        .then(value => { if (active) setToken(value); })
        .catch(() => { if (active) setToken(null); });
    }
    return () => { active = false; };
  }, [path, privatePhoto]);
  if (privatePhoto && !token) return null;
  const uri = privatePhoto ? fileUrl(path)
    : /^(https?:|file:|content:|data:|blob:)/i.test(path) ? path : fileUrl(path);
  return <Image
    source={{
      uri,
      ...(privatePhoto ? { headers: { Authorization: `Bearer ${token}` } } : {}),
    }}
    style={style}
    contentFit={contentFit}
  />;
}
