<template>
  <v-app>
    <v-app-bar app color="primary">
      <v-app-bar-title>ADB Watcher</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-btn to="/" text>仪表盘</v-btn>
      <v-btn to="/config" text>配置</v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <v-footer app>
      <div class="text-center w-100">
        <span>&copy; {{ new Date().getFullYear() }} ADB Watcher</span>
      </div>
    </v-footer>
  </v-app>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {}
  }
}
</script>

<style>
/* Global styles here */
</style> 