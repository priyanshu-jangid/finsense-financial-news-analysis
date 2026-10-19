import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { IconEye, IconEyeOff, IconAlertCircle } from '../components/Icons';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide both email and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: unknown) {
      // Extract backend detail error if available
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const detail = axiosErr?.response?.data?.detail;
      setError(
        detail || 'Authentication failed. Please verify your email and password.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 16px',
      }}
    >
      <div
        className="fin-card"
        style={{
          width: '100%',
          maxWidth: '400px',
          padding: '32px 28px',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              display: 'inline-block',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              color: 'var(--accent-text)',
              backgroundColor: 'var(--accent-subtle)',
              padding: '3px 8px',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '12px',
            }}
          >
            PORTAL ACCESS
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Sign In to FinSense</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Financial intelligence & sentiment analytics
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: '10px 14px',
              backgroundColor: 'var(--sentiment-neg-bg)',
              border: '1px solid var(--sentiment-neg-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--sentiment-neg-text)',
              fontSize: '13px',
              marginBottom: '18px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <IconAlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label
              htmlFor="login-email"
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}
            >
              Email Address
            </label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="analyst@firm.com"
              required
              className="fin-input"
              style={{ width: '100%' }}
              autoComplete="email"
              disabled={loading}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <label
                htmlFor="login-password"
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                }}
              >
                Password
              </label>
            </div>
            <div style={{ position: 'relative' }}>
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="fin-input"
                style={{ width: '100%', paddingRight: '38px' }}
                autoComplete="current-password"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                }}
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <IconEyeOff size={16} /> : <IconEye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="fin-btn fin-btn-primary"
            style={{ width: '100%', marginTop: '8px', height: '40px' }}
          >
            {loading ? 'Authenticating…' : 'Sign In'}
          </button>
        </form>

        <div
          style={{
            marginTop: '24px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border-subtle)',
            textAlign: 'center',
            fontSize: '13px',
            color: 'var(--text-muted)',
          }}
        >
          Do not have an account?{' '}
          <NavLink
            to="/register"
            style={{
              color: 'var(--accent-primary)',
              fontWeight: 600,
            }}
          >
            Register here
          </NavLink>
        </div>
      </div>
    </div>
  );
};

export default Login;
