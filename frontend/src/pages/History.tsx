import React, { useState, useEffect } from 'react';
import { Table, Button, Space, message, Popconfirm, Tag, Card, Modal, List, Divider, Alert } from 'antd';
import { EyeOutlined, DeleteOutlined, FileExcelOutlined, FileWordOutlined, FilePptOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { getHistoryFiles, deleteFile, batchDeleteFiles, getFileDetail, exportScores, HistoryFile } from '../services/api';
import { formatFileSize, formatDateTime } from '../utils/format';
import { StudentScore } from '../types/score';
import type { ColumnsType } from 'antd/es/table';
import type { Key } from 'react';

const History: React.FC = () => {
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
                setLoadError('当前有文件正在分析中，请等待分析完成后刷新页面');
                message.warning({
                    content: '当前有文件正在分析中，请稍后刷新页面查看历史记录',
                    duration: 5,
                });
            } else {
                setLoadError('加载历史记录失败');
                message.error(error.response?.data?.detail || '加载历史记录失败，请稍后重试');
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
            message.success('删除成功');
            // 重新加载当前页
            loadFiles(pagination.current, pagination.pageSize);
        } catch (error: any) {
            message.error(error.response?.data?.detail || '删除失败');
        }
    };

    // 批量删除
    const handleBatchDelete = async () => {
        if (selectedRowKeys.length === 0) {
            message.warning('请先选择要删除的文件');
            return;
        }

        Modal.confirm({
            title: '批量删除确认',
            content: `确认要删除选中的 ${selectedRowKeys.length} 个文件吗？删除后无法恢复。`,
            okText: '确认删除',
            cancelText: '取消',
            okButtonProps: { danger: true },
            onOk: async () => {
                try {
                    const fileIds = selectedRowKeys.map(key => Number(key));
                    const result = await batchDeleteFiles(fileIds);
                    message.success(result.message);
                    setSelectedRowKeys([]);
                    loadFiles(pagination.current, pagination.pageSize);
                } catch (error: any) {
                    message.error(error.response?.data?.detail || '批量删除失败');
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
            message.error(error.response?.data?.detail || '加载详情失败');
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
            a.download = `${currentFileDetail.filename.replace(/\.\w+$/, '')}_分析报告.${format === 'excel' ? 'xlsx' : 'docx'}`;
            a.click();
            window.URL.revokeObjectURL(url);
            message.success('导出成功');
        } catch (error: any) {
            message.error(error.response?.data?.detail || '导出失败');
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
            title: '文件名',
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
            title: '文件大小',
            dataIndex: 'file_size',
            key: 'file_size',
            width: 120,
            render: (size: number) => formatFileSize(size),
        },
        {
            title: '学生数量',
            dataIndex: 'student_count',
            key: 'student_count',
            width: 100,
            render: (count: number) => <Tag color="blue">{count} 人</Tag>,
        },
        {
            title: '分析状态',
            dataIndex: 'analysis_completed',
            key: 'analysis_completed',
            width: 100,
            render: (completed: boolean) => (
                <Tag color={completed ? 'success' : 'processing'}>
                    {completed ? '已完成' : '处理中'}
                </Tag>
            ),
        },
        {
            title: '上传时间',
            dataIndex: 'uploaded_at',
            key: 'uploaded_at',
            width: 180,
            render: (time: string) => formatDateTime(time),
        },
        {
            title: '分析时间',
            dataIndex: 'analyzed_at',
            key: 'analyzed_at',
            width: 180,
            render: (time: string | null) => time ? formatDateTime(time) : '-',
        },
        {
            title: '操作',
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
                        查看
                    </Button>
                    <Popconfirm
                        title="确认删除"
                        description="删除后无法恢复，确认要删除这个文件吗？"
                        onConfirm={() => handleDelete(record.id)}
                        okText="确认"
                        cancelText="取消"
                    >
                        <Button
                            type="link"
                            danger
                            icon={<DeleteOutlined />}
                            size="small"
                        >
                            删除
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
                title="历史记录" 
                extra={
                    <Space>
                        {selectedRowKeys.length > 0 && (
                            <Button 
                                danger 
                                icon={<DeleteOutlined />}
                                onClick={handleBatchDelete}
                            >
                                批量删除 ({selectedRowKeys.length})
                            </Button>
                        )}
                        <Button 
                            icon={<ReloadOutlined />}
                            onClick={() => loadFiles(pagination.current, pagination.pageSize)}
                            loading={loading}
                        >
                            刷新
                        </Button>
                    </Space>
                }
                styles={{ body: { padding: '20px' } }}
            >
                {loadError && (
                    <Alert
                        message="加载提示"
                        description={loadError}
                        type="warning"
                        showIcon
                        closable
                        style={{ marginBottom: 16 }}
                        action={
                            <Button size="small" type="primary" onClick={() => loadFiles(pagination.current, pagination.pageSize)}>
                                重新加载
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
                        showTotal: (total) => `共 ${total} 条记录`,
                    }}
                    onChange={handleTableChange}
                    scroll={{ x: 1000 }}
                />
            </Card>

            {/* 详情查看弹窗 */}
            <Modal
                title={`成绩分析结果 - ${currentFileDetail?.filename || ''}`}
                open={detailModalVisible}
                onCancel={() => {
                    setDetailModalVisible(false);
                    setCurrentFileDetail(null);
                }}
                width={1000}
                footer={[
                    <Button key="close" onClick={() => setDetailModalVisible(false)}>
                        关闭
                    </Button>,
                    <Button
                        key="export-excel"
                        type="primary"
                        icon={<DownloadOutlined />}
                        onClick={() => handleExport('excel')}
                        disabled={!currentFileDetail?.students?.length}
                    >
                        导出 Excel
                    </Button>,
                    <Button
                        key="export-word"
                        type="primary"
                        icon={<DownloadOutlined />}
                        onClick={() => handleExport('word')}
                        disabled={!currentFileDetail?.students?.length}
                    >
                        导出 Word
                    </Button>,
                ]}
                styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
            >
                {detailLoading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        加载中...
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
                                <div style={{ color: '#666', marginTop: '4px' }}>学生人数</div>
                            </div>
                            <div style={{ flex: 1, textAlign: 'center' }}>
                                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                                    {(currentFileDetail.students.reduce((sum, s) => sum + s.total_score, 0) / currentFileDetail.students.length).toFixed(1)}
                                </div>
                                <div style={{ color: '#666', marginTop: '4px' }}>平均分</div>
                            </div>
                        </div>

                        <Divider>学生成绩列表</Divider>

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
                                                {student.total_score} 分
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
                                                <strong style={{ color: '#1890ff' }}>📊 AI 分析：</strong>
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
                                                <strong style={{ color: '#52c41a' }}>💡 改进建议：</strong>
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
                        暂无分析数据
                    </div>
                )}
            </Modal>
        </>
    );
};

export default History;
