import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { IconSun, IconMoon } from './Icons';

export const Navbar: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const [theme, setTheme] = useState<string>(() => {
    return localStorage.getItem('finsense-theme') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('finsense-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-subtle)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      <div
        style={{
          maxWidth: '1360px',
          margin: '0 auto',
          padding: '0 20px',
          height: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Brand Wordmark & Nav */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
          <NavLink
            to="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              textDecoration: 'none',
              color: 'var(--text-primary)',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-sans)',
                fontWeight: 700,
                fontSize: '18px',
                letterSpacing: '-0.02em',
                color: 'var(--text-primary)',
              }}
            >
              FinSense
            </span>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: 'var(--accent-text)',
                backgroundColor: 'var(--accent-subtle)',
                padding: '2px 6px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--accent-border)',
              }}
            >
              INTELLIGENCE
            </span>
          </NavLink>

          <nav style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <NavLink
              to="/"
              end
              style={({ isActive }) => ({
                padding: '6px 12px',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--accent-subtle)' : 'transparent',
                borderRadius: 'var(--radius-md)',
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              })}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/news"
              style={({ isActive }) => ({
                padding: '6px 12px',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--accent-subtle)' : 'transparent',
                borderRadius: 'var(--radius-md)',
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              })}
            >
              News
            </NavLink>
            <NavLink
              to="/watchlist"
              style={({ isActive }) => ({
                padding: '6px 12px',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--accent-subtle)' : 'transparent',
                borderRadius: 'var(--radius-md)',
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              })}
            >
              Watchlist
            </NavLink>
          </nav>
        </div>

        {/* Right Section: Theme Toggle & User Auth */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={toggleTheme}
            className="fin-btn fin-btn-ghost fin-btn-sm"
            style={{ width: '34px', padding: 0 }}
            title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
            aria-label="Toggle theme"
          >
            {theme === 'light' ? <IconMoon size={16} /> : <IconSun size={16} />}
          </button>

          <div style={{ width: '1px', height: '20px', backgroundColor: 'var(--border-subtle)' }} />

          {isAuthenticated && user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 10px',
                  backgroundColor: 'var(--bg-surface-subtle)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--sentiment-pos)',
                  }}
                />
                <span style={{ maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.email}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="fin-btn fin-btn-secondary fin-btn-sm"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <NavLink to="/login" className="fin-btn fin-btn-ghost fin-btn-sm">
                Sign In
              </NavLink>
              <NavLink to="/register" className="fin-btn fin-btn-primary fin-btn-sm">
                Register
              </NavLink>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
