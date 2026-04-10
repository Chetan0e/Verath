import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import Tabs from "./screens/Tabs";

export default function App() {
  return (
    <NavigationContainer>
      <Tabs />
    </NavigationContainer>
  );
}
