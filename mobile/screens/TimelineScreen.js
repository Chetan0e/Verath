import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { getTimeline } from "../services/api";

export default function TimelineScreen() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTimeline = async () => {
    setLoading(true);
    const data = await getTimeline();
    setEvents(data.timeline || []);
    setLoading(false);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    const data = await getTimeline();
    setEvents(data.timeline || []);
    setRefreshing(false);
  };

  useEffect(() => {
    fetchTimeline();
  }, []);

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#080b14", "#0f172a", "#080b14"]}
        style={StyleSheet.absoluteFill}
      />
      
      <View style={styles.header}>
        <View>
          <Text style={styles.headerSubtitle}>Activity Log</Text>
          <Text style={styles.headerTitle}>Neural Timeline</Text>
        </View>
        <TouchableOpacity style={styles.filterButton}>
          <MaterialCommunityIcons name="filter-variant" size={24} color="#38bdf8" />
        </TouchableOpacity>
      </View>

      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#38bdf8" />
          <Text style={styles.loadingText}>Syncing with Neural Core...</Text>
        </View>
      ) : events.length === 0 ? (
        <View style={styles.centerContainer}>
          <MaterialCommunityIcons name="brain" size={64} color="rgba(255,255,255,0.1)" />
          <Text style={styles.emptyText}>No neurological traces found today.</Text>
          <TouchableOpacity style={styles.refreshButton} onPress={fetchTimeline}>
            <Text style={styles.refreshButtonText}>Initialize Scan</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView 
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />
          }
        >
          {events.map((event, index) => (
            <View key={event.id || index} style={styles.timelineItem}>
              <View style={styles.timelineLeft}>
                <View style={[
                  styles.dot, 
                  { backgroundColor: event.importance > 0.7 ? "#ef4444" : "#10b981" }
                ]} />
                {index !== events.length - 1 && <View style={styles.line} />}
              </View>
              <View style={styles.card}>
                <LinearGradient
                  colors={["rgba(30, 41, 59, 0.4)", "rgba(15, 23, 42, 0.6)"]}
                  style={styles.cardGradient}
                >
                  <View style={styles.cardHeader}>
                    <Text style={styles.time}>
                      {new Date(event.timestamp * 1000).toLocaleDateString([], { month: 'short', day: 'numeric' })} • {new Date(event.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </Text>
                    <View style={[
                      styles.badge,
                      { backgroundColor: event.importance > 0.7 ? "rgba(239, 68, 68, 0.1)" : "rgba(16, 185, 129, 0.1)" }
                    ]}>
                      <Text style={[
                        styles.badgeText,
                        { color: event.importance > 0.7 ? "#ef4444" : "#10b981" }
                      ]}>{event.importance > 0.7 ? "Critical" : "Insight"}</Text>
                    </View>
                  </View>
                  <Text style={styles.text}>{event.text}</Text>
                  <View style={styles.footer}>
                    <View style={styles.speakerBadge}>
                      <MaterialCommunityIcons 
                        name={event.speaker && event.speaker !== "unknown" ? "account-tie" : "account-outline"} 
                        size={14} 
                        color={event.speaker && event.speaker !== "unknown" ? "#38bdf8" : "#64748b"} 
                      />
                      <Text style={[styles.speaker, { color: event.speaker && event.speaker !== "unknown" ? "#38bdf8" : "#64748b" }]}>
                        {event.speaker && event.speaker !== "unknown" ? event.speaker : "Unknown Speaker"}
                      </Text>
                    </View>
                    <View style={styles.sourceBadge}>
                      <MaterialCommunityIcons name="headphones" size={14} color="#64748b" />
                      <Text style={styles.sourceText}>Voice</Text>
                    </View>
                  </View>
                </LinearGradient>
              </View>
            </View>
          ))}
        </ScrollView>
      )}
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
    paddingBottom: 24,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.05)",
  },
  headerSubtitle: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 4,
  },
  headerTitle: {
    fontSize: 26,
    fontWeight: "800",
    color: "#f8fafc",
    letterSpacing: -0.5,
  },
  filterButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: "rgba(30, 41, 59, 0.5)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  scrollContent: {
    padding: 24,
    paddingBottom: 100,
  },
  centerContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 40,
  },
  loadingText: {
    color: "#94a3b8",
    marginTop: 16,
    fontSize: 14,
    fontWeight: "600",
  },
  emptyText: {
    color: "#64748b",
    marginTop: 16,
    fontSize: 16,
    fontWeight: "600",
    textAlign: "center",
  },
  refreshButton: {
    marginTop: 24,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: "rgba(56, 189, 248, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(56, 189, 248, 0.3)",
  },
  refreshButtonText: {
    color: "#38bdf8",
    fontWeight: "700",
  },
  timelineItem: {
    flexDirection: "row",
  },
  timelineLeft: {
    width: 20,
    alignItems: "center",
    marginRight: 16,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    zIndex: 1,
    marginTop: 24,
    borderWidth: 2,
    borderColor: "#080b14",
  },
  line: {
    width: 1,
    flex: 1,
    backgroundColor: "rgba(255,255,255,0.08)",
    marginVertical: 4,
  },
  card: {
    flex: 1,
    borderRadius: 24,
    marginBottom: 24,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
  },
  cardGradient: {
    padding: 20,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  time: {
    color: "#38bdf8",
    fontSize: 13,
    fontWeight: "700",
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  badgeText: {
    fontSize: 9,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  text: {
    color: "#f1f5f9",
    fontSize: 15,
    lineHeight: 22,
    fontWeight: "500",
    marginBottom: 16,
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  speakerBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "rgba(56, 189, 248, 0.05)",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  speaker: {
    color: "#38bdf8",
    fontSize: 11,
    fontWeight: "700",
  },
  sourceBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  sourceText: {
    color: "#64748b",
    fontSize: 11,
    fontWeight: "600",
  },
});
