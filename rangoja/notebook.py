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
        "chave de API": "sim" if config.chave_disponivel() else "não (use replay)",
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


def preparar_secao(secao_id: str) -> Secao:
    """Isola a seção: armazém novo, relógio e falhas zerados. Qualquer seção roda sozinha."""
    spec: SpecSecao = SECOES[secao_id]
    diretorio = Path(tempfile.mkdtemp(prefix=f"rangoja-{secao_id}-"))
    Armazem.reset(diretorio / "armazem.db")
    relogio.reset()
    falhas.limpar()
    s = Secao(spec.id, spec.caso, spec.falha, spec.correcao, dict(spec.gravacoes),
              dict(spec.casos_extra), spec.roteiro)
    _exibir(f"<small>seção <b>{s.id}</b> · caso <b>{s.caso}</b> · "
            f"falha: <code>{getattr(s.falha, 'nome', '—')}</code> → correção: "
            f"<code>{getattr(s.correcao, 'nome', '—')}</code></small>",
            f"[{s.id}] caso {s.caso}; falha {getattr(s.falha, 'nome', '-')}; correção {getattr(s.correcao, 'nome', '-')}")
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


def verificar(condicao: bool, mensagem: str) -> None:
    marca = "✅" if condicao else "❌"
    _exibir(f"<div>{marca} {html.escape(mensagem)}</div>", f"{marca} {mensagem}")
    assert condicao, mensagem


def verificar_falha(atendimento: Any, condicao: bool, mensagem: str) -> None:
    """Para células de falha: só afirma se a resposta veio de gravação ou roteiro (reproduzível)."""
    reproduzivel = bool(atendimento.fonte) and set(atendimento.fonte) <= {"gravacao", "roteiro"}
    if reproduzivel:
        verificar(condicao, mensagem)
    else:
        aviso = f"⚠️ {mensagem} (não verificado: o modelo ao vivo pode não repetir a falha)"
        _exibir(f"<div>{html.escape(aviso)}</div>", aviso)


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
        f"<div><b>{html.escape(a.versao)}</b> · caso {a.caso_id} · status <b>{a.status}</b>"
        + (f" · <span style='color:#b00'>erro: {html.escape(a.erro[:120])}</span>" if a.erro else "")
        + f"</div><div>decisão: {html.escape(decisao)}</div>"
        f"<div>resposta: <i>{html.escape((a.resposta or '—')[:260])}</i></div>"
        f"<table><tr><th>agente</th><th>ferramenta</th><th>argumentos</th><th>efeito</th></tr>{linhas}</table>"
        f"<div><small>fonte das respostas do modelo: {fonte}</small></div>"
    )
    texto = f"{a.versao} {a.caso_id} {a.status} | {decisao} | {[c.ferramenta for c in a.trajetoria]}"
    _exibir(corpo, texto)


def amostra(nome_gravacao: str) -> None:
    """Diz de onde vem uma gravação: modelo, data e, se houver, a taxa do critério de escolha."""
    import json
    caminho = config.GRAVACOES / f"{nome_gravacao}.json"
    meta = json.loads(caminho.read_text(encoding="utf-8"))
    partes = [f"gravação <code>{nome_gravacao}</code>: modelo <b>{meta.get('modelo', '?')}</b> em {meta.get('gravada_em', '?')[:10]}"]
    am = meta.get("amostra")
    if am:
        partes.append(f"escolhida entre {am['tentativas']} execuções; critério <i>{am['criterio']}</i> satisfeito em "
                      f"<b>{am['satisfizeram']} de {am['tentativas']}</b>")
    _exibir("<small>" + " · ".join(partes) + "</small>", " | ".join(partes))
