import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Brain, 
  Search, 
  ShieldCheck, 
  Bell, 
  ArrowRight, 
  Mail, 
  Lock, 
  User, 
  CheckCircle2 
} from 'lucide-react';

const AuthLanding = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || !window.location.hostname
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    const endpoint = isLogin ? '/auth/login' : '/auth/signup';
    
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('verath_token', data.access_token);
        localStorage.setItem('verath_username', username);
        if (!isLogin) {
          setSuccess('Account created! Redirecting...');
        }
        setTimeout(() => {
          window.location.href = '/legacy/dashboard.html';
        }, 500);
      } else {
        setError(data.detail || (isLogin ? 'Invalid credentials' : 'Registration failed'));
      }
    } catch (err) {
      console.error('Auth error:', err);
      setError('Could not connect to server.');
    } finally {
      setLoading(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { 
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.2 }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1, transition: { duration: 0.6, ease: "easeOut" } }
  };

  return (
    <div className="relative min-h-screen bg-background overflow-x-hidden flex items-center justify-center font-sans">
      {/* Background Elements */}
      <div className="absolute inset-0 bg-mesh z-0" />
      <div className="bg-noise" />
      
      {/* Animated Glow Blobs */}
      <motion.div 
        animate={{ 
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary rounded-full mix-blend-screen filter blur-[128px] opacity-30 z-0 pointer-events-none"
      />
      <motion.div 
        animate={{ 
          scale: [1, 1.3, 1],
          opacity: [0.2, 0.4, 0.2],
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        className="absolute bottom-1/4 right-1/4 w-[30rem] h-[30rem] bg-secondary rounded-full mix-blend-screen filter blur-[128px] opacity-20 z-0 pointer-events-none"
      />

      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 py-12 lg:py-20 lg:px-12 grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center min-h-screen">
        
        {/* Left Section - Branding & Value Proposition */}
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col space-y-10"
        >
          {/* Header */}
          <motion.div variants={itemVariants} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg shadow-primary/30">
                <span className="text-white font-display font-bold text-xl">V</span>
              </div>
              <span className="text-2xl font-display font-bold tracking-tight text-white">Verath</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-surface border border-border">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs font-medium text-gray-300">System Online</span>
            </div>
          </motion.div>

          {/* Hero Copy */}
          <motion.div variants={itemVariants} className="space-y-6">
            <h1 className="text-5xl lg:text-7xl font-display font-bold tracking-tight leading-tight text-transparent bg-clip-text bg-gradient-to-br from-white via-white to-gray-400">
              Your intelligent <br/>digital memory.
            </h1>
            <p className="text-lg text-gray-400 leading-relaxed max-w-xl">
              Capture conversations, thoughts, meetings, and ideas — then retrieve them instantly using AI-powered semantic memory.
            </p>
          </motion.div>

          {/* Features Grid */}
          <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { icon: Brain, title: "AI Memory Extraction", desc: "Auto-detects intents & entities." },
              { icon: Search, title: "Hybrid Semantic Search", desc: "Vector search + neural re-ranking." },
              { icon: ShieldCheck, title: "Cloud Inference Privacy", desc: "Secure & fast processing." },
              { icon: Bell, title: "Smart Reminder Intelligence", desc: "Extracts temporal deadlines." },
            ].map((feature, idx) => (
              <motion.div 
                key={idx}
                whileHover={{ y: -4, scale: 1.02 }}
                className="p-5 rounded-2xl glass-card border border-white/10 group cursor-default transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-[0_0_30px_rgba(139,92,246,0.18)] hover:bg-white/[0.03]"
              >
                <div className="w-10 h-10 rounded-lg bg-surface-hover flex items-center justify-center mb-4 transition-all duration-300 group-hover:bg-primary/20 group-hover:scale-110 group-hover:shadow-lg group-hover:shadow-primary/20">
                  <feature.icon className="w-5 h-5 text-gray-400 group-hover:text-primary" />
                </div>
                <h3 className="text-white font-medium mb-1">{feature.title}</h3>
                <p className="text-sm text-gray-500">{feature.desc}</p>
              </motion.div>
            ))}
          </motion.div>
          
          <motion.div variants={itemVariants} className="flex gap-4 pt-4">
            <div className="flex -space-x-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className={`w-10 h-10 rounded-full border-2 border-background bg-surface flex items-center justify-center bg-gradient-to-br from-gray-700 to-gray-900 z-${50-i*10}`}>
                   <User className="w-4 h-4 text-gray-400" />
                </div>
              ))}
            </div>
            <div className="flex flex-col justify-center">
              <div className="flex items-center gap-1">
                {[1,2,3,4,5].map(i => <Star key={i} />)}
              </div>
              <span className="text-xs text-gray-400 font-medium mt-1">Trusted by 10,000+ thinkers</span>
            </div>
          </motion.div>

        </motion.div>

        {/* Right Section - Auth Card */}
        <motion.div 
         initial={{ opacity: 0, x: 20 }}
         animate={{ 
         opacity: 1, 
         x: 0,
         y: [0, -4, 0]
         }}
         transition={{ 
         duration: 6,
         repeat: Infinity,
         ease: "easeInOut"
         }}
         className="flex justify-center lg:justify-end"
         >
          <div className="relative w-full max-w-md">
            {/* Ambient Card Glow */}
            <div className="absolute -inset-1 bg-gradient-to-r from-primary to-secondary rounded-3xl blur opacity-20"></div>
            
            <div className="relative p-8 rounded-3xl glass-card border border-white/10 hover:border-primary/20 transition-all duration-500">
              <div className="flex items-center justify-between mb-8 p-1 bg-surface-hover rounded-xl">
                <button 
                  onClick={() => { setIsLogin(true); setError(''); setSuccess(''); }}
                 className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-300 hover:scale-[1.02] ${
                 isLogin
                 ? 'bg-white/10 text-white shadow-lg shadow-primary/10'
                 : 'text-gray-400 hover:text-white hover:bg-white/5'
                 }`}
                 >
                  Sign In
                </button>
                <button 
                  onClick={() => { setIsLogin(false); setError(''); setSuccess(''); }}
                  className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-300 hover:scale-[1.02] ${
                 !isLogin
                 ? 'bg-white/10 text-white shadow-lg shadow-primary/10'
                 : 'text-gray-400 hover:text-white hover:bg-white/5'
                 }`}
                >
                  Register
                </button>
              </div>

              <div className="mb-8">
                <h2 className="text-2xl font-display font-bold text-white mb-2">
                  {isLogin ? 'Welcome back' : 'Create your vault'}
                </h2>
                <p className="text-sm text-gray-400">
                  {isLogin ? 'Enter your credentials to access your memory.' : 'Start capturing your thoughts today.'}
                </p>
              </div>

              <form className="space-y-4" onSubmit={handleSubmit}>
                {error && <div className="text-red-400 text-sm">{error}</div>}
                {success && <div className="text-green-400 text-sm">{success}</div>}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-300 ml-1">
                    {isLogin ? 'Username' : 'Choose a Username'}
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input 
                      type="text" 
                      placeholder={isLogin ? "username" : "creative_mind"}
                      className="input-field pl-10" 
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between ml-1">
                    <label className="text-xs font-medium text-gray-300">
                      {isLogin ? 'Password' : 'Create Password'}
                    </label>
                    {isLogin && <a href="#" className="text-xs text-primary hover:text-violet-400 transition-colors">Forgot password?</a>}
                  </div>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input 
                      type="password" 
                      placeholder={isLogin ? "••••••••" : "Min. 8 characters"}
                      className="input-field pl-10" 
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={!isLogin ? 8 : undefined}
                    />
                  </div>
                </div>

                {isLogin && (
                  <div className="flex items-center gap-2 mt-2">
                    <input type="checkbox" id="remember" className="rounded border-gray-600 bg-surface text-primary focus:ring-primary focus:ring-offset-background" />
                    <label htmlFor="remember" className="text-xs text-gray-400 cursor-pointer">Remember me for 30 days</label>
                  </div>
                )}

                <motion.button 
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="btn-primary mt-6 disabled:opacity-50 transition-all duration-300 hover:shadow-[0_0_25px_rgba(139,92,246,0.35)] hover:-translate-y-0.5"
                  disabled={loading}
                >
                  {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Create Account')}
                  {!loading && <ArrowRight className="w-4 h-4" />}
                </motion.button>
              </form>

              <div className="mt-8 relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border"></div>
                </div>
                <div className="relative flex justify-center text-xs">
                 <span className="px-3 py-1 rounded-full bg-[#0a0d1d]/90 border border-white/5 text-gray-500 backdrop-blur-sm"> Or continue with</span>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-3">
                <button className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-surface border border-border hover:bg-surface-hover hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-300 text-sm font-medium text-white hover:shadow-lg hover:shadow-primary/10">
                  <GoogleIcon />
                  Google
                </button>
                <button className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-surface border border-border hover:bg-surface-hover hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-300 text-sm font-medium text-white hover:shadow-lg hover:shadow-primary/10">
                  <GithubIcon />
                  GitHub
                </button>
              </div>
            </div>
          </div>
        </motion.div>

      </div>
    </div>
  );
};

// SVG Icons
const Star = () => (
  <svg className="w-3.5 h-3.5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
  </svg>
);

const GoogleIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
);

const GithubIcon = () => (
  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.379.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.416 22 12c0-5.523-4.477-10-10-10z" />
  </svg>
);

export default AuthLanding;
