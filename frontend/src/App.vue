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
          <button @click="fetchNews" class="refresh-btn" :disabled="loading">
            {{ loading ? '[LOADING...]' : '[REFRESH]' }}
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
    const modules = import.meta.glob('./data/*');
    const paths = Object.keys(modules);
    if (paths.length === 0) {
      throw new Error('No data file found');
    }
    // Sort paths by date in filename (descending)
    const latestPath = paths.sort((a, b) => {
      const dateA = a.match(/\d{4}-\d{2}-\d{2}/)?.[0] || '';
      const dateB = b.match(/\d{4}-\d{2}-\d{2}/)?.[0] || '';
      return dateB.localeCompare(dateA);
    })[0];
    const module = await modules[latestPath]();
    news.value = module.default;
  } catch (err) {
    error.value = 'Failed to load news data: ' + err.message;
    console.error('Error loading news:', err);
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
</style>
