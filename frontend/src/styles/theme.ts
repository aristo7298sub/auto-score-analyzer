// Morandi色系配置
export const morandiColors = {
  // 主色调
  primary: '#678ea2',
  secondary: '#8b7692',
  tertiary: '#565f88',
  
  // 浅色主题
  light: {
    background: '#f5f5f5',
    surface: 'rgba(255, 255, 255, 0.8)',
    surfaceHover: 'rgba(255, 255, 255, 0.95)',
    text: '#2d3748',
    textSecondary: '#718096',
    border: '#e2e8f0',
    shadow: 'rgba(103, 142, 162, 0.1)',
    
    // 状态色
    success: '#81c784',
    warning: '#ffb74d',
    error: '#e57373',
    info: '#64b5f6',
  },
  
  // 深色主题
  dark: {
    background: '#1a202c',
    surface: 'rgba(45, 55, 72, 0.8)',
    surfaceHover: 'rgba(45, 55, 72, 0.95)',
    text: '#f7fafc',
    textSecondary: '#a0aec0',
    border: '#2d3748',
    shadow: 'rgba(0, 0, 0, 0.3)',
    
    // 状态色
    success: '#81c784',
    warning: '#ffb74d',
    error: '#e57373',
    info: '#64b5f6',
  },
};

// 生成CSS变量
export const generateThemeCSS = (theme: 'light' | 'dark') => {
  const colors = theme === 'light' ? morandiColors.light : morandiColors.dark;
  
  return `
    --color-primary: ${morandiColors.primary};
    --color-secondary: ${morandiColors.secondary};
    --color-tertiary: ${morandiColors.tertiary};
    
    --color-background: ${colors.background};
    --color-surface: ${colors.surface};
    --color-surface-hover: ${colors.surfaceHover};
    --color-text: ${colors.text};
    --color-text-secondary: ${colors.textSecondary};
    --color-border: ${colors.border};
    --color-shadow: ${colors.shadow};
    
    --color-success: ${colors.success};
    --color-warning: ${colors.warning};
    --color-error: ${colors.error};
    --color-info: ${colors.info};
  `;
};

// 毛玻璃效果样式
export const glassStyle = {
  background: 'var(--color-surface)',
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  border: '1px solid var(--color-border)',
  boxShadow: '0 8px 32px 0 var(--color-shadow)',
};

// 卡片样式
export const cardStyle = {
  ...glassStyle,
  borderRadius: '16px',
  padding: '24px',
  transition: 'all 0.3s ease',
};

// 按钮样式
export const buttonStyle = {
  primary: {
    background: `linear-gradient(135deg, ${morandiColors.primary}, ${morandiColors.secondary})`,
    color: '#fff',
    border: 'none',
    borderRadius: '12px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    boxShadow: '0 4px 12px var(--color-shadow)',
  },
  
  secondary: {
    background: 'transparent',
    color: 'var(--color-primary)',
    border: '2px solid var(--color-primary)',
    borderRadius: '12px',
    padding: '10px 22px',
    fontSize: '16px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
};

// 输入框样式
export const inputStyle = {
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: '12px',
  padding: '12px 16px',
  fontSize: '16px',
  color: 'var(--color-text)',
  outline: 'none',
  transition: 'all 0.3s ease',
  
  '&:focus': {
    borderColor: 'var(--color-primary)',
    boxShadow: '0 0 0 3px rgba(103, 142, 162, 0.1)',
  },
};
