import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Animated, Easing } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";

export default function HomeScreen() {
  const [status, setStatus] = useState("Listening");
  const [scaleValue] = useState(new Animated.Value(1));
  const [opacityValue] = useState(new Animated.Value(0.3));

  useEffect(() => {
    if (status === "Listening") {
      Animated.loop(
        Animated.parallel([
          Animated.sequence([
            Animated.timing(scaleValue, {
              toValue: 1.5,
              duration: 2000,
              easing: Easing.out(Easing.ease),
              useNativeDriver: true,
            }),
            Animated.timing(scaleValue, {
              toValue: 1,
              duration: 2000,
              easing: Easing.in(Easing.ease),
              useNativeDriver: true,
            }),
          ]),
          Animated.sequence([
            Animated.timing(opacityValue, {
              toValue: 0.7,
              duration: 2000,
              useNativeDriver: true,
            }),
            Animated.timing(opacityValue, {
              toValue: 0.3,
              duration: 2000,
              useNativeDriver: true,
            }),
          ]),
        ])
      ).start();
    } else {
      scaleValue.setValue(1);
      opacityValue.setValue(0.3);
    }
  }, [status]);

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#050a12", "#0d1117"]}
        style={StyleSheet.absoluteFill}
      />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>SecondBrain</Text>
        <TouchableOpacity>
          <MaterialCommunityIcons name="account-circle-outline" size={28} color="#94a3b8" />
        </TouchableOpacity>
      </View>

      <View style={styles.auraContainer}>
        <Animated.View
          style={[
            styles.aura,
            {
              transform: [{ scale: scaleValue }],
              opacity: opacityValue,
            },
          ]}
        />
        <View style={styles.micCircle}>
          <MaterialCommunityIcons 
            name={status === "Listening" ? "microphone" : "pencil-outline"} 
            size={50} 
            color="#fff" 
          />
        </View>
      </View>

      <View style={styles.statusContainer}>
        <Text style={styles.statusText}>{status}</Text>
        <View style={styles.pulseIndicator} />
      </View>

      <View style={styles.statsContainer}>
        <View style={styles.statBox}>
          <Text style={styles.statValue}>1.2k</Text>
          <Text style={styles.statLabel}>Nodes</Text>
        </View>
        <View style={[styles.statBox, styles.statBoxActive]}>
          <Text style={[styles.statValue, { color: "#38bdf8" }]}>3</Text>
          <Text style={styles.statLabel}>Direct Insights</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statValue}>12h</Text>
          <Text style={styles.statLabel}>Uptime</Text>
        </View>
      </View>

      <TouchableOpacity 
        style={styles.actionButton}
        onPress={() => setStatus(s => s === "Listening" ? "Manual Mode" : "Listening")}
      >
        <Text style={styles.actionButtonText}>
          {status === "Listening" ? "Pause Listening" : "Resume Intelligence"}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    paddingTop: 60,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 40,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: "700",
    color: "#f8fafc",
    letterSpacing: -0.5,
  },
  auraContainer: {
    alignItems: "center",
    justifyContent: "center",
    height: 300,
  },
  aura: {
    position: "absolute",
    width: 150,
    height: 150,
    borderRadius: 75,
    backgroundColor: "#38bdf8",
  },
  micCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: "#1e293b",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    elevation: 10,
    shadowColor: "#38bdf8",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
  },
  statusContainer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    marginBottom: 40,
  },
  statusText: {
    color: "#94a3b8",
    fontSize: 16,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  pulseIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#10b981",
  },
  statsContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 40,
  },
  statBox: {
    flex: 1,
    alignItems: "center",
    padding: 16,
    backgroundColor: "rgba(30, 41, 59, 0.4)",
    borderRadius: 20,
    marginHorizontal: 4,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  statBoxActive: {
    borderColor: "rgba(56, 189, 248, 0.3)",
    backgroundColor: "rgba(56, 189, 248, 0.05)",
  },
  statValue: {
    fontSize: 20,
    fontWeight: "700",
    color: "#f8fafc",
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 10,
    color: "#64748b",
    textTransform: "uppercase",
    fontWeight: "600",
  },
  actionButton: {
    backgroundColor: "#38bdf8",
    paddingVertical: 18,
    borderRadius: 16,
    alignItems: "center",
    shadowColor: "#38bdf8",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
  },
  actionButtonText: {
    color: "#050a12",
    fontSize: 16,
    fontWeight: "700",
  },
});
