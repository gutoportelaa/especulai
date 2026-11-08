import demo from "./demo-hero.json";
import { reaisCompacto } from "./formato";

// `demo-hero.json` sai de `ml/pipeline/mapa_bairros.py`: limites dos bairros (só o desenho) e os
// bairros com confiança alta, cada um com a estimativa do modelo para o mesmo imóvel padrão.

export const N_PINS = 7;
const TENTATIVAS = 30;
// Em unidades do mapa: dois pins só ficam perto se um estiver bem acima do outro (ícone + etiqueta)
// ou bem ao lado (etiqueta mais larga).
export const AFASTAMENTO = { x: 190, y: 150 };

export function afastados(a, b) {
	return (
		Math.abs(a.x - b.x) >= AFASTAMENTO.x || Math.abs(a.y - b.y) >= AFASTAMENTO.y
	);
}

export const NEGOCIO_DEMO = {
	venda: { rotulo: "Venda", sufixo: "", etiqueta: reaisCompacto },
	aluguel: {
		rotulo: "Aluguel",
		sufixo: "/mês",
		etiqueta: reaisCompacto, // "/mês" fica no card e no selo, a etiqueta cabe no mapa
	},
};

function umSorteio(pool, aleatorio) {
	const embaralhado = [...pool];
	for (let i = embaralhado.length - 1; i > 0; i--) {
		const j = Math.floor(aleatorio() * (i + 1));
		[embaralhado[i], embaralhado[j]] = [embaralhado[j], embaralhado[i]];
	}
	const escolhidos = [];
	for (const c of embaralhado) {
		if (escolhidos.every((e) => afastados(e, c))) escolhidos.push(c);
		if (escolhidos.length === N_PINS) break;
	}
	return escolhidos;
}

/**
 * Bairros sorteados entre os candidatos do negócio, sem etiquetas se encostando. No aluguel os
 * candidatos se concentram no centro, então vale o melhor de vários sorteios.
 */
export function sortearPins(
	negocio,
	aleatorio = Math.random,
	candidatos = demo.candidatos,
) {
	const pool = candidatos.filter((c) => c[negocio]);
	let melhor = [];
	for (let t = 0; t < TENTATIVAS && melhor.length < N_PINS; t++) {
		const s = umSorteio(pool, aleatorio);
		if (s.length > melhor.length) melhor = s;
	}
	return melhor.map((c) => ({ ...c, ...c[negocio] }));
}
