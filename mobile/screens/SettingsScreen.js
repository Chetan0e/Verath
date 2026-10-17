import React from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Switch, Dimensions, Alert } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";

import AsyncStorage from "@react-native-async-storage/async-storage";
import { TOKEN_KEY, REFRESH_KEY, USERNAME_KEY } from "../services/authKeys";

const { width } = Dimensions.get("window");

export default function SettingsScreen({ onLogout }) {
  const [privacyMode, setPrivacyMode] = React.useState(false);
  const [autoSync, setAutoSync] = React.useState(true);
  const [username, setUsername] = React.useState("");

  React.useEffect(() => {
    AsyncStorage.getItem('verath_privacy_mode').then(val => {
      if (val !== null) setPrivacyMode(val === 'true');
    });
    AsyncStorage.getItem('verath_auto_sync').then(val => {
      if (val !== null) setAutoSync(val === 'true');
    });
    AsyncStorage.getItem(USERNAME_KEY).then(val => {
      if (val) setUsername(val);
    });
  }, []);

  const handlePrivacyChange = async (val) => {
    setPrivacyMode(val);
    await AsyncStorage.setItem('verath_privacy_mode', String(val));
  };

  const handleSyncChange = async (val) => {
    setAutoSync(val);
    await AsyncStorage.setItem('verath_auto_sync', String(val));
  };

  const handleLogout = async () => {
    try {
      await AsyncStorage.removeItem(TOKEN_KEY);
      await AsyncStorage.removeItem(REFRESH_KEY);
      await AsyncStorage.removeItem(USERNAME_KEY);
      if (onLogout) onLogout();
    } catch (e) {
      console.error(e);
    }
  };

  const SettingItem = ({ icon, label, value, onValueChange, type = "switch", subtitle, onPress }) => (
    <TouchableOpacity 
      activeOpacity={type === "chevron" ? 0.7 : 1}
      style={styles.settingItem}
      onPress={type === "chevron" ? onPress : undefined}
    >
      <View style={styles.settingLeft}>
        <LinearGradient
          colors={["rgba(56, 189, 248, 0.1)", "rgba(129, 140, 248, 0.1)"]}
          style={styles.iconBox}
        >
          <MaterialCommunityIcons name={icon} size={22} color="#38bdf8" />
        </LinearGradient>
        <View>
          <Text style={styles.settingLabel}>{label}</Text>
          {subtitle && <Text style={styles.settingSubtitle}>{subtitle}</Text>}
        </View>
      </View>
      {type === "switch" ? (
        <Switch
          value={value}
          onValueChange={onValueChange}
          trackColor={{ false: "#1e293b", true: "#38bdf8" }}
          thumbColor={value ? "#fff" : "#94a3b8"}
          ios_backgroundColor="#1e293b"
        />
      ) : (
        <MaterialCommunityIcons name="chevron-right" size={20} color="#475569" />
      )}
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#080b14", "#0f172a", "#080b14"]}
        style={StyleSheet.absoluteFill}
      />
      
      <View style={styles.header}>
        <View>
          <Text style={styles.headerSubtitle}>Core Parameters</Text>
          <Text style={styles.headerTitle}>System Config</Text>
        </View>
        <TouchableOpacity 
          style={styles.headerIcon}
          onPress={() => Alert.alert("System Config", "Verath Mobile Client v1.0.4 - All neural nodes nominal.")}
          accessibilityLabel="System status"
        >
          <MaterialCommunityIcons name="cog-outline" size={24} color="#38bdf8" />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Intelligence</Text>
          <SettingItem 
            icon="shield-lock" 
            label="Privacy Mode" 
            subtitle="Local processing only"
            value={privacyMode} 
            onValueChange={handlePrivacyChange} 
          />
          <SettingItem 
            icon="sync" 
            label="Cloud Sync" 
            subtitle="Secure neural backup"
            value={autoSync} 
            onValueChange={handleSyncChange} 
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>User Profile</Text>
          <View style={styles.cardContainer}>
            <SettingItem 
              icon="account" 
              label="Identity Settings" 
              type="chevron"
              onPress={() => Alert.alert("Identity", `Active Profile: ${username || 'Standard User'}`)}
            />
            <View style={styles.separator} />
            <SettingItem 
              icon="database" 
              label="Memory Index" 
              type="chevron" 
              onPress={() => Alert.alert("Memory Index", "Local ChromaDB vector index is synchronized.")}
            />
            <View style={styles.separator} />
            <SettingItem 
              icon="bell-ring" 
              label="Neural Alerts" 
              type="chevron" 
              onPress={() => Alert.alert("Neural Alerts", "Proactive reminder notifications are active.")}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Environment</Text>
          <View style={styles.cardContainer}>
            <SettingItem 
              icon="volume-high" 
              label="Audio Precision" 
              type="chevron" 
              onPress={() => Alert.alert("Audio Precision", "16kHz, 16-bit PCM voice sampling enabled.")}
            />
            <View style={styles.separator} />
            <SettingItem 
              icon="language-python" 
              label="Model Config" 
              type="chevron" 
              onPress={() => Alert.alert("Model Config", "Hybrid pipeline: Local Faster-Whisper + Neural Core.")}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Global</Text>
          <SettingItem 
            icon="information" 
            label="Core version 1.0.4" 
            type="chevron" 
            onPress={() => Alert.alert("Verath Mobile", "Core Version: 1.0.4\nClient Architecture: React Native / Expo")}
          />
          <SettingItem 
            icon="lifebuoy" 
            label="Technical Support" 
            type="chevron" 
            onPress={() => Alert.alert("Support", "Verath Engineering Helpdesk: support@verath.local")}
          />
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <LinearGradient
            colors={["rgba(239, 68, 68, 0.1)", "rgba(239, 68, 68, 0.05)"]}
            style={styles.logoutGradient}
          >
            <MaterialCommunityIcons name="power" size={20} color="#ef4444" />
            <Text style={styles.logoutText}>Terminate Neural Session</Text>
          </LinearGradient>
        </TouchableOpacity>
        
        <Text style={styles.versionInfo}>SECOND BRAIN OS © 2026</Text>
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
  },
  headerIcon: {
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
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: "800",
    color: "#38bdf8",
    textTransform: "uppercase",
    letterSpacing: 1.5,
    marginBottom: 16,
    marginLeft: 4,
  },
  cardContainer: {
    backgroundColor: "rgba(15, 23, 42, 0.4)",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
    overflow: "hidden",
  },
  settingItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 18,
    backgroundColor: "rgba(30, 41, 59, 0.2)",
  },
  settingLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
  },
  iconBox: {
    width: 42,
    height: 42,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(56, 189, 248, 0.2)",
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: "700",
    color: "#f1f5f9",
  },
  settingSubtitle: {
    fontSize: 12,
    color: "#64748b",
    marginTop: 2,
    fontWeight: "500",
  },
  separator: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.05)",
    marginHorizontal: 18,
  },
  logoutButton: {
    marginTop: 10,
    borderRadius: 20,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.2)",
  },
  logoutGradient: {
    padding: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  logoutText: {
    color: "#ef4444",
    fontSize: 15,
    fontWeight: "800",
  },
  versionInfo: {
    textAlign: "center",
    color: "#334155",
    fontSize: 10,
    fontWeight: "800",
    marginTop: 32,
    letterSpacing: 2,
  },
});
