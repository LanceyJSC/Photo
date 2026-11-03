import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Animated, FlatList, Pressable, StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import YoutubePlayer, { YoutubeIframeRef } from 'react-native-youtube-iframe';
import { useKeepAwake } from 'expo-keep-awake';
import * as Haptics from 'expo-haptics';
import { CHANNELS, Video } from './src/channels';
import { Static } from './src/Static';

const PINK = '#ff2d95', YELLOW = '#ffe600', CYAN = '#00e5ff', BG = '#0a0a0f';
const shuffle = <T,>(a: T[]) => { const r = a.slice(); for (let i = r.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [r[i], r[j]] = [r[j], r[i]]; } return r; };
const pad = (n: number) => String(n).padStart(2, '0');

function Main() {
  useKeepAwake();
  const { width } = useWindowDimensions();
  const playerRef = useRef<YoutubeIframeRef>(null);
  const queues = useRef<Record<number, Video[]>>({});
  const fails = useRef(0);

  const [on, setOn] = useState(false);
  const [ch, setCh] = useState(0);
  const [video, setVideo] = useState<Video | null>(null);
  const [snow, setSnow] = useState(false);
  const [ident, setIdent] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [lower, setLower] = useState<{ kicker?: string; a: string; b: string; c: string } | null>(null);
  const lowerAnim = useRef(new Animated.Value(0)).current;
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const later = (fn: () => void, ms: number) => { timers.current.push(setTimeout(fn, ms)); };
  const clearAll = () => { timers.current.forEach(clearTimeout); timers.current = []; };

  const showLower = (data: NonNullable<typeof lower>, ms: number) => {
    setLower(data);
    Animated.timing(lowerAnim, { toValue: 1, duration: 350, useNativeDriver: true }).start();
    later(() => Animated.timing(lowerAnim, { toValue: 0, duration: 300, useNativeDriver: true }).start(), ms);
  };

  const next = useCallback((c: number, prev?: Video | null) => {
    const chan = CHANNELS[c];
    let q = queues.current[chan.num];
    if (!q || !q.length) { q = shuffle(chan.videos); if (prev && q[0][0] === prev[0] && q.length > 1) q.push(q.shift()!); queues.current[chan.num] = q; }
    return q.shift()!;
  }, []);

  const tune = (c: number, withIdent = true) => {
    clearAll(); Animated.timing(lowerAnim, { toValue: 0, duration: 0, useNativeDriver: true }).start();
    const idx = (c + CHANNELS.length) % CHANNELS.length;
    setCh(idx); setSnow(true); setVideo(null);
    if (withIdent) setIdent(CHANNELS[idx].tag.toUpperCase());
    Haptics.selectionAsync().catch(() => {});
    later(() => setSnow(false), 600);
    later(() => { setIdent(null); fails.current = 0; setVideo(next(idx)); }, withIdent ? 1800 : 500);
  };

  const skip = () => { clearAll(); setSnow(true); setVideo(null); later(() => setSnow(false), 400); later(() => setVideo(next(ch, video)), 450); };

  const onState = (s: string) => {
    if (s === 'playing' && video) {
      fails.current = 0;
      later(() => showLower({ a: video[1], b: `“${video[2]}”`, c: `${video[3]} · ${CHANNELS[ch].name}` }, 7000), 1200);
    } else if (s === 'ended') {
      setIdent('WTC · MUSIC TELEVISION'); setSnow(true); setVideo(null);
      later(() => setSnow(false), 350);
      later(() => { setIdent(null); setVideo(next(ch, video)); }, 1600);
    }
  };
  const onError = () => { if (++fails.current > CHANNELS[ch].videos.length) return; setVideo(next(ch, video)); };

  // "Up next" card near the end of each video
  useEffect(() => {
    if (!video) return;
    const t = setInterval(async () => {
      const [d, cur] = [await playerRef.current?.getDuration(), await playerRef.current?.getCurrentTime()];
      if (d && cur != null && d > 20 && d - cur < 11 && d - cur > 9.4) {
        const peek = queues.current[CHANNELS[ch].num]?.[0];
        if (peek) showLower({ a: 'UP NEXT', b: `${peek[1]} — “${peek[2]}”`, c: CHANNELS[ch].name }, 8000);
      }
    }, 500);
    return () => clearInterval(t);
  }, [video, ch]);

  const power = () => { setOn(true); tune(ch); };

  const h = (width * 9) / 16;
  return (
    <SafeAreaView style={s.root}>
      <StatusBar style="light" />
      <View style={s.header}><Text style={s.logo}>WTC</Text><Text style={s.sub}>MUSIC TELEVISION</Text></View>

      <View style={[s.tv, { height: h }]}>
        {video && <YoutubePlayer ref={playerRef} height={h - 6} width={width - 6} videoId={video[0]} play mute={muted}
          onChangeState={onState} onError={onError}
          initialPlayerParams={{ controls: false, modestbranding: true, rel: false, preventFullScreen: true }} webViewProps={{ allowsInlineMediaPlayback: true, mediaPlaybackRequiresUserAction: false }} />}
        {/* block taps on YouTube's own UI */}
        <View style={StyleSheet.absoluteFill} />
        {snow && <Static />}
        {ident && <View style={s.ident}><Text style={s.identLogo}>WTC</Text><Text style={s.identSub}>{ident}</Text></View>}
        {on && <Text style={s.osd}>{pad(CHANNELS[ch].num)}  <Text style={{ fontSize: 12 }}>{CHANNELS[ch].name}</Text></Text>}
        {lower && (
          <Animated.View pointerEvents="none" style={[s.lower, { opacity: lowerAnim, transform: [{ translateX: lowerAnim.interpolate({ inputRange: [0, 1], outputRange: [-width, 0] }) }] }]}>
            <View style={s.lowerLogo}><Text style={s.lowerLogoT}>WTC</Text></View>
            <View style={s.lowerBody}>
              <Text style={s.lowA} numberOfLines={1}>{lower.a.toUpperCase()}</Text>
              <Text style={s.lowB} numberOfLines={1}>{lower.b}</Text>
              <Text style={s.lowC} numberOfLines={1}>{lower.c.toUpperCase()}</Text>
            </View>
          </Animated.View>
        )}
        {!on && (
          <Pressable style={s.power} onPress={power} accessibilityRole="button" accessibilityLabel="Turn on WTC">
            <Text style={[s.identLogo, { fontSize: 64 }]}>WTC</Text>
            <View style={s.cta}><Text style={s.ctaT}>▶  TUNE IN</Text></View>
          </Pressable>
        )}
      </View>

      <View style={s.remote}>
        <Btn label="CH −" onPress={() => on && tune(ch - 1)} />
        <Btn label="CH +" onPress={() => on && tune(ch + 1)} />
        <Btn label="SKIP ⏭" onPress={() => on && skip()} />
        <Btn label={muted ? 'UNMUTE' : 'MUTE'} onPress={() => setMuted(m => !m)} />
      </View>

      <Text style={s.guideH}>CHANNEL GUIDE</Text>
      <FlatList data={CHANNELS} keyExtractor={c => String(c.num)} contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 24 }}
        renderItem={({ item, index }) => (
          <Pressable onPress={() => on ? tune(index) : (setCh(index))} style={[s.row, index === ch && s.rowOn]}>
            <Text style={s.rowN}>{pad(item.num)}</Text>
            <View style={{ flex: 1 }}>
              <Text style={s.rowName}>{item.name}</Text>
              <Text style={s.rowTag} numberOfLines={1}>{index === ch && video ? `Now: ${video[1]} — ${video[2]}` : item.tag}</Text>
            </View>
          </Pressable>
        )} />
    </SafeAreaView>
  );
}

const Btn = ({ label, onPress }: { label: string; onPress: () => void }) => (
  <Pressable onPress={onPress} style={({ pressed }) => [s.btn, pressed && { backgroundColor: PINK }]}><Text style={s.btnT}>{label}</Text></Pressable>
);

export default function App() { return <SafeAreaProvider><Main /></SafeAreaProvider>; }

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: BG },
  header: { flexDirection: 'row', alignItems: 'baseline', gap: 10, paddingHorizontal: 16, paddingVertical: 10 },
  logo: { color: YELLOW, fontSize: 30, fontWeight: '900', fontStyle: 'italic', textShadowColor: PINK, textShadowOffset: { width: 2, height: 2 }, textShadowRadius: 0 },
  sub: { color: '#fff', fontSize: 11, letterSpacing: 4, fontWeight: '700' },
  tv: { backgroundColor: '#000', borderWidth: 3, borderColor: '#1b1b24', overflow: 'hidden' },
  osd: { position: 'absolute', top: 8, right: 10, color: '#39ff14', fontSize: 22, fontWeight: '700', fontFamily: 'Courier', textShadowColor: '#000', textShadowOffset: { width: 1, height: 1 }, textShadowRadius: 2 },
  ident: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#1a0630', alignItems: 'center', justifyContent: 'center' },
  identLogo: { color: YELLOW, fontSize: 56, fontWeight: '900', fontStyle: 'italic', textShadowColor: PINK, textShadowOffset: { width: 3, height: 3 }, textShadowRadius: 0 },
  identSub: { color: '#fff', fontSize: 11, letterSpacing: 4, marginTop: 6, fontWeight: '700' },
  power: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#1a0630', alignItems: 'center', justifyContent: 'center' },
  cta: { marginTop: 14, backgroundColor: PINK, borderRadius: 99, paddingVertical: 9, paddingHorizontal: 22 },
  ctaT: { color: '#000', fontWeight: '900', letterSpacing: 3, fontSize: 13 },
  lower: { position: 'absolute', left: 0, bottom: 16, flexDirection: 'row', maxWidth: '92%' },
  lowerLogo: { backgroundColor: YELLOW, paddingHorizontal: 10, justifyContent: 'center' },
  lowerLogoT: { fontWeight: '900', fontStyle: 'italic', fontSize: 18 },
  lowerBody: { backgroundColor: 'rgba(10,10,15,.9)', borderLeftWidth: 3, borderLeftColor: PINK, paddingVertical: 5, paddingHorizontal: 10, flexShrink: 1 },
  lowA: { color: '#fff', fontWeight: '800', fontSize: 14 },
  lowB: { color: CYAN, fontStyle: 'italic', fontSize: 12, fontWeight: '600' },
  lowC: { color: '#aaa', fontSize: 9, letterSpacing: 2, marginTop: 1 },
  remote: { flexDirection: 'row', gap: 8, padding: 16 },
  btn: { flex: 1, backgroundColor: '#1b1b24', borderColor: '#3a3a48', borderWidth: 1, borderRadius: 99, paddingVertical: 12, alignItems: 'center' },
  btnT: { color: '#fff', fontWeight: '800', fontSize: 11, letterSpacing: 1 },
  guideH: { color: YELLOW, letterSpacing: 4, fontSize: 12, fontWeight: '800', paddingHorizontal: 16, paddingBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 14, backgroundColor: '#15151d', borderColor: '#2a2a36', borderWidth: 1, borderRadius: 10, padding: 12, marginBottom: 6 },
  rowOn: { borderColor: PINK, backgroundColor: '#2a0f20' },
  rowN: { color: CYAN, fontFamily: 'Courier', fontSize: 18, fontWeight: '700' },
  rowName: { color: '#fff', fontWeight: '800', fontSize: 15 },
  rowTag: { color: '#999', fontSize: 12, marginTop: 2 },
});
