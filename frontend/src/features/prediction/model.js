// Inferência no cliente: soma das 200 árvores do GradientBoosting exportado por
// ml/pipeline/export_web.py. Sem runtime de ML, sem WASM — a travessia é aritmética de
// índice sobre arrays achatados. Um modelo por negócio (venda, aluguel), alvo em log.
//
// A paridade com o sklearn está travada em model.test.js contra fixtures geradas pelo Python.

import { buildFeatureVector, nivelConfianca } from "./features";

export const NEGOCIOS = ["venda", "aluguel"];

const modeloUrl = (negocio) =>
	`${import.meta.env.BASE_URL}model/especulai-${negocio}.json`;

const carregando = {};

/** Carrega o modelo de um negócio uma única vez por sessão. */
export function loadModel(negocio) {
	if (!NEGOCIOS.includes(negocio)) {
		return Promise.reject(new Error(`Negócio desconhecido: ${negocio}`));
	}
	if (!carregando[negocio]) {
		carregando[negocio] = fetch(modeloUrl(negocio))
			.then((r) => {
				if (!r.ok) throw new Error(`Modelo indisponível (HTTP ${r.status})`);
				return r.json();
			})
			.catch((err) => {
				// Sem isto, uma falha de rede transitória envenena o cache para sempre.
				carregando[negocio] = null;
				throw err;
			});
	}
	return carregando[negocio];
}

/** Bairros que o modelo conhece — alimenta o autocomplete. */
export async function listarBairros(negocio = "venda") {
	return (await loadModel(negocio)).bairros;
}

/** Desce uma árvore até a folha. `raiz` é o índice do nó inicial nos arrays. */
function percorrer(trees, raiz, x) {
	let no = raiz;
	// feature === -1 marca folha; nós internos sempre têm os dois filhos.
	while (trees.feature[no] !== -1) {
		no =
			x[trees.feature[no]] <= trees.threshold[no]
				? trees.left[no]
				: trees.right[no];
	}
	return trees.value[no];
}

/** Log do preço: init + learning_rate * Σ folhas. */
export function predictLog(vetor, modelo) {
	// As árvores do sklearn comparam X JÁ convertido para float32 contra um threshold float64.
	const x = vetor.map(Math.fround);
	let soma = 0;
	for (const raiz of modelo.trees.roots)
		soma += percorrer(modelo.trees, raiz, x);
	return modelo.init + modelo.learning_rate * soma;
}

export function predictFromVector(vetor, modelo) {
	return Math.exp(predictLog(vetor, modelo));
}

/** Limites do intervalo: a meia-largura (em log) depende do terço de preço previsto. */
export function intervaloDe(preco, { cortes, meia_largura: largura, nivel }) {
	const faixa = cortes.filter((c) => c < preco).length;
	const w = largura[faixa];
	return { minimo: preco * Math.exp(-w), maximo: preco * Math.exp(w), nivel };
}

/**
 * @param {"venda"|"aluguel"} negocio
 * @param {{area:number, quartos:number, banheiros:number, tipo:string, bairro:string, vagas?:number}} entrada
 */
export async function predictImovel(negocio, entrada) {
	const modelo = await loadModel(negocio);
	const { vetor, bairro, tipo, n } = buildFeatureVector(entrada, modelo);
	const preco = predictFromVector(vetor, modelo);

	return {
		negocio,
		preco_estimado: preco,
		...intervaloDe(preco, modelo.intervalo),
		confianca: nivelConfianca({
			bairro,
			tipo,
			n,
			area: Math.max(Number(entrada.area), 1),
		}),
	};
}
