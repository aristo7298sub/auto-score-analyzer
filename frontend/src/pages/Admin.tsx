import React, { useState, useEffect } from 'react';
import { Card, Tabs, Table, Button, Input, Tag, Space, Statistic, Row, Col, message, Modal, InputNumber, Badge } from 'antd';
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
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useAppStore } from '../store/appStore';
import { adminApi } from '../services/apiClient';
import type { ColumnsType } from 'antd/es/table';
import '../styles/admin.css';

interface AdminUser {
  id: number;
  username: string;
  email: string;
  is_vip: boolean;
  is_admin: boolean;
  is_active: boolean;
  quota_balance: number;
  quota_used: number;
  referral_count: number;
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
  
  // 配额弹窗
  const [quotaModalVisible, setQuotaModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [quotaAmount, setQuotaAmount] = useState(100);
  const [quotaDescription, setQuotaDescription] = useState('');

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
      message.error(error.response?.data?.detail || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    const response = await adminApi.getStats();
    setStats(response.data);
  };

  const loadUsers = async () => {
    const response = await adminApi.getUsers(100, 0, searchText || undefined);
    setUsers(response.data);
  };

  const loadLogs = async () => {
    const response = await adminApi.getLogs(100, 0);
    setLogs(response.data);
  };

  const handleSetVip = async (userId: number, isVip: boolean) => {
    try {
      await adminApi.setVip(userId, isVip);
      message.success(`VIP状态已${isVip ? '开通' : '取消'}`);
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  const handleToggleActive = async (userId: number) => {
    try {
      await adminApi.toggleActive(userId);
      message.success('用户状态已更新');
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  const handleAddQuota = async () => {
    if (!selectedUser) return;
    
    try {
      await adminApi.addQuota(selectedUser.id, quotaAmount, quotaDescription || undefined);
      message.success(`已为 ${selectedUser.username} 添加 ${quotaAmount} 配额`);
      setQuotaModalVisible(false);
      setQuotaAmount(100);
      setQuotaDescription('');
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '添加配额失败');
    }
  };

  const handleLogout = () => {
    logout();
    message.success('已退出登录');
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
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (text, record) => (
        <Space>
          {text}
          {record.is_admin && <Tag color="red">管理员</Tag>}
        </Space>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'VIP',
      dataIndex: 'is_vip',
      key: 'is_vip',
      render: (isVip) => (
        isVip ? <Tag color="gold"><CrownOutlined /> VIP</Tag> : <Tag>普通</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive) => (
        <Badge status={isActive ? 'success' : 'error'} text={isActive ? '正常' : '禁用'} />
      ),
    },
    {
      title: '配额余额',
      dataIndex: 'quota_balance',
      key: 'quota_balance',
      render: (balance) => <Tag color="blue">{balance}</Tag>,
    },
    {
      title: '已用配额',
      dataIndex: 'quota_used',
      key: 'quota_used',
    },
    {
      title: '推荐人数',
      dataIndex: 'referral_count',
      key: 'referral_count',
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            type={record.is_vip ? 'default' : 'primary'}
            onClick={() => handleSetVip(record.id, !record.is_vip)}
          >
            {record.is_vip ? '取消VIP' : '设为VIP'}
          </Button>
          <Button
            size="small"
            danger={record.is_active}
            onClick={() => handleToggleActive(record.id)}
          >
            {record.is_active ? '禁用' : '启用'}
          </Button>
          <Button
            size="small"
            icon={<PlusOutlined />}
            onClick={() => {
              setSelectedUser(record);
              setQuotaModalVisible(true);
            }}
          >
            加配额
          </Button>
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
      title: '用户',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: '学生数',
      dataIndex: 'student_count',
      key: 'student_count',
    },
    {
      title: '配额消耗',
      dataIndex: 'quota_cost',
      key: 'quota_cost',
      render: (cost) => <Tag color="orange">{cost}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
          success: { color: 'success', icon: <CheckCircleOutlined />, text: '成功' },
          failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
          processing: { color: 'processing', icon: <FileTextOutlined />, text: '处理中' },
        };
        const config = statusConfig[status] || statusConfig.processing;
        return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>;
      },
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '错误信息',
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
          <span className="admin-title">{language === 'zh' ? 'AI成绩分析平台 - 管理后台' : 'AI Score Analyzer - Admin'}</span>
        </div>
        <div className="admin-navbar-right">
          <Button
            type="text"
            icon={<HomeOutlined />}
            onClick={() => navigate('/')}
          >
            返回首页
          </Button>
          <button className="toolbar-btn" onClick={handleLanguageToggle} title="Language">
            {language === 'zh' ? '中' : 'EN'}
          </button>
          <button className="toolbar-btn" onClick={toggleTheme} title="Theme">
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <div className="admin-user-info">
            <span>{user?.username}</span>
            <Tag color="red">管理员</Tag>
          </div>
          <Button
            type="text"
            danger
            icon={<LogoutOutlined />}
            onClick={handleLogout}
          >
            退出
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
                  数据概览
                </span>
              ),
              children: stats && (
                <div>
                  <Row gutter={[16, 16]} className="stats-row">
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title="总用户数"
                          value={stats.total_users}
                          prefix={<TeamOutlined />}
                          valueStyle={{ color: '#3f8600' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title="活跃用户"
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
                          title="VIP用户"
                          value={stats.vip_users}
                          prefix={<CrownOutlined />}
                          valueStyle={{ color: '#cf1322' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title="总分析次数"
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
                          title="成功分析"
                          value={stats.success_analyses}
                          suffix={`/ ${stats.total_analyses}`}
                          valueStyle={{ color: '#52c41a' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={8}>
                      <Card>
                        <Statistic
                          title="失败分析"
                          value={stats.failed_analyses}
                          suffix={`/ ${stats.total_analyses}`}
                          valueStyle={{ color: '#ff4d4f' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={8}>
                      <Card>
                        <Statistic
                          title="总配额消耗"
                          value={stats.total_quota_used}
                          valueStyle={{ color: '#fa8c16' }}
                        />
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
                  用户管理
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Space>
                      <Input
                        placeholder="搜索用户名或邮箱"
                        prefix={<SearchOutlined />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        onPressEnter={loadUsers}
                        style={{ width: 300 }}
                      />
                      <Button type="primary" onClick={loadUsers}>
                        搜索
                      </Button>
                    </Space>
                  </div>
                  <Table
                    columns={userColumns}
                    dataSource={users}
                    rowKey="id"
                    loading={loading}
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
                  分析日志
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

        {/* 添加配额弹窗 */}
        <Modal
          title={`为 ${selectedUser?.username} 添加配额`}
          open={quotaModalVisible}
          onOk={handleAddQuota}
          onCancel={() => {
            setQuotaModalVisible(false);
            setQuotaAmount(100);
            setQuotaDescription('');
          }}
          okText="确认"
          cancelText="取消"
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <div style={{ marginBottom: 8 }}>配额数量</div>
              <InputNumber
                min={1}
                max={10000}
                value={quotaAmount}
                onChange={(value) => setQuotaAmount(value || 100)}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <div style={{ marginBottom: 8 }}>备注（可选）</div>
              <Input.TextArea
                placeholder="添加配额的原因或备注"
                value={quotaDescription}
                onChange={(e) => setQuotaDescription(e.target.value)}
                rows={3}
              />
            </div>
            <div style={{ color: '#666', fontSize: 12 }}>
              当前配额余额: {selectedUser?.quota_balance || 0}
            </div>
          </Space>
        </Modal>
      </div>
    </div>
  );
};

export default Admin;
