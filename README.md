# RangoJá — do prompt ao agente robusto

Um prompt bem escrito resolve muita coisa, até o dia em que precisa consultar um dado, executar uma ação ou
resistir a um cliente insistente. Este repositório mostra, passo a passo, **como as capacidades se acumulam** entre
o uso mais simples de um LLM (um prompt) e um agente em que se pode confiar.

O caso é sempre o mesmo: o atendimento do **RangoJá**, um app de delivery fictício. Um cliente reclama de um pedido,
e cada notebook acrescenta uma camada ao atendente, mostrando primeiro a falha e depois a correção.

## A trilha

| Notebook | Pergunta | O que entra |
|---|---|---|
| [`alem_do_prompt`](alem_do_prompt.ipynb) | O que separa um prompt de um agente? | ferramentas (o loop ReAct), contrato de saída, regras em código |
| [`agente_controlado`](agente_controlado.ipynb) | Como impedir o que o agente não deve fazer? | menor privilégio, guardrails (entrada, ação, saída), humano no loop, memória de longo prazo |
| `agente_robusto` *(em breve)* | O que acontece quando algo dá errado? | traces, erros estruturados, retry e fallback, limites, idempotência |
| `agente_avaliado` *(em breve)* | Como saber que ele funciona e continua funcionando? | testes de regra, casos golden, testes metamórficos, comparação entre versões |

A ideia que atravessa todos: **o modelo propõe, o código autoriza.** A cada passo, uma garantia sai do prompt, que
só pede, e passa para o código, que garante.

Cada notebook é autossuficiente. Os dados, as ferramentas, o agente e as regras estão nas células, sem nenhum pacote
escondido. De fora vêm só o [Google ADK](https://google.github.io/adk-docs/) e o pydantic.

## Como rodar

Com o [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run jupyter lab alem_do_prompt.ipynb
```

Os notebooks usam o gpt-4o-mini ao vivo e precisam de uma chave de API da OpenAI: copie `.env.example` para `.env`
e preencha `OPENAI_API_KEY`. As respostas mudam entre execuções, o que faz parte do que se observa, e um notebook
inteiro custa poucos centavos de tokens.

## Licença

[MIT](LICENSE).
