import React, { useEffect } from 'react';
import { Outlet, useNavigate, NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { message, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import { useAuthStore } from '../store/authStore';
import { useAppStore } from '../store/appStore';
import '../styles/layout.css';

const MainLayout: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, language, toggleTheme, setLanguage } = useAppStore();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const handleLogout = () => {
    logout();
    message.success(t('common.success'));
    navigate('/login');
  };

  const handleLanguageToggle = () => {
    setLanguage(language === 'zh' ? 'en' : 'zh');
  };

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      label: `${t('common.profile')}${t('common.wipSuffix')}`,
    },
    {
      key: 'settings',
      label: `${t('common.settings')}${t('common.wipSuffix')}`,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      label: t('common.logout'),
      onClick: handleLogout,
    },
  ];

  return (
    <div className="layout">
      {/* 顶部导航栏 */}
      <nav className="navbar">
        <div className="navbar-left">
          {/* 品牌Logo */}
          <a href="/" className="brand">
            <img src="/logo.svg" alt="Logo" className="brand-logo" />
            <span className="brand-text">{t('app.title')}</span>
          </a>

          {/* 主导航菜单 */}
          <div className="main-nav">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <span className="nav-icon">📊</span>
              <span>{t('nav.analysis')}</span>
            </NavLink>

            <NavLink to="/history" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <span className="nav-icon">📝</span>
              <span>{t('nav.history')}</span>
            </NavLink>

            <NavLink to="/quota" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <span className="nav-icon">💎</span>
              <span>{t('nav.quota')}</span>
            </NavLink>
          </div>
        </div>

        {/* 右侧工具栏 */}
        <div className="navbar-right">
          {/* 配额显示 */}
          <div className="quota-display">
            <span className="quota-icon">💎</span>
            <span>{user?.is_vip ? t('quota.unlimited') : user?.quota_balance}</span>
          </div>

          {/* 语言切换 */}
          <button className="toolbar-btn" onClick={handleLanguageToggle} title={t('common.language')}>
            {language === 'zh' ? '中' : 'EN'}
          </button>

          {/* 主题切换 */}
          <button className="toolbar-btn" onClick={toggleTheme} title={t('common.theme')}>
            {theme === 'light' ? '🌙' : '☀️'}
          </button>

          {/* 用户菜单 */}
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" trigger={['click']}>
            <div className="user-menu">
              <div className="user-avatar-small">
                {user?.username.charAt(0).toUpperCase()}
              </div>
              <span className="user-name-small">{user?.username}</span>
              {user?.is_vip && <span className="vip-badge-small">VIP</span>}
            </div>
          </Dropdown>
        </div>
      </nav>

      {/* 主内容区 */}
      <main className="main-container">
        <div className="content-wrapper">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
