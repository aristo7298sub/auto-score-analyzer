import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, Card, Col, DatePicker, Divider, Image, Input, Modal, Row, Segmented, Space, Table, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { Dayjs } from 'dayjs';
import { useTranslation } from 'react-i18next';

import { authApi, quotaApi } from '../services/apiClient';
import { useAuthStore } from '../store/authStore';
import { useAppStore } from '../store/appStore';
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
  const { t } = useTranslation();
  const { user, updateUser } = useAuthStore();
  const { language } = useAppStore();

  const [pageLoading, setPageLoading] = useState(false);
  const [consumptionLoading, setConsumptionLoading] = useState(false);

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

  // Preserve window scroll position when switching consumption ranges.
  const consumptionScrollYRef = useRef<number | null>(null);

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
      message.error(t('quotaPage.copyFailed'));
    }
  };

  const loadConsumption = async () => {
    try {
      // Prevent backend 400 when switching to custom before picking dates.
      if (consumeTimeRange === 'custom' && !consumeCustomStart) {
        return;
      }

      setConsumptionLoading(true);
      const startAt = consumeTimeRange === 'custom' && consumeCustomStart ? consumeCustomStart.toISOString() : undefined;
      const endAt = consumeTimeRange === 'custom' && consumeCustomEnd ? consumeCustomEnd.toISOString() : undefined;
      const res = await quotaApi.getConsumption(50, 0, consumeTimeRange, startAt, endAt);
      const data = res.data as ConsumptionResponse;
      setConsumptionItems(data.items || []);
      setConsumptionSummary(data.summary || null);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || t('quotaPage.loadConsumptionFailed'));
    } finally {
      setConsumptionLoading(false);

      // If AntD/DOM updates caused a jump, restore previous scroll.
      if (consumptionScrollYRef.current !== null) {
        const y = consumptionScrollYRef.current;
        consumptionScrollYRef.current = null;
        requestAnimationFrame(() => {
          window.scrollTo({ top: y, behavior: 'auto' });
        });
      }
    }
  };

  const loadMyData = async () => {
    setPageLoading(true);
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
      message.error(e?.response?.data?.detail || t('quotaPage.loadQuotaFailed'));
    } finally {
      setPageLoading(false);
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
      title: t('quotaPage.consumption.columns.time'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v) => new Date(v).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US'),
    },
    {
      title: t('quotaPage.consumption.columns.consumed'),
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      render: (v) => Math.abs(Number(v || 0)),
    },
    {
      title: t('quotaPage.consumption.columns.balanceAfter'),
      dataIndex: 'balance_after',
      key: 'balance_after',
      width: 100,
    },
  ];

  return (
    <div>
      <Title level={2} style={{ marginBottom: 8 }}>{t('quotaPage.title')}</Title>

      <Alert
        type="info"
        showIcon
        message={<span>{t('quotaPage.supportMessage')}</span>}
        description={
          <div>
            <Text strong>{t('quotaPage.supportDescription')}</Text>
          </div>
        }
        style={{ marginBottom: 16 }}
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title={t('quotaPage.cards.myQuota')} loading={pageLoading}>
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ marginBottom: 8, color: 'var(--color-text-secondary)' }}>{t('quotaPage.currentBalance')}</div>
                <div><span className="quota-pill quota-pill--lg">{user?.is_vip ? '∞' : String(user?.quota_balance ?? 0)}</span></div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: 8, color: 'var(--color-text-secondary)' }}>{t('quotaPage.totalUsed')}</div>
                <div><span className="quota-pill quota-pill--lg">{String(user?.quota_used ?? 0)}</span></div>
              </Col>
            </Row>

            <Divider />

            <Paragraph style={{ marginBottom: 8 }}>
              <Text strong>{t('quotaPage.pricingRuleLabel')}</Text> {t('quotaPage.pricingRuleValue')}
            </Paragraph>

            <Paragraph style={{ marginBottom: 0 }}>
              <Text strong>{t('quotaPage.vipLabel')}</Text>
              {user?.is_vip ? (
                vipRemaining?.mode === 'expires' ? (
                  <span className="quota-pill">{t('quotaPage.vipActiveRemainingDays', { days: vipRemaining.days })}</span>
                ) : (
                  <span className="quota-pill">{t('quotaPage.vipActiveUnlimited')}</span>
                )
              ) : (
                <span className="quota-pill">{t('quotaPage.vipInactive')}</span>
              )}
            </Paragraph>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title={t('quotaPage.cards.inviteCode')} loading={pageLoading}>
            <Paragraph>
              {t('quotaPage.inviteIntro')}<br />
              <Text strong>{t('quotaPage.inviteYouBonus', { amount: referralCode?.bonus_referrer ?? 30 })}</Text>，{t('quotaPage.inviteNewUserBonusPrefix')} <Text strong>{t('quotaPage.inviteNewUserBonus', { amount: referralCode?.bonus_new_user ?? 20 })}</Text>。
              <br />
              <Text type="secondary">{t('quotaPage.newUserDefaultZero')}</Text>
            </Paragraph>

            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Space.Compact style={{ width: '100%' }}>
                <Input readOnly value={referralCode?.referral_code || ''} placeholder="-" />
                <Button onClick={() => referralCode?.referral_code && copy(referralCode.referral_code, t('quotaPage.inviteCodeCopied'))}>{t('quotaPage.copyInviteCode')}</Button>
              </Space.Compact>

              <Space.Compact style={{ width: '100%' }}>
                <Input readOnly value={referralLink || ''} placeholder="-" />
                <Button onClick={() => referralLink && copy(referralLink, t('quotaPage.inviteLinkCopied'))}>{t('quotaPage.copyInviteLink')}</Button>
              </Space.Compact>

              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                {t('quotaPage.shareLinkHint')}
              </Paragraph>
            </Space>

            <Divider />

            <Paragraph style={{ marginBottom: 0 }}>
              {t('quotaPage.invitedCountLabel')} <span className="quota-pill">{referralStats?.total_referrals ?? referralCode?.referral_count ?? 0}</span> {t('quotaPage.peopleUnit')}
              {typeof referralStats?.total_bonus_earned === 'number' && (
                <>
                  ，{t('quotaPage.totalBonusLabel')} <span className="quota-pill">{referralStats.total_bonus_earned}</span> {t('quotaPage.quotaUnit')}
                </>
              )}
            </Paragraph>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title={t('quotaPage.cards.topupOrVip')} loading={pageLoading}>
            <Paragraph>
              <Text strong>{t('quotaPage.topupQuotaLabel')}</Text>{t('quotaPage.topupQuotaValue')}
            </Paragraph>
            <Button type="primary" block onClick={() => setTopupOpen(true)}>
              {t('quotaPage.topupQuotaButton')}
            </Button>

            <Divider plain>OR</Divider>

            <Paragraph>
              <Text strong>{t('quotaPage.vipMonthlyLabel')}</Text>{t('quotaPage.vipMonthlyValue')}
            </Paragraph>
            <Button type="primary" block onClick={() => setVipOpen(true)}>
              {t('quotaPage.vipMonthlyButton')}
            </Button>

            <Divider />

            <Paragraph type="secondary" style={{ marginBottom: 0 }}>
              {t('quotaPage.contactAdminAfterPay')}
            </Paragraph>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title={t('quotaPage.consumption.title')}
            extra={
              <Space wrap>
                <Segmented
                  value={consumeTimeRange}
                  options={[
                    { label: t('quotaPage.timeRanges.1d'), value: '1d' },
                    { label: t('quotaPage.timeRanges.7d'), value: '7d' },
                    { label: t('quotaPage.timeRanges.30d'), value: '30d' },
                    { label: t('quotaPage.timeRanges.custom'), value: 'custom' },
                  ]}
                  onChange={(v) => {
                    consumptionScrollYRef.current = window.scrollY;
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
                      placeholder={t('common.startTime')}
                    />
                    <DatePicker
                      showTime
                      value={consumeCustomEnd}
                      onChange={(v) => setConsumeCustomEnd(v)}
                      placeholder={t('common.endTime')}
                    />
                  </Space>
                )}
                <Button
                  onClick={() => {
                    consumptionScrollYRef.current = window.scrollY;
                    loadConsumption();
                  }}
                >
                  {t('common.refresh')}
                </Button>
              </Space>
            }
          >
            <Paragraph type="secondary" style={{ marginBottom: 12 }}>
              {t('quotaPage.consumption.summary', {
                count: consumptionSummary?.task_count ?? consumptionItems.length,
                total: consumptionSummary?.total_consumed ?? 0,
              })}
            </Paragraph>
            <Table
              rowKey="id"
              columns={consumptionColumns}
              dataSource={consumptionItems}
              pagination={false}
              size="middle"
              scroll={{ y: 10 * 44 }}
              loading={consumptionLoading}
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title={t('quotaPage.modals.topupTitle')}
        open={topupOpen}
        onCancel={() => setTopupOpen(false)}
        footer={null}
      >
        <Paragraph>
          {t('quotaPage.modals.topupDesc')}
        </Paragraph>
        <Image
          width="100%"
          src="/payments/quota-topup.jpg"
          fallback="/payments/placeholder.svg"
        />
      </Modal>

      <Modal
        title={t('quotaPage.modals.vipTitle')}
        open={vipOpen}
        onCancel={() => setVipOpen(false)}
        footer={null}
      >
        <Paragraph>
          {t('quotaPage.modals.vipDesc')}
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
