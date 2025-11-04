import React, { useState } from 'react';
import { Upload, Card, Input, Button, List, message, Typography, Space, Divider, Tag, Tabs } from 'antd';
import { UploadOutlined, SearchOutlined, DownloadOutlined, FileTextOutlined, CheckCircleOutlined, SyncOutlined } from '@ant-design/icons';
import { StudentScore } from '../types/score';
import { uploadFile, getStudentScore, exportScores } from '../services/api';

const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography;

const Home: React.FC = () => {
    // 按文件分组存储数据
    const [fileGroups, setFileGroups] = useState<Array<{
        filename: string;
        scores: StudentScore[];
        uploadTime: string;
        status: 'uploading' | 'analyzing' | 'complete' | 'error';
        statusMessage?: string;
    }>>([]);
    const [activeFileKey, setActiveFileKey] = useState<string>('');
    const [searchText, setSearchText] = useState('');
    const [loading, setLoading] = useState(false);

    const handleUpload = async (file: File) => {
        const tempFilename = file.name;
        
        /* 
         * TODO: 未来优化 - 实现真实后端状态同步
         * 
         * 方案：使用 Server-Sent Events (SSE)
         * 1. 后端创建流式endpoint: GET /api/upload/stream/{task_id}
         * 2. 前端使用 EventSource 监听：
         *    const eventSource = new EventSource(`/api/upload/stream/${taskId}`);
         *    eventSource.onmessage = (event) => {
         *      const status = JSON.parse(event.data);
         *      updateFileGroupStatus(status);
         *    };
         * 3. 后端在每个处理阶段发送事件：
         *    yield f"data: {json.dumps({stage: 'parsing', progress: 30})}\n\n"
         * 
         * 当前方案：前端模拟状态，优点是简单可靠，缺点是不能反映真实进度
         */
        
        try {
            // 1. 显示上传中状态
            setFileGroups(prev => [...prev, {
                filename: tempFilename,
                scores: [],
                uploadTime: new Date().toLocaleString('zh-CN'),
                status: 'uploading',
                statusMessage: '📤 正在上传文件到服务器...'
            }]);
            
            // 2. 模拟上传完成
            setTimeout(() => {
                setFileGroups(prev => prev.map(group => 
                    group.filename === tempFilename 
                        ? { ...group, statusMessage: '📦 文件上传成功，正在解析数据...' }
                        : group
                ));
            }, 300);
            
            // 3. 开始调用后端API（异步）
            const uploadPromise = uploadFile(file);
            
            // 4. 模拟解析阶段
            setTimeout(() => {
                setFileGroups(prev => prev.map(group => 
                    group.filename === tempFilename 
                        ? { 
                            ...group, 
                            status: 'analyzing' as const,
                            statusMessage: '📊 数据解析完成，正在准备分析...' 
                        }
                        : group
                ));
            }, 800);
            
            // 5. 模拟分析开始
            setTimeout(() => {
                setFileGroups(prev => prev.map(group => 
                    group.filename === tempFilename 
                        ? { ...group, statusMessage: '🧠 AI 正在智能分析学生成绩...' }
                        : group
                ));
            }, 1200);
            
            // 6. 模拟分析进行中
            setTimeout(() => {
                setFileGroups(prev => prev.map(group => 
                    group.filename === tempFilename 
                        ? { ...group, statusMessage: '⚡ 正在为每位学生生成个性化建议...' }
                        : group
                ));
            }, 2000);
            
            // 7. 等待实际API响应
            const response = await uploadPromise;
            
            if (response.success && response.data) {
                const finalFilename = response.original_filename || file.name;
                const studentCount = response.data.length;
                
                // 8. 显示完成状态
                setFileGroups(prev => prev.map(group => 
                    group.filename === tempFilename 
                        ? {
                            ...group,
                            filename: finalFilename,
                            scores: response.data!,
                            status: 'complete' as const,
                            statusMessage: `🎉 分析完成！已为 ${studentCount} 名学生生成详细报告`
                        }
                        : group
                ));
                
                // 设置为活动标签页
                setActiveFileKey(finalFilename);
                message.success(`文件 ${file.name} 处理成功！`);
                
            } else {
                // 更新为错误状态
                setFileGroups(prev => prev.map(group => 
                    group.filename === tempFilename 
                        ? { 
                            ...group, 
                            status: 'error' as const, 
                            statusMessage: `❌ ${response.message || '处理失败，请重试'}` 
                        }
                        : group
                ));
                message.error(response.message || '上传失败');
            }
        } catch (error) {
            // 发生异常
            setFileGroups(prev => prev.map(group => 
                group.filename === tempFilename 
                    ? { 
                        ...group, 
                        status: 'error' as const, 
                        statusMessage: '❌ 网络错误或服务器异常，请检查连接后重试' 
                    }
                    : group
            ));
            message.error('上传文件失败，请检查网络连接后重试');
        }
    };

    const handleSearch = async () => {
        if (!searchText) {
            message.warning('请输入学生姓名');
            return;
        }
        try {
            setLoading(true);
            const response = await getStudentScore(searchText);
            if (response.success && response.data) {
                // 搜索结果也作为一个临时文件组
                setFileGroups([{
                    filename: `搜索结果: ${searchText}`,
                    scores: response.data,
                    uploadTime: new Date().toLocaleString('zh-CN'),
                    status: 'complete'
                }]);
                setActiveFileKey(`搜索结果: ${searchText}`);
            } else {
                message.error(response.message || '查询失败');
            }
        } catch (error) {
            message.error('查询失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async (format: string, fileGroup: { filename: string; scores: StudentScore[] }) => {
        try {
            setLoading(true);
            const blob = await exportScores(format, fileGroup.scores, fileGroup.filename);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // 生成文件名
            const baseName = fileGroup.filename.replace(/\.[^/.]+$/, '');
            a.download = `${baseName}-成绩分析.${format}`;
            
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            message.success('导出成功');
        } catch (error) {
            message.error('导出失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ 
            padding: '32px', 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            minHeight: '100vh'
        }}>
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                {/* Header */}
                <div style={{ 
                    textAlign: 'center', 
                    marginBottom: '40px',
                    color: 'white'
                }}>
                    <Title level={1} style={{ color: 'white', marginBottom: '8px' }}>
                        🎓 学生成绩分析系统
                    </Title>
                </div>

                {/* Upload Section */}
                <Card 
                    style={{ 
                        marginBottom: '24px',
                        borderRadius: '12px',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.12)'
                    }}
                >
                    <Dragger
                        accept=".xlsx,.docx,.pptx"
                        multiple={true}  // 支持多文件
                        beforeUpload={(file) => {
                            handleUpload(file);
                            return false;  // 阻止自动上传
                        }}
                        showUploadList={false}
                        style={{
                            background: '#fafafa',
                            borderRadius: '8px'
                        }}
                    >
                        <p className="ant-upload-drag-icon">
                            <UploadOutlined style={{ color: '#667eea', fontSize: '48px' }} />
                        </p>
                        <p className="ant-upload-text" style={{ fontSize: '18px', fontWeight: 500 }}>
                            点击或拖拽文件到此区域上传
                        </p>
                        <p className="ant-upload-hint" style={{ color: '#999' }}>
                            支持 .xlsx, .docx, .pptx 格式的文件，支持多文件上传
                        </p>
                    </Dragger>

                    {/* 文件处理状态列表 */}
                    {fileGroups.length > 0 && (
                        <div style={{ marginTop: '20px' }}>
                            <Space direction="vertical" style={{ width: '100%' }} size="middle">
                                {fileGroups.map((group, index) => {
                                    // 判断是否处理中
                                    const isProcessing = group.status === 'uploading' || group.status === 'analyzing';
                                    const isComplete = group.status === 'complete';
                                    const isError = group.status === 'error';
                                    
                                    // 根据状态选择emoji
                                    let statusEmoji = '';
                                    if (isProcessing && group.status === 'uploading') statusEmoji = '📤';
                                    else if (isProcessing && group.status === 'analyzing') statusEmoji = '🧠';
                                    else if (isComplete) statusEmoji = '✅';
                                    else if (isError) statusEmoji = '❌';
                                    
                                    return (
                                        <div 
                                            key={index}
                                            style={{
                                                padding: '18px 24px',
                                                background: isComplete 
                                                    ? 'linear-gradient(135deg, rgba(82, 196, 26, 0.05) 0%, rgba(82, 196, 26, 0.1) 100%)'
                                                    : isError 
                                                    ? 'linear-gradient(135deg, rgba(255, 77, 79, 0.05) 0%, rgba(255, 77, 79, 0.1) 100%)'
                                                    : 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.15) 100%)',
                                                borderRadius: '16px',
                                                border: `2px solid ${
                                                    isComplete ? 'rgba(82, 196, 26, 0.3)' : 
                                                    isError ? 'rgba(255, 77, 79, 0.3)' :
                                                    'rgba(102, 126, 234, 0.4)'
                                                }`,
                                                boxShadow: isProcessing 
                                                    ? '0 8px 24px rgba(102, 126, 234, 0.25), 0 0 0 1px rgba(102, 126, 234, 0.1) inset' 
                                                    : isComplete
                                                    ? '0 4px 16px rgba(82, 196, 26, 0.15)'
                                                    : '0 4px 16px rgba(0, 0, 0, 0.08)',
                                                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                                                transform: isProcessing ? 'translateY(-2px)' : 'translateY(0)',
                                                backdropFilter: 'blur(10px)'
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px' }}>
                                                {/* 状态图标 */}
                                                <div style={{ fontSize: '32px', marginTop: '4px', minWidth: '40px', textAlign: 'center' }}>
                                                    {isProcessing ? (
                                                        <div style={{ position: 'relative' }}>
                                                            <SyncOutlined 
                                                                spin 
                                                                style={{ 
                                                                    color: '#667eea',
                                                                    fontSize: '32px',
                                                                    filter: 'drop-shadow(0 2px 8px rgba(102, 126, 234, 0.3))'
                                                                }} 
                                                            />
                                                        </div>
                                                    ) : (
                                                        <span style={{ 
                                                            fontSize: '32px',
                                                            filter: `drop-shadow(0 2px 4px ${
                                                                isComplete ? 'rgba(82, 196, 26, 0.3)' : 'rgba(255, 77, 79, 0.3)'
                                                            })`
                                                        }}>
                                                            {statusEmoji}
                                                        </span>
                                                    )}
                                                </div>
                                                
                                                {/* 文件信息 */}
                                                <div style={{ flex: 1 }}>
                                                    <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                        <Text strong style={{ 
                                                            fontSize: '17px', 
                                                            color: isProcessing ? '#667eea' : '#262626',
                                                            fontWeight: 600
                                                        }}>
                                                            {group.filename}
                                                        </Text>
                                                        {isComplete && (
                                                            <Tag 
                                                                color="success" 
                                                                style={{ 
                                                                    fontSize: '13px', 
                                                                    padding: '4px 12px',
                                                                    borderRadius: '8px',
                                                                    fontWeight: 500,
                                                                    background: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)',
                                                                    border: 'none',
                                                                    color: 'white'
                                                                }}
                                                            >
                                                                📊 {group.scores.length} 名学生
                                                            </Tag>
                                                        )}
                                                    </div>
                                                    <div>
                                                        <Text 
                                                            style={{ 
                                                                fontSize: '15px',
                                                                color: isProcessing ? '#667eea' : isComplete ? '#52c41a' : '#ff4d4f',
                                                                fontWeight: isProcessing ? 500 : 400,
                                                                lineHeight: '1.6'
                                                            }}
                                                        >
                                                            {group.statusMessage}
                                                        </Text>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </Space>
                        </div>
                    )}
                </Card>

                {/* Search Section */}
                <Card 
                    title={<Text strong style={{ fontSize: '16px' }}>🔍 成绩查询</Text>}
                    style={{ 
                        marginBottom: '24px',
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
                    }}
                >
                    <Input.Search
                        placeholder="请输入学生姓名"
                        enterButton={<SearchOutlined />}
                        size="large"
                        onSearch={handleSearch}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        loading={loading}
                        style={{ borderRadius: '8px' }}
                    />
                </Card>

                {/* Results Section with Tabs */}
                <Card 
                    title={
                        <Text strong style={{ fontSize: '16px' }}>
                            📊 成绩分析结果
                        </Text>
                    }
                    style={{ 
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
                    }}
                >
                    {fileGroups.filter(g => g.status === 'complete').length === 0 ? (
                        <div style={{ 
                            textAlign: 'center', 
                            padding: '60px 20px',
                            color: '#999'
                        }}>
                            <FileTextOutlined style={{ fontSize: '64px', marginBottom: '16px', color: '#d9d9d9' }} />
                            <Paragraph style={{ fontSize: '16px', color: '#999' }}>
                                暂无数据，请上传文件或搜索学生
                            </Paragraph>
                        </div>
                    ) : (
                        <Tabs
                            activeKey={activeFileKey}
                            onChange={setActiveFileKey}
                            type="card"
                            items={fileGroups.filter(g => g.status === 'complete').map((group) => ({
                                key: group.filename,
                                label: (
                                    <Space>
                                        <FileTextOutlined />
                                        <span>{group.filename}</span>
                                        <Tag color="blue">{group.scores.length}</Tag>
                                    </Space>
                                ),
                                children: (
                                    <div>
                                        {/* 每个 Tab 的导出按钮 */}
                                        <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                                            <Space>
                                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                                    上传时间: {group.uploadTime}
                                                </Text>
                                                <Button.Group>
                                                    <Button 
                                                        icon={<DownloadOutlined />} 
                                                        onClick={() => handleExport('xlsx', group)}
                                                        loading={loading}
                                                        type="primary"
                                                    >
                                                        导出Excel
                                                    </Button>
                                                    <Button 
                                                        icon={<FileTextOutlined />} 
                                                        onClick={() => handleExport('docx', group)}
                                                        loading={loading}
                                                        type="primary"
                                                    >
                                                        导出Word
                                                    </Button>
                                                </Button.Group>
                                            </Space>
                                        </div>

                                        {/* 学生列表 */}
                                        <List
                                            dataSource={group.scores}
                                            pagination={group.scores.length > 10 ? { pageSize: 10, showSizeChanger: true } : false}
                                            renderItem={(score, index) => (
                                                <List.Item style={{ border: 'none', padding: '12px 0' }}>
                                                    <Card 
                                                        style={{ 
                                                            width: '100%',
                                                            borderRadius: '8px',
                                                            border: '1px solid #f0f0f0',
                                                            boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                                                            transition: 'all 0.3s'
                                                        }}
                                                        hoverable
                                                    >
                                                        <div style={{ marginBottom: '16px' }}>
                                                            <Space>
                                                                <Tag color="blue" style={{ fontSize: '14px', padding: '4px 12px' }}>
                                                                    #{index + 1}
                                                                </Tag>
                                                                <Title level={4} style={{ margin: 0 }}>
                                                                    {score.student_name}
                                                                </Title>
                                                                <Tag color="green" style={{ fontSize: '14px', padding: '4px 12px' }}>
                                                                    总分：{score.total_score}
                                                                </Tag>
                                                            </Space>
                                                        </div>

                                                        {score.analysis && (
                                                            <div>
                                                                <Divider style={{ margin: '12px 0' }} />
                                                                <div style={{ 
                                                                    background: '#fafafa', 
                                                                    padding: '16px', 
                                                                    borderRadius: '6px',
                                                                    lineHeight: '1.8'
                                                                }}>
                                                                    <Text strong style={{ color: '#1890ff', marginBottom: '8px', display: 'block' }}>
                                                                        📝 成绩分析
                                                                    </Text>
                                                                    <Paragraph 
                                                                        style={{ 
                                                                            marginBottom: 0,
                                                                            whiteSpace: 'pre-wrap',
                                                                            fontSize: '14px'
                                                                        }}
                                                                    >
                                                                        {score.analysis}
                                                                    </Paragraph>
                                                                </div>
                                                            </div>
                                                        )}

                                                        {score.suggestions && score.suggestions.length > 0 && (
                                                            <div style={{ marginTop: '12px' }}>
                                                                <Divider style={{ margin: '12px 0' }} />
                                                                <Text strong style={{ color: '#52c41a', marginBottom: '8px', display: 'block' }}>
                                                                    💡 改进建议
                                                                </Text>
                                                                <ul style={{ 
                                                                    margin: '8px 0',
                                                                    paddingLeft: '20px',
                                                                    listStyle: 'none'
                                                                }}>
                                                                    {score.suggestions.map((suggestion, idx) => (
                                                                        <li key={idx} style={{ 
                                                                            marginBottom: '8px',
                                                                            padding: '8px 12px',
                                                                            background: '#f6ffed',
                                                                            borderRadius: '4px',
                                                                            borderLeft: '3px solid #52c41a'
                                                                        }}>
                                                                            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: '8px' }} />
                                                                            {suggestion}
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}
                                                    </Card>
                                                </List.Item>
                                            )}
                                        />
                                    </div>
                                )
                            }))}
                        />
                    )}
                </Card>
            </div>
        </div>
    );
};

export default Home; 