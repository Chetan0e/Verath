import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import AuthLanding from './pages/Auth/AuthLanding'
import LoadingScreen from './components/LoadingScreen'
import ErrorBoundary from './components/ErrorBoundary'
import './index.css'

const App = () => {
  const [loading, setLoading] = useState(true)
  const [fadeOut, setFadeOut] = useState(false)

  useEffect(() => {
    const fadeTimer = setTimeout(() => {
      setFadeOut(true)
    }, 2800)
    const loadTimer = setTimeout(() => {
      setLoading(false)
    }, 3200)
    return () => {
      clearTimeout(fadeTimer)
      clearTimeout(loadTimer)
    }
  }, [])

  return (
    <ErrorBoundary>
      {loading && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 9999,
          opacity: fadeOut ? 0 : 1,
          transition: 'opacity 0.4s ease',
          pointerEvents: fadeOut ? 'none' : 'all'
        }}>
          <LoadingScreen />
        </div>
      )}
      <div style={{
        opacity: fadeOut ? 1 : 0,
        transition: 'opacity 0.4s ease 0.2s'
      }}>
        <AuthLanding />
      </div>
    </ErrorBoundary>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)