<template>
  <div>
    <h1 class="text-h4 mb-4">配置</h1>
    
    <v-alert
      v-if="alert.show"
      :type="alert.type"
      :text="alert.message"
      class="mb-4"
      closable
      @click:close="alert.show = false"
    ></v-alert>
    
    <v-tabs v-model="activeTab" bg-color="primary">
      <v-tab value="general">常规</v-tab>
      <v-tab value="adb">ADB 设置</v-tab>
      <v-tab value="notification">通知</v-tab>
      <v-tab value="mapping">路径映射</v-tab>
    </v-tabs>
    
    <v-card class="mt-4">
      <v-card-text>
        <v-window v-model="activeTab">
          <!-- General Tab -->
          <v-window-item value="general">
            <v-form @submit.prevent>
              <div class="d-flex align-center mb-4 mt-8">
                <h3 class="text-h6">常规设置</h3>
              </div>
              
              <v-select
                v-model="config.general.log_level"
                :items="logLevels"
                label="日志级别"
                variant="outlined"
                class="mb-4"
              ></v-select>
              
              <v-text-field
                v-model.number="config.general.cooldown_seconds"
                type="number"
                label="事件冷却时间（秒）"
                hint="防止重复事件的冷却时间"
                variant="outlined"
              ></v-text-field>
            </v-form>
          </v-window-item>
          
          <!-- ADB Settings Tab -->
          <v-window-item value="adb">
            <v-form @submit.prevent>
              <div class="d-flex align-center justify-space-between mb-4 mt-8">
                <h3 class="text-h6">ADB 设置</h3>
                <v-btn 
                  color="primary" 
                  @click="testAdbConnection"
                  :loading="testAdb.loading"
                >
                  测试 ADB 连接
                </v-btn>
              </div>
              
              <v-alert
                v-if="testAdb.result"
                :type="testAdb.result.status === 'success' ? 'success' : 'error'"
                :text="testAdb.result.message"
                class="mb-4"
              ></v-alert>
              
              <v-text-field
                v-model="config.adb.device_id"
                label="ADB 设备 ID"
                hint="设备 ID、IP:PORT，或留空使用第一个可用设备"
                variant="outlined"
                class="mb-4"
                :rules="[deviceIdRule]"
              ></v-text-field>
              
              <v-text-field
                v-model="config.adb.logcat.tags"
                label="Logcat 标签"
                hint="过滤 logcat 的标签（例如 ActivityTaskManager:I）"
                variant="outlined"
                class="mb-4"
              ></v-text-field>
              
              <v-text-field
                v-model="config.adb.logcat.pattern"
                label="Logcat 匹配模式"
                hint="logcat 正则过滤模式（例如 com.doopoodigital.dpplayer.app）"
                variant="outlined"
                class="mb-4"
              ></v-text-field>
              
              <v-text-field
                v-model="config.adb.logcat.buffer"
                label="Logcat 缓冲区"
                hint="使用的 logcat 缓冲区（system、main、events 等）"
                variant="outlined"
                class="mb-4"
              ></v-text-field>
            </v-form>
          </v-window-item>
          
          <!-- Notification Tab -->
          <v-window-item value="notification">
            <v-form @submit.prevent>
              <div class="d-flex align-center justify-space-between mb-4 mt-8">
                <h3 class="text-h6">通知设置</h3>
                <v-btn 
                  color="primary" 
                  @click="testNotificationEndpoint"
                  :loading="testEndpoint.loading"
                  :disabled="!config.notification.endpoint"
                >
                  测试端点
                </v-btn>
              </div>
              
              <v-alert
                v-if="testEndpoint.result"
                :type="testEndpoint.result.status === 'success' ? 'success' : 'error'"
                :text="testEndpoint.result.message"
                class="mb-4"
              ></v-alert>
              
              <v-text-field
                v-model="config.notification.endpoint"
                label="通知端点"
                hint="视频播放时通知的 HTTP 端点（留空禁用通知）"
                variant="outlined"
                class="mb-4"
              ></v-text-field>
              
              <v-text-field
                v-model.number="config.notification.timeout_seconds"
                type="number"
                label="请求超时（秒）"
                hint="通知请求的超时时间"
                variant="outlined"
                class="mb-4"
              ></v-text-field>
            </v-form>
          </v-window-item>
          
          <!-- Path Mappings Tab -->
          <v-window-item value="mapping">
            <div class="d-flex align-center mb-4 mt-8">
              <h3 class="text-h6">路径映射</h3>
            </div>
            
            <div v-if="!config.mapping_paths || config.mapping_paths.length === 0" class="text-center my-4">
              <p>尚未配置路径映射。请在下方添加映射。</p>
            </div>
            
            <v-list v-else>
              <v-list-item v-for="(mapping, index) in config.mapping_paths" :key="index">
                <v-list-item-title>
                  <strong>源路径:</strong> {{ mapping.source }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  <strong>目标路径:</strong> {{ mapping.target }}
                </v-list-item-subtitle>
                <template v-slot:append>
                  <v-btn icon="mdi-delete" variant="text" color="error" @click="removeMappingPath(index)"></v-btn>
                </template>
              </v-list-item>
            </v-list>
            
            <v-divider class="my-4"></v-divider>
            
            <!-- Add New Mapping -->
            <v-form @submit.prevent="addMappingPath" class="mt-8">
              <v-row>
                <v-col cols="12" md="5">
                  <v-text-field
                    v-model="newMapping.source"
                    label="源路径"
                    hint="要匹配的源路径"
                    variant="outlined"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="5">
                  <v-text-field
                    v-model="newMapping.target"
                    label="目标路径"
                    hint="替换后的目标路径"
                    variant="outlined"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="2" class="d-flex align-center">
                  <v-btn 
                    color="primary" 
                    block 
                    @click="addMappingPath" 
                    :disabled="!newMapping.source || !newMapping.target"
                  >
                    添加
                  </v-btn>
                </v-col>
              </v-row>
            </v-form>
          </v-window-item>
        </v-window>
      </v-card-text>
      
      <v-divider></v-divider>
      
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="error" @click="resetConfig">重置</v-btn>
        <v-btn color="primary" @click="saveConfig" :loading="saving">保存配置</v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script>
import api from '../services/api.js'

export default {
  name: 'Config',
  data() {
    return {
      activeTab: 'general',
      config: {
        general: {
          log_level: 'INFO',
          cooldown_seconds: 3,
          enable_watcher: true
        },
        adb: {
          device_id: null,
          logcat: {
            pattern: '',
            buffer: 'system',
            tags: 'ActivityTaskManager:I'
          }
        },
        notification: {
          endpoint: null,
          timeout_seconds: 10
        },
        logging: {
          file: 'player_watcher.log'
        },
        mapping_paths: []
      },
      originalConfig: null,
      logLevels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
      saving: false,
      alert: {
        show: false,
        type: 'success',
        message: ''
      },
      newMapping: {
        source: '',
        target: ''
      },
      testAdb: {
        loading: false,
        result: null
      },
      testEndpoint: {
        loading: false,
        result: null
      }
    }
  },
  async mounted() {
    await this.loadConfig()
  },
  methods: {
    deviceIdRule(value) {
      if (!value) return true // Allow empty value
      const ipPortRegex = /^(\d{1,3}\.){3}\d{1,3}(:\d{1,5})?$/
      return ipPortRegex.test(value) || '请输入有效的IP地址格式 (例如: 192.168.1.100 或 192.168.1.100:5555)'
    },
    async loadConfig() {
      try {
        const response = await api.getConfig()
        this.config = response.data.config
        
        // Store original config for reset functionality
        this.originalConfig = JSON.parse(JSON.stringify(this.config))
        
        // Ensure mapping_paths is an array
        if (!this.config.mapping_paths) {
          this.config.mapping_paths = []
        }
      } catch (error) {
        console.error('Error loading configuration:', error)
        this.showAlert('error', 'Failed to load configuration')
      }
    },
    
    async saveConfig() {
      this.saving = true
      try {
        const response = await api.updateConfig(this.config)
        if (response.data.success) {
          this.showAlert('success', 'Configuration saved successfully')
          // Update the original config
          this.originalConfig = JSON.parse(JSON.stringify(this.config))
        } else {
          this.showAlert('error', 'Failed to save configuration')
        }
      } catch (error) {
        console.error('Error saving configuration:', error)
        this.showAlert('error', 'Failed to save configuration')
      } finally {
        this.saving = false
      }
    },
    
    resetConfig() {
      if (this.originalConfig) {
        this.config = JSON.parse(JSON.stringify(this.originalConfig))
        this.showAlert('info', 'Configuration reset to last saved state')
      }
    },
    
    showAlert(type, message) {
      this.alert = {
        show: true,
        type,
        message
      }
      
      // Auto-hide after 5 seconds
      setTimeout(() => {
        this.alert.show = false
      }, 5000)
    },
    
    addMappingPath() {
      if (!this.newMapping.source || !this.newMapping.target) {
        return
      }
      
      // Ensure mapping_paths is an array
      if (!this.config.mapping_paths) {
        this.config.mapping_paths = []
      }
      
      // Add new mapping
      this.config.mapping_paths.push({
        source: this.newMapping.source,
        target: this.newMapping.target
      })
      
      // Clear form
      this.newMapping = {
        source: '',
        target: ''
      }
    },
    
    removeMappingPath(index) {
      this.config.mapping_paths.splice(index, 1)
    },
    
    async testAdbConnection() {
      this.testAdb.loading = true
      this.testAdb.result = null
      
      try {
        const deviceId = this.config.adb.device_id || null
        
        // Validate device ID format if provided
        if (deviceId && !this.deviceIdRule(deviceId)) {
          this.testAdb.result = {
            status: 'error',
            message: '无效的IP地址格式，请使用 IP 或 IP:PORT 格式 (例如: 192.168.1.100 或 192.168.1.100:5555)'
          }
          return
        }
        
        const response = await api.testAdbConnection(deviceId)
        this.testAdb.result = response.data
      } catch (error) {
        console.error('Error testing ADB connection:', error)
        this.testAdb.result = {
          status: 'error',
          message: 'Error testing connection: ' + (error.response?.data?.message || error.message)
        }
      } finally {
        this.testAdb.loading = false
      }
    },
    
    async testNotificationEndpoint() {
      this.testEndpoint.loading = true
      this.testEndpoint.result = null
      
      try {
        const response = await api.testEndpoint(this.config.notification.endpoint)
        this.testEndpoint.result = response.data
      } catch (error) {
        console.error('Error testing endpoint:', error)
        this.testEndpoint.result = {
          status: 'error',
          message: 'Error testing endpoint: ' + (error.response?.data?.message || error.message)
        }
      } finally {
        this.testEndpoint.loading = false
      }
    }
  }
}
</script>

<style scoped>
/* Add margin to first form element in each tab */
.v-window-item :first-child .v-input:first-of-type {
  margin-top: 24px;
}
</style> 