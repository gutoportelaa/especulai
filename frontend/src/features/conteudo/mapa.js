import { numero, pct, reaisCompacto } from "./formato";
import dados from "./mapa-bairros.json";

// `mapa-bairros.json` é gerado por `ml/pipeline/mapa_bairros.py` (no `make export-web`) a partir do
// modelo publicado e da malha de bairros do IBGE. Não edite à mão: `tests/test_metricas_site.py` confere.

export const MAPA = dados;

const ordemNome = (a, b) => a.nome.localeCompare(b.nome, "pt-BR");
export const BAIRROS_POR_NOME = [...dados.bairros].sort(ordemNome);
export const BAIRRO_POR_ID = Object.fromEntries(
	dados.bairros.map((b) => [b.id, b]),
);

/** R$ 7.450 na venda, R$ 33,3 no aluguel: abaixo de R$ 100/m² a casa decimal importa. */
export function reaisM2(valor) {
	return `R$ ${valor.toLocaleString("pt-BR", { maximumFractionDigits: valor < 100 ? 1 : 0 })}`;
}

/** "R$ 6.020/m²" na venda, "R$ 34,8/m² ao mês" no aluguel. */
export function precoM2(valor, sufixo) {
	return `${reaisM2(valor)}/m²${sufixo ? " ao mês" : ""}`;
}

// Um tom só, do claro ao escuro (magnitude); a rampa começa longe do branco da página.
export const RAMPA = ["#dbe5fc", "#a6c0f6", "#6b93ec", "#2b63df", "#0a3a9e"];
export const SEM_DADOS = "#f4f4f5";

/**
 * Métricas que colorem o mapa. `valor` devolve `undefined` quando o bairro não tem dado. Quando há
 * `legenda`, a unidade vai uma vez no título da legenda (`unidade`) em vez de em cada classe.
 */
export const METRICAS_MAPA = [
	{
		id: "m2",
		rotulo: "R$/m² pedido",
		titulo: "Preço pedido mediano por m²",
		valor: (d) => d.m2,
		formato: (v, sufixo) => precoM2(v, sufixo),
		legenda: (v) => reaisM2(v),
		unidade: (sufixo) => (sufixo ? ", ao mês" : ""),
	},
	{
		id: "imoveis",
		rotulo: "Imóveis anunciados",
		titulo: "Imóveis distintos nos anúncios de treino e validação",
		valor: (d) => (d.imoveis > 0 ? d.imoveis : undefined),
		formato: (v) => numero(v),
	},
	{
		id: "padrao",
		rotulo: "Imóvel padrão",
		titulo: "Estimativa central para o mesmo imóvel em cada bairro",
		valor: (d) => d.padrao.central,
		formato: (v, sufixo) => `${reaisCompacto(v)}${sufixo}`,
		legenda: (v) => reaisCompacto(v),
		unidade: (sufixo) => (sufixo ? ", por mês" : ""),
	},
	{
		id: "erro",
		rotulo: "Erro do modelo",
		titulo:
			"Erro mediano da estimativa central, em anúncios que o modelo não viu",
		valor: (d) => d.erro,
		formato: (v) => pct(v, { casas: 0 }),
	},
];

/** Cortes por quantil: `k` classes com quantidades parecidas de bairros. Cortes repetidos somem. */
export function cortesQuantil(valores, k = RAMPA.length) {
	const v = valores.filter((x) => x !== undefined).sort((a, b) => a - b);
	if (v.length === 0) return [];
	const cortes = [];
	for (let i = 1; i < k; i++) {
		const c = v[Math.floor((i * v.length) / k)];
		if (c > v[0] && !cortes.includes(c)) cortes.push(c);
	}
	return cortes;
}

/** Índice da classe: abaixo do primeiro corte é 0; igual a um corte já sobe de classe. */
export function classe(valor, cortes) {
	let i = 0;
	while (i < cortes.length && valor >= cortes[i]) i++;
	return i;
}

/** Cor da rampa espalhada pelas classes que existem (com 3 classes: claro, meio, escuro). */
export function corDaClasse(i, nClasses) {
	if (nClasses <= 1) return RAMPA[RAMPA.length - 1];
	return RAMPA[Math.round((i * (RAMPA.length - 1)) / (nClasses - 1))];
}
