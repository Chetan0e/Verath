import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { askQuestion } from '../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { colors, fonts, spacing, radius, intentColors } from '../theme';

const { width } = Dimensions.get('window');

const SUGGESTIONS = [
  "What meetings do I have?",
  "What are my upcoming deadlines?",
  "What tasks did I mention?",
  "What did I commit to this week?"
];

const HISTORY_TURNS = 6;

const Message = ({ text, isUser, sources, confidence }) => {
  return (
    <View style={[styles.messageRow, isUser && styles.messageRowUser]}>
      {!isUser && (
        <View style={styles.avatarV}>
          <Text style={styles.avatarText}>V</Text>
        </View>
      )}
      <View style={[styles.messageBubble, isUser ? styles.bubbleUser : styles.bubbleAI]}>
        <Text style={[styles.messageText, isUser && styles.messageTextUser]}>{text}</Text>
        {!isUser && sources && sources.length > 0 && (
          <View style={styles.sourcesRow}>
            {sources.slice(0, 3).map((s, i) => (
              <View key={i} style={styles.sourceChip}>
                <View style={[styles.sourceDot, { backgroundColor: intentColors[s.intent]?.text || colors.accentPrimary }]} />
                <Text style={styles.sourceText}>{Math.round((s.confidence || 0) * 100)}%</Text>
              </View>
            ))}
          </View>
        )}
        {confidence !== undefined && !isUser && (
          <Text style={styles.confidenceText}>Confidence: {Math.round(confidence * 100)}%</Text>
        )}
      </View>
      {isUser && (
        <View style={styles.avatarUser}>
          <Feather name="user" size={16} color={colors.textPrimary} />
        </View>
      )}
    </View>
  );
};

export default function AskScreen({ navigation }) {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const scrollViewRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  const handleSubmit = async () => {
    if (!query.trim() || loading) return;

    const userQuery = query.trim();
    setQuery('');

    setMessages(prev => [...prev, { id: Date.now(), text: userQuery, isUser: true }]);
    setLoading(true);
    scrollToBottom();

    const history = messages
      .slice(-HISTORY_TURNS)
      .map(m => ({ role: m.isUser ? 'user' : 'assistant', content: m.text }));

    try {
      const response = await askQuestion(userQuery, { history });
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: response.answer || "I couldn't find an answer to that question.",
        isUser: false,
        sources: response.sources || [],
        confidence: response.confidence_score || 0
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: "Sorry, I couldn't connect to Verath. Please check your connection and try again.",
        isUser: false
      }]);
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  };

  const handleSuggestion = (suggestion) => {
    setQuery(suggestion);
    inputRef.current?.focus();
  };

  const clearChat = () => {
    Alert.alert(
      'Clear conversation?',
      'This will remove all messages.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Clear', style: 'destructive', onPress: () => setMessages([]) }
      ]
    );
  };

  const showEmptyState = messages.length === 0 && !loading;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Ask Verath</Text>
        {messages.length > 0 && (
          <TouchableOpacity onPress={clearChat}>
            <Feather name="trash-2" size={20} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>

      <ScrollView
        ref={scrollViewRef}
        style={styles.messagesContainer}
        contentContainerStyle={styles.messagesContent}
        showsVerticalScrollIndicator={false}
      >
        {showEmptyState ? (
          <View style={styles.emptyState}>
            <View style={styles.emptyIcon}>
              <Feather name="message-circle" size={40} color={colors.accentPrimary} />
            </View>
            <Text style={styles.emptyTitle}>Ask anything about your memories</Text>
            <Text style={styles.emptySubtitle}>
              Try asking about meetings, deadlines, tasks, or people you mentioned
            </Text>
            
            <View style={styles.suggestionsContainer}>
              {SUGGESTIONS.map((suggestion, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.suggestionChip}
                  onPress={() => handleSuggestion(suggestion)}
                >
                  <Text style={styles.suggestionText}>{suggestion}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ) : (
          <>
            {messages.map((message) => (
              <Message
                key={message.id}
                text={message.text}
                isUser={message.isUser}
                sources={message.sources}
                confidence={message.confidence}
              />
            ))}
            
            {loading && (
              <View style={styles.loadingRow}>
                <View style={styles.avatarV}>
                  <Text style={styles.avatarText}>V</Text>
                </View>
                <View style={styles.loadingBubble}>
                  <ActivityIndicator size="small" color={colors.accentPrimary} />
                  <Text style={styles.loadingText}>Thinking...</Text>
                </View>
              </View>
            )}
          </>
        )}
      </ScrollView>

      <View style={styles.inputContainer}>
        <View style={styles.inputWrapper}>
          <TextInput
            ref={inputRef}
            style={styles.input}
            placeholder="Ask Verath anything..."
            placeholderTextColor={colors.textTertiary}
            value={query}
            onChangeText={setQuery}
            multiline
            maxLength={500}
            returnKeyType="send"
            onSubmitEditing={handleSubmit}
            blurOnSubmit={false}
          />
          <TouchableOpacity
            style={[styles.sendButton, (!query.trim() || loading) && styles.sendButtonDisabled]}
            onPress={handleSubmit}
            disabled={!query.trim() || loading}
          >
            <Feather name="arrow-up" size={20} color={colors.textPrimary} />
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: {
    fontFamily: fonts.display,
    fontSize: 20,
    color: colors.textPrimary,
    fontWeight: '700',
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    padding: 24,
    paddingBottom: 40,
  },
  emptyState: {
    alignItems: 'center',
    paddingTop: 64,
    paddingHorizontal: 24,
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 32,
    backgroundColor: colors.accentPrimary + '15',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  emptyTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: 18,
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 40,
  },
  suggestionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  suggestionChip: {
    backgroundColor: colors.card,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border,
  },
  suggestionText: {
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.textSecondary,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 16,
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  avatarV: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.accentPrimary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  avatarText: {
    fontFamily: fonts.display,
    fontSize: 14,
    color: colors.textPrimary,
    fontWeight: '700',
  },
  avatarUser: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.accentSecondary,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  messageBubble: {
    maxWidth: width * 0.75,
    padding: 16,
    borderRadius: 20,
  },
  bubbleUser: {
    backgroundColor: colors.accentSecondary,
    borderBottomRightRadius: 6,
  },
  bubbleAI: {
    backgroundColor: colors.card,
    borderBottomLeftRadius: 6,
    borderWidth: 1,
    borderColor: colors.border,
  },
  messageText: {
    fontFamily: fonts.body,
    fontSize: 15,
    color: colors.textPrimary,
    lineHeight: 22,
  },
  messageTextUser: {
    color: colors.background,
  },
  sourcesRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  sourceChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.surface,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  sourceDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  sourceText: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.textSecondary,
  },
  confidenceText: {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textTertiary,
    marginTop: 4,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  loadingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.card,
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    borderBottomLeftRadius: 6,
  },
  loadingText: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.textSecondary,
  },
  inputContainer: {
    padding: 16,
    paddingBottom: Platform.OS === 'ios' ? 30 : 16,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.background,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: colors.card,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  input: {
    flex: 1,
    fontFamily: fonts.body,
    fontSize: 15,
    color: colors.textPrimary,
    maxHeight: 100,
    paddingTop: 8,
    paddingBottom: 8,
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.accentPrimary,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  sendButtonDisabled: {
    backgroundColor: colors.textMuted,
  },
});
