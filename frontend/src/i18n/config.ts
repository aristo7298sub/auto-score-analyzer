import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  zh: {
    translation: {
      // 通用
      common: {
        confirm: '确认',
        cancel: '取消',
        save: '保存',
        delete: '删除',
        edit: '编辑',
        loading: '加载中...',
        success: '成功',
        error: '错误',
        logout: '退出登录',
        profile: '个人资料',
        settings: '设置',
      },
      
      // 导航
      nav: {
        analysis: '成绩分析',
        history: '历史记录',
        quota: '配额管理',
        admin: '管理后台',
      },
      
      // 认证
      auth: {
        login: '登录',
        register: '注册',
        username: '用户名',
        email: '邮箱',
        password: '密码',
        referralCode: '引荐码（可选）',
        hasAccount: '已有账号？',
        noAccount: '还没有账号？',
        loginSuccess: '登录成功',
        registerSuccess: '注册成功',
        loginFailed: '登录失败',
        registerFailed: '注册失败',
        usernamePlaceholder: '请输入用户名',
        emailPlaceholder: '请输入邮箱地址',
        passwordPlaceholder: '请输入密码',
        referralPlaceholder: '输入引荐码可获得额外配额',
      },
      
      // 配额
      quota: {
        balance: '配额余额',
        used: '已使用',
        unlimited: '无限制',
        vipUser: 'VIP用户',
        transactions: '交易记录',
        referral: '引荐系统',
        myReferralCode: '我的引荐码',
        referralCount: '引荐人数',
        bonusEarned: '获得奖励',
        copyCode: '复制引荐码',
        copied: '已复制',
        insufficientQuota: '配额不足',
      },
      
      // 分析
      analysis: {
        upload: '上传文件',
        uploadHint: '目前仅支持 Excel (.xlsx)',
        dragFile: '点击上传文件或拖拽文件到此处',
        fileFormats: '目前仅支持Excel (.xlsx)',
        oneShotLabel: '🎨 示例风格参考（可选填）',
        oneShotPlaceholder: '📝 可粘贴一段你过往的成绩分析，或者你希望AI模仿的风格/结构的示例（留空则使用默认风格）',
        analyzeNow: '一键AI分析',
        parsing: '正在解析文件...',
        parsedReady: '已解析，等待AI分析',
        searchTitle: '分析结果查询',
        searchPlaceholder: '请输入学生姓名',
        searchButton: '搜索',
        records: '分析记录',
        analyzing: '分析中...',
        analysisComplete: '分析完成',
        studentCount: '学生数量',
        quotaCost: '配额消耗',
        exportExcel: '导出Excel',
        exportWord: '导出Word',
      },
      
      // 管理员
      admin: {
        userManagement: '用户管理',
        systemStats: '系统统计',
        totalUsers: '总用户数',
        activeUsers: '活跃用户',
        vipUsers: 'VIP用户',
        totalAnalyses: '总分析次数',
        setVip: '设置VIP',
        removeVip: '取消VIP',
        enableAccount: '启用账号',
        disableAccount: '禁用账号',
        addQuota: '添加配额',
      },
    },
  },
  
  en: {
    translation: {
      // Common
      common: {
        confirm: 'Confirm',
        cancel: 'Cancel',
        save: 'Save',
        delete: 'Delete',
        edit: 'Edit',
        loading: 'Loading...',
        success: 'Success',
        error: 'Error',
        logout: 'Logout',
        profile: 'Profile',
        settings: 'Settings',
      },
      
      // Navigation
      nav: {
        analysis: 'Score Analysis',
        history: 'History',
        quota: 'Quota Management',
        admin: 'Admin Panel',
      },
      
      // Authentication
      auth: {
        login: 'Login',
        register: 'Register',
        username: 'Username',
        email: 'Email',
        password: 'Password',
        referralCode: 'Referral Code (Optional)',
        hasAccount: 'Already have an account?',
        noAccount: "Don't have an account?",
        loginSuccess: 'Login successful',
        registerSuccess: 'Registration successful',
        loginFailed: 'Login failed',
        registerFailed: 'Registration failed',
        usernamePlaceholder: 'Enter username',
        emailPlaceholder: 'Enter email address',
        passwordPlaceholder: 'Enter password',
        referralPlaceholder: 'Enter referral code for bonus quota',
      },
      
      // Quota
      quota: {
        balance: 'Quota Balance',
        used: 'Used',
        unlimited: 'Unlimited',
        vipUser: 'VIP User',
        transactions: 'Transactions',
        referral: 'Referral System',
        myReferralCode: 'My Referral Code',
        referralCount: 'Referrals',
        bonusEarned: 'Bonus Earned',
        copyCode: 'Copy Code',
        copied: 'Copied',
        insufficientQuota: 'Insufficient quota',
      },
      
      // Analysis
      analysis: {
        upload: 'Upload File',
        uploadHint: 'Currently only Excel (.xlsx) is supported',
        dragFile: 'Click to upload or drag & drop file here',
        fileFormats: 'Currently only Excel (.xlsx) is supported',
        oneShotLabel: '🎨 Style example (optional)',
        oneShotPlaceholder: '📝 Paste a past analysis or an example style/structure for AI to follow (leave empty to use default style)',
        analyzeNow: 'Run AI Analysis',
        parsing: 'Parsing file...',
        parsedReady: 'Parsed. Ready for AI analysis',
        searchTitle: 'Analysis Results Search',
        searchPlaceholder: 'Enter student name',
        searchButton: 'Search',
        records: 'Analysis Records',
        analyzing: 'Analyzing...',
        analysisComplete: 'Analysis Complete',
        studentCount: 'Student Count',
        quotaCost: 'Quota Cost',
        exportExcel: 'Export Excel',
        exportWord: 'Export Word',
      },
      
      // Admin
      admin: {
        userManagement: 'User Management',
        systemStats: 'System Statistics',
        totalUsers: 'Total Users',
        activeUsers: 'Active Users',
        vipUsers: 'VIP Users',
        totalAnalyses: 'Total Analyses',
        setVip: 'Set VIP',
        removeVip: 'Remove VIP',
        enableAccount: 'Enable Account',
        disableAccount: 'Disable Account',
        addQuota: 'Add Quota',
      },
    },
  },
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'zh',
    fallbackLng: 'zh',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
