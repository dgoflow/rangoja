# 04 — Execução, seções e helpers de notebook

> Proposta original (v0.1), mantida como registro. Onde a implementação diverge, vale o
> [README desta pasta](README.md) e os desvios em [`IMPLEMENTACAO.md`](../../IMPLEMENTACAO.md#desvios-da-spec-e-por-quê).

## `execucao.py`

As funções públicas são síncronas, para funcionar em células do Jupyter (que já têm um
loop rodando). Estratégia, a mesma do `Runner.run` síncrono do ADK: um **thread de fundo
com loop de eventos próprio e persistente** (`execucao._laco`), e as corrotinas são
submetidas com `asyncio.run_coroutine_threadsafe`. Para que `ContextVar`s (contexto de
execução, falhas injetadas) atravessem para o thread, a submissão copia o contexto do
chamador (`contextvars.copy_context()`) e cria a tarefa dentro dele. Cada função tem uma
variante `*_async` (`atender_async`, …) usada pelos testes com `pytest-asyncio`.

### `atender(versao, caso, *, gravacao=None, roteiro=None, cliente_id=None, temperatura=None, run_config=None) -> Atendimento`

1. Resolve `caso` (id ou objeto) e `cliente_id` (padrão: o do caso).
2. Define o contexto de execução (modo, gravação, roteiro, temperatura) e constrói a
   versão (cache por composição).
3. Para cada atendimento do caso (mais de um em `C08`, `C13`):
   - cria sessão (`app_name="rangoja"`, `user_id=cliente_id`) no serviço de sessão
     corrente (em memória ou SQLite da seção);
   - para cada mensagem: sem o componente `estado`, cria uma sessão nova por mensagem;
     roda `runner.run_async(...)`, coleta eventos;
   - se aparecer um evento `adk_request_confirmation`, registra a pendência no `armazem`
     (com `relogio.agora()`), marca `aguardando_aprovacao` e interrompe as mensagens
     restantes.
4. Monta o `Atendimento` do último atendimento; os anteriores vão em `anteriores`.
5. Exceções não tratadas viram `status="erro"` com `erro` preenchido (não sobem), para
   que a célula de falha mostre o resultado.

### `Atendimento`

Campos do contrato (ver `notebooks/README.md`) e mais: `anteriores: list[Atendimento]`,
`erro: str | None`, `pendencia: Pendencia | None`, `modelos_usados: list[str]`.

`status` é derivado nesta precedência: `erro` > `aguardando_aprovacao` >
`encaminhado_seguranca` > `escalado` > `aguardando_cliente` > `concluido`, a partir de
`estado["status"]` (gravado por ferramentas e callbacks) e dos eventos.

`resposta`: v0 → texto final; v1 → `decisao.mensagem_ao_cliente`; sequência → `estado
["resposta"]`; guardrail ou contrato que respondeu no lugar do agente → esse texto.

`_repr_html_` mostra: status, decisão, resposta, trajetória pública em tabela, fonte e
link do trace.

### Demais funções

| Função | Comportamento |
|---|---|
| `continuar(a, mensagem)` | Novo turno na sessão de `a`; devolve novo `Atendimento` |
| `aprovar(a)` | Encontra a confirmação pendente; envia `FunctionResponse(name="adk_request_confirmation", id=<chamada>, response={"confirmed": True})`; com `persistencia`, passa `invocation_id` para retomar; marca a pendência resolvida |
| `recusar(a, motivo)` | Idem com `confirmed: False` e `hint=motivo` |
| `expirar_pendencias()` | Para cada pendência aberta com `relogio.agora() - criada_em > PRAZO_APROVACAO`: `recusar(..., "prazo vencido")`; se o agente não escalou, chama `escalar_para_humano` programaticamente. Devolve os atendimentos afetados |
| `reiniciar_runner()` | Descarta runner, versões construídas e serviço de sessão em memória (as sessões em memória somem); mantém o SQLite da seção e o `armazem`. Atendimentos antigos continuam válidos como referência (`sessao_id`, `invocation_id`) |

## `trajetoria.py`

```python
@dataclass(frozen=True)
class Chamada:
    agente: str; ferramenta: str; args: dict; resultado: dict | None
    erro: str | None; efetiva: bool    # False se bloqueada, pendente de confirmação ou erro
```

- `publicas(trajetoria)`: remove `set_model_response`, `adk_request_confirmation`,
  `transfer_to_agent`.
- `chamou(a, f, efetiva=True)`, `contar_chamadas(a, f, efetivas=True)`,
  `ferramenta_antes(a, x, y)` (toda chamada efetiva de `y` tem uma de `x` antes; falso se
  `y` ocorreu sem `x`; verdadeiro se `y` não ocorreu).
- Aceitam `Atendimento` ou lista de `Chamada`. Consideram também `a.anteriores` quando
  `incluir_anteriores=True`.

## `falhas.py`

- `injetar(tipo, **opcoes)` é gerenciador de contexto; aninhável; registro numa
  `ContextVar` (propaga para tarefas assíncronas do ADK).
- Tipos e efeitos: ver `notebooks/specs/03_falhas_e_observabilidade.md`.
- Ganchos usados pelo pacote: `na_ferramenta(nome)`, `apos_efeito(nome)`,
  `no_modelo(papel)`; contadores de `vezes`.
- `limpar()` (usado por `preparar_secao`).

## `relogio.py`

`agora()`, `avancar(**timedelta_kwargs)`, `dormir(segundos)` (virtual em `replay`: avança o
relógio sem esperar; real em `live`/`record`), `reset(inicio=2026-11-10 12:00 -03:00)`.
Ferramentas, pendências e regras de recorrência usam só `relogio.agora()`.

## `secoes.py`

Registro declarativo de todas as seções N0.1–N4.10.

```python
@dataclass(frozen=True)
class SpecSecao:
    id: str
    caso: str | None
    falha: Versao | None
    correcao: Versao | None
    gravacoes: dict[str, str] = {}      # nome → id da gravação ("falha" → "N2.1/falha")
    roteiros: dict[str, Roteiro] = {}
    sementes: list[Semente] = []

# Sementes declarativas
SementeReembolsos(cliente_id, n, valor, dias_atras)
SementeMemoria(cliente_id, chave, valor)             # estado user:
SementePendencia(versao, caso)                        # roda atender até a pausa
```

Exemplos obrigatórios:

```python
SECOES["N2.1"] = SpecSecao("N2.1", caso="C09", falha=v1,
                           correcao=montar(v1, com=["aprovacao"]),
                           gravacoes={"falha": "N2.1/falha"})
SECOES["N3.5"] = SpecSecao("N3.5", caso="C09",
                           falha=v3.sem("persistencia", "idempotencia"),
                           correcao=v3.sem("idempotencia"),
                           sementes=[SementePendencia(v3.sem("persistencia","idempotencia"), "C09")])
```

As composições de cada seção são as das tabelas "Composições por seção" das specs dos
notebooks; `tests/test_secoes.py` confere que cada correção é a anterior mais um
componente, e que a última correção de cada notebook é a versão de chegada.

## `notebook.py`

| Função | Comportamento |
|---|---|
| `preparar_ambiente()` | `load_dotenv`; valida modo e chave (aviso se `live` sem chave → cai para `replay`); liga observabilidade; imprime tabela com modo, modelos, Phoenix, versão do ADK. Idempotente |
| `preparar_secao(id) -> Secao` | Cria diretório temporário da seção; `armazem.reset`; novo serviço de sessão; `relogio.reset`; `falhas.limpar`; `reiniciar_runner`; semeia `clientes.json` no armazém; aplica sementes; devolve `Secao` (`id`, `caso`, `falha`, `correcao`, `gravacoes`, `roteiros`) e imprime um cabeçalho com o que foi preparado |
| `mostrar(obj)` | Código-fonte com destaque (Pygments → HTML); para `Versao`, a tabela de componentes; para `Roteiro`, os passos |
| `verificar(condicao, mensagem)` | ✅/❌ em HTML; lança `AssertionError` se falso |
| `verificar_falha(a, condicao, mensagem)` | Igual, mas só afirma se `a.fonte in {"gravacao","roteiro"}`; em `live`/`cache`, mostra ⚠️ "a falha pode não se repetir com o modelo ao vivo" |
| `matriz(arquivo, versoes, *, marcadores=None) -> Tabela` | Para cada versão: `pytest <arquivo> --versao <nome> -q --junitxml=<tmp>` em subprocesso com o mesmo `RANGOJA_MODO`; lê o JUnit; tabela teste × versão com ✅ ❌ ➖ (skip "não se aplica"); `record_property` (taxas) aparece como número; `Tabela` é um `pandas.DataFrame` com estilo |

## `observabilidade.py`

- `ligar()`: se `RANGOJA_PHOENIX=on`, inicia o Phoenix local (`phoenix.launch_app` ou
  servidor já existente na porta), registra o tracer (`phoenix.otel.register`, projeto
  `rangoja`) e instrumenta o ADK (`GoogleADKInstrumentor().instrument(...)`). Falha →
  aviso, nunca exceção.
- `trace_url(atendimento)`: link do Phoenix filtrado pela sessão/trace do atendimento.
- `anatomia(atendimento)`: árvore textual (agente → modelo → ferramenta) a partir dos
  eventos, para quando não há Phoenix.
- `metricas(desde=None)`: consulta os spans do projeto e devolve taxa de erro de
  ferramenta, taxa de escalonamento, latência p50/p95 (N3.7).

## `casos.py`

`caso(id) -> Caso`, `casos(filtro=None)`, `variantes(origem)`, validação descrita em 01.
