import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Apply saved theme or default to light
const savedTheme = localStorage.getItem('finsense-theme') || 'light'
document.documentElement.setAttribute('data-theme', savedTheme)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
