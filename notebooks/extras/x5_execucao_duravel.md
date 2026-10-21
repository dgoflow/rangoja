# X5 — Quando o fluxo fica longo: execução durável

> Texto, sem código executável. Não é um tutorial de Temporal: o objetivo é saber **quando a retomada que construímos em N3.5 deixa de bastar**.

## O que já temos (N3.5)

Em N3.5 o atendimento sobrevive à queda do processo com três peças:

- a conversa fica num **banco** (`SqliteSessionService`), então o estado não se perde;
- a aprovação humana é uma **fila** no armazém (tabela `pendencias`), que sobrevive ao reinício;
- a **idempotência** (N3.6) garante que reexecutar um passo não duplique o efeito.

Para um fluxo curto, com uma espera de aprovação de até algumas horas, isso é suficiente e simples de entender.

## O que um motor de workflow durável acrescenta

Motores como o [Temporal](https://temporal.io/) tratam o fluxo inteiro como um programa que **pode ser retomado exatamente de onde parou**, não só o seu estado:

| Capacidade | Em palavras | Equivalente no RangoJá de hoje |
|---|---|---|
| **Histórico de eventos** | Cada passo e seu resultado ficam gravados; após uma queda, o motor reexecuta o código reaproveitando o histórico, sem refazer efeitos já feitos | Reconstruímos "onde estava" a partir do estado da sessão e da fila, escrevendo a lógica de retomada à mão |
| **Timers duráveis** | "Espere 24 h" sobrevive a deploys e quedas; podem ser dias ou meses | `expirar_pendencias()` precisa ser chamada por alguém (um agendador externo) |
| **Sinais** | Um evento externo (a decisão do supervisor) chega ao fluxo em andamento | `aprovar()` e `recusar()` mexem na fila; o fluxo é que "olha" a fila depois |
| **Consultas** | Ler o estado de um fluxo em execução, sem interrompê-lo | Ler o armazém e a sessão |
| **Retentativas por política** | Cada atividade (chamada ao modelo, ferramenta) tem a sua política de retry e de timeout | `retry` e `limites` do NB03, escritos por nós |

A parte do fluxo que chama o modelo e as ferramentas continua sendo o que construímos nos notebooks. O motor cuida de **quando** e **se** cada passo roda. Duas ressalvas que valem para qualquer motor: as atividades continuam precisando ser **idempotentes** (a execução é "pelo menos uma vez"), e o código do fluxo precisa ser determinístico para o replay funcionar, o que combina mal com chamar o modelo diretamente dentro dele; chamadas ao modelo ficam em atividades.

## Quando vale a pena

Vale considerar quando **vários** destes aparecem:

- esperas **longas** e numerosas (aprovação em dias, prazo de resposta do cliente, janelas de arrependimento);
- fluxos com **muitos passos** em que refazer do começo é caro ou perigoso;
- **auditoria** exigida: poder mostrar o histórico completo de cada decisão e a ordem em que aconteceu;
- **volume** suficiente para que "alguém chama `expirar_pendencias`" vire fonte de incidentes;
- vários serviços e equipes dependendo do mesmo fluxo.

## Quando não vale

- o atendimento termina em minutos e a única espera é uma aprovação curta;
- a equipe é pequena e o custo de operar mais um sistema (servidor, filas de trabalho, versionamento de fluxos) supera o benefício;
- a fila no armazém, com um agendador simples, já cobre o caso.

A pergunta prática: **qual é o pior que acontece hoje se o processo cair no meio?** Se a resposta é "o cliente espera uns minutos e a retomada de N3.5 resolve", não precisa. Se é "perdemos um prazo legal ou duplicamos um pagamento que só o histórico completo explicaria", comece a olhar para um motor durável.

## Fora do escopo deste material

Não implementamos nem rodamos Temporal aqui. Este texto não substitui a documentação do motor, e a comparação acima é conceitual.
