<template>
  <div class="terminal">
    <div class="terminal-header">
      <div class="title">WiseCrawl v0.1.0</div>
      <div class="controls">
        <span class="minimize"></span>
        <span class="maximize"></span>
        <span class="close"></span>
      </div>
    </div>
    
    <div class="terminal-body">
      <div class="ascii-title">
        <pre>
 _    _ _          ____                    _ 
| |  | (_)        / ___|_ __ __ ___      _| |
| |  | |_ ___  ___| |   | '__/ _' \ \ /\ / / |
| |/\| | / __|/ _ \ |___| | | (_| |\ V  V /| |
\  /\  / \__ \  __/\____|_|  \__,_| \_/\_/ |_|
 \/  \/|_|___/\___|                           
        </pre>
      </div>

      <div class="command-line">
        <span class="prompt">$</span>
        <div class="filters">
          <button 
            v-for="(source, index) in visibleSources" 
            :key="source"
            :class="{ active: selectedSource === source }"
            @click="setSource(source)"
          >
            {{ source === 'all' ? '[ALL]' : '[' + source.toUpperCase() + ']' }}
          </button>
          <button 
            v-if="sources.length > maxVisibleSources"
            @click="toggleExpand"
            class="expand-btn"
          >
            {{ isExpanded ? '[-]' : `[+${sources.length - maxVisibleSources}]` }}
          </button>
        </div>
      </div>

      <div class="output-area">
        <div v-if="loading" class="loading">
          <pre>
Loading news feed...
[===>-----------------] 25%
          </pre>
        </div>
        
        <div v-else-if="error" class="error">
          <pre>
ERROR: {{ error }}
Type 'refresh' to try again.
          </pre>
        </div>
        
        <div v-else class="news-list">
          <div v-for="(item, index) in filteredNews" :key="index" class="news-item" box-="double">
            <div class="news-header">
              <span class="index">[{{ index + 1 }}]</span>
              <span class="title">{{ item.title }}</span>
            </div>
            <div class="news-meta">
              <span class="source">src://{{ item.source }}</span>
              <span class="hot" v-if="item.hot">heat={{ formatHot(item.hot) }}</span>
              <span class="time" v-if="item.timestamp">time={{ formatTime(item.timestamp) }}</span>
              <span class="tech-tag" v-if="item.is_tech">[TECH]</span>
            </div>
            <div class="news-content" v-if="item.desc || item.summary">
              <pre>{{ item.desc || (item.summary !== '[Summary cannot be generated: Insufficient content or source information]' ? item.summary : '') }}</pre>
            </div>
            <div class="news-link">
              <a :href="item.url" target="_blank">$ curl {{ item.url }}</a>
            </div>
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
const isExpanded = ref(false);
const maxVisibleSources = 20;

const sources = computed(() => {
  const uniqueSources = new Set(news.value.map(item => item.source));
  return ['all', ...uniqueSources];
});

const visibleSources = computed(() => {
  if (isExpanded.value) {
    return sources.value;
  }
  return sources.value.slice(0, maxVisibleSources);
});

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

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
@layer base, utils, components;

@import "@webtui/css/base.css";
@import "@webtui/css/utils/box.css";
@import "@webtui/css/components/button.css";
@import "@webtui/css/components/typography.css";

:root {
  --terminal-bg: #1a1b1e;
  --terminal-text: #98c379;
  --terminal-prompt: #61afef;
  --terminal-header: #2c323c;
  --terminal-border: #3e4451;
  --box-border-color: var(--terminal-border);
  --box-rounded-radius: 6px;
}

body {
  margin: 0;
  padding: 20px;
  background: #2c323c;
  font-family: 'Fira Code', monospace;
  height: 100vh;
  overflow: hidden;
}

.terminal {
  max-width: 1200px;
  margin: 0 auto;
  background: var(--terminal-bg);
  border: 1px solid var(--terminal-border);
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  min-height: 95vh;
  max-height: 95vh;
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: calc(100% - 40px);
}

.terminal-header {
  background: var(--terminal-header);
  padding: 4px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--terminal-border);
}

.title {
  color: var(--terminal-text);
  font-size: 14px;
}

.controls {
  display: flex;
  gap: 4px;
}

.controls span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.controls span:hover {
  opacity: 1;
}

.minimize { background: #f1fa8c; }
.maximize { background: #50fa7b; }
.close { background: #ff5555; }

.terminal-body {
  padding: 20px;
  color: var(--terminal-text);
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.ascii-title {
  color: #61afef;
  margin-bottom: 20px;
  text-align: center;
}

.command-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 16px;
}

.prompt {
  color: var(--terminal-prompt);
  font-weight: bold;
  font-size: 0.9em;
}

.filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: flex-start;
  max-width: 100%;
  justify-content: center;
  min-height: 64px;
  align-content: flex-start;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--terminal-border);
}

.filters button {
  background: transparent;
  border: 1px solid var(--terminal-border);
  color: var(--terminal-text);
  padding: 2px 8px;
  cursor: pointer;
  font-family: 'Fira Code', monospace;
  font-size: 0.8em;
  transition: all 0.2s;
  min-width: 60px;
  text-align: center;
  flex: 0 1 auto;
  margin-bottom: 4px;
  height: 24px;
  line-height: 1.2;
}

.filters button:focus {
  outline: none;
  box-shadow: none;
}

.filters button.active {
  background: var(--terminal-prompt);
  color: var(--terminal-bg);
  border-color: var(--terminal-prompt) !important;
}

.filters .expand-btn {
  color: #61afef;
  border-style: dashed;
  min-width: auto;
  flex: 0 0 auto;
  margin-bottom: 0;
  padding: 2px 6px;
}

.filters .expand-btn:hover {
  background: rgba(97, 175, 239, 0.1);
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.news-item {
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
}

.news-header {
  margin-bottom: 8px;
}

.news-header .index {
  color: #c678dd;
  margin-right: 8px;
}

.news-header .title {
  color: #e5c07b;
  font-weight: bold;
}

.news-meta {
  font-size: 0.9em;
  color: #56b6c2;
  margin-bottom: 12px;
  display: flex;
  gap: 16px;
}

.news-content {
  margin: 12px 0;
  color: #abb2bf;
  font-size: 0.95em;
  line-height: 1.5;
}

.news-content pre {
  white-space: pre-wrap;
  margin: 0;
}

.news-link a {
  color: #61afef;
  text-decoration: none;
  font-family: 'Fira Code', monospace;
}

.news-link a:hover {
  text-decoration: underline;
}

.loading pre, .error pre {
  color: #e06c75;
  margin: 0;
}

.tech-tag {
  color: #98c379;
  font-weight: bold;
}

.output-area {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
</style>
