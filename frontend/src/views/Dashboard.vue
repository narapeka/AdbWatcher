<template>
  <div>
    <h1 class="text-h4 mb-4">ADB Watcher 仪表盘</h1>
    
    <!-- Status Card -->
    <v-card class="mb-4">
      <v-card-title>
        状态
        <v-spacer></v-spacer>
        <v-btn @click="refreshStatus" icon="mdi-refresh" variant="text"></v-btn>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="4">
            <v-sheet class="pa-4 rounded text-center">
              <div class="text-h6">监控状态</div>
              <v-chip 
                :color="getMonitoringStatusColor()" 
                class="mt-2"
              >
                {{ getMonitoringStatusText() }}
              </v-chip>
            </v-sheet>
          </v-col>
          <v-col cols="12" sm="4">
            <v-sheet class="pa-4 rounded text-center">
              <div class="text-h6">设备状态</div>
              <v-chip :color="getConnectionStatusColor()" class="mt-2">
                {{ getConnectionStatusText() }}
              </v-chip>
              <div v-if="status.device_id" class="mt-2 text-body-2">{{ status.device_id }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" sm="4">
            <v-sheet class="pa-4 rounded text-center">
              <div class="text-h6">通知</div>
              <v-chip :color="status.notification_endpoint ? 'success' : 'warning'" class="mt-2">
                {{ status.notification_endpoint ? '已启用' : '已禁用' }}
              </v-chip>
              <div v-if="status.notification_endpoint" class="mt-2 text-body-2 text-truncate">
                {{ status.notification_endpoint }}
              </div>
            </v-sheet>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn 
          color="success" 
          :disabled="status.is_running"
          @click="startMonitoring"
          :loading="loading.start"
        >
          启动
        </v-btn>
        <v-btn 
          color="error" 
          :disabled="!status.is_running"
          @click="stopMonitoring"
          :loading="loading.stop"
        >
          停止
        </v-btn>
        <v-btn 
          color="warning" 
          @click="restartMonitoring"
          :loading="loading.restart"
        >
          重启
        </v-btn>
      </v-card-actions>
    </v-card>
    
    <!-- Log Viewer Card -->
    <v-card>
      <v-card-title>
        实时日志查看器
        <v-spacer></v-spacer>
        <v-btn @click="refreshLogs" icon="mdi-refresh" variant="text"></v-btn>
      </v-card-title>
      <v-card-text>
        <v-sheet 
          class="overflow-y-auto log-container"
          height="400"
          ref="logContainer"
        >
          <div v-if="logs.length === 0" class="text-center pa-4">
            暂无日志。启动监控以查看日志。
          </div>
          <div v-else class="log-content px-4 py-2">
            <div v-for="(log, index) in logs" :key="index" class="log-entry mb-4">
              <div class="log-timestamp text-caption text-grey">{{ log.timestamp }}</div>
              <div class="log-original">{{ log.original_event }}</div>
              <div class="log-mapped text-subtitle-1 text-primary font-weight-medium mt-1">{{ log.mapped_path }}</div>
              <div v-if="log.notification_status" class="log-notification" :class="getNotificationStatusClass(log.notification_status)">
                <v-icon size="small" :color="getNotificationIconColor(log.notification_status)" class="mr-1">
                  {{ getNotificationIcon(log.notification_status) }}
                </v-icon>
                通知: {{ log.notification_status }}
              </div>
            </div>
          </div>
        </v-sheet>
      </v-card-text>
      <v-card-actions>
        <v-switch v-model="autoRefresh" label="自动刷新日志"></v-switch>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="refreshLogs" :loading="loading.logs">
          刷新日志
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script>
import api from '../services/api.js'

export default {
  name: 'Dashboard',
  data() {
    return {
      status: {
        is_running: false,
        device_connected: false,
        device_id: null,
        notification_enabled: false,
        notification_endpoint: null
      },
      logs: [],
      autoRefresh: true,
      loading: {
        start: false,
        stop: false,
        restart: false,
        logs: false
      },
      refreshInterval: null
    }
  },
  mounted() {
    // Initialize the page
    this.refreshStatus()
    this.refreshLogs()
    
    // Set up auto-refresh
    this.setupAutoRefresh()
  },
  beforeUnmount() {
    // Clear interval when component is destroyed
    this.clearRefreshInterval()
  },
  watch: {
    autoRefresh(newVal) {
      if (newVal) {
        this.setupAutoRefresh()
      } else {
        this.clearRefreshInterval()
      }
    }
  },
  methods: {
    setupAutoRefresh() {
      // Clear any existing interval
      this.clearRefreshInterval()
      
      // Set up new interval if auto-refresh is enabled
      if (this.autoRefresh) {
        this.refreshInterval = setInterval(() => {
          if (this.status.is_running) {
            this.refreshLogs()
          }
          this.refreshStatus()
        }, 3000) // Refresh every 3 seconds
      }
    },
    
    clearRefreshInterval() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval)
        this.refreshInterval = null
      }
    },
    
    async refreshStatus() {
      try {
        const response = await api.getStatus()
        this.status = response.data
      } catch (error) {
        console.error('Error fetching status:', error)
      }
    },
    
    async refreshLogs() {
      this.loading.logs = true
      try {
        const response = await api.getFilteredLogs()
        this.logs = response.data
        
        // Scroll to bottom of log container
        this.$nextTick(() => {
          if (this.$refs.logContainer) {
            this.$refs.logContainer.scrollTop = this.$refs.logContainer.scrollHeight
          }
        })
      } catch (error) {
        console.error('Error fetching logs:', error)
      } finally {
        this.loading.logs = false
      }
    },
    
    async startMonitoring() {
      this.loading.start = true
      try {
        await api.startMonitoring()
        // Wait a moment for the service to start
        setTimeout(() => {
          this.refreshStatus()
          this.refreshLogs()
          this.loading.start = false
        }, 1000)
      } catch (error) {
        console.error('Error starting monitoring:', error)
        this.loading.start = false
      }
    },
    
    async stopMonitoring() {
      this.loading.stop = true
      try {
        await api.stopMonitoring()
        // Refresh status
        setTimeout(() => {
          this.refreshStatus()
          this.refreshLogs()
          this.loading.stop = false
        }, 1000)
      } catch (error) {
        console.error('Error stopping monitoring:', error)
        this.loading.stop = false
      }
    },
    
    async restartMonitoring() {
      this.loading.restart = true
      try {
        await api.restartMonitoring()
        // Wait a moment for the service to restart
        setTimeout(() => {
          this.refreshStatus()
          this.refreshLogs()
          this.loading.restart = false
        }, 2000)
      } catch (error) {
        console.error('Error restarting monitoring:', error)
        this.loading.restart = false
      }
    },

    getNotificationStatusClass(status) {
      if (status.includes('success') || status.includes('Successfully')) {
        return 'text-success';
      } else if (status.includes('Failed')) {
        return 'text-error';
      } else {
        return 'text-warning';
      }
    },

    getNotificationIconColor(status) {
      if (status.includes('success') || status.includes('Successfully')) {
        return 'success';
      } else if (status.includes('Failed')) {
        return 'error';
      } else {
        return 'warning';
      }
    },

    getNotificationIcon(status) {
      if (status.includes('success') || status.includes('Successfully')) {
        return 'mdi-check-circle';
      } else if (status.includes('Failed')) {
        return 'mdi-alert-circle';
      } else if (status.includes('duplicate')) {
        return 'mdi-content-duplicate';
      } else {
        return 'mdi-information';
      }
    },

    getMonitoringStatusColor() {
      if (this.status.monitoring_failed) {
        return 'warning'; // Yellow for abnormal state
      } else if (this.status.is_running) {
        return 'success'; // Green for running
      } else {
        return 'error'; // Red for stopped
      }
    },

    getMonitoringStatusText() {
      if (this.status.monitoring_failed) {
        if (!this.status.device_connected) {
          return '设备连接丢失'; // Device connection lost
        }
        return '异常'; // Abnormal state
      } else if (this.status.is_running) {
        return '运行中'; // Running
      } else {
        return '已停止'; // Stopped
      }
    },
    
    getConnectionStatusColor() {
      if (this.status.device_connected) {
        return 'success'; // Green for connected
      } else if (this.status.monitoring_failed) {
        return 'error'; // Red for disconnected and failed
      } else {
        return 'warning'; // Yellow for disconnected but not failed yet
      }
    },
    
    getConnectionStatusText() {
      if (this.status.device_connected) {
        return '已连接'; // Connected
      } else {
        return '未连接'; // Not connected
      }
    }
  }
}
</script>

<style scoped>
.log-container {
  background-color: #1e1e1e;
  font-family: monospace;
  border-radius: 4px;
}

.log-content {
  white-space: pre-wrap;
  word-break: break-all;
}

.log-entry {
  border-bottom: 1px solid #333;
  padding-bottom: 8px;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-original {
  color: #e0e0e0;
}

.log-mapped {
  color: #4caf50;
  font-weight: bold;
}

.log-notification {
  font-size: 0.9em;
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
}

.text-success {
  color: #4caf50 !important;
}

.text-error {
  color: #f44336 !important;
}

.text-warning {
  color: #ff9800 !important;
}
</style> 