"""Helpers dos notebooks. A superfície pública está em notebooks/README.md (contrato do pacote)."""
from __future__ import annotations

import html
import inspect
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config, falhas, observabilidade, relogio, roteiros
from .armazem import Armazem
from .modelo import ModeloRangoja
from .modelo.roteiro import Roteiro
from .secoes import SECOES, SpecSecao
from .versoes import Versao

try:  # fora do Jupyter, cai para texto
    from IPython.display import HTML, display
except Exception:  # pragma: no cover
    HTML = None
    display = None


def _exibir(corpo: str, texto: str) -> None:
    if display is not None and HTML is not None:
        display(HTML(corpo))
    else:
        print(texto)


def preparar_ambiente() -> None:
    """Carrega a configuração, liga a observabilidade e mostra o resumo. Idempotente."""
    obs = observabilidade.ligar()
    info = {
        "modo": config.modo(),
        "modelo": config.modelo_primario(),
        "chave de API": config.estado_chave(),
        "observabilidade": obs,
    }
    linhas = "".join(f"<tr><td><b>{html.escape(k)}</b></td><td>{html.escape(str(v))}</td></tr>" for k, v in info.items())
    _exibir(f"<table>{linhas}</table>", "\n".join(f"{k}: {v}" for k, v in info.items()))


@dataclass
class Secao:
    """O que uma seção de notebook precisa, já com armazém e relógio isolados."""
    id: str
    caso: str | None
    falha: Versao | None
    correcao: Versao | None
    gravacoes: dict[str, str] = field(default_factory=dict)
    casos_extra: dict[str, str] = field(default_factory=dict)
    _roteiro: str | None = None

    def roteiro(self, versao: Versao | None = None) -> dict:
        """Roteiro escrito à mão desta seção, na forma da versão dada (padrão: a de falha)."""
        if self._roteiro is None:
            raise KeyError(f"{self.id} não tem roteiro")
        alvo = versao or self.falha
        assert alvo is not None
        return roteiros.ROTEIROS[self._roteiro](alvo)


def gravacao(nome: str, agente: str = "unico") -> ModeloRangoja:
    """Um modelo que repete o que o modelo real respondeu quando gravamos `nome` (rangoja/gravacoes/).

    Serve de `model=` para um LlmAgent montado à mão, sem rede e sem chave. `agente` precisa ser o `name`
    do LlmAgent: a gravação guarda as respostas por agente. Independe das seções (não usa a gravação que
    `atender()` deixou no contexto) e recomeça do início se a célula rodar de novo.
    """
    return ModeloRangoja(agente=agente, avulso=True, replay=Roteiro.de_arquivo(config.GRAVACOES / f"{nome}.json"))


def preparar_secao(secao_id: str) -> Secao:
    """Isola a seção: armazém novo, relógio e falhas zerados. Qualquer seção roda sozinha."""
    spec: SpecSecao = SECOES[secao_id]
    diretorio = Path(tempfile.mkdtemp(prefix=f"rangoja-{secao_id}-"))
    Armazem.reset(diretorio / "armazem.db")
    relogio.reset()
    falhas.limpar()
    s = Secao(spec.id, spec.caso, spec.falha, spec.correcao, dict(spec.gravacoes),
              dict(spec.casos_extra), spec.roteiro)
    sem_correcao = s.correcao is None
    texto_falha = f"{s.falha.titulo}" if s.falha is not None else "nenhuma"
    corpo = (f"**Seção {s.id}**: caso {s.caso}. Versão com o problema: `{texto_falha}`. "
             + ("Esta seção não tem correção." if sem_correcao else f"Versão corrigida: `{s.correcao.titulo}`."))
    _exibir(f"<small>{html.escape(corpo.replace('**', '').replace('`', ''))}</small>", corpo.replace("**", "").replace("`", ""))
    return s


def _codigo_html(codigo: str) -> str:
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import PythonLexer
        formatador = HtmlFormatter(noclasses=True)
        return highlight(codigo, PythonLexer(), formatador)
    except Exception:
        return f"<pre>{html.escape(codigo)}</pre>"


DESCRICOES = {
    "prompt": "agente sem ferramentas; política na instrução",
    "ferramentas": "buscar_pedido, consultar_politica, cupom, reembolso, reenvio, escalar, segurança",
    "schema": "decisão estruturada (Decisao) como contrato com o código",
    "estado": "uma sessão por atendimento; estado da conversa",
    "contexto_enxuto": "ferramentas devolvem só o necessário; política por consulta",
    "memoria_livre": "anotar_observacao: memória livre do cliente",
    "memoria_segura": "só preferências permitidas; recorrência limita compensação",
    "aprovacao": "reembolso acima de R$ 50 vira pendência de aprovação humana",
    "guardrail_entrada": "injeção sinalizada; fora do escopo recusado",
    "guardrail_saida": "dados do entregador removidos da resposta",
    "sequencia": "triagem → resolução → resposta, com consulta do pedido em código",
    "categorias": "a categoria define as ferramentas permitidas; golpe só encaminha",
    "contrato": "a etapa seguinte só roda se a anterior entregou o que precisa",
    "erros_estruturados": "erro de ferramenta vira resultado que o agente entende",
    "retry": "repete falhas transitórias do modelo, com espera",
    "fallback": "troca para o modelo secundário se o primário falhar",
    "limites": "no máximo 3 chamadas por ferramenta; teto de chamadas ao modelo",
    "persistencia": "sessões em SQLite; sobrevivem à queda do runner",
    "idempotencia": "chave (pedido, motivo): reembolso não se repete",
}


def mostrar(objeto: Any) -> None:
    """Exibe o código-fonte (módulo, função, classe) ou a tabela de componentes de uma Versao."""
    if isinstance(objeto, Versao):
        linhas = "".join(
            f"<tr><td><code>{c}</code></td><td>{html.escape(DESCRICOES.get(c, ''))}</td></tr>"
            for c in sorted(objeto.componentes)
        )
        _exibir(f"<b>{html.escape(objeto.nome)}</b><table>{linhas}</table>", f"{objeto.nome}: {sorted(objeto.componentes)}")
        return
    if isinstance(objeto, dict):  # roteiro
        texto = "\n".join(f"{a}: {[(p.tipo, p.dados) for p in passos]}" for a, passos in objeto.items())
        _exibir(f"<pre>{html.escape(texto)}</pre>", texto)
        return
    codigo = inspect.getsource(objeto)
    _exibir(_codigo_html(codigo), codigo)


_CALLBACKS = ["before_agent_callback", "before_model_callback", "after_model_callback",
              "before_tool_callback", "on_tool_error_callback", "after_tool_callback", "after_agent_callback"]


def _nomes(valor: Any) -> list[str]:
    if valor is None:
        return []
    return [getattr(v, "__name__", type(v).__name__) for v in (valor if isinstance(valor, list) else [valor])]


def _ferramenta(f: Any) -> str:
    """Nome da ferramenta e as opções com que a fábrica a montou (ex.: com_aprovacao=True)."""
    nome = getattr(f, "__name__", type(f).__name__)
    opcoes = {n: c.cell_contents for n, c in zip(getattr(getattr(f, "__code__", None), "co_freevars", ()), f.__closure__ or [])
              if isinstance(c.cell_contents, bool)} if getattr(f, "__closure__", None) else {}
    return nome + (f"({', '.join(f'{k}={v}' for k, v in sorted(opcoes.items()))})" if opcoes else "")


def _ficha(versao: Versao) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Lê do agente construído (o mesmo que o ADK roda) o que define o comportamento de cada agente e da execução."""
    construida = versao.construir()
    raiz = construida.agente_raiz
    agentes = list(raiz.sub_agents) if raiz.sub_agents else [raiz]
    ficha = {}
    for ag in agentes:
        ficha[ag.name] = {
            "instrução": getattr(ag, "instruction", "") or "",
            "ferramentas": [_ferramenta(f) for f in getattr(ag, "tools", [])],
            "saída estruturada": getattr(getattr(ag, "output_schema", None), "__name__", None) or "—",
            **{cb: ", ".join(_nomes(getattr(ag, cb, None))) or "—" for cb in _CALLBACKS},
        }
    m = getattr(agentes[0], "model", None)
    execucao = {
        "agentes": " → ".join(a.name for a in agentes) + (" (SequentialAgent)" if raiz.sub_agents else ""),
        "sessão": "uma por atendimento" if "estado" in versao else "uma nova a cada mensagem",
        "sessões guardadas em": "SQLite (sobrevivem à queda)" if "persistencia" in versao else "memória",
        "máximo de chamadas ao modelo": str(construida.run_config.max_llm_calls),
        "retry do modelo": "sim" if getattr(m, "retry", False) else "não",
        "fallback do modelo": "sim" if getattr(m, "fallback", None) is not None else "não",
    }
    return ficha, execucao


def _diff_instrucao(antes: str, depois: str) -> tuple[list[str], list[str]]:
    import difflib
    a, d = antes.splitlines(), depois.splitlines()
    sai = [ln for ln in difflib.ndiff(a, d) if ln.startswith("- ") and ln[2:].strip()]
    entra = [ln for ln in difflib.ndiff(a, d) if ln.startswith("+ ") and ln[2:].strip()]
    return [ln[2:] for ln in sai], [ln[2:] for ln in entra]


def comparar(antes: Versao | None, depois: Versao) -> None:
    """Mostra o que muda de uma versão para a outra, lido dos agentes construídos: prompt, ferramentas,
    saída estruturada, callbacks e execução. Com `antes=None`, mostra a ficha completa de `depois`."""
    fd, ed = _ficha(depois)
    fa, ea = _ficha(antes) if antes is not None else ({}, {})
    html_partes, texto = [], []

    def linha(sinal: str, conteudo: str, cor: str) -> None:
        html_partes.append(f"<div style='font-family:monospace;white-space:pre-wrap;color:{cor}'>{sinal} {html.escape(conteudo)}</div>")
        texto.append(f"{sinal} {conteudo}")

    def titulo(t: str) -> None:
        html_partes.append(f"<div style='margin-top:6px'><b>{html.escape(t)}</b></div>")
        texto.append(t)

    def bloco(sinal: str, linhas: list[str], cor: str, rotulo: str) -> None:
        mostradas = linhas if len(linhas) <= 6 else linhas[:4]
        for ln in mostradas:
            linha(sinal, ln, cor)
        if len(linhas) > len(mostradas):
            resto = linhas[len(mostradas):]
            corpo = "".join(f"<div style='font-family:monospace;white-space:pre-wrap;color:{cor}'>{sinal} {html.escape(ln)}</div>" for ln in resto)
            html_partes.append(f"<details><summary>{sinal} mais {len(resto)} linhas {rotulo}</summary>{corpo}</details>")
            texto.append(f"{sinal} … mais {len(resto)} linhas {rotulo}")

    verde, vermelho, cinza = "#1a7f37", "#cf222e", "#6e7781"
    if antes is not None:
        titulo("Componentes")
        for c in sorted(depois.componentes - antes.componentes):
            linha("+", f"{c}: {DESCRICOES.get(c, '')}", verde)
        for c in sorted(antes.componentes - depois.componentes):
            linha("−", f"{c}: {DESCRICOES.get(c, '')}", vermelho)

    mudou_agente = False
    for nome in list(dict.fromkeys([*fa, *fd])):
        a, d = fa.get(nome), fd.get(nome)
        if a == d:
            continue
        mudou_agente = True
        titulo(f"Agente {nome}" + (" (novo)" if a is None else " (removido)" if d is None else ""))
        a = a or {k: ("" if k == "instrução" else [] if k == "ferramentas" else "—") for k in (d or {})}
        d = d or {k: ("" if k == "instrução" else [] if k == "ferramentas" else "—") for k in a}
        if a["instrução"] != d["instrução"]:
            sai, entra = _diff_instrucao(a["instrução"], d["instrução"])
            linha("", "prompt:", cinza)
            bloco("−", sai, vermelho, "saem do prompt")
            bloco("+", entra, verde, "entram no prompt")
        if a["ferramentas"] != d["ferramentas"]:
            linha("", "ferramentas:", cinza)
            for f in d["ferramentas"]:
                if f not in a["ferramentas"]:
                    linha("+", f, verde)
            for f in a["ferramentas"]:
                if f not in d["ferramentas"]:
                    linha("−", f, vermelho)
            iguais = [f for f in d["ferramentas"] if f in a["ferramentas"]]
            if iguais:
                linha(" ", "iguais: " + ", ".join(iguais), cinza)
        for campo in ["saída estruturada", *_CALLBACKS]:
            if a.get(campo) != d.get(campo):
                linha("", f"{campo}: {a.get(campo)} → {d.get(campo)}", verde)
    if antes is not None and not mudou_agente:
        titulo("Agente")
        linha(" ", "igual: mesmo prompt, mesmas ferramentas, mesmos callbacks", cinza)

    mudancas = {k: (ea.get(k), v) for k, v in ed.items() if ea.get(k) != v} if antes is not None else {k: (None, v) for k, v in ed.items()}
    if mudancas:
        titulo("Execução")
        for k, (va, vd) in mudancas.items():
            linha("", f"{k}: {va} → {vd}" if va is not None else f"{k}: {vd}", verde if va is not None else cinza)

    cab = f"O que muda: <code>{html.escape(antes.titulo)}</code> → <code>{html.escape(depois.titulo)}</code>" if antes is not None \
        else f"Ficha de <code>{html.escape(depois.titulo)}</code>"
    _exibir(f"<div style='border-left:3px solid {cinza};padding-left:8px'><b>{cab}</b>{''.join(html_partes)}</div>",
            ((f"O que muda: {antes.titulo} → {depois.titulo}" if antes is not None else f"Ficha de {depois.titulo}") + "\n" + "\n".join(texto)))


def afirmar(condicao: bool, mensagem: str) -> None:
    """Afirma que algo é verdade. Mostra ✅ se for e ❌ se não for, e nesse caso interrompe o notebook (como `assert`).
    Para o que depende do modelo ao vivo, use `esperar`."""
    marca = "✅" if condicao else "❌"
    _exibir(f"<div>{marca} {html.escape(mensagem)}</div>", f"{marca} {mensagem}")
    assert condicao, mensagem


def esperar(atendimento: Any, condicao: bool, mensagem: str) -> None:
    """Espera um resultado que depende do modelo. Com resposta de gravação ou de roteiro (reproduzível),
    afirma como `afirmar`. Com o modelo ao vivo, que varia entre execuções, só informa: ✅ se aconteceu,
    ⚠️ se não aconteceu desta vez (sem interromper o notebook)."""
    reproduzivel = bool(atendimento.fonte) and set(atendimento.fonte) <= {"gravacao", "roteiro"}
    if reproduzivel:
        afirmar(condicao, mensagem)
    elif condicao:
        _exibir(f"<div>✅ {html.escape(mensagem)} <small>(modelo ao vivo)</small></div>", f"✅ {mensagem} (modelo ao vivo)")
    else:
        aviso = f"⚠️ {mensagem}: não se confirmou desta vez (o modelo ao vivo varia entre execuções)"
        _exibir(f"<div>{html.escape(aviso)}</div>", aviso)


# nomes antigos, que os notebooks 02 a 04 ainda usam
verificar = afirmar
conferir = verificar_falha = esperar


class Tabela:
    def __init__(self, titulos: list[str], linhas: list[list[str]]) -> None:
        self.titulos, self.linhas = titulos, linhas

    def _repr_html_(self) -> str:
        cab = "".join(f"<th>{html.escape(t)}</th>" for t in self.titulos)
        corpo = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in linha) + "</tr>" for linha in self.linhas)
        return f"<table><tr>{cab}</tr>{corpo}</table>"

    def __str__(self) -> str:
        larguras = [max(len(str(x)) for x in col) for col in zip(self.titulos, *self.linhas)]
        def fmt(linha):
            return "  ".join(str(c).ljust(w) for c, w in zip(linha, larguras))
        return "\n".join([fmt(self.titulos)] + [fmt(linha) for linha in self.linhas])

    __repr__ = __str__


def matriz(arquivo: str, versoes: list[Versao | str]) -> Tabela:
    """Roda o pytest do arquivo contra cada versão e monta teste × versão: ✅ passa, ❌ falha, ➖ não se aplica."""
    raiz = config.RAIZ
    nomes = [v if isinstance(v, str) else v.nome for v in versoes]
    resultados: dict[str, dict[str, str]] = {}
    ordem: list[str] = []
    for nome in nomes:
        with tempfile.TemporaryDirectory() as tmp:
            xml = Path(tmp) / "r.xml"
            env = {**os.environ, "PYTHONPATH": f"{raiz}:{raiz / 'tests'}"}
            subprocess.run(
                [sys.executable, "-m", "pytest", str(raiz / "tests" / arquivo), "--versao", nome, "-q",
                 "-p", "no:warnings", f"--junitxml={xml}"],
                cwd=raiz, env=env, capture_output=True, text=True,
            )
            for caso in ET.parse(xml).getroot().iter("testcase"):
                teste = caso.get("name", "")
                if teste not in ordem:
                    ordem.append(teste)
                estado = "✅"
                if caso.find("failure") is not None or caso.find("error") is not None:
                    estado = "❌"
                elif caso.find("skipped") is not None:
                    estado = "➖"
                resultados.setdefault(teste, {})[nome] = estado
    linhas = [[t] + [resultados.get(t, {}).get(n, "?") for n in nomes] for t in ordem]
    return Tabela(["teste"] + nomes, linhas)


def _titulo(a: Any) -> str:
    """Nome legível da versão que atendeu (o atendimento guarda só a chave curta)."""
    return getattr(getattr(a, "_versao", None), "titulo", a.versao)


def resumo(a: Any) -> None:
    """Mostra um atendimento: status, decisão, resposta ao cliente e trajetória das ferramentas."""
    d = a.decisao
    decisao = f"{d.categoria} → {d.solucao}" + (f" (R$ {d.valor:.2f})" if d.valor is not None else "") if d else "— (sem decisão estruturada)"
    linhas = "".join(
        f"<tr><td>{html.escape(c.agente)}</td><td><code>{html.escape(c.ferramenta)}</code></td>"
        f"<td>{html.escape(str(c.args))}</td><td>{'✅ com efeito' if c.efetiva else '⛔ sem efeito'}</td></tr>"
        for c in a.trajetoria
    ) or "<tr><td colspan='4'><i>nenhuma ferramenta chamada</i></td></tr>"
    fonte = ", ".join(sorted(set(a.fonte))) or "—"
    corpo = (
        f"<div><b>{html.escape(_titulo(a))}</b> · caso {a.caso_id} · status <b>{a.status}</b>"
        + (f" · <span style='color:#b00'>erro: {html.escape(a.erro[:120])}</span>" if a.erro else "")
        + f"</div><div>decisão: {html.escape(decisao)}</div>"
        f"<div>resposta: <i>{html.escape((a.resposta or '—')[:260])}</i></div>"
        f"<table><tr><th>agente</th><th>ferramenta</th><th>argumentos</th><th>efeito</th></tr>{linhas}</table>"
        f"<div><small>fonte das respostas do modelo: {fonte}</small></div>"
    )
    texto = f"{_titulo(a)} {a.caso_id} {a.status} | {decisao} | {[c.ferramenta for c in a.trajetoria]}"
    _exibir(corpo, texto)


CRITERIOS = {  # os critérios de scripts/gravar_secoes.py, ditos para quem lê o notebook
    "consultou": "o modelo consultou o pedido",
    "consulta_unica": "o modelo consultou o pedido uma única vez",
    "consulta_repetida": "o modelo consultou o pedido mais de uma vez",
    "consulta_e_valor_real": "o modelo consultou o pedido e reembolsou o valor real do item",
    "sem_portaria": "a resposta não menciona a portaria",
    "menciona_portaria": "a resposta menciona a portaria",
}


def amostra(nome_gravacao: str) -> None:
    """Diz de onde vem uma gravação: modelo, data e, se houver, a taxa do critério de escolha.
    Em live ou record, a gravação não é a resposta mostrada: vira a referência para comparar."""
    import json
    caminho = config.GRAVACOES / f"{nome_gravacao}.json"
    meta = json.loads(caminho.read_text(encoding="utf-8"))
    data = meta.get("gravada_em", "?")[:10]
    if config.modo() == "replay":
        partes = [f"resposta gravada do <b>{meta.get('modelo', '?')}</b> em {data} (<code>{nome_gravacao}</code>)"]
    else:
        partes = [f"referência: gravação do <b>{meta.get('modelo', '?')}</b> em {data} (<code>{nome_gravacao}</code>); a resposta acima é do modelo ao vivo"]
    am = meta.get("amostra")
    if am:
        o_que = CRITERIOS.get(am["criterio"], am["criterio"])
        partes.append(f"de <b>{am['tentativas']}</b> execuções gravadas, em <b>{am['satisfizeram']}</b> {o_que}")
    _exibir("<small>" + " · ".join(partes) + "</small>", " | ".join(partes))
