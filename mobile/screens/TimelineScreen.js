import React, { useState, useEffect, useRef } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl, Alert } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { Audio } from "expo-av";
import { getTimeline, deleteMemory } from "../services/api";
import { API_BASE_URL } from "../config";

export default function TimelineScreen() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [playingId, setPlayingId] = useState(null);
  const [error, setError] = useState(null);
  const soundRef = useRef(null);

  const fetchTimeline = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTimeline();
      console.log('Timeline data:', data);
      setEvents(data.timeline || []);
    } catch (error) {
      console.error('Error fetching timeline:', error);
      setError(error.message || 'Failed to load timeline');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
  setRefreshing(true);
  try {
    const data = await getTimeline();
    setEvents(data.timeline || []);
  } catch (e) {
    setError('Failed to refresh timeline');
  } finally {
    setRefreshing(false);
  }
};

  const playAudio = async (audioFile, eventId) => {
    try {
      // Stop any currently playing sound
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }

      if (playingId === eventId) {
        setPlayingId(null);
        return;
      }

      if (audioFile) {
        const audioUrl = audioFile.startsWith('http') ? audioFile : `${API_BASE_URL}/${audioFile.replace(/\\/g, '/')}`;
        const { sound } = await Audio.Sound.createAsync(
          { uri: audioUrl },
          { shouldPlay: true }
        );
        soundRef.current = sound;
        setPlayingId(eventId);

        sound.setOnPlaybackStatusUpdate((status) => {
          if (!status.isLoaded) return;
          if (status.didJustFinish) {
            setPlayingId(null);
          }
        });
      }
    } catch (error) {
      console.error("Error playing audio:", error);
    }
  };

  const handleDelete = (eventId) => {
    Alert.alert(
      "Delete Memory",
      "Are you sure you want to delete this memory?",
      [
        {
          text: "Cancel",
          style: "cancel"
        },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            const result = await deleteMemory(eventId);
            if (result.success !== false) {
              setEvents(events.filter(e => e.id !== eventId));
            } else {
              Alert.alert("Error", result.error || "Failed to delete memory");
            }
          }
        }
      ]
    );
  };

  useEffect(() => {
    return () => {
      if (soundRef.current) {
        soundRef.current.unloadAsync();
      }
    };
  }, []);

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
      ) : error ? (
        <View style={styles.centerContainer}>
          <MaterialCommunityIcons name="alert-circle" size={64} color="#ef4444" />
          <Text style={styles.emptyText}>{error}</Text>
          <TouchableOpacity style={styles.refreshButton} onPress={fetchTimeline}>
            <Text style={styles.refreshButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : events.length === 0 ? (
        <View style={styles.centerContainer}>
          <MaterialCommunityIcons name="brain" size={64} color="rgba(255,255,255,0.1)" />
          <Text style={styles.emptyText}>No memories from last 24 hours. Start recording to build your timeline.</Text>
          <TouchableOpacity style={styles.refreshButton} onPress={fetchTimeline}>
            <Text style={styles.refreshButtonText}>Refresh</Text>
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
                    <View style={styles.headerRight}>
                      <View style={[
                        styles.badge,
                        { backgroundColor: event.importance > 0.7 ? "rgba(239, 68, 68, 0.1)" : "rgba(16, 185, 129, 0.1)" }
                      ]}>
                        <Text style={[
                          styles.badgeText,
                          { color: event.importance > 0.7 ? "#ef4444" : "#10b981" }
                        ]}>{event.importance > 0.7 ? "Critical" : "Insight"}</Text>
                      </View>
                      <TouchableOpacity
                        style={styles.deleteButton}
                        onPress={() => handleDelete(event.id)}
                      >
                        <MaterialCommunityIcons name="delete-outline" size={18} color="#ef4444" />
                      </TouchableOpacity>
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
                    {event.audio_file ? (
                      <TouchableOpacity
                        style={styles.sourceBadge}
                        onPress={() => playAudio(event.audio_file, event.id)}
                      >
                        <MaterialCommunityIcons
                          name={playingId === event.id ? "pause-circle" : "play-circle"}
                          size={14}
                          color={playingId === event.id ? "#38bdf8" : "#64748b"}
                        />
                        <Text style={[styles.sourceText, { color: playingId === event.id ? "#38bdf8" : "#64748b" }]}>
                          {playingId === event.id ? "Playing" : "Voice"}
                        </Text>
                      </TouchableOpacity>
                    ) : (
                      <View style={styles.sourceBadge}>
                        <MaterialCommunityIcons name="headphones" size={14} color="#64748b" />
                        <Text style={styles.sourceText}>Voice</Text>
                      </View>
                    )}
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
    alignItems: 'center',
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
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
  deleteButton: {
    padding: 4,
    borderRadius: 6,
    backgroundColor: "rgba(239, 68, 68, 0.1)",
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
