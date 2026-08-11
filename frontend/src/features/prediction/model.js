// Inferência no cliente: soma das 200 árvores do GradientBoosting exportado
// por ml/pipeline/export_web.py. Sem runtime de ML, sem WASM — a travessia é
// aritmética de índice sobre arrays achatados.
//
// A paridade com o sklearn está travada em features.test.js contra fixtures
// geradas pelo Python. Mudou a matemática aqui? O teste quebra.

import { buildFeatureVector, nivelConfianca } from "./features";

const MODEL_URL = `${import.meta.env.BASE_URL}model/especulai.json`;

let carregando = null;

/** Carrega o modelo uma única vez por sessão. */
export function loadModel() {
	if (!carregando) {
		carregando = fetch(MODEL_URL)
			.then((r) => {
				if (!r.ok) throw new Error(`Modelo indisponível (HTTP ${r.status})`);
				return r.json();
			})
			.catch((err) => {
				// Sem isto, uma falha de rede transitória envenena o cache para sempre.
				carregando = null;
				throw err;
			});
	}
	return carregando;
}

/** Lista de bairros que o modelo conhece — alimenta o autocomplete. */
export async function listarBairros() {
	const modelo = await loadModel();
	return modelo.bairros;
}

/** Normaliza o vetor cru com os mesmos mean/scale do StandardScaler do treino. */
function escalar(vetor, { mean, scale }) {
	return vetor.map((v, i) => (v - mean[i]) / scale[i]);
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

// As árvores do sklearn comparam o valor JÁ convertido para float32 contra um
// threshold em float64. Sem replicar a conversão, um valor a 1e-8 do corte
// desce pelo ramo errado — visto na prática: 9 em 300 casos, até 1,3% de erro.
const paraFloat32 = (v) => Math.fround(v);

/** preco = init + learning_rate * Σ folhas — a definição do GradientBoosting. */
export function predictFromVector(vetor, modelo) {
	const x = escalar(vetor, modelo.scaler).map(paraFloat32);
	const { trees } = modelo;

	let soma = 0;
	for (const raiz of trees.roots) {
		soma += percorrer(trees, raiz, x);
	}

	return modelo.init + modelo.learning_rate * soma;
}

/**
 * @param {{area:number, quartos:number, banheiros:number, tipo:string, bairro:string}} entrada
 * @returns {Promise<{preco_estimado:number, confianca:string}>}
 */
export async function predictImovel(entrada) {
	const modelo = await loadModel();
	const { vetor, bairro, temPerfil } = buildFeatureVector(entrada, modelo);

	return {
		preco_estimado: predictFromVector(vetor, modelo),
		confianca: nivelConfianca({
			bairro,
			temPerfil,
			tipo: String(entrada.tipo ?? "").toLowerCase(),
			area: Math.max(Number(entrada.area), 1),
		}),
	};
}
