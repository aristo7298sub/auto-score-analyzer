import React from 'react';
import { Layout } from 'antd';
import Home from './pages/Home';
import './App.css';

const { Header, Content } = Layout;

const App: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px' }}>
        <h1 style={{ margin: 0, lineHeight: '64px' }}>学生成绩分析系统</h1>
      </Header>
      <Content>
        <Home />
      </Content>
    </Layout>
  );
};

export default App;
