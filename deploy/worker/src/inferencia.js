// Inferência sem sklearn: monta o vetor de features e soma as árvores exportadas.
// Espelha ml.experiments.baseline_atributos.matriz e ml.experiments.renda_ibge.X_com, o código
// que o treino usa. test/inferencia.test.js trava a paridade contra as fixtures geradas por
// tests/test_web_export_parity.py a partir do sklearn.

const MAGIC = new TextEncoder().encode("ESPC2");
const AAD = new TextEncoder().encode("especulai-modelo-v2");
const TAM_NONCE = 12;
const MIN_AMOSTRAS_BAIRRO = 15;

const hexParaBytes = (hex) =>
	Uint8Array.from(hex.match(/../g) ?? [], (b) => Number.parseInt(b, 16));

/** Abre um modelo cifrado por ml/pipeline/cifrar_modelo.py (AES-256-GCM). */
export async function decifrar(buffer, chaveHex) {
	const bytes = new Uint8Array(buffer);
	if (!MAGIC.every((b, i) => bytes[i] === b)) throw new Error("arquivo de modelo inválido");
	if (!/^[0-9a-f]{64}$/i.test(chaveHex ?? "")) throw new Error("MODEL_KEY ausente ou inválida");
	const inicio = MAGIC.length;
	const chave = await crypto.subtle.importKey("raw", hexParaBytes(chaveHex), "AES-GCM", false, [
		"decrypt",
	]);
	const claro = await crypto.subtle.decrypt(
		{
			name: "AES-GCM",
			iv: bytes.slice(inicio, inicio + TAM_NONCE),
			additionalData: AAD,
		},
		chave,
		bytes.slice(inicio + TAM_NONCE),
	);
	return JSON.parse(new TextDecoder().decode(claro));
}

/** Chave de comparação: sem acento, sem caixa, sem separadores (igual à do treino). */
export function chaveNormalizada(valor) {
	return String(valor ?? "")
		.normalize("NFKD")
		.replace(/[^\x00-\x7f]/g, "")
		.toLowerCase()
		.replace(/[^a-z0-9]/g, "");
}

export function resolver(valor, colunas, prefixo) {
	const alvo = chaveNormalizada(valor);
	if (!alvo) return null;
	for (const col of colunas) {
		if (!col.startsWith(prefixo)) continue;
		const nome = col.slice(prefixo.length);
		if (chaveNormalizada(nome) === alvo) return nome;
	}
	return null;
}

/**
 * Vagas não informadas seguem o treino: 0 vagas e Vagas_informado = 0. Bairro sem renda no IBGE
 * (ou fora do treino) usa -1 e IBGE_casou = 0.
 */
export function montarVetor(entrada, modelo) {
	const colunas = modelo.feature_columns;
	const bairro = resolver(entrada.bairro, colunas, "Bairro_");
	const tipo = resolver(entrada.tipo, colunas, "Tipo_Imovel_");
	const info = bairro ? (modelo.bairro_info[bairro] ?? null) : null;
	const vagas = entrada.vagas ?? null;

	const informado = {
		Area_m2: Math.max(Number(entrada.area), 1),
		Quartos: Math.trunc(Number(entrada.quartos)),
		Banheiros: Math.trunc(Number(entrada.banheiros)),
		Vagas_Garagem: vagas ?? 0,
		Vagas_informado: vagas === null ? 0 : 1,
		Renda_bairro: info ? info.renda : -1,
		Densidade_bairro: info ? info.densidade : -1,
		IBGE_casou: info ? info.casou : 0,
	};
	const ativas = new Set([bairro && `Bairro_${bairro}`, tipo && `Tipo_Imovel_${tipo}`]);
	const vetor = colunas.map((c) => (c in informado ? informado[c] : ativas.has(c) ? 1 : 0));
	return { vetor, achouBairro: bairro !== null, achouTipo: tipo !== null, n: info ? info.n : 0 };
}

/** Log do preço. O sklearn compara X já em float32 contra um threshold em float64. */
export function preverLog(vetor, modelo) {
	const x = vetor.map(Math.fround);
	const t = modelo.trees;
	let soma = 0;
	for (const raiz of t.roots) {
		let no = raiz;
		while (t.feature[no] !== -1) {
			no = x[t.feature[no]] <= t.threshold[no] ? t.left[no] : t.right[no];
		}
		soma += t.value[no];
	}
	return modelo.init + modelo.learning_rate * soma;
}

/** Meia-largura em log por terço de preço previsto; o corte pertence à faixa de baixo. */
export function intervalo(preco, { cortes, meia_largura: largura }) {
	const w = largura[cortes.filter((c) => c < preco).length];
	return [preco * Math.exp(-w), preco * Math.exp(w)];
}

export function confianca({ achouBairro, achouTipo, n, area }) {
	if (!achouBairro) return "baixa";
	if (!achouTipo || n < MIN_AMOSTRAS_BAIRRO || area < 15 || area > 1000) return "média";
	return "alta";
}

/** Faixa de preço pedido não precisa de centavos; arredondar também reduz o que uma sequência
 * de consultas revelaria do modelo. */
export function arredondar(valor) {
	const passo = valor >= 10_000 ? 1000 : 10;
	return Math.round(valor / passo) * passo;
}

export function estimar(negocio, entrada, modelo) {
	const { vetor, ...achou } = montarVetor(entrada, modelo);
	const preco = Math.exp(preverLog(vetor, modelo));
	const [minimo, maximo] = intervalo(preco, modelo.intervalo);
	return {
		negocio,
		preco_estimado: arredondar(preco),
		minimo: arredondar(minimo),
		maximo: arredondar(maximo),
		nivel: modelo.intervalo.nivel,
		confianca: confianca({ ...achou, area: Math.max(Number(entrada.area), 1) }),
	};
}
