import React, { useState } from "react";
import { 
  View, 
  Text, 
  StyleSheet, 
  TextInput, 
  TouchableOpacity, 
  KeyboardAvoidingView, 
  Platform, 
  Dimensions, 
  ActivityIndicator,
  Alert
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { TOKEN_KEY, REFRESH_KEY, USERNAME_KEY } from "../services/authKeys";
import axios from "axios";
import { API_BASE_URL } from "../config";

const { width } = Dimensions.get("window");
const API_BASE = API_BASE_URL; // Use centralized config

export default function LoginScreen({ onLoginSuccess, onSwitchToRegister }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!username || !password) {
      Alert.alert("Error", "Please enter both username and password");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/auth/login`, {
        username,
        password,
      });

      if (response.data.access_token) {
        await AsyncStorage.setItem(TOKEN_KEY, response.data.access_token);
        if (response.data.refresh_token) {
          await AsyncStorage.setItem(REFRESH_KEY, response.data.refresh_token);
        }
        await AsyncStorage.setItem(USERNAME_KEY, username);
        onLoginSuccess();
      } else {
        Alert.alert("Login Failed", "Invalid credentials");
      }
    } catch (error) {
      console.error(error);
      const ERROR_MSG = error.response?.data?.detail || "Could not reach the neural core.";
      Alert.alert("Connection Error", ERROR_MSG);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView 
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
    >
      <LinearGradient
        colors={["#080b14", "#0f172a", "#080b14"]}
        style={StyleSheet.absoluteFill}
      />
      
      <View style={styles.header}>
        <View style={styles.logoContainer}>
          <LinearGradient
            colors={["#38bdf8", "#818cf8"]}
            style={styles.logoGradient}
          >
            <MaterialCommunityIcons name="brain" size={60} color="#fff" />
          </LinearGradient>
        </View>
        <Text style={styles.title}>Verath</Text>
        <Text style={styles.subtitle}>Initialize your neural connection</Text>
      </View>

      <View style={styles.form}>
        <View style={styles.inputContainer}>
          <MaterialCommunityIcons name="account-outline" size={20} color="#64748b" style={styles.inputIcon} />
          <TextInput
            style={styles.input}
            placeholder="Username"
            placeholderTextColor="#64748b"
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
          />
        </View>

        <View style={styles.inputContainer}>
          <MaterialCommunityIcons name="lock-outline" size={20} color="#64748b" style={styles.inputIcon} />
          <TextInput
            style={styles.input}
            placeholder="Password"
            placeholderTextColor="#64748b"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
        </View>

        <TouchableOpacity 
          style={styles.button} 
          onPress={handleLogin}
          disabled={loading}
        >
          <LinearGradient
            colors={["#38bdf8", "#2563eb"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.buttonGradient}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>ESTABLISH LINK</Text>
            )}
          </LinearGradient>
        </TouchableOpacity>

        <TouchableOpacity style={styles.footer} onPress={onSwitchToRegister}>
          <Text style={styles.footerText}>
            No neural profile? <Text style={styles.footerLink}>Create Instance</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
  },
  header: {
    alignItems: "center",
    marginBottom: 48,
  },
  logoContainer: {
    width: 100,
    height: 100,
    borderRadius: 30,
    overflow: "hidden",
    marginBottom: 20,
    elevation: 20,
    shadowColor: "#38bdf8",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
  },
  logoGradient: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    fontSize: 36,
    fontWeight: "900",
    color: "#f8fafc",
    letterSpacing: -1,
  },
  subtitle: {
    fontSize: 14,
    color: "#64748b",
    marginTop: 8,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  form: {
    gap: 16,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(15, 23, 42, 0.6)",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
    paddingHorizontal: 16,
    height: 60,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    color: "#f8fafc",
    fontSize: 16,
  },
  button: {
    height: 60,
    borderRadius: 16,
    overflow: "hidden",
    marginTop: 12,
    elevation: 8,
    shadowColor: "#38bdf8",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
  },
  buttonGradient: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "800",
    letterSpacing: 1,
  },
  footer: {
    marginTop: 24,
    alignItems: "center",
  },
  footerText: {
    color: "#64748b",
    fontSize: 14,
  },
  footerLink: {
    color: "#38bdf8",
    fontWeight: "700",
  },
});
