import React, { useState, useEffect } from 'react';
import { Table, Button, Space, message, Popconfirm, Tag, Card, Modal, List, Divider, Alert } from 'antd';
import { EyeOutlined, DeleteOutlined, FileExcelOutlined, FileWordOutlined, FilePptOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getHistoryFiles, deleteFile, batchDeleteFiles, getFileDetail, exportScores, HistoryFile } from '../services/api';
import { formatFileSize, formatDateTime } from '../utils/format';
import { StudentScore } from '../types/score';
import type { ColumnsType } from 'antd/es/table';
import type { Key } from 'react';

const History: React.FC = () => {
    const { t } = useTranslation();
    const [loading, setLoading] = useState(false);
    const [files, setFiles] = useState<HistoryFile[]>([]);
    const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 10,
        total: 0,
    });
    
    // 详情弹窗状态
    const [detailModalVisible, setDetailModalVisible] = useState(false);
    const [detailLoading, setDetailLoading] = useState(false);
    const [currentFileDetail, setCurrentFileDetail] = useState<{
        filename: string;
        students: StudentScore[];
    } | null>(null);

    // 加载历史文件列表
    const loadFiles = async (page: number = 1, pageSize: number = 10) => {
        setLoading(true);
        setLoadError(null);
        try {
            const response = await getHistoryFiles(page, pageSize);
            setFiles(response.data);
            setPagination({
                current: response.pagination.page,
                pageSize: response.pagination.page_size,
                total: response.pagination.total,
            });
        } catch (error: any) {
            // 检查是否是超时错误
            if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
                setLoadError(t('history.timeoutHint'));
                message.warning({
                    content: t('history.timeoutToast'),
                    duration: 5,
                });
            } else {
                setLoadError(t('history.loadFailed'));
                message.error(error.response?.data?.detail || t('history.loadFailedRetry'));
            }
            // 即使失败也清空 loading 状态
            setFiles([]);
        } finally {
            setLoading(false);
        }
    };

    // 删除单个文件
    const handleDelete = async (fileId: number) => {
        try {
            await deleteFile(fileId);
            message.success(t('history.deleteSuccess'));
            // 重新加载当前页
            loadFiles(pagination.current, pagination.pageSize);
        } catch (error: any) {
            message.error(error.response?.data?.detail || t('history.deleteFailed'));
        }
    };

    // 批量删除
    const handleBatchDelete = async () => {
        if (selectedRowKeys.length === 0) {
            message.warning(t('history.selectToDeleteFirst'));
            return;
        }

        Modal.confirm({
            title: t('history.batchDeleteTitle'),
            content: t('history.batchDeleteConfirm', { count: selectedRowKeys.length }),
            okText: t('history.confirmDelete'),
            cancelText: t('common.cancel'),
            okButtonProps: { danger: true },
            onOk: async () => {
                try {
                    const fileIds = selectedRowKeys.map(key => Number(key));
                    const result = await batchDeleteFiles(fileIds);
                    message.success(result.message || t('history.deleteSuccess'));
                    setSelectedRowKeys([]);
                    loadFiles(pagination.current, pagination.pageSize);
                } catch (error: any) {
                    message.error(error.response?.data?.detail || t('history.batchDeleteFailed'));
                }
            }
        });
    };

    // 查看文件详情
    const handleView = async (fileId: number) => {
        setDetailLoading(true);
        setDetailModalVisible(true);
        try {
            const response = await getFileDetail(fileId);
            setCurrentFileDetail({
                filename: response.data.filename,
                students: response.data.students || []
            });
        } catch (error: any) {
            message.error(error.response?.data?.detail || t('history.loadDetailFailed'));
            setDetailModalVisible(false);
        } finally {
            setDetailLoading(false);
        }
    };

    // 导出详情数据
    const handleExport = async (format: 'excel' | 'word') => {
        if (!currentFileDetail) return;
        
        try {
            // 转换格式参数：excel -> xlsx, word -> docx
            const apiFormat = format === 'excel' ? 'xlsx' : 'docx';
            const blob = await exportScores(apiFormat, currentFileDetail.students, currentFileDetail.filename);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentFileDetail.filename.replace(/\.\w+$/, '')}_${t('analysis.reportSuffix')}.${format === 'excel' ? 'xlsx' : 'docx'}`;
            a.click();
            window.URL.revokeObjectURL(url);
            message.success(t('history.exportSuccess'));
        } catch (error: any) {
            message.error(error.response?.data?.detail || t('history.exportFailed'));
        }
    };

    // 获取文件图标
    const getFileIcon = (fileType: string) => {
        switch (fileType) {
            case 'xlsx':
                return <FileExcelOutlined style={{ color: '#52c41a', fontSize: 20 }} />;
            case 'docx':
                return <FileWordOutlined style={{ color: '#1890ff', fontSize: 20 }} />;
            case 'pptx':
                return <FilePptOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;
            default:
                return null;
        }
    };

    // 表格列定义
    const columns: ColumnsType<HistoryFile> = [
        {
            title: t('history.columns.filename'),
            dataIndex: 'filename',
            key: 'filename',
            render: (filename: string, record: HistoryFile) => (
                <Space>
                    {getFileIcon(record.file_type)}
                    <span>{filename}</span>
                </Space>
            ),
        },
        {
            title: t('history.columns.fileSize'),
            dataIndex: 'file_size',
            key: 'file_size',
            width: 120,
            render: (size: number) => formatFileSize(size),
        },
        {
            title: t('history.columns.studentCount'),
            dataIndex: 'student_count',
            key: 'student_count',
            width: 100,
            render: (count: number) => <Tag color="blue">{t('history.studentCountTag', { count })}</Tag>,
        },
        {
            title: t('history.columns.analysisStatus'),
            dataIndex: 'analysis_completed',
            key: 'analysis_completed',
            width: 100,
            render: (completed: boolean) => (
                <Tag color={completed ? 'success' : 'processing'}>
                    {completed ? t('history.status.complete') : t('history.status.processing')}
                </Tag>
            ),
        },
        {
            title: t('history.columns.uploadedAt'),
            dataIndex: 'uploaded_at',
            key: 'uploaded_at',
            width: 180,
            render: (time: string) => formatDateTime(time),
        },
        {
            title: t('history.columns.analyzedAt'),
            dataIndex: 'analyzed_at',
            key: 'analyzed_at',
            width: 180,
            render: (time: string | null) => time ? formatDateTime(time) : '-',
        },
        {
            title: t('history.columns.actions'),
            key: 'action',
            width: 150,
            fixed: 'right',
            render: (_, record: HistoryFile) => (
                <Space>
                    <Button
                        type="link"
                        icon={<EyeOutlined />}
                        onClick={() => handleView(record.id)}
                        size="small"
                    >
                        {t('history.actions.view')}
                    </Button>
                    <Popconfirm
                        title={t('history.deleteConfirmTitle')}
                        description={t('history.deleteConfirmDesc')}
                        onConfirm={() => handleDelete(record.id)}
                        okText={t('common.confirm')}
                        cancelText={t('common.cancel')}
                    >
                        <Button
                            type="link"
                            danger
                            icon={<DeleteOutlined />}
                            size="small"
                        >
                            {t('history.actions.delete')}
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    // 页面加载时获取数据
    useEffect(() => {
        loadFiles();
    }, []);

    // 处理表格分页变化
    const handleTableChange = (newPagination: any) => {
        loadFiles(newPagination.current, newPagination.pageSize);
    };

    // 表格行选择配置
    const rowSelection = {
        selectedRowKeys,
        onChange: (newSelectedRowKeys: Key[]) => {
            setSelectedRowKeys(newSelectedRowKeys);
        },
    };

    return (
        <>
            <Card 
                title={t('history.title')} 
                extra={
                    <Space>
                        {selectedRowKeys.length > 0 && (
                            <Button 
                                danger 
                                icon={<DeleteOutlined />}
                                onClick={handleBatchDelete}
                            >
                                {t('history.batchDeleteButton', { count: selectedRowKeys.length })}
                            </Button>
                        )}
                        <Button 
                            icon={<ReloadOutlined />}
                            onClick={() => loadFiles(pagination.current, pagination.pageSize)}
                            loading={loading}
                        >
                            {t('common.refresh')}
                        </Button>
                    </Space>
                }
                styles={{ body: { padding: '20px' } }}
            >
                {loadError && (
                    <Alert
                        message={t('history.loadHintTitle')}
                        description={loadError}
                        type="warning"
                        showIcon
                        closable
                        style={{ marginBottom: 16 }}
                        action={
                            <Button size="small" type="primary" onClick={() => loadFiles(pagination.current, pagination.pageSize)}>
                                {t('common.retry')}
                            </Button>
                        }
                    />
                )}
                <Table
                    rowSelection={rowSelection}
                    columns={columns}
                    dataSource={files}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        ...pagination,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total) => t('history.totalRecords', { total }),
                    }}
                    onChange={handleTableChange}
                    scroll={{ x: 1000 }}
                />
            </Card>

            {/* 详情查看弹窗 */}
            <Modal
                title={t('history.detailTitle', { filename: currentFileDetail?.filename || '' })}
                open={detailModalVisible}
                onCancel={() => {
                    setDetailModalVisible(false);
                    setCurrentFileDetail(null);
                }}
                width={1000}
                footer={[
                    <Button key="close" onClick={() => setDetailModalVisible(false)}>{t('common.close')}</Button>,
                    <Button
                        key="export-excel"
                        type="primary"
                        icon={<DownloadOutlined />}
                        onClick={() => handleExport('excel')}
                        disabled={!currentFileDetail?.students?.length}
                    >
                        {t('history.exportExcel')}
                    </Button>,
                    <Button
                        key="export-word"
                        type="primary"
                        icon={<DownloadOutlined />}
                        onClick={() => handleExport('word')}
                        disabled={!currentFileDetail?.students?.length}
                    >
                        {t('history.exportWord')}
                    </Button>,
                ]}
                styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
            >
                {detailLoading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        {t('common.loading')}
                    </div>
                ) : currentFileDetail?.students?.length ? (
                    <>
                        {/* 统计信息 */}
                        <div style={{ 
                            display: 'flex', 
                            gap: '20px', 
                            marginBottom: '20px',
                            padding: '16px',
                            background: '#f5f5f5',
                            borderRadius: '8px'
                        }}>
                            <div style={{ flex: 1, textAlign: 'center' }}>
                                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                                    {currentFileDetail.students.length}
                                </div>
                                <div style={{ color: '#666', marginTop: '4px' }}>{t('history.detail.studentCount')}</div>
                            </div>
                            <div style={{ flex: 1, textAlign: 'center' }}>
                                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                                    {(currentFileDetail.students.reduce((sum, s) => sum + s.total_score, 0) / currentFileDetail.students.length).toFixed(1)}
                                </div>
                                <div style={{ color: '#666', marginTop: '4px' }}>{t('history.detail.avgScore')}</div>
                            </div>
                        </div>

                        <Divider>{t('history.detail.listTitle')}</Divider>

                        {/* 学生列表 */}
                        <List
                            dataSource={currentFileDetail.students}
                            renderItem={(student) => (
                                <List.Item
                                    style={{
                                        background: '#fff',
                                        marginBottom: '12px',
                                        padding: '16px',
                                        borderRadius: '8px',
                                        border: '1px solid #f0f0f0'
                                    }}
                                >
                                    <div style={{ width: '100%' }}>
                                        {/* 学生名称和分数 */}
                                        <div style={{ 
                                            display: 'flex', 
                                            justifyContent: 'space-between', 
                                            alignItems: 'center',
                                            marginBottom: '12px'
                                        }}>
                                            <h3 style={{ margin: 0, fontSize: '18px' }}>
                                                {student.student_name}
                                            </h3>
                                            <Tag color="blue" style={{ fontSize: '16px', padding: '4px 12px' }}>
                                                {t('history.detail.scoreTag', { score: student.total_score })}
                                            </Tag>
                                        </div>

                                        {/* AI 分析 */}
                                        {student.analysis && (
                                            <div style={{ 
                                                background: '#f0f5ff', 
                                                padding: '12px',
                                                borderRadius: '6px',
                                                marginBottom: '8px',
                                                borderLeft: '3px solid #1890ff'
                                            }}>
                                                <strong style={{ color: '#1890ff' }}>{t('history.detail.aiAnalysisLabel')}</strong>
                                                <p style={{ margin: '8px 0 0 0', lineHeight: '1.6' }}>
                                                    {student.analysis}
                                                </p>
                                            </div>
                                        )}

                                        {/* 改进建议 */}
                                        {student.suggestions && student.suggestions.length > 0 && (
                                            <div style={{ 
                                                background: '#f6ffed', 
                                                padding: '12px',
                                                borderRadius: '6px',
                                                borderLeft: '3px solid #52c41a'
                                            }}>
                                                <strong style={{ color: '#52c41a' }}>{t('history.detail.suggestionsLabel')}</strong>
                                                <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
                                                    {student.suggestions.map((suggestion, idx) => (
                                                        <li key={idx} style={{ lineHeight: '1.6' }}>{suggestion}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                </List.Item>
                            )}
                        />
                    </>
                ) : (
                    <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                        {t('history.detail.noData')}
                    </div>
                )}
            </Modal>
        </>
    );
};

export default History;
