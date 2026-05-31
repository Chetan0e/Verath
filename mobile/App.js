import React, { useState, useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SplashScreen from "expo-splash-screen";
import { useFonts } from "expo-font";
import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
} from "@expo-google-fonts/inter";
import {
  SpaceGrotesk_500Medium,
  SpaceGrotesk_700Bold,
} from "@expo-google-fonts/space-grotesk";
import Tabs from "./screens/Tabs";
import LoginScreen from "./screens/LoginScreen";
import RegisterScreen from "./screens/RegisterScreen";
import { View, ActivityIndicator, Text, StyleSheet } from "react-native";
import { colors } from "./theme";

// Keep splash screen visible while loading
SplashScreen.preventAutoHideAsync();

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);

  // Load fonts
  const [fontsLoaded, fontError] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    SpaceGrotesk_500Medium,
    SpaceGrotesk_700Bold,
  });

  // Check auth status
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = await AsyncStorage.getItem("verath_token");
        setIsAuthenticated(!!token);
      } catch (e) {
        console.error("Auth check error:", e);
      } finally {
        // Always mark auth as checked, even on failure
        setAuthChecked(true);
      }
    };
    checkAuth();
  }, []);

  // FIX: Hide splash screen via useEffect — not via onLayout callback.
  // Previously, hideAsync() was only called inside onLayoutRootView, which
  // is attached to the root View. But during the loading state, the component
  // returns a different View WITHOUT onLayout, so hideAsync() would never
  // fire if loading got stuck — causing an indefinite splash screen hang.
  // Now hideAsync() is tied directly to state resolution, not layout mounting.
  useEffect(() => {
    if ((fontsLoaded || fontError) && authChecked) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded, fontError, authChecked]);

  // Loading state — splash is still visible, this renders underneath it
  if ((!fontsLoaded && !fontError) || !authChecked) {
    return (
      <View style={styles.loadingContainer}>
        <View style={styles.logoMark}>
          <Text style={styles.logoText}>V</Text>
        </View>
        <ActivityIndicator
          size="small"
          color={colors.accentPrimary}
          style={styles.spinner}
        />
      </View>
    );
  }

  // Auth screens — no onLayout needed anymore
  if (!isAuthenticated) {
    return (
      <View style={styles.container}>
        {isRegistering ? (
          <RegisterScreen
            onRegisterSuccess={() => setIsRegistering(false)}
            onSwitchToLogin={() => setIsRegistering(false)}
          />
        ) : (
          <LoginScreen
            onLoginSuccess={() => setIsAuthenticated(true)}
            onSwitchToRegister={() => setIsRegistering(true)}
          />
        )}
      </View>
    );
  }

  // Main app — no onLayout needed anymore
  return (
    <View style={styles.container}>
      <NavigationContainer>
        <Tabs onLogout={() => setIsAuthenticated(false)} />
      </NavigationContainer>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: "center",
    alignItems: "center",
  },
  logoMark: {
    width: 64,
    height: 64,
    borderRadius: 16,
    backgroundColor: colors.accentPrimary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 24,
    shadowColor: colors.accentPrimary,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 10,
  },
  logoText: {
    fontFamily: "SpaceGrotesk_700Bold",
    fontSize: 28,
    color: "#fff",
  },
  spinner: {
    marginTop: 8,
  },
});