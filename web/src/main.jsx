import React from 'react'
import ReactDOM from 'react-dom/client'
import AuthLanding from './pages/Auth/AuthLanding'
import ErrorBoundary from './components/ErrorBoundary';
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthLanding />
    </ErrorBoundary>
  </React.StrictMode>,
)
