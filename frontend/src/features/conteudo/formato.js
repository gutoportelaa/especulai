const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

export const numero = (valor) => inteiro.format(valor);

export const reais = (valor) => `R$ ${inteiro.format(valor)}`;

/** R$ 1.800 · R$ 450 mil · R$ 1,2 mi — para eixos, rótulos e textos corridos. */
export function reaisCompacto(valor) {
	if (valor >= 1e6) {
		const mi = valor / 1e6;
		return `R$ ${mi.toLocaleString("pt-BR", { maximumFractionDigits: mi < 10 ? 1 : 0 })} mi`;
	}
	if (valor >= 1e4) return `R$ ${inteiro.format(valor / 1000)} mil`;
	return reais(valor);
}

/** Fração (0,814) ou pontos percentuais (21,06) para "81,4%"; `pp` diz qual é a entrada. */
export function pct(valor, { casas = 1, pp = false, sinal = false } = {}) {
	const p = pp ? valor : valor * 100;
	const texto = Math.abs(p).toLocaleString("pt-BR", {
		minimumFractionDigits: casas,
		maximumFractionDigits: casas,
	});
	const prefixo = p < 0 ? "−" : sinal && p > 0 ? "+" : "";
	return `${prefixo}${texto}%`;
}

export const decimal = (valor, casas = 2) =>
	valor.toLocaleString("pt-BR", {
		minimumFractionDigits: casas,
		maximumFractionDigits: casas,
	});
