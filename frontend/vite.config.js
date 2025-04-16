import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'

// Get project root path
const projectRoot = path.resolve(__dirname, '..')

// Function to get the latest JSON file from the processed_output directory
function getLatestJsonFile() {
  const outputDir = path.join(projectRoot, 'data/processed_output')
  
  try {
    // Get all files in the directory
    const files = fs.readdirSync(outputDir)
    
    // Filter for JSON files that match the pattern
    const jsonFiles = files.filter(file => 
      file.startsWith('processed_news_') && file.endsWith('.json')
    )
    
    if (jsonFiles.length === 0) {
      console.error('No JSON files found in the output directory')
      return null
    }
    
    // Sort files by timestamp in filename (newest first)
    jsonFiles.sort((a, b) => {
      // Extract timestamp from filename: processed_news_YYYY-MM-DD_HH-MM-SS.json
      const getTimestamp = filename => {
        const match = filename.match(/processed_news_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.json/)
        if (match) {
          // Convert date format to something JS can parse
          const dateStr = match[1].replace(/_/g, 'T').replace(/-/g, ':')
          return new Date(dateStr).getTime()
        }
        return 0
      }
      
      return getTimestamp(b) - getTimestamp(a)
    })
    
    // Return path to the latest file
    return path.join(outputDir, jsonFiles[0])
  } catch (error) {
    console.error('Error reading output directory:', error)
    return null
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api/news': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/news/, ''),
        configure: (proxy, options) => {
          // Here we can intercept the request and directly return local JSON file content
          proxy.on('proxyReq', (proxyReq, req, res) => {
            const jsonPath = getLatestJsonFile()
            
            if (!jsonPath) {
              res.writeHead(500)
              res.end(JSON.stringify({ error: 'No news data files found' }))
              return true
            }
            
            try {
              const content = fs.readFileSync(jsonPath, 'utf-8')
              console.log(`Serving latest news file: ${path.basename(jsonPath)}`)
              res.writeHead(200, {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(content)
              })
              res.end(content)
            } catch (error) {
              console.error('Error reading news data:', error)
              res.writeHead(500)
              res.end(JSON.stringify({ error: 'Failed to load news data' }))
            }
            
            // Terminate the original request
            return true
          })
        }
      }
    }
  }
})
