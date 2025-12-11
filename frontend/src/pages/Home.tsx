import React, { useState, useEffect } from 'react';
import { Upload, Card, Input, Button, List, message, Tag, Empty, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import { StudentScore } from '../types/score';
import { scoreApi } from '../services/apiClient';
import { useAuthStore } from '../store/authStore';
import { useScoreStore, FileGroup } from '../store/scoreStore';
import '../styles/home.css';

const { Dragger } = Upload;

const Home: React.FC = () => {
  const { t } = useTranslation();
  const { user, updateUser } = useAuthStore();
  const { 
    fileGroups, 
    activeFileId, 
    setScores, 
    setFileGroups, 
    setActiveFileId 
  } = useScoreStore();
  
  const [searchText, setSearchText] = useState('');
  const [filteredScores, setFilteredScores] = useState<StudentScore[]>([]);
  const [loading, setLoading] = useState(false);

  // 页面加载时，检查会话 ID，如果是新会话则清空数据
  useEffect(() => {
    const currentSessionId = sessionStorage.getItem('session-id');
    const storedSessionId = localStorage.getItem('last-session-id');
    
    // 如果是新会话，清空所有数据
    if (currentSessionId && currentSessionId !== storedSessionId) {
      setFileGroups([]);
      setActiveFileId('');
      setFilteredScores([]);
      localStorage.setItem('last-session-id', currentSessionId);
      return;
    }
    
    // 否则恢复之前的数据
    if (activeFileId && fileGroups.length > 0) {
      const activeGroup = fileGroups.find(g => g.id === activeFileId);
      if (activeGroup && activeGroup.scores.length > 0) {
        setFilteredScores(activeGroup.scores);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 只在组件挂载时执行一次

  const handleUpload = async (file: File) => {
    const fileId = `${Date.now()}-${file.name}`;
    
    try {
      // 1. 添加上传中状态
      const newGroup: FileGroup = {
        id: fileId,
        filename: file.name,
        scores: [],
        uploadTime: new Date().toLocaleString('zh-CN'),
        status: 'uploading',
        statusMessage: '📤 文件上传中...'
      };
      
      setFileGroups(prev => [newGroup, ...prev]);
      setActiveFileId(fileId);
      setSearchText(''); // 清空搜索框

      // 更新状态为解析中
      setFileGroups(prev => prev.map(group => 
        group.id === fileId 
          ? { ...group, statusMessage: '📋 正在解析文件...' }
          : group
      ));

      // 2. 调用API
      const response = await scoreApi.upload(file);
      const result = response.data;
      
      if (!result.success || !result.data) {
        throw new Error(result.message || '上传失败');
      }

      const { data: scores, processing_info } = result;

      // 3. 更新完成状态
      setFileGroups(prev => prev.map(group => 
        group.id === fileId 
          ? {
              ...group,
              scores: scores!,
              status: 'complete',
              statusMessage: '✅ 分析完成',
              studentCount: processing_info?.student_count,
              quotaCost: processing_info?.quota_cost,
            }
          : group
      ));
      
      setFilteredScores(scores!); // 显示所有学生

      // 4. 保存到持久化 store
      setScores(scores!, file.name, processing_info);

      // 5. 更新用户配额
      if (user && processing_info?.quota_remaining !== undefined) {
        updateUser({ quota_balance: processing_info.quota_remaining });
      }

      message.success(`✨ 成功分析 ${processing_info?.student_count || scores!.length} 名学生的成绩！`);
    } catch (error: any) {
      setFileGroups(prev => prev.map(group => 
        group.id === fileId 
          ? { 
              ...group, 
              status: 'error',
              statusMessage: error.response?.data?.detail || error.message || '上传失败，请重试'
            }
          : group
      ));
      message.error(error.response?.data?.detail || error.message || '上传失败，请重试');
    }
  };

  const handleExport = async (format: 'xlsx' | 'docx', group: FileGroup) => {
    try {
      setLoading(true);
      const response = await scoreApi.export(format, group.scores, group.filename);
      
      // 下载文件
      const blob = response.data;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const baseName = group.filename.replace(/\.[^/.]+$/, '');
      a.download = `${baseName}-分析报告.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      message.success('导出成功！');
    } catch (error) {
      message.error('导出失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    const activeGroup = fileGroups.find(g => g.id === activeFileId);
    if (!activeGroup || activeGroup.status !== 'complete') {
      message.warning('请先上传并分析文件');
      return;
    }

    const trimmedSearch = searchText.trim();
    
    // 如果搜索框为空,显示所有学生
    if (!trimmedSearch) {
      setFilteredScores(activeGroup.scores);
      return;
    }

    // 搜索匹配的学生
    const filtered = activeGroup.scores.filter(student => 
      student.student_name.toLowerCase().includes(trimmedSearch.toLowerCase())
    );
    
    if (filtered.length > 0) {
      setFilteredScores(filtered);
      message.success(`找到 ${filtered.length} 名学生`);
    } else {
      setFilteredScores([]);
      message.info('未找到匹配的学生');
    }
  };

  const activeGroup = fileGroups.find(g => g.id === activeFileId);
  
  // 使用filteredScores或全部scores
  const displayScores = filteredScores.length > 0 || searchText.trim() 
    ? filteredScores 
    : (activeGroup?.scores || []);

  return (
    <div className="home-page">
      {/* 上传区域 */}
      <div className="upload-section">
        <div className="upload-card">
          <Dragger
            accept=".xlsx,.docx,.pptx"
            multiple={false}
            beforeUpload={(file) => {
              handleUpload(file);
              return false;
            }}
            showUploadList={false}
            className="modern-dragger"
          >
            <div className="dragger-content">
              <div className="upload-icon">📤</div>
              <p className="upload-text">{t('analysis.dragFile')}</p>
              <p className="upload-hint">{t('analysis.fileFormats')}</p>
            </div>
          </Dragger>
          
          {/* 上传进度提示 */}
          {activeGroup && activeGroup.status === 'uploading' && (
            <div className="upload-progress">
              <Spin />
              <span className="progress-text">{activeGroup.statusMessage}</span>
              <div style={{ marginTop: 12, color: '#ff7700', fontSize: 13 }}>
                ⚠️ 正在分析中，请勿切换到其他页面，否则可能影响加载速度
              </div>
            </div>
          )}
        </div>
        
        {/* 搜索框 - 仅在无文件或文件完成时显示 */}
        {(!activeGroup || activeGroup.status === 'complete') && (
          <div className="search-card">
            <div className="search-header">
              <span className="search-icon">🔍</span>
              <span className="search-title">搜索学生成绩</span>
            </div>
            <div className="search-input-group">
              <Input
                placeholder={activeGroup ? "输入学生姓名搜索，留空显示全部" : "请先上传文件"}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onPressEnter={handleSearch}
                disabled={!activeGroup}
                className="input"
              />
              <Button 
                type="primary" 
                onClick={handleSearch}
                disabled={!activeGroup}
                className="btn-primary"
              >
                搜索
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 文件列表 */}
      {fileGroups.length > 0 && (
        <div className="files-section">
          <div className="section-header">
            <h3 className="section-title">
              <span>📊</span>
              <span>分析记录</span>
            </h3>
            <span className="file-count">{fileGroups.length}</span>
          </div>

          <div className="file-tabs">
            {fileGroups.map(group => (
              <div
                key={group.id}
                className={`file-tab ${activeFileId === group.id ? 'active' : ''}`}
                onClick={() => {
                  setActiveFileId(group.id);
                  setSearchText('');
                  setFilteredScores(group.scores);
                }}
              >
                <span className="file-name">{group.filename}</span>
                {group.status === 'uploading' && <Spin size="small" />}
                {group.status === 'complete' && (
                  <Tag color="success" className="status-tag">✓ 完成</Tag>
                )}
                {group.status === 'error' && (
                  <Tag color="error" className="status-tag">✗ 失败</Tag>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 分析结果 */}
      {activeGroup && (
        <Card className="results-card card" bordered={false}>
          <div className="results-header">
            <div className="results-title">
              <span className="results-icon">📈</span>
              <h3>成绩分析结果</h3>
            </div>
            
            {activeGroup.status === 'complete' && activeGroup.scores.length > 0 && (
              <div className="export-buttons">
                <Button 
                  onClick={() => handleExport('xlsx', activeGroup)}
                  loading={loading}
                  className="btn-secondary"
                >
                  导出 Excel
                </Button>
                <Button 
                  onClick={() => handleExport('docx', activeGroup)}
                  loading={loading}
                  className="btn-secondary"
                >
                  导出 Word
                </Button>
              </div>
            )}
          </div>

          {/* 成绩统计 */}
          {activeGroup.status === 'complete' && displayScores.length > 0 && (
            <>
              <div className="stats-grid">`
                <div className="stat-card glass">
                  <div className="stat-icon">👥</div>
                  <div className="stat-value">{activeGroup.studentCount || activeGroup.scores.length}</div>
                  <div className="stat-label">学生人数</div>
                </div>
                
                {activeGroup.quotaCost !== undefined && (
                  <div className="stat-card glass">
                    <div className="stat-icon">💎</div>
                    <div className="stat-value">{activeGroup.quotaCost}</div>
                    <div className="stat-label">配额消耗</div>
                  </div>
                )}
                
                <div className="stat-card glass">
                  <div className="stat-icon">📝</div>
                  <div className="stat-value">
                    {Math.round(activeGroup.scores.reduce((sum, s) => sum + s.total_score, 0) / activeGroup.scores.length)}
                  </div>
                  <div className="stat-label">平均分</div>
                </div>
              </div>

              {/* 学生列表 */}
              <div className="students-list">
                <List
                  dataSource={displayScores}
                  renderItem={(student) => (
                    <div className="student-card glass">
                      <div className="student-header">
                        <div className="student-name">
                          <span className="name-badge">{student.student_name.charAt(0)}</span>
                          <span className="name-text">{student.student_name}</span>
                        </div>
                        <div className="student-score">
                          <span className="score-value">{student.total_score}</span>
                          <span className="score-label">分</span>
                        </div>
                      </div>
                      
                      {student.analysis && (
                        <div className="student-analysis">
                          <div className="analysis-label">📊 AI 分析</div>
                          <p className="analysis-text">{student.analysis}</p>
                        </div>
                      )}
                    </div>
                  )}
                />
              </div>
            </>
          )}

          {activeGroup.status === 'complete' && displayScores.length === 0 && (
            <Empty description={searchText.trim() ? "未找到匹配的学生" : "暂无数据"} />
          )}
        </Card>
      )}
    </div>
  );
};

export default Home;