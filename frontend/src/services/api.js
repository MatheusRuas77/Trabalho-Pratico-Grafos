import { onScopeDispose, reactive, ref, watch } from 'vue'

export const requisicoes = reactive(new Map())

export function url(path, params) {
  return '/api/' + path + (params ? '?' + new URLSearchParams(params) : '')
}

export function useApi(
  endpoint,
  atraso = 0,
  statusLocal = false,
  preservarAoRecarregar = false,
) {
  const dados = ref(null)
  const erro = ref('')
  const carregando = ref(false)
  const tentativa = ref(0)
  const recarregar = () => tentativa.value++
  const chave = Symbol()

  if (!statusLocal) {
    requisicoes.set(chave, { erro, carregando, recarregar })
    onScopeDispose(() => requisicoes.delete(chave))
  }

  watch(
    [endpoint, tentativa],
    ([caminho], anterior, onCleanup) => {
      const controller = new AbortController()
      erro.value = ''
      if (!preservarAoRecarregar || caminho !== anterior?.[0]) dados.value = null
      carregando.value = Boolean(caminho)
      if (!caminho) return
      const timer = setTimeout(async () => {
        try {
          const resposta = await fetch(caminho, { signal: controller.signal })
          const json = await resposta.json().catch(() => null)
          if (!resposta.ok || !json) {
            throw new Error(
              typeof json?.detail === 'string'
                ? json.detail
                : 'Não foi possível consultar a API.',
            )
          }
          if (!controller.signal.aborted) dados.value = json
        } catch (error) {
          if (!controller.signal.aborted)
            erro.value =
              error instanceof TypeError ? 'Não foi possível conectar à API.' : error.message
        } finally {
          if (!controller.signal.aborted) carregando.value = false
        }
      }, atraso)
      onCleanup(() => {
        clearTimeout(timer)
        controller.abort()
      })
    },
    { immediate: true },
  )

  return { dados, erro, carregando, recarregar }
}

export function useResultadoEmCalculo(dados, recarregar, pendente) {
  watch(dados, (atual, _, onCleanup) => {
    if (!atual || !pendente(atual)) return
    const timer = setTimeout(recarregar, 30000)
    onCleanup(() => clearTimeout(timer))
  })
}
