import React, { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const LoadingScreen = () => {
    const [msgIdx, setMsgIdx] = useState(0)
    const [phase, setPhase] = useState('loading')
    const [dots, setDots] = useState(0)
    const canvasRef = useRef(null)
    const animRef = useRef(null)

    const messages = [
        'Initializing neural core',
        'Mounting memory engine',
        'Connecting to Groq LLM',
        'Loading ChromaDB vectors',
        'Syncing RAG pipeline',
        'Verath is ready',
    ]

    // ── same wave canvas from original ──────────────────────────────
    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        let t = 0
        const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight }
        resize()
        window.addEventListener('resize', resize)
        const draw = () => {
            const { width, height } = canvas
            ctx.clearRect(0, 0, width, height)
            const waves = [
                { amp: 28, freq: 0.012, speed: 0.018, color: 'rgba(124,58,237,0.18)', offset: 0 },
                { amp: 18, freq: 0.018, speed: 0.026, color: 'rgba(99,102,241,0.14)', offset: 1.2 },
                { amp: 38, freq: 0.008, speed: 0.011, color: 'rgba(139,92,246,0.09)', offset: 2.4 },
                { amp: 12, freq: 0.025, speed: 0.034, color: 'rgba(167,139,250,0.12)', offset: 0.7 },
            ]
            waves.forEach(w => {
                ctx.beginPath()
                for (let x = 0; x <= width; x += 2) {
                    const y = height / 2
                        + Math.sin(x * w.freq + t * w.speed + w.offset) * w.amp
                        + Math.sin(x * w.freq * 0.5 + t * w.speed * 0.7 + w.offset) * (w.amp * 0.4)
                    if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                }
                ctx.strokeStyle = w.color; ctx.lineWidth = 1.5; ctx.stroke()
            })
            const scanX = (t * 1.5) % width
            const grad = ctx.createLinearGradient(scanX - 40, 0, scanX + 40, 0)
            grad.addColorStop(0, 'transparent')
            grad.addColorStop(0.5, 'rgba(124,58,237,0.22)')
            grad.addColorStop(1, 'transparent')
            ctx.fillStyle = grad; ctx.fillRect(scanX - 40, 0, 80, height)
            t += 1
            animRef.current = requestAnimationFrame(draw)
        }
        draw()
        return () => { cancelAnimationFrame(animRef.current); window.removeEventListener('resize', resize) }
    }, [])

    // ── message cycling ──────────────────────────────────────────────
    useEffect(() => {
        const timer = setInterval(() => {
            setMsgIdx(prev => {
                if (prev >= messages.length - 1) {
                    clearInterval(timer)
                    setTimeout(() => setPhase('done'), 300)
                    return prev
                }
                return prev + 1
            })
        }, 520)
        return () => clearInterval(timer)
    }, [])

    // ── animated ellipsis ────────────────────────────────────────────
    useEffect(() => {
        const t = setInterval(() => setDots(d => (d + 1) % 4), 400)
        return () => clearInterval(t)
    }, [])

    const isLast = msgIdx === messages.length - 1

    return (
        <div style={{
            background: '#04060f',
            minHeight: '100dvh',
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            position: 'fixed',
            inset: 0,
        }}>
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&family=JetBrains+Mono:wght@400;500&display=swap');
                @keyframes glowPulse {
                    0%,100% { text-shadow: 0 0 24px rgba(139,92,246,0.45), 0 0 64px rgba(124,58,237,0.18); }
                    50%      { text-shadow: 0 0 48px rgba(139,92,246,0.9), 0 0 120px rgba(124,58,237,0.4); }
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                @keyframes ripple {
                    0%   { transform: scale(0.85); opacity: 0.7; }
                    100% { transform: scale(2.2);  opacity: 0; }
                }
            `}</style>

            {/* ── background: same as original ── */}
            <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />

            {/* Glowing grid squares */}
            <div style={{
                position: 'absolute', inset: 0, pointerEvents: 'none',
                backgroundImage: `
                    linear-gradient(rgba(99,102,241,0.08) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(99,102,241,0.08) 1px, transparent 1px)
                `,
                backgroundSize: '52px 52px',
            }} />
            {/* Center glow over grid */}
            <div style={{
                position: 'absolute', inset: 0, pointerEvents: 'none',
                background: 'radial-gradient(ellipse 50% 40% at 50% 50%, rgba(88,60,210,0.15) 0%, transparent 70%)',
            }} />

            <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(ellipse 70% 60% at 50% 50%, transparent 20%, #04060f 100%)' }} />
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '30%', pointerEvents: 'none', background: 'linear-gradient(to bottom, #04060f, transparent)' }} />
            <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '30%', pointerEvents: 'none', background: 'linear-gradient(to top, #04060f, transparent)' }} />
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: '80vw', height: '40vh', background: 'radial-gradient(ellipse, rgba(99,58,210,0.10) 0%, transparent 70%)', pointerEvents: 'none' }} />

            {/* ── main content ── */}
            <div style={{
                position: 'relative', zIndex: 10,
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                width: '100%', padding: '0 28px', boxSizing: 'border-box', gap: 0,
            }}>

                {/* Logo spinner ring */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                    style={{ position: 'relative', width: 88, height: 88, marginBottom: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                    {/* Ripple rings */}
                    {[0, 1].map(i => (
                        <div key={i} style={{
                            position: 'absolute', inset: 0, borderRadius: '50%',
                            border: '1px solid rgba(124,58,237,0.35)',
                            animation: `ripple 2.4s ease-out infinite`,
                            animationDelay: `${i * 1.2}s`,
                        }} />
                    ))}

                    {/* Spinning arc */}
                    <svg width="88" height="88" viewBox="0 0 88 88" fill="none"
                        style={{ position: 'absolute', inset: 0, animation: 'spin 2s linear infinite' }}>
                        <circle cx="44" cy="44" r="40"
                            stroke="url(#arcGrad)" strokeWidth="1.5"
                            strokeDasharray="60 192" strokeLinecap="round" />
                        <defs>
                            <linearGradient id="arcGrad" x1="0" y1="0" x2="88" y2="88" gradientUnits="userSpaceOnUse">
                                <stop offset="0%" stopColor="#a78bfa" />
                                <stop offset="100%" stopColor="#7c3aed" stopOpacity="0" />
                            </linearGradient>
                        </defs>
                    </svg>

                    {/* Counter-spin slower arc */}
                    <svg width="66" height="66" viewBox="0 0 66 66" fill="none"
                        style={{ position: 'absolute', animation: 'spin 3.5s linear infinite reverse' }}>
                        <circle cx="33" cy="33" r="29"
                            stroke="rgba(99,102,241,0.4)" strokeWidth="1"
                            strokeDasharray="30 152" strokeLinecap="round" />
                    </svg>

                    {/* Core badge */}
                    <div style={{
                        width: 48, height: 48, borderRadius: 14,
                        background: 'linear-gradient(135deg, #5b21b6 0%, #4f46e5 100%)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        boxShadow: '0 0 0 1px rgba(124,58,237,0.5), 0 8px 32px rgba(79,70,229,0.4)',
                        position: 'relative', zIndex: 2,
                    }}>
                        <span style={{
                            fontFamily: "'Outfit', sans-serif",
                            fontWeight: 900, fontSize: 22, color: '#fff', letterSpacing: '-1px',
                        }}>V</span>
                    </div>
                </motion.div>

                {/* Wordmark */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
                    style={{ textAlign: 'center', marginBottom: '2.5rem' }}
                >
                    <div style={{
                        fontFamily: "'Outfit', sans-serif",
                        fontWeight: 900,
                        fontSize: 'clamp(44px, 14vw, 72px)',
                        color: '#fff',
                        letterSpacing: '-4px',
                        lineHeight: 1,
                        animation: 'glowPulse 3s ease-in-out infinite',
                    }}>Verath</div>
                    <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 'clamp(8px, 2.2vw, 10px)',
                        color: 'rgba(139,92,246,0.5)',
                        letterSpacing: '5px',
                        textTransform: 'uppercase',
                        marginTop: 8,
                    }}>AI · Memory · Platform</div>
                </motion.div>

                {/* Animated status message */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.35 }}
                    style={{
                        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20,
                        width: '100%', maxWidth: 340,
                    }}
                >
                    {/* Message */}
                    <div style={{
                        height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        overflow: 'hidden',
                    }}>
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={msgIdx}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -8 }}
                                transition={{ duration: 0.22 }}
                                style={{
                                    fontFamily: "'JetBrains Mono', monospace",
                                    fontSize: 'clamp(10px, 3vw, 12px)',
                                    color: isLast ? 'rgba(34,197,94,0.85)' : 'rgba(255,255,255,0.38)',
                                    letterSpacing: '0.3px',
                                    display: 'flex', alignItems: 'center', gap: 4,
                                    whiteSpace: 'nowrap',
                                }}
                            >
                                <span style={{ color: isLast ? 'rgba(34,197,94,0.7)' : 'rgba(124,58,237,0.65)' }}>
                                    {isLast ? '✓' : '▶'}
                                </span>
                                {messages[msgIdx]}
                                {!isLast && (
                                    <span style={{ color: 'rgba(139,92,246,0.6)', minWidth: 18, display: 'inline-block' }}>
                                        {'.'.repeat(dots)}
                                    </span>
                                )}
                            </motion.div>
                        </AnimatePresence>
                    </div>

                    {/* Step pills */}
                    <div style={{ display: 'flex', gap: 5, width: '100%' }}>
                        {messages.map((_, i) => {
                            const active = i === msgIdx
                            const done = i < msgIdx
                            return (
                                <motion.div
                                    key={i}
                                    animate={{
                                        opacity: done ? 1 : active ? 0.9 : 0.18,
                                        scaleY: active ? 1.8 : 1,
                                    }}
                                    transition={{ duration: 0.35 }}
                                    style={{
                                        flex: 1, height: 3, borderRadius: 2,
                                        background: done
                                            ? 'linear-gradient(90deg, #7c3aed, #a78bfa)'
                                            : active
                                                ? '#c4b5fd'
                                                : 'rgba(255,255,255,0.1)',
                                        boxShadow: active ? '0 0 10px rgba(196,181,253,0.7)' : done ? '0 0 6px rgba(124,58,237,0.4)' : 'none',
                                        transformOrigin: 'center',
                                    }}
                                />
                            )
                        })}
                    </div>

                    {/* Step counter */}
                    <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 'clamp(9px, 2.5vw, 10px)',
                        color: 'rgba(255,255,255,0.18)',
                        letterSpacing: '2px',
                    }}>
                        {String(msgIdx + 1).padStart(2, '0')} / {String(messages.length).padStart(2, '0')}
                    </div>
                </motion.div>

            </div>
        </div>
    )
}

export default LoadingScreen