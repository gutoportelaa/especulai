"""Corpus canônico: unifica as fontes, agrupa anúncios do mesmo imóvel e define o split.

Entrada:  data/raw_<fonte>.csv (hoje só o VivaReal; o Rocha entra quando for recoletado)
Saída:    data/canonico.csv                 um registro por anúncio, com ID_Grupo
          data/splits/<negocio>.csv         ID_Imovel, ID_Grupo, split (treino/validacao/teste)
          data/splits/amostra_pares.csv     pares agrupados, para conferência manual

Duplicatas **não são apagadas**: recebem o mesmo `ID_Grupo`, e o split é feito por grupo.
Apagar com regra aproximada é irreversível; agrupar não é e basta para evitar o vazamento
treino→teste (P20). O VivaReal traz a rua sem número, então dois apartamentos iguais no mesmo
prédio parecem o mesmo anúncio — por isso a regra "provável" é mais estrita e não mescla.
"""

from __future__ import annotations

import argparse
import logging
import re
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

from config.paths import DATA_ROOT

logger = logging.getLogger(__name__)

SPLITS_DIR = DATA_ROOT / "splits"
CANONICO_FILE = DATA_ROOT / "canonico.csv"

SEED = 42
FONTES = ("vivareal", "chaves")
FRACOES = (("treino", 0.70), ("validacao", 0.15), ("teste", 0.15))
FAIXAS_PRECO = 5  # estratos de preço para o split não depender da sorte

# Rótulos de tipo que as fontes escrevem de formas diferentes.
ALIAS_TIPO = {"Casa Em Condominio": "Casa de Condomínio"}

RESIDENCIAIS = {
    "Apartamento",
    "Casa",
    "Sobrado",
    "Casa de Condomínio",
    "Casa de Vila",
    "Kitnet",
    "Flat",
    "Cobertura",
    "Studio",
}
FAIXA_VALOR = {"aluguel": (300.0, 25_000.0), "venda": (50_000.0, 15_000_000.0)}
FAIXA_AREA = (15.0, 1500.0)

# Limiares escolhidos por julgamento, não medidos: ver amostra_pares.csv.
SIMILARIDADE_RUA = 0.75
TOL_AREA_CERTO, TOL_PRECO_CERTO = 0.02, 0.10
TOL_AREA_PROVAVEL, TOL_PRECO_PROVAVEL = 0.005, 0.05

_PREFIXOS_RUA = re.compile(r"^(rua|r|avenida|av|travessa|tv|praca|pc|alameda|estrada)\b\.?\s*")


_NUMERO_RUA = re.compile(r",?\s*(\d+)\b.*$")


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def _normaliza_rua(texto: object) -> str:
    """Nome do logradouro sem prefixo nem número ('Av. Roraima, 2250' -> 'roraima')."""
    if not isinstance(texto, str) or not texto.strip():
        return ""
    base = _NUMERO_RUA.sub("", _sem_acento(texto).lower().strip())
    return _PREFIXOS_RUA.sub("", base).strip(" ,")


def _numero_rua(texto: object) -> str:
    if not isinstance(texto, str):
        return ""
    m = _NUMERO_RUA.search(texto)
    return m.group(1) if m else ""


def _unifica_bairros(bairros: pd.Series) -> pd.Series:
    """Mesma grafia para o mesmo bairro entre fontes (acento e caixa); vale a mais frequente."""
    chave = bairros.map(lambda b: _sem_acento(str(b)).lower().strip())
    grafia = bairros.groupby(chave).agg(lambda g: g.value_counts().index[0])
    return chave.map(grafia)


def carregar_fontes() -> pd.DataFrame:
    """Lê todos os `raw_<fonte>.csv` presentes e devolve no schema canônico."""
    arquivos = [DATA_ROOT / f"raw_{fonte}.csv" for fonte in FONTES]
    arquivos = [a for a in arquivos if a.exists()]
    if not arquivos:
        raise FileNotFoundError(f"nenhum bruto de fonte em {DATA_ROOT}")
    df = pd.concat([pd.read_csv(a) for a in arquivos], ignore_index=True)
    df["Bairro"] = _unifica_bairros(df["Bairro"].fillna(""))
    df["Tipo_Negocio"] = df["Tipo_Negocio"].astype(str).str.strip().str.lower()
    df["Tipo_Imovel"] = df["Tipo_Imovel"].replace(ALIAS_TIPO)
    df["Categoria"] = np.where(df["Tipo_Imovel"].isin(RESIDENCIAIS), "residencial", "outro")
    return df


def filtrar_plausiveis(df: pd.DataFrame) -> pd.DataFrame:
    """Residencial com campos essenciais e valores dentro de faixas plausíveis."""
    df = df[df["Categoria"] == "residencial"].dropna(subset=["Area_m2", "Valor_Anuncio", "Bairro"])
    df = df[df["Area_m2"].between(*FAIXA_AREA)]
    partes = []
    for negocio, (lo, hi) in FAIXA_VALOR.items():
        sub = df[df["Tipo_Negocio"] == negocio]
        partes.append(sub[sub["Valor_Anuncio"].between(lo, hi)])
    return pd.concat(partes, ignore_index=True)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.pai = list(range(n))

    def achar(self, i: int) -> int:
        while self.pai[i] != i:
            self.pai[i] = self.pai[self.pai[i]]
            i = self.pai[i]
        return i

    def unir(self, a: int, b: int) -> None:
        self.pai[self.achar(a)] = self.achar(b)


def _proximos(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol * max(a, b)


def _nivel_par(x: pd.Series, y: pd.Series) -> str | None:
    """'certo', 'provavel' ou None. Quartos e banheiros precisam coincidir (ou faltar nos dois)."""
    if not (x["Quartos"] == y["Quartos"] or (pd.isna(x["Quartos"]) and pd.isna(y["Quartos"]))):
        return None
    if not (
        x["Banheiros"] == y["Banheiros"] or (pd.isna(x["Banheiros"]) and pd.isna(y["Banheiros"]))
    ):
        return None
    if x["_rua"] and y["_rua"]:
        # número diferente nos dois lados = prédios diferentes na mesma rua
        if x["_num"] and y["_num"] and x["_num"] != y["_num"]:
            return None
        if SequenceMatcher(None, x["_rua"], y["_rua"]).ratio() < SIMILARIDADE_RUA:
            return None
        if _proximos(x["Area_m2"], y["Area_m2"], TOL_AREA_CERTO) and _proximos(
            x["Valor_Anuncio"], y["Valor_Anuncio"], TOL_PRECO_CERTO
        ):
            return "certo"
        return None
    if _proximos(x["Area_m2"], y["Area_m2"], TOL_AREA_PROVAVEL) and _proximos(
        x["Valor_Anuncio"], y["Valor_Anuncio"], TOL_PRECO_PROVAVEL
    ):
        return "provavel"
    return None


def agrupar_duplicatas(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Atribui `ID_Grupo` por união transitiva dentro de cada bloco. Devolve (df, pares)."""
    df = df.reset_index(drop=True).copy()
    df["_rua"] = df["Endereco_Completo"].map(_normaliza_rua)
    df["_num"] = df["Endereco_Completo"].map(_numero_rua)
    uf = _UnionFind(len(df))
    pares: list[dict[str, object]] = []

    blocos = df.groupby(["Tipo_Negocio", "Tipo_Imovel", "Bairro"], sort=False).indices
    for indices in blocos.values():
        for pos, i in enumerate(indices):
            for j in indices[pos + 1 :]:
                nivel = _nivel_par(df.loc[i], df.loc[j])
                if nivel is None:
                    continue
                uf.unir(i, j)
                pares.append(
                    {"nivel": nivel, "i": df.at[i, "ID_Imovel"], "j": df.at[j, "ID_Imovel"]}
                )

    df["ID_Grupo"] = [f"g{uf.achar(i)}" for i in range(len(df))]
    df["n_no_grupo"] = df.groupby("ID_Grupo")["ID_Imovel"].transform("size")
    return df.drop(columns=["_rua", "_num"]), pd.DataFrame(pares)


def dividir_por_grupo(df: pd.DataFrame) -> pd.Series:
    """Split estratificado por faixa de preço, atribuindo grupos inteiros a cada parte."""
    rng = np.random.default_rng(SEED)
    grupos = df.groupby("ID_Grupo")["Valor_Anuncio"].median()
    faixas = pd.qcut(grupos, FAIXAS_PRECO, labels=False, duplicates="drop")
    destino: dict[str, str] = {}
    for faixa in sorted(faixas.dropna().unique()):
        ids = grupos.index[faixas == faixa].to_numpy()
        rng.shuffle(ids)
        corte1 = int(round(len(ids) * FRACOES[0][1]))
        corte2 = corte1 + int(round(len(ids) * FRACOES[1][1]))
        for k, gid in enumerate(ids):
            destino[gid] = (
                FRACOES[0][0] if k < corte1 else FRACOES[1][0] if k < corte2 else FRACOES[2][0]
            )
    return df["ID_Grupo"].map(destino)


def relatorio(df: pd.DataFrame, negocio: str) -> None:
    logger.info(
        "== %s: %d anúncios, %d imóveis (grupos)", negocio, len(df), df["ID_Grupo"].nunique()
    )
    for nome, _ in FRACOES:
        sub = df[df["split"] == nome]
        logger.info(
            "   %-9s %5d anúncios | %5d grupos | %4.1f%% | mediana R$ %s",
            nome,
            len(sub),
            sub["ID_Grupo"].nunique(),
            100 * len(sub) / len(df),
            f"{sub['Valor_Anuncio'].median():,.0f}",
        )
    treino_bairros = set(df.loc[df["split"] == "treino", "Bairro"])
    for nome in ("validacao", "teste"):
        sub = df[df["split"] == nome]
        fora = ~sub["Bairro"].isin(treino_bairros)
        logger.info("   %s: %d anúncios em bairro que o treino não viu", nome, int(fora.sum()))
    # o split precisa ser limpo: nenhum grupo em duas partes
    assert (df.groupby("ID_Grupo")["split"].nunique() == 1).all(), "grupo cruzou o split"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    argparse.ArgumentParser(description="Corpus canônico, dedup por grupo e split").parse_args()

    df = filtrar_plausiveis(carregar_fontes())
    df, pares = agrupar_duplicatas(df)
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    partes = []
    for negocio, sub in df.groupby("Tipo_Negocio"):
        sub = sub.copy()
        sub["split"] = dividir_por_grupo(sub)
        relatorio(sub, str(negocio))
        sub[["ID_Imovel", "ID_Grupo", "split"]].to_csv(SPLITS_DIR / f"{negocio}.csv", index=False)
        partes.append(sub)
    pd.concat(partes).to_csv(CANONICO_FILE, index=False)

    if not pares.empty:
        amostra = pares.groupby("nivel", group_keys=False).apply(
            lambda g: g.sample(min(len(g), 50), random_state=SEED)
        )
        amostra.to_csv(SPLITS_DIR / "amostra_pares.csv", index=False)
        logger.info("pares agrupados por nível: %s", pares["nivel"].value_counts().to_dict())
    logger.info(
        "grupos com mais de 1 anúncio: %d | maior grupo: %d anúncios",
        int((df.groupby("ID_Grupo").size() > 1).sum()),
        int(df["n_no_grupo"].max()),
    )


if __name__ == "__main__":
    main()
