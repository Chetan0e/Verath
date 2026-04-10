import React from "react";
import { View, Text } from "react-native";

export default function MemoryCard({ item }) {
  return (
    <View
      style={{
        backgroundColor: "#151b23",
        borderRadius: 16,
        padding: 16,
        marginBottom: 12,
      }}
    >
      <Text style={{ color: "#8b949e", marginBottom: 8 }}>{item.speaker || "unknown"}</Text>
      <Text style={{ color: "#f0f6fc", marginBottom: 8 }}>{item.text}</Text>
      <Text style={{ color: "#58a6ff" }}>
        Importance: {typeof item.importance === "number" ? item.importance.toFixed(2) : "0.50"}
      </Text>
    </View>
  );
}
