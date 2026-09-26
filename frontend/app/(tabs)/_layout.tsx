import { Platform } from "react-native";
import { Tabs } from "expo-router";
import Feather from "@react-native-vector-icons/feather";

import { colors } from "@/src/theme";

export const usesNativeTabs =
  Platform.OS === "ios" && parseInt(String(Platform.Version), 10) >= 26;

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.onSurface,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.divider,
          ...(Platform.OS === "web" ? { height: 64 } : {}),
        },
        tabBarItemStyle: { alignSelf: "center" },
        tabBarLabelStyle: { fontSize: 10, letterSpacing: 2 },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "DISCOVER",
          tabBarIcon: ({ color }) => <Feather name="grid" size={20} color={color} />,
        }}
      />
      <Tabs.Screen
        name="tryon"
        options={{
          title: "TRY-ON",
          tabBarIcon: ({ color }) => <Feather name="camera" size={20} color={color} />,
        }}
      />
      <Tabs.Screen
        name="wishlist"
        options={{
          title: "SAVED",
          tabBarIcon: ({ color }) => <Feather name="bookmark" size={20} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "PROFILE",
          tabBarIcon: ({ color }) => <Feather name="user" size={20} color={color} />,
        }}
      />
    </Tabs>
  );
}
