import React from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Switch } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";

export default function SettingsScreen() {
  const [privacyMode, setPrivacyMode] = React.useState(false);
  const [autoSync, setAutoSync] = React.useState(true);

  const SettingItem = ({ icon, label, value, onValueChange, type = "switch" }) => (
    <View style={styles.settingItem}>
      <View style={styles.settingLeft}>
        <View style={styles.iconBox}>
          <MaterialCommunityIcons name={icon} size={22} color="#38bdf8" />
        </View>
        <Text style={styles.settingLabel}>{label}</Text>
      </View>
      {type === "switch" ? (
        <Switch
          value={value}
          onValueChange={onValueChange}
          trackColor={{ false: "#1e293b", true: "#38bdf8" }}
          thumbColor={value ? "#fff" : "#94a3b8"}
        />
      ) : (
        <MaterialCommunityIcons name="chevron-right" size={24} color="#64748b" />
      )}
    </View>
  );

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#050a12", "#0d1117"]}
        style={StyleSheet.absoluteFill}
      />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>System Configuration</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Intelligence</Text>
          <SettingItem 
            icon="shield-lock-outline" 
            label="Privacy Mode" 
            value={privacyMode} 
            onValueChange={setPrivacyMode} 
          />
          <SettingItem 
            icon="sync" 
            label="Cloud Synchronization" 
            value={autoSync} 
            onValueChange={setAutoSync} 
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account</Text>
          <SettingItem icon="account-outline" label="Profile Settings" type="chevron" />
          <SettingItem icon="database-outline" label="Storage Management" type="chevron" />
          <SettingItem icon="bell-outline" label="Notification Clusters" type="chevron" />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>System</Text>
          <SettingItem icon="information-outline" label="Core Version" type="chevron" />
          <SettingItem icon="help-circle-outline" label="Neural Support" type="chevron" />
        </View>

        <TouchableOpacity style={styles.logoutButton}>
          <Text style={styles.logoutText}>Purge Session (Logout)</Text>
        </TouchableOpacity>
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
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: "700",
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: 1.5,
    marginBottom: 16,
    marginLeft: 4,
  },
  settingItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "rgba(30, 41, 59, 0.4)",
    padding: 16,
    borderRadius: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  settingLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: "rgba(56, 189, 248, 0.1)",
    alignItems: "center",
    justifyContent: "center",
  },
  settingLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: "#f8fafc",
  },
  logoutButton: {
    marginTop: 20,
    padding: 18,
    borderRadius: 16,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.2)",
    backgroundColor: "rgba(239, 68, 68, 0.05)",
  },
  logoutText: {
    color: "#ef4444",
    fontSize: 15,
    fontWeight: "700",
  },
});
