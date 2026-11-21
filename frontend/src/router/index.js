import { createRouter, createWebHistory } from 'vue-router'

export const paginas = [
  {
    path: '/',
    nome: 'Visão geral',
    titulo: 'Visão geral',
    descricao: 'Resumo da base processada e dos resultados produzidos pelos algoritmos.',
    component: () => import('../views/OverviewView.vue'),
  },
  {
    path: '/rede',
    nome: 'Exploração da rede',
    titulo: 'Exploração da rede',
    descricao: 'Navegue pelas contas e transferências em um subconjunto da rede financeira.',
    component: () => import('../views/NetworkView.vue'),
  },
  {
    path: '/ciclos',
    nome: 'Ciclos',
    titulo: 'Detecção de ciclos',
    descricao: 'Sequências de transferências que retornam à conta de origem.',
    component: () => import('../views/CyclesView.vue'),
  },
  {
    path: '/grau',
    nome: 'Grau',
    titulo: 'Análise de grau',
    descricao: 'Compare as conexões de entrada e saída e identifique comportamentos atípicos.',
    component: () => import('../views/DegreeView.vue'),
  },
  {
    path: '/centralidade',
    nome: 'Centralidade',
    titulo: 'Centralidade',
    descricao: 'Identifique contas que atuam como intermediárias relevantes na rede.',
    component: () => import('../views/CentralityView.vue'),
  },
  {
    path: '/componentes',
    nome: 'Componentes conexos',
    titulo: 'Componentes conexos',
    descricao: 'Explore grupos de contas conectadas e a densidade de suas relações.',
    component: () => import('../views/ComponentsView.vue'),
  },
]

export default createRouter({
  history: createWebHistory(),
  routes: [
    ...paginas.map(({ path, titulo, descricao, component }) => ({
      path,
      component,
      meta: { titulo, descricao },
    })),
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
