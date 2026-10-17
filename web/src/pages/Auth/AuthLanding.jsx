import React, { useState, useEffect, useRef } from 'react';
import Button from '../../components/Button';
import Input from '../../components/Input';
import { validateAuthForm } from '../../utils/validation';
import { motion } from 'framer-motion';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import FeaturesSection from '../../components/FeaturesSection';
import HowItWorksSection from '../../components/HowItWorksSection';
import AboutSection from '../../components/AboutSection';
import BlogSection from '../../components/BlogSection';
import ContactSection from '../../components/ContactSection';
import DocsModal from '../../components/DocsModal';
import DiscordModal from '../../components/DiscordModal';
import LegalModal from '../../components/LegalModal';
import {
  Brain,
  Search,
  ShieldCheck,
  Bell,
  ArrowRight,
  Lock,
  User,
} from 'lucide-react';

const AnimatedHeading = ({ text, className }) => {
  const words = text.split(' ');
  const container = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.11, delayChildren: 0.3 } }
  };
  const word = {
    hidden: { y: 52, opacity: 0, rotateX: -28 },
    visible: {
      y: 0, opacity: 1, rotateX: 0,
      transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] }
    }
  };
  return (
    <motion.h1
      variants={container}
      initial="hidden"
      animate="visible"
      className={className}
      style={{ perspective: 800, display: 'flex', flexWrap: 'wrap', gap: '0 0.28em', lineHeight: 1.1, minWidth: 0 }}
    >
      {words.map((w, i) => (
        <span key={i} style={{ overflow: 'hidden', display: 'inline-block', minWidth: 0 }}>
          <motion.span variants={word} style={{ display: 'inline-block' }}>{w}</motion.span>
        </span>
      ))}
    </motion.h1>
  );
};

const AnimatedSubtitle = ({ text, className }) => (
  <motion.p
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.7, delay: 1.0, ease: [0.16, 1, 0.3, 1] }}
    className={className}
  >
    {text}
  </motion.p>
);

const AuthLanding = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  // Modals state
  const [isDocsOpen, setIsDocsOpen] = useState(false);
  const [isDiscordOpen, setIsDiscordOpen] = useState(false);
  const [legalModalType, setLegalModalType] = useState(null); // 'privacy' | 'terms' | null

  const authCardRef = useRef(null);

  const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || !window.location.hostname
    ? "" // Use Vite proxy in development
    : `${window.location.protocol}//${window.location.hostname}:8000`;

  // Listen to URL hashes on load and hashchange
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash;
      if (hash === '#docs') {
        setIsDocsOpen(true);
      } else if (hash === '#discord') {
        setIsDiscordOpen(true);
      } else if (hash === '#privacy') {
        setLegalModalType('privacy');
      } else if (hash === '#terms') {
        setLegalModalType('terms');
      } else if (hash) {
        const el = document.querySelector(hash);
        if (el) {
          setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 100);
        }
      }
    };

    handleHash();
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errors = validateAuthForm(username, password, isLogin);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setFieldErrors({});
    setLoading(true);
    setError('');
    setSuccess('');
    const endpoint = isLogin ? '/auth/login' : '/auth/signup';
    try {
      if (isLogin) {
        const response = await fetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        if (response.ok) {
          localStorage.setItem('verath_token', data.access_token);
          localStorage.setItem('verath_username', username);
          setTimeout(() => { window.location.href = '/legacy/dashboard.html'; }, 300);
        } else {
          setError(data.detail || 'Invalid credentials');
        }
      } else {
        const signupRes = await fetch(`${API_BASE}/auth/signup`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        const signupData = await signupRes.json();
        if (signupRes.ok) {
          // Automatically log in post-registration to obtain tokens
          const loginRes = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
          });
          const loginData = await loginRes.json();
          if (loginRes.ok && loginData.access_token) {
            localStorage.setItem('verath_token', loginData.access_token);
            localStorage.setItem('verath_username', username);
            setSuccess('Account created! Entering your vault...');
            setTimeout(() => { window.location.href = '/legacy/dashboard.html'; }, 500);
          } else {
            setSuccess('Account created! Please sign in with your credentials.');
            setIsLogin(true);
          }
        } else {
          setError(signupData.detail || 'Registration failed');
        }
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
    visible: { opacity: 1, transition: { staggerChildren: 0.1, delayChildren: 0.2 } }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1, transition: { duration: 0.6, ease: "easeOut" } }
  };

  const scrollToAuth = () => {
    if (authCardRef.current) {
      authCardRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="relative min-h-screen bg-white overflow-x-hidden font-sans w-full flex flex-col">
      {/* Navigation */}
      <Navbar
        onOpenDocs={() => setIsDocsOpen(true)}
        onGetStarted={scrollToAuth}
      />

      {/* Hero Section */}
      <div className="relative z-10 w-full max-w-7xl mx-auto px-3 sm:px-4 md:px-6 pt-24 sm:pt-28 md:pt-32 lg:pt-36 pb-8 sm:pb-12 lg:pb-20 lg:px-12 flex flex-col lg:grid lg:grid-cols-2 gap-8 sm:gap-12 lg:gap-20 items-start lg:items-center">

        {/* Left Section - Hero Content */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col space-y-4 sm:space-y-6 lg:space-y-10 min-w-0 order-2 lg:order-1 mt-4 sm:mt-8 lg:mt-0 relative z-0"
        >
          <div className="space-y-4 lg:space-y-6 min-w-0">
            <AnimatedHeading
              text="Your intelligent digital memory."
              className="text-3xl sm:text-4xl lg:text-7xl font-display font-bold tracking-tight text-gray-900"
            />
            <AnimatedSubtitle
              text="Capture conversations, thoughts, meetings, and ideas — then retrieve them instantly using AI-powered semantic memory."
              className="text-base sm:text-lg text-gray-600 leading-relaxed max-w-xl break-words"
            />
          </div>

          {/* Features Grid */}
          <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 lg:gap-4">
            {[
              { icon: Brain, title: "AI Memory Extraction", desc: "Auto-detects intents & entities.", borderColor: "border-purple-500", iconColor: "text-purple-600", iconBg: "bg-purple-100" },
              { icon: Search, title: "Hybrid Semantic Search", desc: "Vector search + neural re-ranking.", borderColor: "border-blue-500", iconColor: "text-blue-600", iconBg: "bg-blue-100" },
              { icon: ShieldCheck, title: "Cloud Inference Privacy", desc: "Secure & fast processing.", borderColor: "border-green-500", iconColor: "text-green-600", iconBg: "bg-green-100" },
              { icon: Bell, title: "Smart Reminder Intelligence", desc: "Extracts temporal deadlines.", borderColor: "border-orange-500", iconColor: "text-orange-600", iconBg: "bg-orange-100" },
            ].map((feature, idx) => (
              <motion.div
                key={idx}
                whileHover={{ y: -4, scale: 1.02 }}
                className={`p-3 sm:p-4 md:p-5 rounded-2xl bg-white border-2 ${feature.borderColor} group cursor-default transition-all duration-300 hover:-translate-y-1 hover:border-opacity-80 hover:shadow-xl`}
              >
                <div className={`w-7 h-7 sm:w-8 sm:h-8 md:w-10 md:h-10 rounded-lg ${feature.iconBg} flex items-center justify-center mb-2 sm:mb-3 md:mb-4 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg`}>
                  <feature.icon className={`w-3.5 h-3.5 sm:w-4 sm:h-4 md:w-5 md:h-5 ${feature.iconColor}`} />
                </div>
                <h3 className="text-gray-900 font-medium mb-1 text-xs sm:text-sm md:text-base">{feature.title}</h3>
                <p className="text-xs sm:text-xs md:text-sm text-gray-600">{feature.desc}</p>
              </motion.div>
            ))}
          </motion.div>

          {/* Trusted By */}
          <motion.div variants={itemVariants} className="hidden sm:flex gap-3 sm:gap-4 pt-2 sm:pt-4">
            <div className="flex -space-x-2 sm:-space-x-3 flex-shrink-0">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="w-8 h-8 sm:w-10 sm:h-10 rounded-full border-2 border-white bg-gray-200 flex items-center justify-center bg-gradient-to-br from-gray-300 to-gray-400">
                  <User className="w-3 h-3 sm:w-4 sm:h-4 text-gray-600" />
                </div>
              ))}
            </div>
            <div className="flex flex-col justify-center min-w-0">
              <div className="flex items-center gap-0.5 sm:gap-1">
                {[1, 2, 3, 4, 5].map(i => <Star key={i} />)}
              </div>
              <span className="text-xs text-gray-600 font-medium mt-1">Trusted by 10,000+ thinkers</span>
            </div>
          </motion.div>
        </motion.div>

        {/* Right Section - Auth Card */}
        <motion.div
          ref={authCardRef}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="flex justify-center lg:justify-end order-1 lg:order-2 w-full mb-0 lg:mb-0 relative z-20"
        >
          <div className="relative w-full max-w-sm sm:max-w-md min-w-0 px-1 sm:px-0">
            <div className="absolute -inset-1 bg-gradient-to-r from-violet-500 to-indigo-500 rounded-3xl blur opacity-25"></div>

            <div className="relative p-4 sm:p-6 md:p-8 rounded-3xl bg-white/95 backdrop-blur-xl border-2 border-gray-200 shadow-2xl hover:border-gray-300 transition-all duration-500">
              <div className="flex items-center justify-between mb-5 sm:mb-6 md:mb-8 p-1 bg-gray-100 rounded-xl border-2 border-gray-200">
                <button
                  onClick={() => { setIsLogin(true); setError(''); setSuccess(''); setFieldErrors({}); }}
                  className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${isLogin ? 'bg-white text-gray-900 shadow-sm border border-gray-200' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'}`}
                >
                  Sign In
                </button>
                <button
                  onClick={() => { setIsLogin(false); setError(''); setSuccess(''); setFieldErrors({}); }}
                  className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${!isLogin ? 'bg-white text-gray-900 shadow-sm border border-gray-200' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'}`}
                >
                  Register
                </button>
              </div>

              <div className="mb-6 sm:mb-8">
                <h2 className="text-xl sm:text-2xl font-display font-bold text-gray-900 mb-2">
                  {isLogin ? 'Welcome back' : 'Create your vault'}
                </h2>
                <p className="text-xs sm:text-sm text-gray-600">
                  {isLogin ? 'Enter your credentials to access your memory.' : 'Start capturing your thoughts today.'}
                </p>
              </div>

              <form className="space-y-3 sm:space-y-4" onSubmit={handleSubmit}>
                {error && <div className="text-red-600 text-sm break-words">{error}</div>}
                {success && <div className="text-green-600 text-sm break-words">{success}</div>}

                <Input
                  type="text"
                  placeholder={isLogin ? "username" : "creative_mind"}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  icon={User}
                  label={isLogin ? 'Username' : 'Choose a Username'}
                  required
                  error={fieldErrors.username}
                />

                <Input
                  type="password"
                  placeholder={isLogin ? "••••••••" : "Min. 8 characters"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  icon={Lock}
                  label={isLogin ? 'Password' : 'Create Password'}
                  required
                  minLength={!isLogin ? 8 : undefined}
                  error={fieldErrors.password}
                />

                {isLogin && (
                  <div className="flex items-center gap-2 mt-2">
                    <input type="checkbox" id="remember" className="rounded border-gray-300 bg-white text-primary focus:ring-primary focus:ring-offset-gray-100" />
                    <label htmlFor="remember" className="text-xs text-gray-600 cursor-pointer">Remember me for 30 days</label>
                  </div>
                )}

                <Button type="submit" loading={loading} className="mt-6">
                  {isLogin ? 'Sign In' : 'Create Account'}
                  {!loading && <ArrowRight className="w-4 h-4" />}
                </Button>
              </form>

              <div className="mt-6 sm:mt-8 relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-3 py-1 rounded-full bg-white border border-gray-200 text-gray-600">
                    Or continue with
                  </span>
                </div>
              </div>

              <div className="mt-4 sm:mt-6 grid grid-cols-1 min-[400px]:grid-cols-2 gap-2 sm:gap-3">
                <button className="flex items-center justify-center gap-2 py-2 sm:py-2.5 px-3 sm:px-4 rounded-xl bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 hover:-translate-y-0.5 transition-all duration-300 text-xs sm:text-sm font-medium text-gray-700 hover:shadow-sm">
                  <GoogleIcon />
                  Google
                </button>
                <button className="flex items-center justify-center gap-2 py-2 sm:py-2.5 px-3 sm:px-4 rounded-xl bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 hover:-translate-y-0.5 transition-all duration-300 text-xs sm:text-sm font-medium text-gray-700 hover:shadow-sm">
                  <GithubIcon />
                  GitHub
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Main Feature Sections */}
      <FeaturesSection />
      <HowItWorksSection />
      <AboutSection />
      <BlogSection />
      <ContactSection />

      {/* Footer */}
      <Footer
        onOpenDocs={() => setIsDocsOpen(true)}
        onOpenDiscord={() => setIsDiscordOpen(true)}
        onOpenLegal={(type) => setLegalModalType(type)}
      />

      {/* Modals */}
      <DocsModal
        isOpen={isDocsOpen}
        onClose={() => setIsDocsOpen(false)}
      />

      <DiscordModal
        isOpen={isDiscordOpen}
        onClose={() => setIsDiscordOpen(false)}
      />

      <LegalModal
        isOpen={!!legalModalType}
        type={legalModalType}
        onClose={() => setLegalModalType(null)}
      />
    </div>
  );
};

const Star = () => (
  <svg className="w-3.5 h-3.5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
  </svg>
);

const GoogleIcon = () => (
  <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
);

const GithubIcon = () => (
  <svg className="w-4 h-4 text-white flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.379.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.416 22 12c0-5.523-4.477-10-10-10z" />
  </svg>
);

export default AuthLanding;