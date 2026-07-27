import React, { useState } from "react";
import { 
  View, Text, StyleSheet, TextInput, TouchableOpacity, 
  KeyboardAvoidingView, Platform, Dimensions, 
  ActivityIndicator, Alert
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_BASE_URL } from "../config";

const { width } = Dimensions.get("window");
const API_BASE = API_BASE_URL;

export default function RegisterScreen({ onRegisterSuccess, onSwitchToLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [focusedInput, setFocusedInput] = useState(null);

  const handleRegister = async () => {
    if (!username || !password) {
      Alert.alert("Error", "Please fill all fields");
      return;
    }
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/auth/signup`, {
        username,
        password,
      });

      if (response.status === 200 || response.status === 201) {
        // FIX (#244): Signup only creates the account — it does not return
        // an auth token. Previously onRegisterSuccess() was called here
        // directly, which just flipped the app back to the login screen
        // with isAuthenticated still false and no token in storage.
        //
        // To actually authenticate the user post-registration (mirroring
        // onLoginSuccess in App.js), we log in immediately with the same
        // credentials, store the resulting token the same way LoginScreen
        // does, and only then call onRegisterSuccess(). If this second
        // step fails for any reason, we fall back to the login screen
        // with a clear message rather than pretending the user is in.
        try {
          const loginResponse = await axios.post(`${API_BASE}/auth/login`, {
            username,
            password,
          });
          const token = loginResponse.data?.access_token;
          if (token) {
            await AsyncStorage.setItem("verath_token", token);
            onRegisterSuccess();
          } else {
            Alert.alert("Account Created", "Please log in to continue.");
            onSwitchToLogin();
          }
        } catch (loginError) {
          console.error(loginError);
          Alert.alert("Account Created", "Please log in to continue.");
          onSwitchToLogin();
        }
      } else {
        Alert.alert("Registration Failed", response.data.detail || "Error");
      }
    } catch (error) {
      console.error(error);
      const ERROR_MSG = error.response?.data?.detail || "Could not synchronize with the neural core.";
      Alert.alert("Deployment Error", ERROR_MSG);
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
            colors={["#818cf8", "#c084fc"]}
            style={styles.logoGradient}
          >
            <MaterialCommunityIcons name="brain" size={60} color="#fff" />
          </LinearGradient>
        </View>
        <Text style={styles.title}>New Instance</Text>
        <Text style={styles.subtitle}>Register your digital consciousness</Text>
      </View>

      <View style={styles.form}>

        <View style={[
          styles.inputContainer,
          focusedInput === 'username' && styles.inputFocused
        ]}>
          <MaterialCommunityIcons name="account-plus-outline" size={20} color="#94a3b8" style={styles.inputIcon} />
          <TextInput
            style={styles.input}
            placeholder="Choose Username"
            placeholderTextColor="#64748b"
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            onFocus={() => setFocusedInput('username')}
            onBlur={() => setFocusedInput(null)}
          />
        </View>

        <View style={[
          styles.inputContainer,
          focusedInput === 'password' && styles.inputFocused
        ]}>
          <MaterialCommunityIcons name="shield-key-outline" size={20} color="#94a3b8" style={styles.inputIcon} />
          <TextInput
            style={styles.input}
            placeholder="Secure Password"
            placeholderTextColor="#64748b"
            value={password}
            onChangeText={setPassword}
            secureTextEntry={!showPassword}
            onFocus={() => setFocusedInput('password')}
            onBlur={() => setFocusedInput(null)}
          />
          <TouchableOpacity 
            onPress={() => setShowPassword(!showPassword)} 
            style={styles.eyeIcon}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <MaterialCommunityIcons 
              name={showPassword ? "eye-off" : "eye"} 
              size={20} 
              color="#94a3b8"
            />
          </TouchableOpacity>
        </View>

        <TouchableOpacity 
          style={styles.button} 
          onPress={handleRegister}
          disabled={loading}
        >
          <LinearGradient
            colors={["#818cf8", "#6366f1"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.buttonGradient}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>DEPLOY CORE</Text>
            )}
          </LinearGradient>
        </TouchableOpacity>

        <TouchableOpacity style={styles.footer} onPress={onSwitchToLogin}>
          <Text style={styles.footerText}>
            Already linked? <Text style={styles.footerLink}>Establish Session</Text>
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
    shadowColor: "#818cf8",
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
    color: "#94a3b8",
    marginTop: 8,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  form: {
    gap: 16,
    backgroundColor: "rgba(15, 23, 42, 0.7)",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    padding: 24,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(15, 23, 42, 0.85)",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)",
    paddingHorizontal: 16,
    height: 60,
  },
  inputFocused: {
    borderColor: "#818cf8",
    borderWidth: 1.5,
  },
  eyeIcon: {
    marginLeft: 8,
    padding: 4,
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
    shadowColor: "#818cf8",
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
    color: "#94a3b8",
    fontSize: 14,
  },
  footerLink: {
    color: "#818cf8",
    fontWeight: "700",
  },
});
