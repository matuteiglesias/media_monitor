<script setup lang="ts">defineProps<{ status: 'implemented' | 'validated' | 'ready' | 'unoperated' }>()</script>
<template><span class="status-badge" :data-status="status"><span aria-hidden="true" class="status-dot" /> <slot>{{ status }}</slot></span></template>
