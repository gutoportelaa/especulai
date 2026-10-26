// Montagem do vetor de features — espelho de ml.experiments.baseline_atributos.matriz e
// ml.experiments.renda_ibge.X_com (o que o treino usa). Qualquer divergência muda o preço em
// silêncio, então o contrato está travado por fixtures em __fixtures__/parity.json
// (geradas por tests/test_web_export_parity.py a partir do código de treino).

/** Chave de comparação: sem acento, sem caixa, sem separadores. */
export function normalizeBairro(value) {
	return String(value ?? "")
		.normalize("NFKD")
		.replace(/\p{Diacritic}/gu, "")
		.toLowerCase()
		.replace(/[^a-z0-9]/g, "");
}

function resolverColuna(valor, prefixo, featureColumns) {
	const alvo = normalizeBairro(valor);
	if (!alvo) return null;
	for (const col of featureColumns) {
		if (!col.startsWith(prefixo)) continue;
		const nome = col.slice(prefixo.length);
		if (normalizeBairro(nome) === alvo) return { nome, coluna: col };
	}
	return null;
}

/** @returns {{nome: string, coluna: string} | null} null se o bairro não existe no treino. */
export function resolveBairro(bairroRaw, featureColumns) {
	return resolverColuna(bairroRaw, "Bairro_", featureColumns);
}

export function resolveTipo(tipoRaw, featureColumns) {
	return resolverColuna(tipoRaw, "Tipo_Imovel_", featureColumns);
}

const semVagas = (v) => v === undefined || v === null || v === "";

/**
 * Monta o vetor na ordem de feature_columns. Vagas não informadas seguem o treino: 0 vagas e
 * Vagas_informado = 0. Bairro sem renda no IBGE (ou fora do treino) usa -1 e IBGE_casou = 0.
 */
export function buildFeatureVector(entrada, meta) {
	const { feature_columns: colunas, bairro_info: info } = meta;

	const bairro = resolveBairro(entrada.bairro, colunas);
	const tipo = resolveTipo(entrada.tipo, colunas);
	const dadosBairro = (bairro && info[bairro.nome]) || null;
	const vagas = semVagas(entrada.vagas) ? null : Number(entrada.vagas);

	const informado = {
		Area_m2: Math.max(Number(entrada.area), 1),
		Quartos: Math.trunc(Number(entrada.quartos)),
		Banheiros: Math.trunc(Number(entrada.banheiros)),
		Vagas_Garagem: vagas ?? 0,
		Vagas_informado: vagas === null ? 0 : 1,
		Renda_bairro: dadosBairro ? dadosBairro.renda : -1,
		Densidade_bairro: dadosBairro ? dadosBairro.densidade : -1,
		IBGE_casou: dadosBairro ? dadosBairro.casou : 0,
	};

	const vetor = colunas.map((col) => {
		if (col in informado) return informado[col];
		if (bairro && col === bairro.coluna) return 1;
		if (tipo && col === tipo.coluna) return 1;
		return 0;
	});

	return { vetor, bairro, tipo, n: dadosBairro ? dadosBairro.n : 0 };
}

/** Confiança pelo quanto o modelo viu do bairro: poucos anúncios ou fora do treino = menos. */
export function nivelConfianca({ bairro, tipo, n, area }) {
	if (!bairro) return "baixa";
	if (!tipo || n < 15 || area < 15 || area > 1000) return "média";
	return "alta";
}
