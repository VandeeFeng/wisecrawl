<template>
  <div class="terminal-container">
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
          <pre class="title-pre">
 _    _ _          ____                    _ 
| |  | (_)        / ___|_ __ __ ___      _| |
| |  | |_ ___  ___| |   | '__/ _' \ \ /\ / / |
| |/\| | / __|/ _ \ |___| | | (_| |\ V  V /| |
\  /\  / \__ \  __/\____|_|  \__,_| \_/\_/ |_|
 \/  \/|_|___/\___|                           
          </pre>
        </div>

        <div class="command-section box box--double">
          <div class="function-buttons">
            <button @click="fetchNews" class="function-btn refresh-btn" :disabled="loading">
              {{ loading ? '[LOADING...]' : '[REFRESH]' }}
            </button>
            <a href="/feed.xml" target="_blank" class="rss-link">
              <button class="function-btn">[RSS]</button>
            </a>
          </div>
          
          <div class="command-line">
            <span class="prompt">$</span>
            <div class="filters">
              <button 
                v-for="(source, index) in visibleSources" 
                :key="source"
                :class="{ active: selectedSource === source }"
                @click="setSource(source)"
                class="button"
              >
                {{ source === 'all' ? '[ALL]' : '[' + source.toUpperCase() + ']' }}
              </button>
              
              <button 
                v-if="!isMobile && sources.length > maxVisibleSources"
                @click="toggleExpand"
                class="expand-btn button button--primary"
              >
                {{ isExpanded ? '[-]' : `[+${sources.length - maxVisibleSources}]` }}
              </button>
              
              <div class="expand-btn-wrapper" v-if="isMobile && sources.length > maxVisibleSources">
                <button 
                  @click="toggleExpand"
                  class="expand-btn button button--primary"
                >
                  {{ isExpanded ? '[-] COLLAPSE' : `[+${sources.length - maxVisibleSources}] MORE` }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="output-area">
          <div v-if="loading" class="loading box box--single">
            <pre>
Loading news feed...
            </pre>
          </div>
          
          <div v-else-if="error" class="error box box--single box--error">
            <pre>
ERROR: {{ error }}
Type 'refresh' to try again.
            </pre>
          </div>
          
          <div v-else class="news-list">
            <div v-for="(item, index) in filteredNews" :key="index" class="news-item box box--double">
              <div class="news-header">
                <span class="index">[{{ index + 1 }}]</span>
                <span class="title type--headline">{{ item.title }}</span>
              </div>
              <div class="news-meta">
                <span class="source type--code">src://{{ item.source }}</span>
                <span class="hot type--code" v-if="item.hot">heat={{ formatHot(item.hot) }}</span>
                <span class="time type--code" v-if="item.timestamp">time={{ formatTime(item.timestamp) }}</span>
                <span class="tech-tag" v-if="item.is_tech">[TECH]</span>
              </div>
              <div class="news-content" v-if="item.content || item.desc || item.summary">
                <pre>{{ (item.summary !== '[Summary cannot be generated: Insufficient content or source information]' ? item.summary : '') || item.content}}</pre>
              </div>
              <div class="news-link">
                <a :href="item.url" target="_blank" class="type--link">$ curl {{ item.url }}</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeMount, watch } from 'vue';

const news = ref([]);
const loading = ref(true);
const error = ref(null);
const selectedSource = ref('all');
const isExpanded = ref(false);
const maxVisibleSources = ref(20);
const isMobile = ref(false);
const scrollPositions = ref({}); // 存储各个来源的滚动位置

const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768;
  maxVisibleSources.value = isMobile.value ? 5 : 15;
};

const sources = computed(() => {
  const uniqueSources = new Set(news.value.map(item => item.source));
  return ['all', ...uniqueSources];
});

const visibleSources = computed(() => {
  if (isExpanded.value) {
    return sources.value;
  }
  return sources.value.slice(0, maxVisibleSources.value);
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
  const outputArea = document.querySelector('.output-area');
  if (outputArea && selectedSource.value) {
    scrollPositions.value[selectedSource.value] = outputArea.scrollTop;
  }
  
  selectedSource.value = source;
  
  setTimeout(() => {
    if (outputArea) {
      outputArea.scrollTop = scrollPositions.value[source] || 0;
    }
  }, 10);
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

// Watch for changes to expanded state to scroll to bottom of filters when expanded
watch(isExpanded, (newValue) => {
  if (newValue && isMobile.value) {
    // Use setTimeout to allow DOM to update before scrolling
    setTimeout(() => {
      const filtersElement = document.querySelector('.filters');
      if (filtersElement) {
        filtersElement.scrollTop = 0; // Scroll to top when expanded
      }
    }, 10);
  }
});

onBeforeMount(() => {
  checkMobile();
  window.addEventListener('resize', checkMobile);
  isExpanded.value = false;
});

onMounted(() => {
  fetchNews();
});
</script>

<!-- No internal styles - all moved to style.css -->
