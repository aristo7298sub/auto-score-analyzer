<template>
  <div class="score-analysis">
    <h2>成绩分析</h2>
    
    <!-- 图表展示区域 -->
    <div class="charts-container">
      <div class="chart-grid">
        <div class="chart-item">
          <h3>成绩分布</h3>
          <img :src="charts.score_distribution" alt="成绩分布" />
        </div>
        <div class="chart-item">
          <h3>题目类型分布</h3>
          <img :src="charts.category_pie" alt="题目类型分布" />
        </div>
        <div class="chart-item">
          <h3>学生成绩对比</h3>
          <img :src="charts.student_comparison" alt="学生成绩对比" />
        </div>
        <div class="chart-item">
          <h3>题目扣分热力图</h3>
          <img :src="charts.question_heatmap" alt="题目扣分热力图" />
        </div>
      </div>
    </div>

    <!-- 现有的成绩列表 -->
    <div class="score-list">
      // ... existing code ...
    </div>
  </div>
</template>

<script>
export default {
  name: 'ScoreAnalysis',
  data() {
    return {
      // ... existing data ...
      charts: {
        score_distribution: '',
        category_pie: '',
        student_comparison: '',
        question_heatmap: ''
      }
    }
  },
  methods: {
    // ... existing methods ...
    
    async loadCharts() {
      try {
        const response = await fetch('/api/charts')
        if (response.ok) {
          const data = await response.json()
          this.charts = data
        }
      } catch (error) {
        console.error('加载图表失败:', error)
      }
    }
  },
  mounted() {
    // ... existing mounted code ...
    this.loadCharts()
  }
}
</script>

<style scoped>
.charts-container {
  margin: 20px 0;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-item {
  background: #fff;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.chart-item h3 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 16px;
}

.chart-item img {
  width: 100%;
  height: auto;
  border-radius: 4px;
}

// ... existing styles ...
</style> 