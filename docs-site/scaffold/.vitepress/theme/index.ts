import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import StatusBadge from './components/StatusBadge.vue'
import LaneCard from './components/LaneCard.vue'
import ArtifactFlow from './components/ArtifactFlow.vue'
import MermaidDiagram from './components/MermaidDiagram.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('StatusBadge', StatusBadge)
    app.component('LaneCard', LaneCard)
    app.component('ArtifactFlow', ArtifactFlow)
    app.component('MermaidDiagram', MermaidDiagram)
  }
} satisfies Theme
