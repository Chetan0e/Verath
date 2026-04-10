import React from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";

const MOCK_EVENTS = [
  { id: 1, time: "2:15 PM", text: "Discussed project architecture and UI improvements.", speaker: "Aris", importance: "High" },
  { id: 2, time: "1:30 PM", text: "Synced on database schema migrations.", speaker: "System", importance: "Medium" },
  { id: 3, time: "11:00 AM", text: "Morning standup: Focused on mobile app integration.", speaker: "Team", importance: "Medium" },
];

export default function TimelineScreen() {
  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#050a12", "#0d1117"]}
        style={StyleSheet.absoluteFill}
      />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Neural Timeline</Text>
        <TouchableOpacity>
          <MaterialCommunityIcons name="filter-variant" size={24} color="#94a3b8" />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {MOCK_EVENTS.map((event, index) => (
          <View key={event.id} style={styles.timelineItem}>
            <View style={styles.timelineLeft}>
              <View style={[
                styles.dot, 
                { backgroundColor: event.importance === "High" ? "#ef4444" : "#38bdf8" }
              ]} />
              {index !== MOCK_EVENTS.length - 1 && <View style={styles.line} />}
            </View>
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Text style={styles.time}>{event.time}</Text>
                <View style={[
                  styles.badge,
                  { backgroundColor: event.importance === "High" ? "rgba(239, 68, 68, 0.1)" : "rgba(56, 189, 248, 0.1)" }
                ]}>
                  <Text style={[
                    styles.badgeText,
                    { color: event.importance === "High" ? "#ef4444" : "#38bdf8" }
                  ]}>{event.importance}</Text>
                </View>
              </View>
              <Text style={styles.text}>{event.text}</Text>
              <View style={styles.footer}>
                <MaterialCommunityIcons name="account-outline" size={14} color="#64748b" />
                <Text style={styles.speaker}>{event.speaker}</Text>
              </View>
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 60,
    paddingHorizontal: 24,
    paddingBottom: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.05)",
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#f8fafc",
  },
  scrollContent: {
    padding: 24,
  },
  timelineItem: {
    flexDirection: "row",
    marginBottom: 0,
  },
  timelineLeft: {
    width: 20,
    alignItems: "center",
    marginRight: 16,
  },
  dot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    zIndex: 1,
    marginTop: 20,
  },
  line: {
    width: 2,
    flex: 1,
    backgroundColor: "rgba(255,255,255,0.05)",
    marginVertical: 4,
  },
  card: {
    flex: 1,
    backgroundColor: "rgba(30, 41, 59, 0.4)",
    borderRadius: 20,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  time: {
    color: "#38bdf8",
    fontSize: 14,
    fontWeight: "700",
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  text: {
    color: "#f8fafc",
    fontSize: 15,
    lineHeight: 22,
    marginBottom: 16,
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  speaker: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "600",
  },
});
