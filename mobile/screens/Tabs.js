import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import AskScreen from "./AskScreen";
import HomeScreen from "./HomeScreen";
import SettingsScreen from "./SettingsScreen";
import TimelineScreen from "./TimelineScreen";

const Tab = createBottomTabNavigator();

export default function Tabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: { backgroundColor: "#0d1117" },
        tabBarActiveTintColor: "#58a6ff",
        tabBarInactiveTintColor: "#8b949e",
      }}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Ask" component={AskScreen} />
      <Tab.Screen name="Timeline" component={TimelineScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}
