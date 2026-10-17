import React, { useState, useEffect, useRef, useCallback } from "react";
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  Animated, 
  ScrollView, 
  RefreshControl,
  ActivityIndicator,
  Dimensions
} from "react-native";
import { Feather } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { colors, fonts, spacing, radius, shadows, intentColors } from "../theme";
import { getStatus, getStatistics, getTimeline, getRemindersUpcoming } from "../services/api";

const { width } = Dimensions.get("window");

// Skeleton component
const SkeletonCard = ({ style }) => {
  const [opacity] = useState(new Animated.Value(0.3));
  
  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.7, duration: 800, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.3, duration: 800, useNativeDriver: true }),
      ])
    ).start();
  }, []);
  
  return (
    <Animated.View style={[style, { opacity, backgroundColor: colors.card, borderRadius: radius.lg }]} />
  );
};

// Stat Card Component
const StatCard = ({ icon, label, value, color, delay = 0 }) => {
  const [animValue] = useState(new Animated.Value(0));
  
  useEffect(() => {
    Animated.timing(animValue, {
      toValue: 1,
      duration: 600,
      delay,
      useNativeDriver: true,
    }).start();
  }, []);
  
  return (
    <Animated.View style={[styles.statCard, { opacity: animValue, transform: [{ translateY: animValue.interpolate({ inputRange: [0, 1], outputRange: [20, 0] }) }] }]}>
      <View style={[styles.statIcon, { backgroundColor: color + '15' }]}>
        <Feather name={icon} size={20} color={color} />
      </View>
      <View>
        <Text style={styles.statLabel}>{label}</Text>
        <Text style={styles.statValue}>{value}</Text>
      </View>
    </Animated.View>
  );
};

// Timeline Item Component
const TimelineItem = ({ item, index }) => {
  const intent = item.intent || 'general';
  const intentColor = intentColors[intent] || intentColors.task;
  const time = item.timestamp ? new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
  
  return (
    <View style={[styles.timelineItem, { borderLeftColor: intentColor.border }]}>
      <Text style={styles.timelineTime}>{time}</Text>
      <View style={styles.timelineContent}>
        <Text style={styles.timelineText} numberOfLines={2}>{item.text || '—'}</Text>
        <View style={styles.timelineMeta}>
          <View style={[styles.badge, { backgroundColor: intentColor.bg }]}>
            <Text style={[styles.badgeText, { color: intentColor.text }]}>{intent}</Text>
          </View>
          {item.speaker && (
            <Text style={styles.speakerText}><Feather name="user" size={10} /> {item.speaker}</Text>
          )}
        </View>
      </View>
    </View>
  );
};

export default function HomeScreen({ navigation }) {
  const [username, setUsername] = useState('');
  const [greeting, setGreeting] = useState('morning');
  const [stats, setStats] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pulseAnim] = useState(new Animated.Value(1));
  
  // Get greeting based on time
  useEffect(() => {
    const hour = new Date().getHours();
    setGreeting(hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening');
  }, []);
  
  // Get username
  useEffect(() => {
    AsyncStorage.getItem('verath_username').then(name => {
      if (name) setUsername(name);
    });
  }, []);
  
  // Pulse animation for mic button
  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.15, duration: 1000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
  }, []);
  
  // Load all data
  const loadData = useCallback(async () => {
    try {
      const [statsRes, timelineRes, remindersRes] = await Promise.all([
        getStatistics(),
        getTimeline(),
        getRemindersUpcoming()
      ]);
      
      setStats(statsRes);
      setTimeline(timelineRes.timeline?.slice(0, 5) || []);
      setReminders(remindersRes.reminders?.slice(0, 3) || []);
    } catch (error) {
      console.error('Error loading home data:', error);
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    loadData();
    // Refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);
  
  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };
  
  const totalMemories = stats?.total || 0;
  const deadlineCount = stats?.by_intent?.deadline || 0;
  const peopleCount = Object.keys(stats?.by_speaker || {}).length;
  const avgImportance = Math.round((stats?.avg_importance || 0) * 100);
  
  return (
    <View style={styles.container}>
      <ScrollView 
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accentPrimary} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Good {greeting},</Text>
            <Text style={styles.username}>{username || 'User'}</Text>
          </View>
          <TouchableOpacity style={styles.avatar} onPress={() => navigation.navigate('Settings')}>
            <Text style={styles.avatarText}>{(username || 'U').charAt(0).toUpperCase()}</Text>
          </TouchableOpacity>
        </View>
        
        {/* Mic Button */}
        <View style={styles.micContainer}>
          <Animated.View style={[styles.pulseRing, { transform: [{ scale: pulseAnim }], opacity: 0.3 }]} />
          <TouchableOpacity style={styles.micButton} onPress={() => navigation.navigate('Ask')}>
            <View style={styles.micInner}>
              <Feather name="mic" size={32} color={colors.textPrimary} />
            </View>
          </TouchableOpacity>
          <Text style={styles.micText}>Tap to ask Verath</Text>
        </View>
        
        {/* Stats Grid */}
        <View style={styles.statsGrid}>
          {loading ? (
            <>
              <SkeletonCard style={[styles.statCard, { height: 80 }]} />
              <SkeletonCard style={[styles.statCard, { height: 80 }]} />
              <SkeletonCard style={[styles.statCard, { height: 80 }]} />
              <SkeletonCard style={[styles.statCard, { height: 80 }]} />
            </>
          ) : (
            <>
              <StatCard icon="database" label="Memories" value={totalMemories.toString()} color={colors.accentPrimary} delay={0} />
              <StatCard icon="alert-circle" label="Deadlines" value={deadlineCount.toString()} color={colors.accentWarm} delay={100} />
              <StatCard icon="users" label="People" value={peopleCount.toString()} color={colors.accentSecondary} delay={200} />
              <StatCard icon="trending-up" label="Importance" value={`${avgImportance}%`} color={colors.accentGold} delay={300} />
            </>
          )}
        </View>
        
        {/* Recent Timeline */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Memories</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Timeline')}>
              <Text style={styles.seeAll}>See all</Text>
            </TouchableOpacity>
          </View>
          
          {loading ? (
            <SkeletonCard style={{ height: 200, marginTop: spacing.md }} />
          ) : timeline.length === 0 ? (
            <View style={styles.emptyCard}>
              <Feather name="inbox" size={32} color={colors.textTertiary} />
              <Text style={styles.emptyText}>No memories yet</Text>
              <Text style={styles.emptySubtext}>Tap the mic to record your first memory</Text>
            </View>
          ) : (
            <View style={styles.timelineList}>
              {timeline.map((item, index) => (
                <TimelineItem key={item.id || index} item={item} index={index} />
              ))}
            </View>
          )}
        </View>
        
        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <TouchableOpacity style={styles.actionBtn} onPress={() => navigation.navigate('Ask')}>
            <View style={[styles.actionIcon, { backgroundColor: colors.accentPrimary + '20' }]}>
              <Feather name="message-circle" size={20} color={colors.accentPrimary} />
            </View>
            <Text style={styles.actionText}>Ask Verath</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.actionBtn} onPress={() => navigation.navigate('Timeline')}>
            <View style={[styles.actionIcon, { backgroundColor: colors.accentSecondary + '20' }]}>
              <Feather name="clock" size={20} color={colors.accentSecondary} />
            </View>
            <Text style={styles.actionText}>Timeline</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    padding: spacing.lg,
    paddingTop: 60,
    paddingBottom: 100,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  greeting: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.textSecondary,
  },
  username: {
    fontFamily: fonts.display,
    fontSize: 24,
    color: colors.textPrimary,
    fontWeight: '700',
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: radius.lg,
    backgroundColor: colors.accentPrimary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontFamily: fonts.bodyMedium,
    fontSize: 18,
    color: colors.textPrimary,
    fontWeight: '600',
  },
  micContainer: {
    alignItems: 'center',
    marginVertical: spacing.xl,
  },
  pulseRing: {
    position: 'absolute',
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: colors.accentPrimary,
  },
  micButton: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.glow,
  },
  micInner: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.accentPrimary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  micText: {
    fontFamily: fonts.body,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: spacing.md,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  statCard: {
    flex: 1,
    minWidth: (width - spacing.lg * 2 - spacing.md) / 2,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  statIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  statLabel: {
    fontFamily: fonts.body,
    fontSize: 11,
    color: colors.textTertiary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  statValue: {
    fontFamily: fonts.display,
    fontSize: 20,
    color: colors.textPrimary,
    fontWeight: '700',
  },
  section: {
    marginBottom: spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: 18,
    color: colors.textPrimary,
  },
  seeAll: {
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.accentPrimary,
  },
  timelineList: {
    gap: spacing.sm,
  },
  timelineItem: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderLeftWidth: 3,
    flexDirection: 'row',
    gap: spacing.md,
  },
  timelineTime: {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textTertiary,
    minWidth: 45,
  },
  timelineContent: {
    flex: 1,
  },
  timelineText: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
    lineHeight: 20,
  },
  timelineMeta: {
    flexDirection: 'row',
    gap: spacing.sm,
    alignItems: 'center',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: radius.pill,
  },
  badgeText: {
    fontFamily: fonts.bodyMedium,
    fontSize: 10,
    textTransform: 'capitalize',
  },
  speakerText: {
    fontFamily: fonts.body,
    fontSize: 11,
    color: colors.textSecondary,
  },
  emptyCard: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.xl,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: 'dashed',
  },
  emptyText: {
    fontFamily: fonts.bodyMedium,
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  emptySubtext: {
    fontFamily: fonts.body,
    fontSize: 12,
    color: colors.textTertiary,
    marginTop: spacing.xs,
  },
  quickActions: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  actionBtn: {
    flex: 1,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  actionIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  actionText: {
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.textPrimary,
  },
});
