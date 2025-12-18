import React, { useEffect, useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { message } from 'antd';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../services/apiClient';
import '../styles/auth.css';

const Register: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const login = useAuthStore((state) => state.login);

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    referral_code: '',
  });
  const [loading, setLoading] = useState(false);

  // 通过注册链接预填邀请码：/register?ref=XXXX
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const ref = params.get('ref');
    if (ref) {
      setFormData((prev) => ({ ...prev, referral_code: ref }));
    }
  }, [location.search]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const registerData: any = {
        username: formData.username,
        password: formData.password,
      };
      
      // 邮箱可选
      if (formData.email) {
        registerData.email = formData.email;
      }
      
      if (formData.referral_code) {
        registerData.referral_code = formData.referral_code;
      }

      const response = await authApi.register(registerData);
      const { access_token, user } = response.data;
      
      login(access_token, user);
      message.success(t('auth.registerSuccess'));
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('auth.registerFailed'));
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
          <p className="auth-subtitle">{t('auth.register')}</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">{t('auth.username')}</label>
            <input
              id="username"
              type="text"
              className="input"
              placeholder={t('auth.usernamePlaceholder')}
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              required
              minLength={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">{t('auth.email')} <span style={{ color: '#999', fontWeight: 'normal' }}>{t('common.optionalSuffix')}</span></label>
            <input
              id="email"
              type="email"
              className="input"
              placeholder={t('auth.emailPlaceholder')}
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">{t('auth.password')}</label>
            <input
              id="password"
              type="password"
              className="input"
              placeholder={t('auth.passwordPlaceholder')}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              minLength={6}
            />
          </div>

          <div className="form-group">
            <label htmlFor="referral_code">{t('auth.referralCode')}</label>
            <input
              id="referral_code"
              type="text"
              className="input"
              placeholder={t('auth.referralPlaceholder')}
              value={formData.referral_code}
              onChange={(e) => setFormData({ ...formData, referral_code: e.target.value })}
            />
          </div>

          <button type="submit" className="btn-primary btn-block" disabled={loading}>
            {loading ? t('common.loading') : t('auth.register')}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            {t('auth.hasAccount')} <Link to="/login">{t('auth.login')}</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
