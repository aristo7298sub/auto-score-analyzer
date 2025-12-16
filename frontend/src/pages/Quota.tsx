import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Col, DatePicker, Divider, Image, Input, Modal, Row, Segmented, Space, Table, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { Dayjs } from 'dayjs';

import { authApi, quotaApi } from '../services/apiClient';
import { useAuthStore } from '../store/authStore';
import '../styles/quota.css';

type QuotaTx = {
  id: number;
  transaction_type: string;
  amount: number;
  balance_after: number;
  description?: string;
  created_at: string;
};

type ConsumptionSummary = {
  start_at: string;
  end_at: string;
  task_count: number;
  total_consumed: number;
};

type ConsumptionResponse = {
  items: QuotaTx[];
  summary: ConsumptionSummary;
};

type ReferralCodeResponse = {
  referral_code: string;
  referral_count: number;
  bonus_referrer: number;
  bonus_new_user: number;
};

type ReferralStatsResponse = {
  referral_code: string;
  total_referrals: number;
  total_bonus_earned: number;
  bonus_referrer: number;
  bonus_new_user: number;
  referred_users: Array<{ username: string; registered_at: string }>;
};

const { Title, Paragraph, Text } = Typography;

const Quota: React.FC = () => {
  const { user, updateUser } = useAuthStore();

  const [loading, setLoading] = useState(false);

  // 我的数据
  const [consumptionItems, setConsumptionItems] = useState<QuotaTx[]>([]);
  const [consumptionSummary, setConsumptionSummary] = useState<ConsumptionSummary | null>(null);
  const [referralCode, setReferralCode] = useState<ReferralCodeResponse | null>(null);
  const [referralStats, setReferralStats] = useState<ReferralStatsResponse | null>(null);

  // 消耗明细：时间范围（默认过去7天）
  const [consumeTimeRange, setConsumeTimeRange] = useState<'1d' | '7d' | '30d' | 'custom'>('7d');
  const [consumeCustomStart, setConsumeCustomStart] = useState<Dayjs | null>(null);
  const [consumeCustomEnd, setConsumeCustomEnd] = useState<Dayjs | null>(null);

  // 弹窗
  const [topupOpen, setTopupOpen] = useState(false);
  const [vipOpen, setVipOpen] = useState(false);

  const referralLink = useMemo(() => {
    if (!referralCode?.referral_code) return '';
    const origin = window.location.origin;
    return `${origin}/register?ref=${encodeURIComponent(referralCode.referral_code)}`;
  }, [referralCode?.referral_code]);

  const vipRemaining = useMemo(() => {
    const isVip = !!user?.is_vip;
    const expiresAt = (user as any)?.vip_expires_at as string | null | undefined;
    if (!isVip) return null;
    if (!expiresAt) return { mode: 'unlimited' as const, days: null as number | null };

    const end = dayjs(expiresAt);
    const diffDays = end.diff(dayjs(), 'day');
    return { mode: 'expires' as const, days: Math.max(0, diffDays) };
  }, [user]);

  const copy = async (text: string, okMsg: string) => {
    try {
      await navigator.clipboard.writeText(text);
      message.success(okMsg);
    } catch {
      message.error('复制失败，请手动复制');
    }
  };

  const loadConsumption = async () => {
    try {
      // Prevent backend 400 when switching to custom before picking dates.
      if (consumeTimeRange === 'custom' && !consumeCustomStart) {
        return;
      }

      setLoading(true);
      const startAt = consumeTimeRange === 'custom' && consumeCustomStart ? consumeCustomStart.toISOString() : undefined;
      const endAt = consumeTimeRange === 'custom' && consumeCustomEnd ? consumeCustomEnd.toISOString() : undefined;
      const res = await quotaApi.getConsumption(50, 0, consumeTimeRange, startAt, endAt);
      const data = res.data as ConsumptionResponse;
      setConsumptionItems(data.items || []);
      setConsumptionSummary(data.summary || null);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载消耗明细失败');
    } finally {
      setLoading(false);
    }
  };

  const loadMyData = async () => {
    setLoading(true);
    try {
      // 刷新当前用户（包含 VIP 到期信息等）
      const me = await authApi.getCurrentUser();
      updateUser(me.data);

      const [codeRes, statsRes, balanceRes] = await Promise.all([
        quotaApi.getReferralCode(),
        quotaApi.getReferralStats(),
        quotaApi.getBalance(),
      ]);

      setReferralCode(codeRes.data);
      setReferralStats(statsRes.data);

      // 同步配额到 store，保证导航栏显示一致
      updateUser({
        quota_balance: balanceRes.data.quota_balance,
        quota_used: balanceRes.data.quota_used,
        is_vip: balanceRes.data.is_vip,
        vip_expires_at: balanceRes.data.vip_expires_at,
      } as any);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载配额信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMyData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadConsumption();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consumeTimeRange, consumeCustomStart, consumeCustomEnd]);

  const consumptionColumns: ColumnsType<QuotaTx> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '消耗额度',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      render: (v) => Math.abs(Number(v || 0)),
    },
    {
      title: '剩余额度',
      dataIndex: 'balance_after',
      key: 'balance_after',
      width: 100,
    },
  ];

  return (
    <div>
      <Title level={2} style={{ marginBottom: 8 }}>额度管理</Title>

      <Alert
        type="info"
        showIcon
        message={<span>开发不易，维护需要成本，请多多支持 🙏</span>}
        description={
          <div>
            <Text strong>只需一杯特价瑞幸的价格，帮你节省2个小时 ☕⏱️</Text>
          </div>
        }
        style={{ marginBottom: 16 }}
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title="我的额度" loading={loading}>
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ marginBottom: 8, color: 'var(--color-text-secondary)' }}>当前余额</div>
                <div><span className="quota-pill quota-pill--lg">{user?.is_vip ? '∞' : String(user?.quota_balance ?? 0)}</span></div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: 8, color: 'var(--color-text-secondary)' }}>累计已用</div>
                <div><span className="quota-pill quota-pill--lg">{String(user?.quota_used ?? 0)}</span></div>
              </Col>
            </Row>

            <Divider />

            <Paragraph style={{ marginBottom: 8 }}>
              <Text strong>计费规则：</Text> 1个学生成绩记录 = 1个额度 = 0.3元
            </Paragraph>

            <Paragraph style={{ marginBottom: 0 }}>
              <Text strong>VIP：</Text>
              {user?.is_vip ? (
                vipRemaining?.mode === 'expires' ? (
                  <span className="quota-pill">已开通（剩余约 {vipRemaining.days} 天）</span>
                ) : (
                  <span className="quota-pill">已开通（无限期）</span>
                )
              ) : (
                <span className="quota-pill">未开通</span>
              )}
            </Paragraph>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="邀请码" loading={loading}>
            <Paragraph>
              你的邀请码是唯一的。对方使用你的邀请码注册：<br />
              <Text strong>你 +{referralCode?.bonus_referrer ?? 30} 额度</Text>，对方 <Text strong>+{referralCode?.bonus_new_user ?? 20} 额度</Text>。
              <br />
              <Text type="secondary">（新用户默认额度为0）</Text>
            </Paragraph>

            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Space.Compact style={{ width: '100%' }}>
                <Input readOnly value={referralCode?.referral_code || ''} placeholder="-" />
                <Button onClick={() => referralCode?.referral_code && copy(referralCode.referral_code, '邀请码已复制')}>一键复制</Button>
              </Space.Compact>

              <Space.Compact style={{ width: '100%' }}>
                <Input readOnly value={referralLink || ''} placeholder="-" />
                <Button onClick={() => referralLink && copy(referralLink, '注册链接已复制')}>复制链接</Button>
              </Space.Compact>

              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                可直接把“注册链接”分享给有需要的人，打开后会自动填入邀请码。
              </Paragraph>
            </Space>

            <Divider />

            <Paragraph style={{ marginBottom: 0 }}>
              已成功邀请：<span className="quota-pill">{referralStats?.total_referrals ?? referralCode?.referral_count ?? 0}</span> 人
              {typeof referralStats?.total_bonus_earned === 'number' && (
                <>
                  ，累计获得：<span className="quota-pill">{referralStats.total_bonus_earned}</span> 额度
                </>
              )}
            </Paragraph>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="充值额度或VIP" loading={loading}>
            <Paragraph>
              <Text strong>额度充值：</Text>0.3元 / 额度（1个学生成绩记录=1额度）
            </Paragraph>
            <Button type="primary" block onClick={() => setTopupOpen(true)}>
              充值额度（扫码购买）
            </Button>

            <Divider plain>OR</Divider>

            <Paragraph>
              <Text strong>VIP（月卡）：</Text>19.9元 / 30天（无限量使用）
            </Paragraph>
            <Button type="primary" block onClick={() => setVipOpen(true)}>
              开通VIP（扫码购买）
            </Button>

            <Divider />

            <Paragraph type="secondary" style={{ marginBottom: 0 }}>
              付款完成后请联系管理员为你的账号充值额度/开通VIP。
            </Paragraph>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title="消耗明细（最近50条）"
            loading={loading}
            extra={
              <Space wrap>
                <Segmented
                  value={consumeTimeRange}
                  options={[
                    { label: '过去1天', value: '1d' },
                    { label: '过去7天', value: '7d' },
                    { label: '过去1个月', value: '30d' },
                    { label: '自定义起止', value: 'custom' },
                  ]}
                  onChange={(v) => {
                    const next = v as any;
                    setConsumeTimeRange(next);
                    if (next !== 'custom') {
                      setConsumeCustomStart(null);
                      setConsumeCustomEnd(null);
                    } else {
                      // Show start/end pickers immediately and avoid empty custom state.
                      setConsumeCustomStart((prev) => prev ?? dayjs().subtract(7, 'day'));
                      setConsumeCustomEnd((prev) => prev ?? dayjs());
                    }
                  }}
                />
                {consumeTimeRange === 'custom' && (
                  <Space size={8}>
                    <DatePicker
                      showTime
                      value={consumeCustomStart}
                      onChange={(v) => setConsumeCustomStart(v)}
                      placeholder="开始时间"
                    />
                    <DatePicker
                      showTime
                      value={consumeCustomEnd}
                      onChange={(v) => setConsumeCustomEnd(v)}
                      placeholder="结束时间"
                    />
                  </Space>
                )}
                <Button onClick={loadConsumption}>刷新</Button>
              </Space>
            }
          >
            <Paragraph type="secondary" style={{ marginBottom: 12 }}>
              汇总：消耗 <span className="quota-pill">{consumptionSummary?.total_consumed ?? 0}</span> 额度，任务 <span className="quota-pill">{consumptionSummary?.task_count ?? 0}</span> 次
            </Paragraph>
            <Table
              rowKey="id"
              columns={consumptionColumns}
              dataSource={consumptionItems}
              pagination={false}
              size="middle"
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title="充值额度（扫码购买）"
        open={topupOpen}
        onCancel={() => setTopupOpen(false)}
        footer={null}
      >
        <Paragraph>
          请使用闲鱼扫描二维码完成购买。购买后通过闲鱼联系管理员为你充值额度。
        </Paragraph>
        <Image
          width="100%"
          src="/payments/quota-topup.jpg"
          fallback="/payments/placeholder.svg"
        />
      </Modal>

      <Modal
        title="开通VIP（月卡，30天，扫码购买）"
        open={vipOpen}
        onCancel={() => setVipOpen(false)}
        footer={null}
      >
        <Paragraph>
          请使用闲鱼扫描二维码完成购买。购买后通过闲鱼联系管理员为你充值VIP。
        </Paragraph>
        <Image
          width="100%"
          src="/payments/vip-month.jpg"
          fallback="/payments/placeholder.svg"
        />
      </Modal>
    </div>
  );
};

export default Quota;
