import React, { useState, useEffect, useRef } from 'react';
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
  const [oneShotText, setOneShotText] = useState('');

  const [pendingFile, setPendingFile] = useState<{
    id: string;
    backendFileId: number;
    filename: string;
    uploadTime: string;
    scores: StudentScore[];
    studentCount?: number;
    quotaCost?: number;
  } | null>(null);

  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<'idle' | 'uploading' | 'parsing' | 'ready' | 'error'>('idle');
  const [uploadStageText, setUploadStageText] = useState('');

  const [aiStage, setAiStage] = useState<'idle' | 'analyzing' | 'complete' | 'error'>('idle');
  const [aiProgress, setAiProgress] = useState(0);
  const aiTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (aiTimerRef.current) {
        window.clearInterval(aiTimerRef.current);
        aiTimerRef.current = null;
      }
    };
  }, []);

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
      // 1) 不在“分析记录”中展示（等待AI分析点击后再加入）
      setPendingFile(null);
      setUploadProgress(5);
      setUploadStage('uploading');
      setUploadStageText('📤 文件上传中...');
      setAiStage('idle');
      setAiProgress(0);

      setSearchText(''); // 清空搜索框
      setFilteredScores([]);

      // 模拟进度：上传 -> 解析
      const startedAt = Date.now();
      let stage: 'uploading' | 'parsing' = 'uploading';
      const uploadTimer = window.setInterval(() => {
        setUploadProgress((p) => {
          const elapsed = Date.now() - startedAt;
          if (stage === 'uploading' && (elapsed > 900 || p >= 40)) {
            stage = 'parsing';
            setUploadStage('parsing');
            setUploadStageText('🧩 正在解析文件...');
            return Math.max(p, 42);
          }

          const cap = stage === 'uploading' ? 40 : 92;
          const next = Math.min(cap, p + (stage === 'uploading' ? 3 : 2));
          return next;
        });
      }, 280);

      // 2. 调用API
      const response = await scoreApi.upload(file);
      const result = response.data;
      
      if (!result.success || !result.data) {
        throw new Error(result.message || '上传失败');
      }

      const { data: scores, processing_info } = result;

      window.clearInterval(uploadTimer);
      setUploadProgress(100);
      setUploadStage('ready');
      setUploadStageText('✅ 解析完成');

      const backendFileId = Number(processing_info?.file_id);
      setPendingFile({
        id: fileId,
        backendFileId,
        filename: file.name,
        uploadTime: new Date().toLocaleString('zh-CN'),
        scores: scores!,
        studentCount: processing_info?.student_count,
        quotaCost: processing_info?.quota_cost,
      });

      // 未触发AI分析前，结果区保持为空
      setFilteredScores([]);

      // 4. 保存到持久化 store（此时仅解析完成）
      setScores(scores!, file.name, processing_info);

      message.success(`✨ 成功解析 ${processing_info?.student_count || scores!.length} 名学生的成绩，等待AI分析`);
    } catch (error: any) {
      setUploadStage('error');
      setUploadStageText('❌ 上传失败，重试');
      message.error(error.response?.data?.detail || error.message || '上传失败，请重试');
    }
  };

  const handleAnalyzeNow = async () => {
    if (!pendingFile || uploadStage !== 'ready') {
      message.warning('请先上传文件并完成解析');
      return;
    }

    try {
      setLoading(true);

      // 点击后才把文件加入“分析记录”列表
      const groupId = pendingFile.id;
      const newGroup: FileGroup = {
        id: groupId,
        backendFileId: pendingFile.backendFileId,
        filename: pendingFile.filename,
        scores: pendingFile.scores,
        uploadTime: pendingFile.uploadTime,
        status: 'analyzing',
        statusMessage: '🤖 AI分析中...',
        studentCount: pendingFile.studentCount,
        quotaCost: pendingFile.quotaCost,
      };
      setFileGroups(prev => [newGroup, ...prev]);
      setActiveFileId(groupId);
      setPendingFile(null);

      // AI 状态（按钮左侧）
      setAiStage('analyzing');
      setAiProgress(6);

      if (aiTimerRef.current) {
        window.clearInterval(aiTimerRef.current);
        aiTimerRef.current = null;
      }

      const startedAt = Date.now();
      aiTimerRef.current = window.setInterval(() => {
        setAiProgress((p) => {
          const elapsed = Date.now() - startedAt;
          const cap = 92;
          const next = Math.min(cap, Math.max(p, 6) + 3);
          if (elapsed > 2200 && next >= cap) {
            return cap;
          }
          return next;
        });
      }, 220);

      const response = await scoreApi.analyzeFile(newGroup.backendFileId!, oneShotText.trim());
      const result = response.data;

      if (!result.success || !result.data) {
        throw new Error(result.message || 'AI分析失败');
      }

      const { data: analyzedScores, processing_info } = result;

      setAiStage('complete');
      if (aiTimerRef.current) {
        window.clearInterval(aiTimerRef.current);
        aiTimerRef.current = null;
      }
      setAiProgress(100);

      setFileGroups(prev => prev.map(group =>
        group.id === groupId
          ? {
              ...group,
              scores: analyzedScores,
              status: 'complete',
              statusMessage: `✅ ${t('analysis.analysisComplete')}`,
              studentCount: processing_info?.student_count ?? group.studentCount,
              quotaCost: processing_info?.quota_cost ?? group.quotaCost,
            }
          : group
      ));

      setFilteredScores(analyzedScores);
      setScores(analyzedScores, newGroup.filename, processing_info);

      // 更新用户配额（AI分析阶段才扣减）
      if (user && processing_info?.quota_remaining !== undefined) {
        updateUser({ quota_balance: processing_info.quota_remaining });
      }

      message.success('🤖 AI分析完成！');
    } catch (error: any) {
      setAiStage('error');
      if (aiTimerRef.current) {
        window.clearInterval(aiTimerRef.current);
        aiTimerRef.current = null;
      }
      setAiProgress(0);
      setFileGroups(prev => prev.map(group =>
        group.id === activeFileId
          ? { ...group, status: 'error', statusMessage: error.response?.data?.detail || error.message || 'AI分析失败，请重试' }
          : group
      ));
      message.error(error.response?.data?.detail || error.message || 'AI分析失败，请重试');
    } finally {
      setLoading(false);
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
      message.warning('请先完成AI分析');
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

  const statsScores: StudentScore[] = activeGroup?.scores?.length
    ? activeGroup.scores
    : pendingFile?.scores || [];

  const statsStudentCount = activeGroup?.studentCount
    ?? pendingFile?.studentCount
    ?? (statsScores.length || 0);

  const statsQuotaCost = activeGroup?.quotaCost ?? pendingFile?.quotaCost;

  const avgScore = statsScores.length
    ? statsScores.reduce((sum, s) => sum + s.total_score, 0) / statsScores.length
    : 0;
  const avgScoreText = avgScore.toFixed(2);

  const shouldShowStats = uploadStage === 'ready' || !!activeGroup;
  
  // 使用filteredScores或全部scores
  const displayScores = filteredScores.length > 0 || searchText.trim() 
    ? filteredScores 
    : (activeGroup?.scores || []);

  return (
    <div className="home-page">
      {/* 上传区域 */}
      <div className="upload-section">
        <div className="upload-split">
          <div className="upload-half upload-half--large">
            <div className="upload-card upload-card--compact">
              <Dragger
                accept=".xlsx"
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
            </div>
          </div>

          <div className="upload-half upload-half--small">
            <div className="upload-card upload-card--compact upload-card--static">
              <div className="oneshot-panel oneshot-panel--no-top">
                <Input.TextArea
                  value={oneShotText}
                  onChange={(e) => setOneShotText(e.target.value)}
                  placeholder={t('analysis.oneShotPlaceholder')}
                  className="oneshot-textarea"
                />
              </div>
            </div>
          </div>
        </div>

        {/* 中间按钮区：位于上方两框与下方结果框之间的正中间 */}
        <div className="split-actions" aria-label="actions">
          <div className="split-actions-half split-actions-half--large">
            <Upload
              accept=".xlsx"
              multiple={false}
              beforeUpload={(file) => {
                handleUpload(file);
                return false;
              }}
              showUploadList={false}
            >
              <Button
                type="primary"
                className={`btn-primary upload-progress-btn ${uploadStage === 'uploading' || uploadStage === 'parsing' ? 'is-progressing' : ''}`}
                disabled={uploadStage === 'uploading' || uploadStage === 'parsing'}
                style={
                  uploadStage === 'uploading' || uploadStage === 'parsing'
                    ? ({ ['--upload-progress' as any]: `${uploadProgress}%` } as React.CSSProperties)
                    : undefined
                }
              >
                <span className="upload-btn-inner">
                  {(uploadStage === 'uploading' || uploadStage === 'parsing') && (
                    <Spin size="small" style={{ marginRight: 8 }} />
                  )}
                  {uploadStage === 'idle' ? '📤 上传文件' : (uploadStageText || '处理中...')}
                </span>
              </Button>
            </Upload>
          </div>

          <div className="split-actions-half split-actions-half--small">
            <Button
              type="primary"
              onClick={handleAnalyzeNow}
              loading={false}
              disabled={!pendingFile || uploadStage !== 'ready' || loading || aiStage === 'analyzing'}
              className={`btn-primary ai-analyze-btn ai-progress-btn ${aiStage === 'analyzing' ? 'is-progressing' : ''}`}
              style={
                aiStage === 'analyzing'
                  ? ({ ['--ai-progress' as any]: `${aiProgress}%` } as React.CSSProperties)
                  : undefined
              }
            >
              <span className="ai-btn-inner">
                {aiStage === 'analyzing' && <Spin size="small" style={{ marginRight: 8 }} />}
                {t('analysis.analyzeNow')}
              </span>
            </Button>
          </div>
        </div>
      </div>

      {/* 文件列表 */}
      {fileGroups.length > 0 && (
        <div className="files-section">
          <div className="section-header">
            <h3 className="section-title">
              <span>📊</span>
              <span>分析记录</span>
            </h3>
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
                {group.status === 'analyzing' && <Spin size="small" />}
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

      {/* 分析结果（默认加载，与之前保持一致） */}
      <Card className="results-card card" bordered={false}>
          <div className="results-header">
            <div className="results-title">
              <span className="results-icon">📈</span>
              <h3>成绩分析结果</h3>
            </div>

            {activeGroup && activeGroup.status === 'complete' && activeGroup.scores.length > 0 && (
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

          {/* 成绩统计：解析完成后即展示；AI完成后再展示搜索与学生结果 */}
          {shouldShowStats && statsScores.length > 0 && (
            <>
              <div className="stats-grid">
                <div className="stat-card glass">
                  <div className="stat-icon">👥</div>
                  <div className="stat-value">{statsStudentCount}</div>
                  <div className="stat-label">学生人数</div>
                </div>

                {statsQuotaCost !== undefined && (
                  <div className="stat-card glass">
                    <div className="stat-icon">💎</div>
                    <div className="stat-value">{statsQuotaCost}</div>
                    <div className="stat-label">预计配额消耗</div>
                  </div>
                )}

                <div className="stat-card glass">
                  <div className="stat-icon">📝</div>
                  <div className="stat-value">{avgScoreText}</div>
                  <div className="stat-label">平均分</div>
                </div>
              </div>

              {(!activeGroup || activeGroup.status !== 'complete') && (
                <div className="status-info status-info--compact">
                  <p>点击⚡一键AI分析后，获取分析结果</p>
                </div>
              )}

              {activeGroup && activeGroup.status === 'complete' && (
                <>
                  {/* 搜索框：放在汇总卡片下方，且位于成绩分析卡片内部 */}
                  <div className="results-search">
                    <div className="search-header">
                      <span className="search-icon">🔍</span>
                      <span className="search-title">搜索学生成绩</span>
                    </div>
                    <div className="search-input-group">
                      <Input
                        placeholder={"输入学生姓名搜索，留空显示全部"}
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

                  {/* 学生列表 */}
                  <div className="students-list students-scroll">
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
            </>
          )}

          {/* AI未处理前：结果区留空（仅保留占位提示） */}
          {(!activeGroup || activeGroup.status !== 'complete') && !shouldShowStats && (
            <div className="status-info">
              <p>📤 请先上传文件并完成解析</p>
            </div>
          )}

          {activeGroup && activeGroup.status === 'complete' && displayScores.length === 0 && (
            <Empty description={searchText.trim() ? "未找到匹配的学生" : "暂无数据"} />
          )}
        </Card>
    </div>
  );
};

export default Home;