import axios from 'axios'

// Create axios instance with base URL
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Add retry logic for initial server unavailability
api.interceptors.response.use(
  response => response, 
  async error => {
    const { config } = error;
    
    // Don't retry if we already tried or if it's not a connection error
    if (config?._retryCount >= 3 || !error.message?.includes('ECONNREFUSED')) {
      return Promise.reject(error);
    }
    
    // Initialize retry count if it doesn't exist
    config._retryCount = config._retryCount || 0;
    config._retryCount++;
    
    // Wait before retrying
    const delay = config._retryCount * 500; // Increasing backoff: 500ms, 1000ms, 1500ms
    
    console.log(`API not ready yet, retrying in ${delay}ms (attempt ${config._retryCount})`);
    
    return new Promise(resolve => {
      setTimeout(() => resolve(api(config)), delay);
    });
  }
);

// API methods
export default {
  // Status
  getStatus() {
    return api.get('/status')
  },

  // Control
  startMonitoring() {
    return api.post('/start')
  },

  stopMonitoring() {
    return api.post('/stop')
  },

  restartMonitoring() {
    return api.post('/restart')
  },

  // Logs
  getLogs(count = 100) {
    return api.get(`/logs?count=${count}`)
  },

  getFilteredLogs(count = 50) {
    return api.get(`/filtered_logs?count=${count}`)
  },

  // Configuration
  getConfig() {
    return api.get('/config')
  },

  updateConfig(config) {
    return api.post('/config', { config })
  },

  // Test connections
  testAdbConnection(deviceId = null) {
    const params = deviceId ? { device_id: deviceId } : {}
    return api.post('/test/adb', params)
  },

  testEndpoint(endpoint) {
    return api.post('/test/endpoint', { endpoint })
  }
} 