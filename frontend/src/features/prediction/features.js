// Montagem do vetor de features — espelho exato de
// ModelService._predict_standard (apps/api/services/model_service.py).
// Qualquer divergência aqui muda o preço em silêncio, então o contrato está
// travado por fixtures em __fixtures__/parity.json (ver features.test.js).

/** Chave de comparação de bairro: sem acento, sem caixa, sem separadores. */
export function normalizeBairro(value) {
	return String(value ?? "")
		.normalize("NFKD")
		.replace(/\p{Diacritic}/gu, "")
		.toLowerCase()
		.replace(/[^a-z0-9]/g, "");
}

/**
 * Casa o bairro digitado com uma coluna one-hot do modelo.
 * @returns {{nome: string, coluna: string} | null} null se não houve no treino.
 */
export function resolveBairro(bairroRaw, featureColumns) {
	const alvo = normalizeBairro(bairroRaw);
	if (!alvo) return null;

	for (const col of featureColumns) {
		if (!col.startsWith("Bairro_")) continue;
		const nome = col.slice("Bairro_".length);
		if (normalizeBairro(nome) === alvo) return { nome, coluna: col };
	}
	return null;
}

/**
 * Monta o vetor na ordem de featureColumns. Precedência por coluna:
 * entrada do usuário > one-hot do bairro > perfil mediano do bairro >
 * mediana global do treino. O preenchimento por mediana é o que impede que
 * colunas não informadas virem 0 e achatem a predição.
 */
export function buildFeatureVector(entrada, meta) {
	const {
		feature_columns: colunas,
		feature_defaults: padroes,
		bairro_profiles: perfis,
	} = meta;

	const area = Math.max(Number(entrada.area), 1);
	const quartos = Math.trunc(Number(entrada.quartos));
	const banheiros = Math.trunc(Number(entrada.banheiros));

	const bairro = resolveBairro(entrada.bairro, colunas);
	const perfil = (bairro && perfis[bairro.nome]) || {};

	const informado = {
		Area_m2: area,
		Quartos: quartos,
		Banheiros: banheiros,
		densidade_comodos: (quartos + banheiros) / area,
	};

	const vetor = colunas.map((col) => {
		if (col in informado) return informado[col];
		if (col.startsWith("Bairro_"))
			return bairro && col === bairro.coluna ? 1 : 0;
		if (col in perfil) return perfil[col];
		return padroes[col] ?? 0;
	});

	return { vetor, bairro, temPerfil: Object.keys(perfil).length > 0 };
}

/** Confiança pelo quanto da entrada o modelo realmente viu no treino. */
export function nivelConfianca({ bairro, temPerfil, tipo, area }) {
	if (!bairro) return "baixa";
	if (!temPerfil || !["apartamento", "casa"].includes(tipo)) return "média";
	if (area < 20 || area > 1000) return "média";
	return "alta";
}
