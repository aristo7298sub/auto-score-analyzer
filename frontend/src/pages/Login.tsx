import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { message } from 'antd';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../services/apiClient';
import '../styles/auth.css';

const Login: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);

  const [mode, setMode] = useState<'password' | 'reset'>('password');

  const [passwordForm, setPasswordForm] = useState({
    username: '',
    password: '',
  });

  const [resetForm, setResetForm] = useState({
    email: '',
    code: '',
    new_password: '',
  });

  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const timer = window.setInterval(() => {
      setCooldownSeconds((s) => Math.max(0, s - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cooldownSeconds]);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await authApi.login(passwordForm);
      const { access_token, user } = response.data;
      
      login(access_token, user);
      message.success(t('auth.loginSuccess'));
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('auth.loginFailed'));
    } finally {
      setLoading(false);
    }
  };


  const handleSendResetCode = async () => {
    const email = (resetForm.email || '').trim();
    if (!email) {
      message.error(t('auth.emailRequired'));
      return;
    }
    if (cooldownSeconds > 0) return;

    setSendingCode(true);
    try {
      const resp = await authApi.passwordResetRequest({ email });
      message.success(resp.data?.message || t('auth.codeSent'));
      setCooldownSeconds(60);
    } catch (error: any) {
      // reset/request is generic by design; still surface backend detail if present
      message.error(error.response?.data?.detail || t('auth.sendCodeFailed'));
    } finally {
      setSendingCode(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const resp = await authApi.passwordResetConfirm({
        email: resetForm.email.trim(),
        code: resetForm.code.trim(),
        new_password: resetForm.new_password,
      });
      message.success(resp.data?.message || t('auth.resetSuccess'));
      setMode('password');
      setResetForm({ email: '', code: '', new_password: '' });
      setCooldownSeconds(0);
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('auth.resetFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <img src="/logo.svg" alt="Logo" className="auth-logo" />
          <h1 className="auth-title">{t('app.title')}</h1>
          <p className="auth-subtitle">
            {mode === 'reset' ? t('auth.resetPassword') : t('auth.login')}
          </p>
        </div>

        {mode === 'password' && (
          <>
            <form className="auth-form" onSubmit={handlePasswordLogin}>
              <div className="form-group">
                <label htmlFor="username">{t('auth.username')}</label>
                <input
                  id="username"
                  type="text"
                  className="input"
                  placeholder={t('auth.usernamePlaceholder')}
                  value={passwordForm.username}
                  onChange={(e) => setPasswordForm({ ...passwordForm, username: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">{t('auth.password')}</label>
                <input
                  id="password"
                  type="password"
                  className="input"
                  placeholder={t('auth.passwordPlaceholder')}
                  value={passwordForm.password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, password: e.target.value })}
                  required
                />
              </div>

              <button type="submit" className="btn-primary btn-block" disabled={loading}>
                {loading ? t('common.loading') : t('auth.login')}
              </button>
            </form>

            <div className="auth-footer">
              <p>
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    setMode('reset');
                    setCooldownSeconds(0);
                  }}
                >
                  {t('auth.forgotPassword')}
                </a>
              </p>
              <p>
                {t('auth.noAccount')} <Link to="/register">{t('auth.register')}</Link>
              </p>
            </div>
          </>
        )}

        {mode === 'reset' && (
          <>
            <form className="auth-form" onSubmit={handleResetPassword}>
              <div className="form-group">
                <label htmlFor="reset_email">{t('auth.email')}</label>
                <input
                  id="reset_email"
                  type="email"
                  className="input"
                  placeholder={t('auth.emailPlaceholder')}
                  value={resetForm.email}
                  onChange={(e) => setResetForm({ ...resetForm, email: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="reset_code">{t('auth.verificationCode')}</label>
                <input
                  id="reset_code"
                  type="text"
                  inputMode="numeric"
                  className="input"
                  placeholder={t('auth.verificationCodePlaceholder')}
                  value={resetForm.code}
                  onChange={(e) => setResetForm({ ...resetForm, code: e.target.value })}
                  required
                  minLength={6}
                  maxLength={6}
                />
                <button
                  type="button"
                  className="btn-primary btn-block"
                  onClick={handleSendResetCode}
                  disabled={sendingCode || loading || cooldownSeconds > 0}
                >
                  {cooldownSeconds > 0
                    ? t('auth.resendInSeconds', { seconds: cooldownSeconds })
                    : (sendingCode ? t('common.loading') : t('auth.sendResetCode'))}
                </button>
              </div>

              <div className="form-group">
                <label htmlFor="new_password">{t('auth.newPassword')}</label>
                <input
                  id="new_password"
                  type="password"
                  className="input"
                  placeholder={t('auth.newPasswordPlaceholder')}
                  value={resetForm.new_password}
                  onChange={(e) => setResetForm({ ...resetForm, new_password: e.target.value })}
                  required
                  minLength={6}
                />
              </div>

              <button type="submit" className="btn-primary btn-block" disabled={loading}>
                {loading ? t('common.loading') : t('auth.confirmReset')}
              </button>
            </form>

            <div className="auth-footer">
              <p>
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    setMode('password');
                    setCooldownSeconds(0);
                  }}
                >
                  {t('auth.backToLogin')}
                </a>
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Login;
