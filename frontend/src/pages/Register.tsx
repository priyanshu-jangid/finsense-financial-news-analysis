import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { IconEye, IconEyeOff, IconAlertCircle } from '../components/Icons';

export const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError('Please provide an email address and password.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters in length.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please re-enter.');
      return;
    }

    setLoading(true);

    try {
      await register(email, password);
      navigate('/');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const detail = axiosErr?.response?.data?.detail;
      setError(
        detail || 'Registration failed. The email may already be in use or is invalid.'
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
          maxWidth: '420px',
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
            CREATE ACCOUNT
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Register for FinSense</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Access financial intelligence, watchlists, and NLP insights
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
              htmlFor="register-email"
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}
            >
              Work Email Address
            </label>
            <input
              id="register-email"
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
            <label
              htmlFor="register-password"
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}
            >
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="register-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
                minLength={8}
                className="fin-input"
                style={{ width: '100%', paddingRight: '38px' }}
                autoComplete="new-password"
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

          <div>
            <label
              htmlFor="register-confirm-password"
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}
            >
              Confirm Password
            </label>
            <input
              id="register-confirm-password"
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat your password"
              required
              minLength={8}
              className="fin-input"
              style={{ width: '100%' }}
              autoComplete="new-password"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="fin-btn fin-btn-primary"
            style={{ width: '100%', marginTop: '8px', height: '40px' }}
          >
            {loading ? 'Creating Account…' : 'Complete Registration'}
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
          Already have an account?{' '}
          <NavLink
            to="/login"
            style={{
              color: 'var(--accent-primary)',
              fontWeight: 600,
            }}
          >
            Sign in
          </NavLink>
        </div>
      </div>
    </div>
  );
};

export default Register;
