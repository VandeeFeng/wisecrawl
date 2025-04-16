<template>
  <div class="container">
    <div class="title-container">
      <h1>Wise Crawl</h1>
    </div>
    
    <div class="filters-container">
      <div class="filters">
        <button 
          v-for="source in sources" 
          :key="source"
          :class="{ active: selectedSource === source }"
          @click="setSource(source)"
        >
          {{ source === 'all' ? 'All' : source }}
        </button>
      </div>
    </div>
    
    <div class="content-container">
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else class="news-list">
        <div v-for="(item, index) in filteredNews" :key="index" class="news-card">
          <h2 class="news-title">{{ item.title }}</h2>
          <div class="news-meta">
            <span class="source">Source: {{ item.source }}</span>
            <span class="hot" v-if="item.hot">Hot: {{ formatHot(item.hot) }}</span>
            <span class="time" v-if="item.timestamp">{{ formatTime(item.timestamp) }}</span>
          </div>
          <p class="news-desc" v-if="item.desc">{{ item.desc }}</p>
          <p class="news-summary" v-else-if="item.summary && item.summary !== '[Summary cannot be generated: Insufficient content or source information]'">{{ item.summary }}</p>
          <div class="news-footer">
            <a :href="item.url" target="_blank" class="news-link">View Original</a>
            <span class="tech-tag" v-if="item.is_tech">Tech</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';

const news = ref([]);
const loading = ref(true);
const error = ref(null);
const selectedSource = ref('all');

const sources = computed(() => {
  const uniqueSources = new Set(news.value.map(item => item.source));
  return ['all', ...uniqueSources];
});

const filteredNews = computed(() => {
  if (selectedSource.value === 'all') {
    return news.value;
  }
  return news.value.filter(item => item.source === selectedSource.value);
});

const setSource = (source) => {
  selectedSource.value = source;
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(parseInt(timestamp));
  return date.toLocaleString('en-US');
};

const formatHot = (hot) => {
  if (hot >= 10000) {
    return (hot / 10000).toFixed(1) + 'w';
  }
  return hot;
};

const fetchNews = async () => {
  try {
    loading.value = true;
    const response = await axios.get('/api/news');
    news.value = response.data;
  } catch (err) {
    error.value = 'Failed to load news data: ' + (err.response?.data?.message || err.message);
    console.error('Error fetching news:', err);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchNews();
});
</script>

<style>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100vh;
}

.title-container {
  width: 100%;
  text-align: center;
  padding: 10px;
}

h1 {
  color: #333;
  margin: 0;
  font-size: 2rem;
}

.filters-container {
  width: 100%;
  padding: 15px;
}

.filters {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 4px;
  max-width: 100%;
  margin-left: auto;
  margin-right: auto;
}

.filters button {
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  margin: 1px;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  max-width: 120px;
  line-height: 1.5;
}

.filters button.active {
  background-color: #1e88e5;
  color: white;
  border-color: #1e88e5;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.filters button:hover {
  background-color: #e3f2fd;
  border-color: #90caf9;
}

.content-container {
  width: 100%;
  padding: 15px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 600px;
}

.loading, .error {
  text-align: center;
  padding: 40px;
  font-size: 18px;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error {
  color: #e53935;
}

.news-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  align-items: stretch;
  width: 100%;
  flex: 1;
  min-height: 500px;
}

.news-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 20px;
  transition: transform 0.4s cubic-bezier(0.215, 0.61, 0.355, 1),
              box-shadow 0.4s cubic-bezier(0.215, 0.61, 0.355, 1),
              height 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  height: 220px;
  min-height: 220px;
  display: flex;
  flex-direction: column;
  background-color: white;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  will-change: transform, height, box-shadow;
}

.news-card::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));
  pointer-events: none;
  transition: opacity 0.4s ease;
}

.news-card::before {
  content: '';
  position: absolute;
  bottom: 5px;
  right: 10px;
  opacity: 0;
}

.news-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: auto;
  z-index: 10;
  height: auto;
  max-height: 500px;
  scrollbar-width: thin;
  transition: transform 0.4s cubic-bezier(0.215, 0.61, 0.355, 1),
              box-shadow 0.4s cubic-bezier(0.215, 0.61, 0.355, 1),
              height 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.news-card:hover::-webkit-scrollbar {
  width: 4px;
}

.news-card:hover::-webkit-scrollbar-thumb {
  background-color: #cecece;
  border-radius: 4px;
}

.news-card:hover::after,
.news-card:hover::before {
  opacity: 0;
  transition: opacity 0.3s ease;
}

.news-card:hover .news-desc,
.news-card:hover .news-summary {
  -webkit-line-clamp: initial;
  height: auto;
  max-height: none;
  transition: height 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.1s,
              max-height 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.1s;
}

.news-card:hover .news-title {
  -webkit-line-clamp: initial;
  height: auto;
}

.news-title {
  font-size: 18px;
  margin-top: 0;
  margin-bottom: 10px;
  line-height: 1.4;
  flex: 0 0 auto;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  height: 2.8em;
  transition: height 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), 
              max-height 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  will-change: height, -webkit-line-clamp;
}

.news-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 14px;
  color: #757575;
  margin-bottom: 10px;
  flex: 0 0 auto;
  transition: all 0.3s ease;
}

.news-desc, .news-summary {
  font-size: 14px;
  line-height: 1.6;
  color: #424242;
  margin-bottom: 15px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  flex: 1 1 auto;
  height: 4.8em;
  transition: height 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), 
              max-height 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  will-change: height, max-height;
}

.news-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 0 0 auto;
  position: sticky;
  bottom: 0;
  background-color: white;
  padding-top: 5px;
  margin-top: auto;
}

.news-link {
  color: #1e88e5;
  text-decoration: none;
  font-size: 14px;
}

.news-link:hover {
  text-decoration: underline;
}

.tech-tag {
  background-color: #ff4081;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.news-card:hover .news-desc,
.news-card:hover .news-summary {
  -webkit-line-clamp: initial;
  height: auto;
  max-height: none;
  transition: height 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.1s,
              max-height 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.1s;
}

.news-card:hover .news-title {
  -webkit-line-clamp: initial;
  height: auto;
  transition: height 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) 0.05s,
              max-height 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) 0.05s;
}
</style>
