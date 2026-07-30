<script setup lang="ts">defineProps<{ title: string; eyebrow: string; href: string }>()</script>
<template><a class="lane-card" :href="href"><small>{{ eyebrow }}</small><strong>{{ title }}</strong><span><slot /></span><b aria-hidden="true">Read dossier →</b></a></template>
