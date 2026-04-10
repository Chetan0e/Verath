import React, { useState } from "react";
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";

export default function AskScreen() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([
    { id: 1, text: "System ready. Ask me anything from your memories.", isBot: true },
  ]);

  const handleSend = () => {
    if (!query.trim()) return;
    
    const userMsg = { id: Date.now(), text: query, isBot: false };
    setMessages(prev => [...prev, userMsg]);
    setQuery("");

    // Simulate response
    setTimeout(() => {
      const botMsg = { 
        id: Date.now() + 1, 
        text: "I've analyzed your project notes. You previously mentioned wanting to improve the UI structure. Is that what you're referring to?", 
        isBot: true 
      };
      setMessages(prev => [...prev, botMsg]);
    }, 1000);
  };

  return (
    <KeyboardAvoidingView 
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
    >
      <LinearGradient
        colors={["#050a12", "#0d1117"]}
        style={StyleSheet.absoluteFill}
      />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Neural Query</Text>
      </View>

      <ScrollView contentContainerStyle={styles.chatContainer}>
        {messages.map(msg => (
          <View 
            key={msg.id} 
            style={[
              styles.messageWrapper, 
              msg.isBot ? styles.botWrapper : styles.userWrapper
            ]}
          >
            <View style={[
              styles.messageBubble,
              msg.isBot ? styles.botBubble : styles.userBubble
            ]}>
              <Text style={[
                styles.messageText,
                msg.isBot ? styles.botText : styles.userText
              ]}>
                {msg.text}
              </Text>
            </View>
          </View>
        ))}
      </ScrollView>

      <View style={styles.inputArea}>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Search memories..."
            placeholderTextColor="#64748b"
            value={query}
            onChangeText={setQuery}
            multiline
          />
          <TouchableOpacity style={styles.sendButton} onPress={handleSend}>
            <MaterialCommunityIcons name="arrow-up" size={24} color="#050a12" />
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
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
  chatContainer: {
    padding: 24,
    paddingBottom: 40,
  },
  messageWrapper: {
    marginBottom: 20,
    flexDirection: "row",
  },
  botWrapper: {
    justifyContent: "flex-start",
  },
  userWrapper: {
    justifyContent: "flex-end",
  },
  messageBubble: {
    maxWidth: "80%",
    padding: 16,
    borderRadius: 20,
  },
  botBubble: {
    backgroundColor: "rgba(30, 41, 59, 0.6)",
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  userBubble: {
    backgroundColor: "#38bdf8",
    borderBottomRightRadius: 4,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },
  botText: {
    color: "#f8fafc",
  },
  userText: {
    color: "#050a12",
    fontWeight: "500",
  },
  inputArea: {
    padding: 24,
    paddingTop: 0,
    backgroundColor: "transparent",
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#1e293b",
    borderRadius: 24,
    paddingLeft: 20,
    paddingRight: 6,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  input: {
    flex: 1,
    color: "#f8fafc",
    fontSize: 16,
    maxHeight: 100,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#38bdf8",
    alignItems: "center",
    justifyContent: "center",
  },
});
