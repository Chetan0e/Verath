import React, { useState, useEffect, useRef } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Animated, Easing, Dimensions, ScrollView } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getStatus, getInsights, startRecording, getTimeline } from "../services/api";

const { width } = Dimensions.get("window");

export default function HomeScreen() {
  const [isListening, setIsListening] = useState(true);
  const [pulseAnim] = useState(new Animated.Value(1));
  const [stats, setStats] = useState({
    nodes: "0",
    insights: "0",
    uptime: "..."
  });
  const [neuralStream, setNeuralStream] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState("");
  const recordingActiveRef = useRef(false);

  const fetchStats = async () => {
    if (!isListening) return;
    try {
      const [statusData, insightsData] = await Promise.all([
        getStatus(),
        getInsights()
      ]);
      
      setStats({
        nodes: statusData.nodes?.toLocaleString() || "0",
        insights: insightsData.insights?.length?.toString() || "0",
        uptime: (statusData.status === "ok" || statusData.status === "running") ? "Online" : "Offline"
      });

      if (insightsData.insights) {
        setNeuralStream(insightsData.insights.slice(0, 5));
      }
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    }
  };

  const startVoiceRecording = async () => {
    try {
      setIsRecording(true);
      setRecordingStatus("Starting microphone...");
      recordingActiveRef.current = true;
      
      // Continuous recording loop with proper cancellation
      const recordLoop = async () => {
        while (recordingActiveRef.current && isListening) {
          try {
            const result = await startRecording(5); // Reduced to 5 seconds for faster response
            if (!recordingActiveRef.current || !isListening) {
              break; // Stop immediately if recording was cancelled
            }
            
            if (result.success) {
              setRecordingStatus("Recording active - Saving to timeline");
              // Fetch timeline after each recording to sync data
              await fetchTimelineData();
            } else {
              setRecordingStatus(`Recording failed: ${result.error}`);
              // Wait before retrying only if still active
              if (recordingActiveRef.current && isListening) {
                await new Promise(resolve => setTimeout(resolve, 2000));
              }
            }
          } catch (error) {
            console.error("Error in recording loop:", error);
            setRecordingStatus("Recording error - Retrying...");
            // Wait before retrying only if still active
            if (recordingActiveRef.current && isListening) {
              await new Promise(resolve => setTimeout(resolve, 2000));
            }
          }
        }
        
        // Clean up when loop exits
        if (!recordingActiveRef.current || !isListening) {
          setIsRecording(false);
          setRecordingStatus("");
        }
      };
      
      recordLoop();
    } catch (error) {
      console.error("Error starting recording:", error);
      setRecordingStatus("Recording error");
      setIsRecording(false);
      recordingActiveRef.current = false;
    }
  };

  const fetchTimelineData = async () => {
    try {
      const timelineData = await getTimeline();
      if (timelineData.timeline && timelineData.timeline.length > 0) {
        setRecordingStatus(`Timeline updated: ${timelineData.timeline.length} entries`);
        // Update neural stream with latest timeline entries
        setNeuralStream(timelineData.timeline.slice(0, 5).map(item => ({
          id: item.id,
          title: item.importance > 0.7 ? "Critical Memory" : "Memory Captured",
          text: item.text,
          timestamp: item.timestamp,
          speaker: item.speaker,
          intent: item.intent
        })));
      }
    } catch (error) {
      console.error("Error fetching timeline:", error);
    }
  };

  useEffect(() => {
    const checkAuthAndFetch = async () => {
      const token = await AsyncStorage.getItem("sb_token");
      if (token && isListening) {
        fetchStats();
      }
    };

    checkAuthAndFetch();
    const interval = setInterval(() => {
      checkAuthAndFetch();
    }, isListening ? 10000 : 30000);
    
    return () => clearInterval(interval);
  }, [isListening]);

  useEffect(() => {
    if (isListening) {
      startVoiceRecording();
      fetchTimelineData();
    } else {
      // Immediately stop recording when isListening becomes false
      recordingActiveRef.current = false;
      setIsRecording(false);
      setRecordingStatus("");
    }
  }, [isListening]);

  useEffect(() => {
    if (isListening) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.2,
            duration: 1500,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 1500,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [isListening]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      recordingActiveRef.current = false;
      setIsRecording(false);
      setRecordingStatus("");
    };
  }, []);

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#020617", "#0f172a", "#020617"]}
        style={StyleSheet.absoluteFill}
      />
      
      {/* Background Decorative Blobs */}
      <View style={[styles.blob, { top: -100, right: -100, backgroundColor: "rgba(56, 189, 248, 0.15)" }]} />
      <View style={[styles.blob, { bottom: -100, left: -100, backgroundColor: "rgba(129, 140, 248, 0.1)" }]} />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View>
            <Text style={styles.headerGreeting}>NEURAL INTERFACE v1.4</Text>
            <Text style={styles.headerTitle}>SecondBrain</Text>
          </View>
          <TouchableOpacity style={styles.profileButton}>
            <LinearGradient
              colors={["#38bdf8", "#818cf8"]}
              style={styles.profileGradient}
            >
              <MaterialCommunityIcons name="brain" size={24} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
        </View>

        <View style={styles.mainCoreContainer}>
          <View style={styles.visualizerContainer}>
            <Animated.View style={[styles.pulseRing, { transform: [{ scale: pulseAnim }], opacity: 0.25 }]} />
            <Animated.View style={[styles.pulseRing, { transform: [{ scale: Animated.multiply(pulseAnim, 1.5) }], opacity: 0.1 }]} />
            
            <TouchableOpacity 
              activeOpacity={0.9}
              onPress={() => setIsListening(!isListening)}
              style={styles.coreButton}
            >
              <LinearGradient
                colors={isListening ? ["#0ea5e9", "#2563eb"] : ["#334155", "#0f172a"]}
                style={styles.coreGradient}
              >
                <MaterialCommunityIcons 
                  name={isListening ? "pulse" : "power-off"} 
                  size={54} 
                  color="#fff" 
                />
              </LinearGradient>
            </TouchableOpacity>
          </View>

          <View style={styles.statusBadge}>
            <View style={[styles.statusDot, { backgroundColor: isListening ? "#10b981" : "#64748b" }]} />
            <Text style={styles.statusText}>{isListening ? "NEURAL CORE ACTIVE" : "SYSTEM STANDBY"}</Text>
          </View>
          
          {isRecording && (
            <View style={styles.recordingBadge}>
              <View style={styles.recordingDot} />
              <Text style={styles.recordingText}>{recordingStatus}</Text>
            </View>
          )}
        </View>

        <View style={styles.statsRow}>
          <View style={styles.compactStatCard}>
            <Text style={styles.compactStatLabel}>MEMORIES</Text>
            <Text style={styles.compactStatValue}>{stats.nodes}</Text>
          </View>
          <View style={[styles.compactStatCard, styles.compactStatCardActive]}>
            <Text style={[styles.compactStatLabel, { color: "#38bdf8" }]}>INSIGHTS</Text>
            <Text style={styles.compactStatValue}>{stats.insights}</Text>
          </View>
          <View style={styles.compactStatCard}>
            <Text style={styles.compactStatLabel}>STATUS</Text>
            <Text style={[styles.compactStatValue, { fontSize: 14, color: isListening ? "#10b981" : "#94a3b8" }]}>{stats.uptime}</Text>
          </View>
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>NEURAL STREAM</Text>
          <TouchableOpacity>
            <Text style={styles.seeAllText}>HISTORY</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.activityList}>
          {neuralStream.length > 0 ? (
            neuralStream.map((item, index) => (
              <View key={item.id || index} style={styles.glassCard}>
                <View style={styles.activityIconWrapper}>
                  <MaterialCommunityIcons 
                    name={item.intent === "task" ? "checkbox-marked-circle-outline" : "lightning-bolt"} 
                    size={20} 
                    color="#38bdf8" 
                  />
                </View>
                <View style={styles.activityInfo}>
                  <Text style={styles.activityMainText}>{item.title || "Insight Detected"}</Text>
                  <Text style={styles.activitySubText}>{item.text}</Text>
                </View>
                <Text style={styles.activityTimeLabel}>
                  {item.timestamp ? new Date(item.timestamp * 1000).toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' • ' + new Date(item.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "RECENT"}
                </Text>
              </View>
            ))
          ) : (
            <View style={[styles.glassCard, { justifyContent: 'center', padding: 30 }]}>
              <Text style={[styles.activitySubText, { textAlign: 'center' }]}>
                {isListening ? "Waiting for neural signals..." : "Interface Standby"}
              </Text>
            </View>
          )}
        </View>

        <TouchableOpacity 
          style={styles.actionButton}
          onPress={() => setIsListening(!isListening)}
        >
          <LinearGradient
            colors={["#38bdf8", "#2563eb"]}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
            style={styles.actionGradient}
          >
            <Text style={styles.actionButtonText}>
              {isListening ? "DEACTIVATE INTERFACE" : "INITIALIZE SYNC"}
            </Text>
            <MaterialCommunityIcons name="chevron-right" size={22} color="#fff" />
          </LinearGradient>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  blob: {
    position: "absolute",
    width: 300,
    height: 300,
    borderRadius: 150,
    filter: "blur(60px)",
  },
  scrollContent: {
    padding: 24,
    paddingTop: 60,
    paddingBottom: 110,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 40,
  },
  headerGreeting: {
    color: "#38bdf8",
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 2,
    marginBottom: 4,
  },
  headerTitle: {
    fontSize: 32,
    fontWeight: "900",
    color: "#f8fafc",
    letterSpacing: -1,
  },
  profileButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  profileGradient: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  mainCoreContainer: {
    alignItems: "center",
    marginBottom: 40,
  },
  visualizerContainer: {
    width: 260,
    height: 260,
    alignItems: "center",
    justifyContent: "center",
  },
  pulseRing: {
    position: "absolute",
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: "#38bdf8",
  },
  coreButton: {
    width: 130,
    height: 130,
    borderRadius: 65,
    elevation: 25,
    shadowColor: "#38bdf8",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 30,
    overflow: "hidden",
    borderWidth: 4,
    borderColor: "rgba(255,255,255,0.08)",
  },
  coreGradient: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(15, 23, 42, 0.7)",
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    marginTop: -10,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 10,
  },
  statusText: {
    color: "#f1f5f9",
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  recordingBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(239, 68, 68, 0.15)",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.3)",
    marginTop: 12,
  },
  recordingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#ef4444",
    marginRight: 10,
  },
  recordingText: {
    color: "#fca5a5",
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 32,
    gap: 12,
  },
  compactStatCard: {
    flex: 1,
    backgroundColor: "rgba(15, 23, 42, 0.4)",
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
    alignItems: "center",
  },
  compactStatCardActive: {
    borderColor: "rgba(56, 189, 248, 0.3)",
    backgroundColor: "rgba(56, 189, 248, 0.05)",
  },
  compactStatLabel: {
    fontSize: 9,
    color: "#64748b",
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 6,
  },
  compactStatValue: {
    fontSize: 20,
    fontWeight: "900",
    color: "#f8fafc",
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
    paddingHorizontal: 4,
  },
  sectionTitle: {
    color: "#f8fafc",
    fontSize: 14,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  seeAllText: {
    color: "#38bdf8",
    fontSize: 11,
    fontWeight: "700",
  },
  activityList: {
    gap: 12,
    marginBottom: 32,
  },
  glassCard: {
    backgroundColor: "rgba(15, 23, 42, 0.3)",
    borderRadius: 20,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  activityIconWrapper: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: "rgba(56, 189, 248, 0.1)",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 14,
  },
  activityInfo: {
    flex: 1,
  },
  activityMainText: {
    color: "#f1f5f9",
    fontSize: 14,
    fontWeight: "700",
  },
  activitySubText: {
    color: "#64748b",
    fontSize: 12,
    marginTop: 2,
  },
  activityTimeLabel: {
    fontSize: 9,
    color: "#475569",
    fontWeight: "800",
  },
  actionButton: {
    height: 64,
    borderRadius: 22,
    overflow: "hidden",
    elevation: 10,
    shadowColor: "#38bdf8",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
  },
  actionGradient: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  actionButtonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "900",
    letterSpacing: 1,
  },
});
