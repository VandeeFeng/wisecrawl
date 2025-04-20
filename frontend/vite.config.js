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
    
    // Get today's date at midnight for comparison
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    
    // Sort files by how close their date is to today
    jsonFiles.sort((a, b) => {
      const getDateDiff = filename => {
        const match = filename.match(/processed_news_(\d{4}-\d{2}-\d{2})/)
        if (match) {
          const fileDate = new Date(match[1])
          // Return absolute difference in days
          return Math.abs(fileDate.getTime() - today.getTime())
        }
        return Infinity
      }
      
      return getDateDiff(a) - getDateDiff(b)
    })
    
    // Among files with the closest date, get the latest one by time
    const closestDate = jsonFiles[0].match(/processed_news_(\d{4}-\d{2}-\d{2})/)[1]
    const filesFromClosestDate = jsonFiles.filter(file => file.includes(closestDate))
    
    // Sort by time for files from the same date
    filesFromClosestDate.sort((a, b) => {
      const getTimestamp = filename => {
        const match = filename.match(/processed_news_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.json/)
        if (match) {
          const dateStr = match[1].replace(/_/g, 'T').replace(/-/g, ':')
          return new Date(dateStr).getTime()
        }
        return 0
      }
      
      return getTimestamp(b) - getTimestamp(a)
    })
    
    // Return path to the latest file from the closest date
    const latestFile = filesFromClosestDate[0]
    console.log(`Selected news file from ${closestDate}: ${latestFile}`)
    return path.join(outputDir, latestFile)
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
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            const jsonPath = getLatestJsonFile()
            
            if (!jsonPath) {
              res.writeHead(500, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ error: 'No news data files found' }))
              return
            }
            
            try {
              const content = fs.readFileSync(jsonPath, 'utf-8')
              const data = JSON.parse(content)
              console.log(`Serving latest news file: ${path.basename(jsonPath)}`)
              res.writeHead(200, {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(content)
              })
              res.end(content)
            } catch (error) {
              console.error('Error reading news data:', error)
              res.writeHead(500, { 'Content-Type': 'application/json' })
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
