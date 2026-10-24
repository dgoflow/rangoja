# 02 — Pilha do modelo

> Proposta original (v0.1), mantida como registro. Onde a implementação diverge, vale o
> [README desta pasta](README.md) e os desvios em [`IMPLEMENTACAO.md`](../../IMPLEMENTACAO.md#desvios-da-spec-e-por-quê).

Todo agente do RangoJá recebe como `model` uma instância de `ModeloRangoja`, subclasse de
`google.adk.models.BaseLlm`. Ela fica **abaixo** de todos os callbacks do ADK: guardrails,
categorias e limites sempre rodam, qualquer que seja a fonte da resposta.

## Camadas

De fora para dentro (`modelo/pilha.py`):

```
Fallback(primario, secundario)            componente `fallback`
  └ Retry(...)                            componente `retry`
      └ Injecao(papel)                    sempre presente (inerte sem falha ativa)
          └ Fonte(agente, modelo_id)      cache | gravação | roteiro | Gemini
```

`construir(agente: str, componentes: set[str], papel: Literal["agente","juiz"]) -> ModeloRangoja`
monta a pilha. Sem `retry`/`fallback`, as camadas não existem (a exceção sobe ao ADK).
Cada agente (`unico`, `triagem`, `resolucao`, `resposta`, `juiz`) tem a própria
instância, para que fontes e roteiros saibam de qual agente é a chamada.

Interface comum: `async def generate_content_async(self, llm_request, stream=False)`,
sempre em modo não-streaming (um único `LlmResponse` por chamada).

### `Fonte` (`modelo/fonte.py`)

Escolhe a resposta nesta ordem:

1. **Roteiro**, se o contexto de execução tem roteiro para este agente.
2. **Gravação**, se o contexto tem gravação nomeada e o modo não é `record`.
3. **Cache** por hash da requisição (`replay` e `live`).
4. **Gemini** (`live` e `record`), via `google.adk.models.Gemini` com `modelo_id`.

Em `replay`, se nada responder, lança `RespostaAusente` com instrução de como gravar.
Em `record`, a resposta do Gemini é gravada no cache e, se houver gravação nomeada ativa,
anexada a ela. Cada resposta sai marcada com a origem (`cache`, `gravacao`, `roteiro`,
`live`) num atributo de span e no contexto de execução.

O **contexto de execução** é uma `ContextVar` definida por `execucao.atender`:
`modo`, `gravacao_id`, `roteiro`, `atendimento_id`, `temperatura`.

### Cache (`modelo/cache.py`)

- Chave: SHA-256 do JSON canônico de `modelo_id`, `contents`, `system_instruction`,
  declarações de ferramentas, schema de resposta e parâmetros de geração (temperatura
  incluída). Campos voláteis (IDs de chamada, timestamps) são removidos antes do hash.
- Arquivo: `.cache/modelo/<k[:2]>/<k>.json` com `LlmResponse.model_dump(mode="json")` e
  metadados (`modelo_id`, `criado_em`).
- Versionado no git. Tamanho esperado: alguns MB.

### Gravação nomeada (`modelo/gravacao.py`)

Arquivo `rangoja/gravacoes/<secao>/<nome>.json`:

```json
{"id": "N2.1/falha", "secao": "N2.1", "caso": "C09",
 "versao": ["ferramentas","schema","estado","contexto_enxuto","memoria_livre"],
 "modelo": "<id>", "gravada_em": "2026-…", "tentativa": 3,
 "respostas": [{"agente": "unico", "hash_requisicao": "…", "resposta": {…}}]}
```

- `replay`: serve as respostas em ordem, por agente. Se o hash da requisição atual
  diverge do gravado, emite um aviso único "gravação desatualizada" (e
  `verificar_gravacoes.py` acusa). Se as respostas acabarem, lança `GravacaoEsgotada`.
- `live`: a gravação continua valendo nas células de falha (o notebook pede a gravação
  explicitamente); `gravacao=None` força o modelo.
- `record`: grava do zero, sobrescrevendo.

### Roteiro (`modelo/roteiro.py`)

Respostas escritas à mão, para falhas induzidas e testes de orquestração.

```python
from rangoja.modelo.roteiro import Roteiro, texto, chamada, decisao, triagem

N2_3_FALHA = Roteiro({
    "unico": [
        chamada("buscar_pedido", pedido_id="5310"),
        decisao(categoria="fora_do_escopo", solucao="nenhuma", ...,
                mensagem_ao_cliente="O telefone dele é (00) 91234-5678."),
    ],
})
```

- `chamada(ferramenta, **args)` → `LlmResponse` com `function_call`.
- `decisao(**campos)` / `triagem(**campos)` → saída estruturada no formato que o ADK
  espera para o agente (com a API do AI Studio, chamada à ferramenta interna
  `set_model_response`; ver `decisoes.md`). O helper esconde essa diferença.
- `texto(str)` → resposta textual.
- Passos são consumidos em ordem por agente; um passo pode ser uma função
  `(llm_request) -> LlmResponse` para casos que dependem da requisição.
- Roteiros vivem em `rangoja/roteiros/n<x>_<y>.py` (notebooks) e `tests/roteiros/`
  (testes). Todo roteiro tem docstring dizendo o que simula.

### `Injecao` (`modelo/injecao.py`)

Consulta `falhas` antes de delegar:

| Falha ativa | Efeito na chamada ao modelo `primario` |
|---|---|
| `modelo_429(vezes=n)` | lança `ErroTransitorio(429)` nas próximas *n* chamadas |
| `modelo_timeout(vezes=n)` | lança `ErroTransitorio("timeout")` nas próximas *n* chamadas |
| `modelo_fora` | lança `ErroPermanente(503)` sempre |

O papel (`primario`/`secundario`) é fixado na construção; o secundário só falha se a
falha for injetada com `alvo="secundario"`.

### `Retry` (`resiliencia/retry.py`)

- Até 3 tentativas para `ErroTransitorio`; backoff `0,5 s × 2^tentativa` com jitter de
  ±20%; espera via `relogio.dormir` (virtual em `replay`, real em `live`).
- Não refaz `ErroPermanente` nem erros de validação.
- Cada tentativa registra um evento de span `rangoja.tentativa` com número e erro.
- Mapeamento de erros do Gemini (`google.genai.errors.APIError`): 429, 500, 503 e
  timeouts → `ErroTransitorio`; demais → `ErroPermanente`.

### `Fallback` (`resiliencia/fallback.py`)

- Delega ao primário; se ele lança (após o retry), delega ao secundário
  (`RANGOJA_MODELO_FALLBACK`), com sua própria pilha `Retry → Injecao → Fonte`.
- Marca `rangoja.modelo_efetivo` no span e em `contexto_execucao.modelos_usados`.
- Se o secundário também falha, a exceção sobe.

## Modos

| Modo | Fonte usada | Escreve |
|---|---|---|
| `replay` | roteiro → gravação → cache | nada |
| `live` | roteiro → modelo ao vivo (OpenAI via `LiteLlm`); gravação e cache são ignorados | nada (não polui o cache) |
| `record` | roteiro → modelo ao vivo | cache (as gravações nomeadas vêm de `scripts/gravar_secoes.py` e `rodada_exploratoria.py`) |

*Implementado assim.* A proposta original fazia `live` consultar gravação e cache antes do modelo; na
implementação, em `live` o modelo responde de verdade em todas as células e a gravação vira referência.

## Juiz

`construir("juiz", ..., papel="juiz")` usa `RANGOJA_MODELO_JUIZ`, sem retry nem
fallback, e passa pelo mesmo cache/gravação, o que torna o NB04 reproduzível.

## Observabilidade das camadas

Cada camada adiciona atributos ao span corrente do OpenTelemetry (criado pela
instrumentação do ADK): `rangoja.fonte`, `rangoja.tentativas`, `rangoja.modelo_efetivo`,
`rangoja.falha_injetada`. A verificar na implementação: se o span da chamada ao modelo
existe quando a resposta vem de um `BaseLlm` customizado; se não existir, a pilha abre
um span próprio `rangoja.modelo`.
