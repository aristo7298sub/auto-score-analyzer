import React, { useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';

import '../styles/settings.css';

import { authApi } from '../services/apiClient';
import { useAuthStore } from '../store/authStore';

const Settings: React.FC = () => {
  const { t } = useTranslation();
  const { user, updateUser } = useAuthStore();

  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');

  const [sendingCode, setSendingCode] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const timer = window.setInterval(() => {
      setCooldownSeconds((s) => Math.max(0, s - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cooldownSeconds]);

  const currentEmail = useMemo(() => (user?.email || '').trim(), [user?.email]);
  const verified = !!user?.email_verified;

  // Prefill with current email for convenience.
  useEffect(() => {
    if (!email && currentEmail) {
      setEmail(currentEmail);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentEmail]);

  const refreshMe = async () => {
    try {
      const resp = await authApi.getCurrentUser();
      updateUser(resp.data);
    } catch {
      // ignore; page is still usable
    }
  };

  const handleSendBindCode = async () => {
    const normalized = (email || '').trim();
    if (!normalized) {
      message.error(t('auth.emailRequired'));
      return;
    }
    if (cooldownSeconds > 0) return;

    setSendingCode(true);
    try {
      const resp = await authApi.bindEmailRequest({ email: normalized });
      message.success(resp.data?.message || t('auth.codeSent'));
      setCooldownSeconds(60);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || t('auth.sendCodeFailed'));
    } finally {
      setSendingCode(false);
    }
  };

  const handleConfirmBind = async () => {
    const normalized = (email || '').trim();
    if (!normalized) {
      message.error(t('auth.emailRequired'));
      return;
    }
    if (!(code || '').trim()) {
      message.error(t('auth.codeRequired'));
      return;
    }
    if (!password) {
      message.error(t('auth.passwordRequired'));
      return;
    }

    setConfirming(true);
    try {
      const resp = await authApi.bindEmailConfirm({
        email: normalized,
        code: (code || '').trim(),
        password,
      });
      message.success(resp.data?.message || t('auth.bindEmailSuccess'));
      setCode('');
      setPassword('');
      await refreshMe();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || t('auth.bindEmailFailed'));
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-center">
        <div className="card settings-card">
          <div className="settings-header">
            <h2 className="settings-title">{t('common.settings')}</h2>
            <p className="settings-subtitle">{t('auth.bindEmail')}</p>
          </div>

          <div className="settings-current">
            <span>{t('auth.currentEmail')}：</span>
            <strong>{currentEmail ? currentEmail : t('auth.emailNotBound')}</strong>
            {currentEmail && (
              <span className="settings-pill">{verified ? t('auth.verified') : t('auth.unverified')}</span>
            )}
          </div>

          <div className="settings-hint">{t('auth.bindEmailHint')}</div>




          <div className="settings-form">
            <div>
              <label htmlFor="bind_email">{t('auth.email')}</label>
              <div className="settings-row" style={{ marginTop: 8 }}>
                <input
                  id="bind_email"
                  type="email"
                  className="input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t('auth.emailPlaceholder')}
                />
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleSendBindCode}
                  disabled={sendingCode || confirming || cooldownSeconds > 0}
                >
                  {cooldownSeconds > 0
                    ? t('auth.resendInSeconds', { seconds: cooldownSeconds })
                    : (sendingCode ? t('common.loading') : t('auth.sendBindCode'))}
                </button>
              </div>
            </div>

            <div>
              <label htmlFor="bind_code">{t('auth.verificationCode')}</label>
              <input
                id="bind_code"
                type="text"
                inputMode="numeric"
                className="input"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder={t('auth.verificationCodePlaceholder')}
                maxLength={6}
              />
            </div>

            <div>
              <label htmlFor="bind_password">{t('auth.password')}</label>
              <input
                id="bind_password"
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.passwordPlaceholder')}
              />
            </div>

            <div className="settings-actions">
              <button
                type="button"
                className="btn-primary"
                onClick={handleConfirmBind}
                disabled={confirming || sendingCode}
              >
                {confirming ? t('common.loading') : t('auth.confirmBindEmail')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
