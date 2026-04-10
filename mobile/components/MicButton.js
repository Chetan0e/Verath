import React from "react";
import { Pressable, Text } from "react-native";

export default function MicButton({ onPress, label = "Record" }) {
  return (
    <Pressable
      onPress={onPress}
      style={{
        backgroundColor: "#1f6feb",
        paddingVertical: 14,
        paddingHorizontal: 20,
        borderRadius: 999,
        alignItems: "center",
      }}
    >
      <Text style={{ color: "#fff", fontWeight: "600" }}>{label}</Text>
    </Pressable>
  );
}
