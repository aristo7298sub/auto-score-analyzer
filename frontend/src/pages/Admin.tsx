import React, { useState, useEffect } from 'react';
import { Card, Tabs, Table, Button, Input, Tag, Space, Statistic, Row, Col, message, Modal, InputNumber, Badge, Popconfirm, DatePicker, Segmented } from 'antd';
import { 
  UserOutlined, 
  TeamOutlined, 
  CrownOutlined, 
  LineChartOutlined,
  SearchOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  DashboardOutlined,
  LogoutOutlined,
  HomeOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../store/authStore';
import { useAppStore } from '../store/appStore';
import { adminApi } from '../services/apiClient';
import type { ColumnsType } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import '../styles/admin.css';

interface AdminUser {
  id: number;
  username: string;
  email: string;
  is_vip: boolean;
  vip_expires_at?: string | null;
  is_admin: boolean;
  is_active: boolean;
  quota_balance: number;
  quota_used: number;
  referral_count: number;
  range_quota_used?: number;
  range_referral_count?: number;
  range_prompt_tokens?: number;
  range_completion_tokens?: number;
  created_at: string;
  last_login: string | null;
}

interface AdminStats {
  total_users: number;
  active_users: number;
  vip_users: number;
  total_analyses: number;
  success_analyses: number;
  failed_analyses: number;
  total_quota_used: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
}

interface AnalysisLog {
  id: number;
  user_id: number;
  username: string;
  filename: string;
  student_count: number;
  quota_cost: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

const Admin: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { language, theme, toggleTheme, setLanguage } = useAppStore();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [logs, setLogs] = useState<AnalysisLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');

  // 用户管理：时间范围（默认过去7天）
  const [userTimeRange, setUserTimeRange] = useState<'1d' | '7d' | '30d' | 'custom'>('7d');
  const [userCustomStart, setUserCustomStart] = useState<Dayjs | null>(null);
  const [userCustomEnd, setUserCustomEnd] = useState<Dayjs | null>(null);
  
  // 配额弹窗
  const [quotaModalVisible, setQuotaModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [quotaAmount, setQuotaAmount] = useState(100);
  const [quotaDescription, setQuotaDescription] = useState('');

  // VIP 弹窗（设置天数）
  const [vipModalVisible, setVipModalVisible] = useState(false);
  const [vipDays, setVipDays] = useState(30);
  const [vipTargetUser, setVipTargetUser] = useState<AdminUser | null>(null);

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'dashboard') {
        await loadStats();
      } else if (activeTab === 'users') {
        await loadUsers();
      } else if (activeTab === 'logs') {
        await loadLogs();
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('adminPage.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    const response = await adminApi.getStats();
    setStats(response.data);
  };

  const loadUsers = async () => {
    const startAt = userTimeRange === 'custom' && userCustomStart ? userCustomStart.toISOString() : undefined;
    const endAt = userTimeRange === 'custom' && userCustomEnd ? userCustomEnd.toISOString() : undefined;
    const response = await adminApi.getUsers(100, 0, searchText || undefined, userTimeRange, startAt, endAt);
    setUsers(response.data);
  };

  const loadLogs = async () => {
    const response = await adminApi.getLogs(100, 0);
    setLogs(response.data);
  };

  const handleSetVip = async (userId: number, isVip: boolean, days?: number) => {
    try {
      await adminApi.setVip(userId, isVip, days);
      message.success(isVip ? t('adminPage.vipEnabled') : t('adminPage.vipDisabled'));
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('adminPage.operationFailed'));
    }
  };

  const openVipModal = (record: AdminUser) => {
    setVipTargetUser(record);
    setVipDays(30);
    setVipModalVisible(true);
  };

  const confirmSetVipWithDays = async () => {
    if (!vipTargetUser) return;
    await handleSetVip(vipTargetUser.id, true, vipDays);
    setVipModalVisible(false);
    setVipTargetUser(null);
  };

  const handleToggleActive = async (userId: number) => {
    try {
      await adminApi.toggleActive(userId);
      message.success(t('adminPage.userStatusUpdated'));
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('adminPage.operationFailed'));
    }
  };

  const handleDeleteUser = async (userId: number) => {
    try {
      await adminApi.deleteUser(userId);
      message.success(t('adminPage.userDeleted'));
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('adminPage.deleteFailed'));
    }
  };

  const handleAddQuota = async () => {
    if (!selectedUser) return;
    
    try {
      await adminApi.addQuota(selectedUser.id, quotaAmount, quotaDescription || undefined);
      message.success(t('adminPage.addQuotaSuccess', { username: selectedUser.username, amount: quotaAmount }));
      setQuotaModalVisible(false);
      setQuotaAmount(100);
      setQuotaDescription('');
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('adminPage.addQuotaFailed'));
    }
  };

  const handleLogout = () => {
    logout();
    message.success(t('adminPage.loggedOut'));
    navigate('/login');
  };

  const handleLanguageToggle = () => {
    setLanguage(language === 'zh' ? 'en' : 'zh');
  };

  // 用户表格列定义
  const userColumns: ColumnsType<AdminUser> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: t('adminPage.users.columns.username'),
      dataIndex: 'username',
      key: 'username',
      render: (text, record) => (
        <Space>
          {text}
          {record.is_admin && <Tag color="red">{t('adminPage.users.badges.admin')}</Tag>}
        </Space>
      ),
    },
    {
      title: t('adminPage.users.columns.email'),
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'VIP',
      dataIndex: 'is_vip',
      key: 'is_vip',
      render: (isVip) => (
        isVip ? <Tag color="gold"><CrownOutlined /> VIP</Tag> : <Tag>{t('adminPage.users.badges.normal')}</Tag>
      ),
    },
    {
      title: t('adminPage.users.columns.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive) => (
        <Badge
          status={isActive ? 'success' : 'error'}
          text={isActive ? t('adminPage.users.status.active') : t('adminPage.users.status.disabled')}
        />
      ),
    },
    {
      title: t('adminPage.users.columns.quotaBalance'),
      dataIndex: 'quota_balance',
      key: 'quota_balance',
      render: (balance) => <Tag color="blue">{balance}</Tag>,
    },
    {
      title: t('adminPage.users.columns.quotaUsed'),
      dataIndex: 'range_quota_used',
      key: 'range_quota_used',
      sorter: (a, b) => (a.range_quota_used ?? 0) - (b.range_quota_used ?? 0),
      sortDirections: ['descend', 'ascend'],
      render: (v) => v ?? 0,
    },
    {
      title: t('adminPage.users.columns.referrals'),
      dataIndex: 'range_referral_count',
      key: 'range_referral_count',
      sorter: (a, b) => (a.range_referral_count ?? 0) - (b.range_referral_count ?? 0),
      sortDirections: ['descend', 'ascend'],
      render: (v) => v ?? 0,
    },
    {
      title: t('adminPage.users.columns.tokens'),
      key: 'range_tokens',
      children: [
        {
          title: 'Input',
          dataIndex: 'range_prompt_tokens',
          key: 'range_prompt_tokens',
          width: 120,
          sorter: (a, b) => (a.range_prompt_tokens ?? 0) - (b.range_prompt_tokens ?? 0),
          sortDirections: ['descend', 'ascend'],
          render: (v) => v ?? 0,
        },
        {
          title: 'Generated',
          dataIndex: 'range_completion_tokens',
          key: 'range_completion_tokens',
          width: 130,
          sorter: (a, b) => (a.range_completion_tokens ?? 0) - (b.range_completion_tokens ?? 0),
          sortDirections: ['descend', 'ascend'],
          render: (v) => v ?? 0,
        },
      ],
    },
    {
      title: t('adminPage.users.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US'),
    },
    {
      title: t('adminPage.users.columns.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            type={record.is_vip ? 'default' : 'primary'}
            onClick={() => {
              if (record.is_vip) {
                handleSetVip(record.id, false);
              } else {
                openVipModal(record);
              }
            }}
          >
            {record.is_vip ? t('adminPage.users.actions.removeVip') : t('adminPage.users.actions.setVip')}
          </Button>
          <Button
            size="small"
            danger={record.is_active}
            onClick={() => handleToggleActive(record.id)}
          >
            {record.is_active ? t('adminPage.users.actions.disable') : t('adminPage.users.actions.enable')}
          </Button>
          <Button
            size="small"
            icon={<PlusOutlined />}
            onClick={() => {
              setSelectedUser(record);
              setQuotaModalVisible(true);
            }}
          >
            {t('adminPage.users.actions.addQuota')}
          </Button>

          <Popconfirm
            title={t('adminPage.users.deleteConfirmTitle')}
            description={t('adminPage.users.deleteConfirmDesc', { username: record.username })}
            okText={t('adminPage.users.deleteConfirmOk')}
            cancelText={t('common.cancel')}
            okButtonProps={{ danger: true }}
            onConfirm={() => handleDeleteUser(record.id)}
            disabled={record.id === user?.id}
          >
            <Button
              size="small"
              danger
              disabled={record.id === user?.id}
            >
              {t('adminPage.users.actions.deleteUser')}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 日志表格列定义
  const logColumns: ColumnsType<AnalysisLog> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: t('adminPage.logs.columns.user'),
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: t('adminPage.logs.columns.filename'),
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: t('adminPage.logs.columns.studentCount'),
      dataIndex: 'student_count',
      key: 'student_count',
    },
    {
      title: t('adminPage.logs.columns.quotaCost'),
      dataIndex: 'quota_cost',
      key: 'quota_cost',
      render: (cost) => <Tag color="orange">{cost}</Tag>,
    },
    {
      title: t('adminPage.logs.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
          success: { color: 'success', icon: <CheckCircleOutlined />, text: t('adminPage.logs.status.success') },
          failed: { color: 'error', icon: <CloseCircleOutlined />, text: t('adminPage.logs.status.failed') },
          processing: { color: 'processing', icon: <FileTextOutlined />, text: t('adminPage.logs.status.processing') },
        };
        const config = statusConfig[status] || statusConfig.processing;
        return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>;
      },
    },
    {
      title: t('adminPage.logs.columns.time'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US'),
    },
    {
      title: t('adminPage.logs.columns.error'),
      dataIndex: 'error_message',
      key: 'error_message',
      render: (msg) => msg ? <span style={{ color: 'red' }}>{msg}</span> : '-',
    },
  ];

  return (
    <div className="admin-layout">
      {/* 管理员导航栏 */}
      <nav className="admin-navbar">
        <div className="admin-navbar-left">
          <img src="/logo.svg" alt="Logo" className="admin-logo" />
          <span className="admin-title">{t('adminPage.title')}</span>
        </div>
        <div className="admin-navbar-right">
          <Button
            type="text"
            icon={<HomeOutlined />}
            onClick={() => navigate('/')}
          >
            {t('adminPage.backHome')}
          </Button>
          <button className="toolbar-btn" onClick={handleLanguageToggle} title={t('common.language')}>
            {language === 'zh' ? '中' : 'EN'}
          </button>
          <button className="toolbar-btn" onClick={toggleTheme} title={t('common.theme')}>
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <div className="admin-user-info">
            <span>{user?.username}</span>
            <Tag color="red">{t('adminPage.users.badges.admin')}</Tag>
          </div>
          <Button
            type="text"
            danger
            icon={<LogoutOutlined />}
            onClick={handleLogout}
          >
            {t('common.logout')}
          </Button>
        </div>
      </nav>

      {/* 管理员内容区 */}
      <div className="admin-page">
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          items={[
            {
              key: 'dashboard',
              label: (
                <span>
                  <DashboardOutlined />
                  {t('adminPage.tabs.dashboard')}
                </span>
              ),
              children: stats && (
                <div>
                  <Row gutter={[16, 16]} className="stats-row">
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title={t('adminPage.stats.totalUsers')}
                          value={stats.total_users}
                          prefix={<TeamOutlined />}
                          valueStyle={{ color: '#3f8600' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title={t('adminPage.stats.activeUsers')}
                          value={stats.active_users}
                          prefix={<UserOutlined />}
                          valueStyle={{ color: '#1890ff' }}
                          suffix={`/ ${stats.total_users}`}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title={t('adminPage.stats.vipUsers')}
                          value={stats.vip_users}
                          prefix={<CrownOutlined />}
                          valueStyle={{ color: '#cf1322' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title={t('adminPage.stats.totalAnalyses')}
                          value={stats.total_analyses}
                          prefix={<LineChartOutlined />}
                          valueStyle={{ color: '#722ed1' }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                    <Col xs={24} sm={12} lg={8}>
                      <Card>
                        <Statistic
                          title={t('adminPage.stats.successAnalyses')}
                          value={stats.success_analyses}
                          suffix={`/ ${stats.total_analyses}`}
                          valueStyle={{ color: '#52c41a' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={8}>
                      <Card>
                        <Statistic
                          title={t('adminPage.stats.failedAnalyses')}
                          value={stats.failed_analyses}
                          suffix={`/ ${stats.total_analyses}`}
                          valueStyle={{ color: '#ff4d4f' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={8}>
                      <Card>
                        <Statistic
                          title={t('adminPage.stats.totalQuotaUsed')}
                          value={stats.total_quota_used}
                          valueStyle={{ color: '#fa8c16' }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                    <Col span={24}>
                      <Card title={t('adminPage.stats.totalTokens')}> 
                        <Row gutter={[16, 16]}>
                          <Col xs={24} sm={12}>
                            <Statistic
                              title="Input"
                              value={stats.total_prompt_tokens}
                            />
                          </Col>
                          <Col xs={24} sm={12}>
                            <Statistic
                              title="Generated"
                              value={stats.total_completion_tokens}
                            />
                          </Col>
                        </Row>
                      </Card>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'users',
              label: (
                <span>
                  <TeamOutlined />
                  {t('adminPage.tabs.users')}
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Space wrap>
                      <Input
                        placeholder={t('adminPage.users.searchPlaceholder')}
                        prefix={<SearchOutlined />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        onPressEnter={loadUsers}
                        style={{ width: 300 }}
                      />
                      <Segmented
                        value={userTimeRange}
                        options={[
                          { label: t('adminPage.timeRanges.1d'), value: '1d' },
                          { label: t('adminPage.timeRanges.7d'), value: '7d' },
                          { label: t('adminPage.timeRanges.30d'), value: '30d' },
                          { label: t('adminPage.timeRanges.custom'), value: 'custom' },
                        ]}
                        onChange={(v) => {
                          const next = v as any;
                          setUserTimeRange(next);
                          if (next !== 'custom') {
                            setUserCustomStart(null);
                            setUserCustomEnd(null);
                          }
                        }}
                      />
                      {userTimeRange === 'custom' && (
                        <Space size={8}>
                          <DatePicker
                            showTime
                            value={userCustomStart}
                            onChange={(v) => setUserCustomStart(v)}
                            placeholder={t('common.startTime')}
                          />
                          <DatePicker
                            showTime
                            value={userCustomEnd}
                            onChange={(v) => setUserCustomEnd(v)}
                            placeholder={t('common.endTime')}
                          />
                        </Space>
                      )}
                      <Button type="primary" onClick={loadUsers}>
                        {t('common.search')}
                      </Button>
                    </Space>
                    <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
                      {t('adminPage.users.rangeHint')}
                    </div>
                  </div>
                  <Table
                    columns={userColumns}
                    dataSource={users}
                    rowKey="id"
                    loading={loading}
                    size="small"
                    className="admin-users-table"
                    scroll={{ x: 'max-content' }}
                    pagination={{ pageSize: 20 }}
                  />
                </div>
              ),
            },
            {
              key: 'logs',
              label: (
                <span>
                  <FileTextOutlined />
                  {t('adminPage.tabs.logs')}
                </span>
              ),
              children: (
                <Table
                  columns={logColumns}
                  dataSource={logs}
                  rowKey="id"
                  loading={loading}
                  pagination={{ pageSize: 20 }}
                />
              ),
            },
          ]}
        />

        {/* 设置VIP弹窗 */}
        <Modal
          title={t('adminPage.vipModal.title', { username: vipTargetUser?.username || '' })}
          open={vipModalVisible}
          onOk={confirmSetVipWithDays}
          onCancel={() => {
            setVipModalVisible(false);
            setVipTargetUser(null);
            setVipDays(30);
          }}
          okText={t('common.confirm')}
          cancelText={t('common.cancel')}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <div style={{ marginBottom: 8 }}>{t('adminPage.vipModal.daysLabel')}</div>
              <InputNumber
                min={30}
                step={30}
                value={vipDays}
                onChange={(value) => setVipDays(value || 30)}
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ color: '#666', fontSize: 12 }}>
              {t('adminPage.vipModal.daysHint')}
            </div>
          </Space>
        </Modal>

        {/* 添加配额弹窗 */}
        <Modal
          title={t('adminPage.quotaModal.title', { username: selectedUser?.username || '' })}
          open={quotaModalVisible}
          onOk={handleAddQuota}
          onCancel={() => {
            setQuotaModalVisible(false);
            setQuotaAmount(100);
            setQuotaDescription('');
          }}
          okText={t('common.confirm')}
          cancelText={t('common.cancel')}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <div style={{ marginBottom: 8 }}>{t('adminPage.quotaModal.amountLabel')}</div>
              <InputNumber
                min={1}
                max={10000}
                value={quotaAmount}
                onChange={(value) => setQuotaAmount(value || 100)}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <div style={{ marginBottom: 8 }}>{t('adminPage.quotaModal.noteLabel')}</div>
              <Input.TextArea
                placeholder={t('adminPage.quotaModal.notePlaceholder')}
                value={quotaDescription}
                onChange={(e) => setQuotaDescription(e.target.value)}
                rows={3}
              />
            </div>
            <div style={{ color: '#666', fontSize: 12 }}>
              {t('adminPage.quotaModal.currentBalance', { balance: selectedUser?.quota_balance || 0 })}
            </div>
          </Space>
        </Modal>
      </div>
    </div>
  );
};

export default Admin;
