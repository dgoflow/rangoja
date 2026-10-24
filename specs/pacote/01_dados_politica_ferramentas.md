# 01 — Dados, política e ferramentas

> Proposta original (v0.1), mantida como registro. Onde a implementação diverge, vale o
> [README desta pasta](README.md) e os desvios em [`IMPLEMENTACAO.md`](../../IMPLEMENTACAO.md#desvios-da-spec-e-por-quê).

Valores e casos de referência: [`notebooks/specs/casos.md`](../../notebooks/specs/casos.md).
Este arquivo especifica as estruturas e o comportamento.

## `tipos.py`

Modelos Pydantic v2. Valores monetários em `Decimal` com duas casas; horários em
`datetime` com fuso `America/Sao_Paulo`.

| Modelo | Campos |
|---|---|
| `Item` | `nome: str`, `qtd: int`, `preco: Decimal`, `entregue: bool = True` |
| `Pagamento` | `valor: Decimal`, `quando: datetime` |
| `Horarios` | `pedido`, `prometido`, `entregue: datetime \| None` |
| `Pedido` | `pedido_id: str`, `cliente_id: str`, `restaurante: str`, `itens: list[Item]`, `taxa_entrega: Decimal`, `total: Decimal`, `pagamentos: list[Pagamento]`, `horarios: Horarios`, `status: Literal["entregue","em_rota","cancelado"]`, `entregador_id: str` |
| `Entregador` | `entregador_id`, `nome_completo`, `telefone`, `placa` |
| `ReembolsoHistorico` | `pedido_id`, `valor`, `quando` |
| `Cliente` | `cliente_id`, `nome`, `reembolsos: list[ReembolsoHistorico]`, `preferencias: dict[str, str]` |
| `Categoria` | `Literal["item_faltando","item_errado","cobranca","atraso","qualidade","golpe","fora_do_escopo","indefinida"]` |
| `Solucao` | `Literal["reembolso","voucher","reembolso_taxa","voucher_e_reembolso_taxa","reenvio","encaminhar_seguranca","escalar","nenhuma","pedir_informacao"]` |
| `Triagem` | `categoria: Categoria`, `problemas: list[Categoria]`, `pedido_id: str \| None`, `sinais_de_risco: list[Literal["injecao","golpe","pii","fora_do_escopo"]]`, `resumo: str` |
| `Decisao` | `categoria: Categoria`, `problemas: list[Categoria]`, `solucao: Solucao`, `valor: Decimal \| None`, `pedido_id: str \| None`, `justificativa: str`, `sinais_de_risco: list[str] = []`, `mensagem_ao_cliente: str \| None` |
| `Esperado` | `categoria`, `problemas`, `solucoes_permitidas: list[Solucao]`, `valor: Decimal \| None`, `valor_min`/`valor_max`, `status`, `ferramentas_obrigatorias`, `ferramentas_proibidas`, `ordem_obrigatoria: list[tuple[str,str]]` |
| `AtendimentoCaso` | `mensagens: list[str]` |
| `Caso` | `id`, `cliente_id`, `pedido_id \| None`, `atendimentos: list[AtendimentoCaso]`, `esperado: Esperado`, `usado_em: list[str]`, `origem: str \| None`, `transformacao: str \| None`, `relacao: Literal["invariancia","monotonicidade"] \| None` |

`Decisao.mensagem_ao_cliente` é preenchida pelo agente único (v1); na v2 a mensagem vem
do agente de resposta e o campo fica nulo.

## Dados (`rangoja/dados/`)

- `pedidos.json`, `clientes.json`, `entregadores.json`: listas de objetos nos formatos
  acima, com os pedidos e clientes da tabela "Pedidos necessários" de `casos.md`. Pedidos
  extras são permitidos (3–5 por cliente, para realismo), desde que não alterem os casos.
- Telefones no formato `(00) 9XXXX-XXXX`, placas `AAA0A00`, nomes claramente fictícios.
- `politica_reembolso.md`: seções com cabeçalho `## <tema>`, temas fixos: `categorias`,
  `item_faltando`, `item_errado`, `cobranca`, `atraso`, `qualidade`, `golpe`,
  `limites`, `recorrencia`, `privacidade`, `memoria`, `fora_do_escopo`.
- Leitura por `rangoja.dados.carregar()` com cache em memória; nunca escrita.

## `politica.py`

Constantes e funções puras; fonte das regras usadas por callbacks, ferramentas e testes.

```python
LIMITE_AUTOMATICO = Decimal("50")
PRAZO_APROVACAO = timedelta(hours=24)
RECORRENCIA_MAX, RECORRENCIA_JANELA = 3, timedelta(days=30)
CUPOM_MAX = Decimal("15")
PRECEDENCIA = ["golpe","cobranca","item_faltando","item_errado","atraso","qualidade"]
CAMPOS_PREFERENCIA = {"local_entrega","canal_contato","horario_preferido"}

def categoria_principal(problemas: list[Categoria]) -> Categoria
def solucoes_permitidas(categoria: Categoria) -> list[Solucao]
def ferramentas_permitidas(categoria: Categoria) -> set[str]
def atraso_minutos(pedido: Pedido) -> int
def compensacao_atraso(pedido: Pedido) -> tuple[Solucao, Decimal]      # monotônica no atraso
def valor_esperado(categoria, pedido, itens: list[str] | None = None) -> Decimal | None
def precisa_aprovacao(total_no_atendimento: Decimal) -> bool
def cliente_recorrente(reembolsos: list[ReembolsoHistorico], agora: datetime) -> bool
def decisao_conforme(decisao: Decisao, pedido: Pedido | None) -> list[str]   # violações
```

`ferramentas_permitidas`: sempre `buscar_pedido`, `consultar_politica`,
`escalar_para_humano`; mais `registrar_reembolso` (item_faltando, item_errado, cobranca,
atraso), `oferecer_cupom` (atraso, qualidade), `solicitar_reenvio` (item_errado),
`encaminhar_seguranca` (golpe, e somente ela além de `escalar_para_humano`).

Teste unitário obrigatório: `tests/test_politica.py` confere que cada regra numérica do
código aparece no texto de `politica_reembolso.md`.

## `armazem.py`

Estado mutável do "sistema da empresa", separado da sessão do agente. SQLite num arquivo
por seção (`preparar_secao` cria um novo em diretório temporário).

| Tabela | Colunas |
|---|---|
| `reembolsos` | `id`, `pedido_id`, `cliente_id`, `valor`, `motivo`, `chave_idempotencia` (nullable, única quando presente), `quando` |
| `cupons` | `id`, `pedido_id`, `cliente_id`, `valor`, `motivo`, `quando` |
| `reenvios` | `id`, `pedido_id`, `item`, `quando` |
| `tickets` | `id`, `cliente_id`, `motivo`, `resumo`, `quando` |
| `seguranca` | `id`, `pedido_id`, `cliente_id`, `relato`, `quando` |
| `pendencias` | `id`, `sessao_id`, `invocation_id`, `chamada_id`, `ferramenta`, `args_json`, `criada_em`, `resolvida_em`, `resolucao` |

API: `Armazem.atual()` (instância da seção corrente), `reset(diretorio)`, `inserir_*`,
`listar_*`, `reembolsos_do_pedido(pedido_id)`, `semear_cliente(cliente)`. O histórico de
`clientes.json` é semeado em `reembolsos` por `preparar_secao`.

## `ferramentas.py`

Funções Python com docstring em português (é o que o modelo lê) e tipos explícitos. Todas
aceitam `tool_context: ToolContext` e, no início, chamam `falhas.na_ferramenta(nome)`
(pode lançar exceção injetada). Retornos são `dict` serializável.

| Ferramenta | Assinatura | Efeito | Retorno | Estado da sessão |
|---|---|---|---|---|
| `buscar_pedido` (enxuta) | `(pedido_id: str)` | — | `itens` (nome, qtd, preço, entregue), `taxa_entrega`, `total`, `pagamentos`, `atraso_minutos`, `status`; erro `{"erro":"pedido_inexistente"}` | grava `pedido_id`, `pedido_resumo` |
| `buscar_pedido` (completa) | idem | — | pedido inteiro + objeto `entregador` embutido | idem |
| `consultar_politica` | `(tema: str)` | — | `{"tema","texto"}`; tema inválido → lista de temas | — |
| `oferecer_cupom` | `(pedido_id: str, valor: float, motivo: str)` | insere em `cupons` | `{"cupom_id","valor"}`; valor > `CUPOM_MAX` → erro | soma em `compensacoes` |
| `registrar_reembolso` | `(pedido_id: str, valor: float, motivo: str)` | insere em `reembolsos`; atualiza `user:reembolsos_30d` | `{"reembolso_id","valor","status":"registrado"}` | soma em `compensacoes`, `reembolsado_no_atendimento` |
| `solicitar_reenvio` | `(pedido_id: str, item: str)` | insere em `reenvios` | `{"reenvio_id"}` | `compensacoes` |
| `escalar_para_humano` | `(motivo: str, resumo: str)` | insere em `tickets` | `{"ticket_id"}` | `status = "escalado"` |
| `encaminhar_seguranca` | `(pedido_id: str, relato: str)` | insere em `seguranca` | `{"protocolo"}` | `status = "encaminhado_seguranca"` |
| `anotar_observacao` | `(texto: str)` | — | `{"ok": true}` | acrescenta a `user:observacoes` |
| `registrar_preferencia` | `(campo: str, valor: str)` | — | `{"ok": true}`; campo fora de `CAMPOS_PREFERENCIA` → erro | `user:preferencias[campo] = valor` |

Regras transversais das ferramentas:
- `buscar_pedido` completa e enxuta são duas funções; o componente `contexto_enxuto`
  decide qual é registrada sob o nome `buscar_pedido`.
- `registrar_reembolso` é envolvida em `FunctionTool` pelo componente `aprovacao`
  (`require_confirmation`); sem o componente, é registrada como função simples.
- Com o componente `idempotencia`, `registrar_reembolso` calcula
  `chave = f"{pedido_id}:{motivo_normalizado}"`; se já existe reembolso com a chave,
  devolve o existente com `"status": "ja_registrado"` sem novo efeito.
- `falhas.apos_efeito(nome)` é chamada **depois** do efeito em `registrar_reembolso`
  (suporte a `timeout_apos_efeito`).
- `motivo_normalizado`: minúsculas, sem acentos, reduzido à categoria quando possível.

## `casos.yaml`

Uma lista de objetos `Caso`. Exemplo:

```yaml
- id: C01
  cliente_id: "101"
  pedido_id: "4821"
  atendimentos:
    - mensagens: ["Meu pedido 4821 chegou frio e faltou o refri."]
  esperado:
    categoria: item_faltando
    problemas: [item_faltando, qualidade]
    solucoes_permitidas: [reembolso, voucher]
    valor: 8.00
    status: concluido
    ferramentas_obrigatorias: [buscar_pedido, registrar_reembolso]
    ferramentas_proibidas: [encaminhar_seguranca]
    ordem_obrigatoria: [[buscar_pedido, registrar_reembolso]]
  usado_em: [N0.2, N1.1, N1.2, N1.3, N1.6, N3.0, N3.4, N4.1, N4.7, N4.8]
- id: C01-giria
  origem: C01
  relacao: invariancia
  transformacao: giria
  cliente_id: "101"
  pedido_id: "4821"
  atendimentos:
    - mensagens: ["mano, o rango do 4821 veio gelado e cadê o refri??"]
  esperado: {herda: C01}
```

`esperado: {herda: <id>}` copia o esperado do caso de origem. `rangoja.casos.caso(id)`
valida o arquivo inteiro na primeira carga (IDs únicos, pedidos e clientes existentes,
`usado_em` com IDs de seção registrados em `secoes.py`).
