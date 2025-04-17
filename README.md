# WiseCrawl

A fork from https://github.com/tuber0613/hot_news_daily_push

## Project Structure

```
wisecrawl/
├── backend/
│   ├── config/         # Configuration files
│   ├── crawler/        # Web crawling modules
│   ├── data/          # Data storage
│   ├── llm_integration/# LLM integration modules
│   ├── notification/  # Notification services
│   ├── processor/     # Data processing modules
│   ├── tests/        # Test files
│   ├── utils/        # Utility functions
│   └── requirements.txt
├── frontend/
│   ├── public/       # Static assets
│   ├── src/          # Source code
│   └── index.html    # Entry point
└── data/            # Shared data directory
```

## Tech Stack

### Backend
- **Language:** Python
- **Core Libraries:**
  - LangChain - LLM integration framework
  - Newspaper3k - Article extraction
  - Trafilatura - Web content extraction

### Frontend
- **Framework:** Vue.js 3
- **Build Tool:** Vite
- **UI Framework:** WebTUI CSS

## Features
- Web crawling and content extraction
- LLM-powered content processing
- News aggregation and summarization
- Modern web interface
- Notification system