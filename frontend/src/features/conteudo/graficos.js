import { pct, reaisCompacto } from "./formato";

// Validadas com o validador de paleta do skill de dataviz (contraste e daltonismo) sobre branco.
export const CORES = {
	serie: "#044bd9",
	acima: "#044bd9",
	abaixo: "#d03b3b",
	grade: "#ececef",
	referencia: "#a1a1aa",
	eixo: "#71717a",
};

/** "250 mil", "1,2 mi", "1.800": rótulo de eixo, sem o "R$". */
export const curto = (valor) => reaisCompacto(valor).replace("R$ ", "");

export function rotuloFaixa({ de, ate }, i, total) {
	if (i === 0) return ["até", curto(ate)];
	if (i === total - 1) return ["acima de", curto(de)];
	return [curto(de), `a ${curto(ate)}`];
}

/** Frase sobre o viés que só afirma regressão à média quando os dados a mostram. */
export function resumoVies(vies) {
	const primeiro = vies[0].vies;
	const ultimo = vies[vies.length - 1].vies;
	if (primeiro > 0.05 && ultimo < -0.05) {
		return `O modelo puxa para o meio do mercado: superestima os mais baratos (${pct(primeiro, { casas: 0, sinal: true })}) e subestima os mais caros (${pct(ultimo, { casas: 0 })}). A faixa de preço é calibrada por terço justamente para compensar.`;
	}
	return "Barras perto de zero indicam que o modelo não tende para cima nem para baixo naquela faixa de preço.";
}
