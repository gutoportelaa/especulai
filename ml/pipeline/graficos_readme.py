"""Gráficos e tabela de resultados do README, gerados de `metricas-modelo.json`.

Mesma fonte da página Como Funciona do site: o que o `export_web` grava para o site vira aqui três
SVGs (previsto × pedido, viés por faixa, importância), com venda e aluguel lado a lado, e o bloco de
resultados do README entre os marcadores `<!-- resultados:inicio -->` e `<!-- resultados:fim -->`.

SVG escrito à mão em vez de matplotlib: sem dependência nova, saída determinística (o teste exige
igualdade exata com o que seria regerado) e diff legível no git. Fundo branco explícito para o
tema escuro do GitHub não apagar o texto.

Uso: uv run python -m ml.pipeline.graficos_readme   (o `export_web` já chama no fim)
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, cast
from xml.sax.saxutils import escape

from config.paths import PROJECT_ROOT

SITE_METRICAS = PROJECT_ROOT / "frontend" / "src" / "features" / "conteudo" / "metricas-modelo.json"
README = PROJECT_ROOT / "README.md"
GRAFICOS_DIR = PROJECT_ROOT / "docs" / "graficos"
INICIO, FIM = "<!-- resultados:inicio -->", "<!-- resultados:fim -->"

# As mesmas da página do site (frontend/src/features/conteudo/graficos.js).
SERIE, ACIMA, ABAIXO = "#044bd9", "#044bd9", "#d03b3b"
GRADE, REFERENCIA, EIXO, TEXTO = "#ececef", "#a1a1aa", "#71717a", "#09090b"
FONTE = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans', sans-serif"

LARGURA, PAINEL, VAO, MARGEM = 820, 375, 30, 20
NEGOCIOS = (("venda", "Venda", ""), ("aluguel", "Aluguel", "/mês"))


class Calibracao(TypedDict):
    pedido: int
    previsto: int
    previsto_p10: int
    previsto_p90: int
    n: int


class Vies(TypedDict):
    de: int
    ate: int
    vies: float
    erro: float
    n: int


class Importancia(TypedDict):
    atributo: str
    peso: float


# ---------------------------------------------------------------- formatação pt-BR


def inteiro(valor: float) -> str:
    return f"{round(valor):,}".replace(",", ".")


def curto(valor: float) -> str:
    if valor >= 1e6:
        mi = valor / 1e6
        texto = f"{mi:.1f}".rstrip("0").rstrip(".") if mi < 10 else f"{mi:.0f}"
        return f"{texto.replace('.', ',')} mi"
    if valor >= 1e4:
        return f"{inteiro(valor / 1000)} mil"
    return inteiro(valor)


def pct(fracao: float, casas: int = 0, sinal: bool = False) -> str:
    p = fracao * 100
    texto = f"{abs(p):.{casas}f}".replace(".", ",")
    prefixo = (
        "−" if p < 0 and float(texto.replace(",", ".")) > 0 else "+" if sinal and p > 0 else ""
    )
    return f"{prefixo}{texto}%"


def decimal(valor: float, casas: int = 2) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


# ---------------------------------------------------------------- escalas (espelham escalas.js)


def escala_log(
    dominio: tuple[float, float], faixa: tuple[float, float]
) -> Callable[[float], float]:
    l0, l1 = math.log(dominio[0]), math.log(dominio[1])
    return lambda v: faixa[0] + (math.log(v) - l0) / (l1 - l0) * (faixa[1] - faixa[0])


def escala_linear(
    dominio: tuple[float, float], faixa: tuple[float, float]
) -> Callable[[float], float]:
    return lambda v: faixa[0] + (v - dominio[0]) / (dominio[1] - dominio[0]) * (faixa[1] - faixa[0])


def marcas_log(dominio: tuple[float, float], maximo: int = 6) -> list[float]:
    marcas = [
        m * 10**k
        for k in range(math.floor(math.log10(dominio[0])), math.ceil(math.log10(dominio[1])) + 1)
        for m in (1, 2, 5)
        if dominio[0] <= m * 10**k <= dominio[1]
    ]
    if len(marcas) <= maximo:
        return marcas
    enxutas = [v for v in marcas if round(v / 10 ** math.floor(math.log10(v) + 1e-9)) in (1, 5)]
    return enxutas if len(enxutas) >= 2 else marcas


def limite_simetrico(valores: list[float], folga: float = 1.2) -> float:
    pico = max(abs(v) for v in valores) * folga
    return max(0.1, math.ceil(pico * 10 - 1e-9) / 10)


# ---------------------------------------------------------------- SVG


def _n(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def texto(
    x: float,
    y: float,
    conteudo: str,
    tam: int = 12,
    cor: str = EIXO,
    ancora: str = "middle",
    **extra: str,
) -> str:
    attrs = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in extra.items())
    return (
        f'<text x="{_n(x)}" y="{_n(y)}" font-size="{tam}" fill="{cor}" '
        f'text-anchor="{ancora}"{attrs}>{escape(conteudo)}</text>'
    )


def linha(
    x1: float, y1: float, x2: float, y2: float, cor: str = GRADE, esp: float = 1, **extra: str
) -> str:
    attrs = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in extra.items())
    return (
        f'<line x1="{_n(x1)}" y1="{_n(y1)}" x2="{_n(x2)}" y2="{_n(y2)}" '
        f'stroke="{cor}" stroke-width="{_n(esp)}"{attrs}/>'
    )


def figura(titulo: str, subtitulo: str, altura: int, corpo: list[str], modelos: str) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{LARGURA}" height="{altura}" '
            f'viewBox="0 0 {LARGURA} {altura}" font-family="{FONTE}">',
            f"<!-- gerado por ml/pipeline/graficos_readme.py; modelos {modelos} -->",
            f"<title>{escape(titulo)}</title>",
            f'<rect width="{LARGURA}" height="{altura}" rx="12" fill="#ffffff"/>',
            texto(MARGEM, 34, titulo, 18, TEXTO, "start", font_weight="700"),
            texto(MARGEM, 56, subtitulo, 12, EIXO, "start"),
            *corpo,
            "</svg>",
            "",
        ]
    )


def paineis() -> list[tuple[float, str, str, str]]:
    """(x0, chave, rótulo, sufixo) de cada painel."""
    return [(MARGEM + i * (PAINEL + VAO), *neg) for i, neg in enumerate(NEGOCIOS)]


def grafico_calibracao(dados: dict[str, list[Calibracao]], modelos: str) -> str:
    topo, alto = 96, 280
    m_esq, m_base = 54, 40
    corpo: list[str] = []
    for x0, chave, rotulo, sufixo in paineis():
        d = dados[chave]
        valores = [v for f in d for v in (f["pedido"], f["previsto_p10"], f["previsto_p90"])]
        dom = (min(valores) * 0.85, max(valores) * 1.15)
        x = escala_log(dom, (x0 + m_esq, x0 + PAINEL - 8))
        y = escala_log(dom, (topo + alto - m_base, topo + 8))
        corpo.append(
            texto(x0, topo - 10, f"{rotulo} (R${sufixo})", 13, TEXTO, "start", font_weight="600")
        )
        for v in marcas_log(dom, 5):
            corpo += [
                linha(x(v), topo + 8, x(v), topo + alto - m_base),
                linha(x0 + m_esq, y(v), x0 + PAINEL - 8, y(v)),
                texto(x(v), topo + alto - m_base + 16, curto(v), 11),
                texto(x0 + m_esq - 6, y(v) + 4, curto(v), 11, ancora="end"),
            ]
        corpo.append(texto((x0 + m_esq + x0 + PAINEL) / 2, topo + alto - 6, "pedido", 11))
        corpo.append(linha(x(dom[0]), y(dom[0]), x(dom[1]), y(dom[1]), REFERENCIA))
        ponta = dom[0] * (dom[1] / dom[0]) ** 0.97
        angulo = math.degrees(math.atan2(y(dom[1]) - y(dom[0]), x(dom[1]) - x(dom[0])))
        corpo.append(
            f'<text transform="translate({_n(x(ponta))} {_n(y(ponta))}) rotate({_n(angulo)})" '
            f'dy="-6" font-size="11" fill="{EIXO}" text-anchor="end">previsto = pedido</text>'
        )
        for f in d:
            cx = x(f["pedido"])
            corpo += [
                linha(
                    cx,
                    y(f["previsto_p10"]),
                    cx,
                    y(f["previsto_p90"]),
                    SERIE,
                    2,
                    stroke_opacity="0.3",
                    stroke_linecap="round",
                ),
                f'<circle cx="{_n(cx)}" cy="{_n(y(f["previsto"]))}" r="5" fill="{SERIE}" '
                f'stroke="#ffffff" stroke-width="2"/>',
            ]
    return figura(
        "Previsto × pedido, em 10 faixas de preço pedido",
        "Ponto: previsão mediana. Linha: onde caem 80% das previsões. Sobre a diagonal, acerto médio."
        " Eixos em log.",
        topo + alto + 14,
        corpo,
        modelos,
    )


def _coluna(cx: float, base: float, ponta: float, larg: float) -> str:
    esq, dir_ = cx - larg / 2, cx + larg / 2
    raio = min(4.0, abs(base - ponta))
    d = raio if ponta < base else -raio
    return (
        f'<path d="M{_n(esq)},{_n(base)} V{_n(ponta + d)} Q{_n(esq)},{_n(ponta)} {_n(esq + raio)},'
        f"{_n(ponta)} H{_n(dir_ - raio)} Q{_n(dir_)},{_n(ponta)} {_n(dir_)},{_n(ponta + d)} "
        f'V{_n(base)} Z"'
    )


def grafico_vies(dados: dict[str, list[Vies]], modelos: str) -> str:
    topo, alto = 112, 260
    m_esq, m_base = 44, 44
    corpo = [
        f'<rect x="{MARGEM}" y="72" width="10" height="10" rx="2" fill="{ACIMA}"/>',
        texto(MARGEM + 16, 81, "previsto acima do pedido", 12, EIXO, "start"),
        f'<rect x="{MARGEM + 190}" y="72" width="10" height="10" rx="2" fill="{ABAIXO}"/>',
        texto(MARGEM + 206, 81, "previsto abaixo do pedido", 12, EIXO, "start"),
    ]
    for x0, chave, rotulo, sufixo in paineis():
        d = dados[chave]
        lim = limite_simetrico([f["vies"] for f in d])
        y = escala_linear((-lim, lim), (topo + alto - m_base, topo + 16))
        fatia = (PAINEL - m_esq - 8) / len(d)
        corpo.append(
            texto(x0, topo - 6, f"{rotulo} (R${sufixo})", 13, TEXTO, "start", font_weight="600")
        )
        for v in (-lim, -lim / 2, 0.0, lim / 2, lim):
            corpo += [
                linha(x0 + m_esq, y(v), x0 + PAINEL - 8, y(v), REFERENCIA if v == 0 else GRADE),
                texto(x0 + m_esq - 6, y(v) + 4, pct(v, sinal=True), 11, ancora="end"),
            ]
        for i, f in enumerate(d):
            cx = x0 + m_esq + fatia * (i + 0.5)
            acima = f["vies"] >= 0
            l1, l2 = (
                ("até", curto(f["ate"]))
                if i == 0
                else ("acima de", curto(f["de"]))
                if i == len(d) - 1
                else (curto(f["de"]), f"a {curto(f['ate'])}")
            )
            corpo += [
                _coluna(cx, y(0), y(f["vies"]), min(24, fatia * 0.5))
                + f' fill="{ACIMA if acima else ABAIXO}"/>',
                texto(
                    cx,
                    y(f["vies"]) - 6 if acima else y(f["vies"]) + 14,
                    pct(f["vies"], sinal=True),
                    12,
                    TEXTO,
                    font_weight="600",
                ),
                texto(cx, topo + alto - m_base + 16, l1, 11),
                texto(cx, topo + alto - m_base + 29, l2, 11),
            ]
    return figura(
        "Viés por faixa de preço pedido",
        "Mediana de previsto ÷ pedido − 1, em 5 faixas com o mesmo número de anúncios.",
        topo + alto + 10,
        corpo,
        modelos,
    )


def grafico_importancia(dados: dict[str, list[Importancia]], modelos: str) -> str:
    topo, passo, rot = 100, 28, 170
    n = max(len(v) for v in dados.values())
    corpo: list[str] = []
    for x0, chave, rotulo, _ in paineis():
        d = dados[chave]
        maior = max(f["peso"] for f in d)
        corpo.append(texto(x0, topo - 14, rotulo, 13, TEXTO, "start", font_weight="600"))
        for i, f in enumerate(d):
            yy = topo + i * passo
            larg = max(2.0, f["peso"] / maior * (PAINEL - rot - 44))
            corpo += [
                texto(x0, yy + 10, f["atributo"], 12, EIXO, "start"),
                f'<rect x="{x0 + rot}" y="{yy}" width="{_n(larg)}" height="12" rx="3" fill="{SERIE}"/>',
                texto(
                    x0 + rot + larg + 6,
                    yy + 10,
                    "<1%" if f["peso"] < 0.005 else pct(f["peso"]),
                    12,
                    TEXTO,
                    "start",
                    font_weight="600",
                ),
            ]
    return figura(
        "O que pesa na estimativa",
        "Redução de erro nas árvores, por informação; bairros e tipos somados. Uso, não causa.",
        topo + n * passo + 6,
        corpo,
        modelos,
    )


# ---------------------------------------------------------------- README


def bloco_readme(m: dict[str, dict[str, object]]) -> str:
    def t(neg: str) -> dict[str, float]:
        teste = cast(dict[str, float], m[neg]["teste"])
        met = cast(dict[str, dict[str, float]], m[neg]["teste"])["metricas"]
        return {
            "n": teste["n_teste"],
            "r2": met["R2_log"],
            "mdape": met["MdAPE%"] / 100,
            "d20": met["dentro20%"] / 100,
            "cob": teste["cobertura"],
            "razao": teste["razao_media_hi_lo"],
        }

    v, a = t("venda"), t("aluguel")
    return "\n".join(
        [
            INICIO,
            "<!-- gerado por ml/pipeline/graficos_readme.py a partir do modelo publicado -->",
            "",
            f"| | Venda ({inteiro(v['n'])} anúncios) | Aluguel ({inteiro(a['n'])} anúncios) |",
            "|---|---:|---:|",
            f"| R² em log | {decimal(v['r2'], 3)} | {decimal(a['r2'], 3)} |",
            f"| Erro mediano (MdAPE) | {pct(v['mdape'], 1)} | {pct(a['mdape'], 1)} |",
            f"| Estimativa central a ±20% do pedido | {pct(v['d20'], 1)} | {pct(a['d20'], 1)} |",
            f"| Cobertura da faixa de 80% | {pct(v['cob'], 1)} | {pct(a['cob'], 1)} |",
            f"| Limite superior ÷ inferior da faixa | {decimal(v['razao'])}× | {decimal(a['razao'])}× |",
            "",
            "Os gráficos usam previsões fora da amostra (validação cruzada agrupada em treino e",
            "validação), sem reabrir o teste. A mesma fonte alimenta a página Como Funciona do site.",
            "",
            '<p align="center">',
            '  <img alt="Previsto contra pedido por faixa de preço" '
            'src="docs/graficos/previsto-pedido.svg" width="100%">',
            '  <img alt="Viés por faixa de preço" src="docs/graficos/vies-por-faixa.svg" width="100%">',
            '  <img alt="Importância de cada informação" src="docs/graficos/importancia.svg" '
            'width="100%">',
            "</p>",
            FIM,
        ]
    )


def gerar(metricas: dict[str, dict[str, object]], readme: str) -> tuple[dict[str, str], str]:
    """Arquivos SVG (nome → conteúdo) e o README com o bloco de resultados trocado."""
    modelos = ", ".join(f"{n}={metricas[n]['modelo']}" for n, _, _ in NEGOCIOS)

    def campo(nome: str) -> dict[str, object]:
        return {n: metricas[n][nome] for n, _, _ in NEGOCIOS}

    svgs = {
        "previsto-pedido.svg": grafico_calibracao(
            cast(dict[str, list[Calibracao]], campo("calibracao")), modelos
        ),
        "vies-por-faixa.svg": grafico_vies(cast(dict[str, list[Vies]], campo("vies")), modelos),
        "importancia.svg": grafico_importancia(
            cast(dict[str, list[Importancia]], campo("importancia")), modelos
        ),
    }
    if readme.count(INICIO) != 1 or readme.count(FIM) != 1:
        raise ValueError(f"README precisa de exatamente um par {INICIO} … {FIM}")
    antes, resto = readme.split(INICIO)
    _, depois = resto.split(FIM)
    return svgs, antes + bloco_readme(metricas) + depois


def main(metricas_path: Path = SITE_METRICAS) -> None:
    metricas = json.loads(metricas_path.read_text("utf-8"))
    svgs, readme = gerar(metricas, README.read_text("utf-8"))
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in svgs.items():
        (GRAFICOS_DIR / nome).write_text(conteudo, "utf-8")
    README.write_text(readme, "utf-8")
    print(
        f"[OK] {len(svgs)} gráficos em {GRAFICOS_DIR.relative_to(PROJECT_ROOT)} e README atualizado"
    )


if __name__ == "__main__":
    main()
