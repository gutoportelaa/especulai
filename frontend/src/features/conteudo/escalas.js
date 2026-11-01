/** Escala log de [min, max] para [a, b] em pixels. */
export function escalaLog([min, max], [a, b]) {
	const l0 = Math.log(min);
	const l1 = Math.log(max);
	return (v) => a + ((Math.log(v) - l0) / (l1 - l0)) * (b - a);
}

/** Escala linear de [min, max] para [a, b] em pixels. */
export function escalaLinear([min, max], [a, b]) {
	return (v) => a + ((v - min) / (max - min)) * (b - a);
}

/** Marcas 1-2-5 × 10^k dentro do domínio; se sobrarem muitas, fica só com as potências de 10 e 5. */
export function marcasLog([min, max], maximo = 6) {
	const marcas = [];
	for (
		let k = Math.floor(Math.log10(min));
		k <= Math.ceil(Math.log10(max));
		k++
	) {
		for (const m of [1, 2, 5]) {
			const v = m * 10 ** k;
			if (v >= min && v <= max) marcas.push(v);
		}
	}
	if (marcas.length <= maximo) return marcas;
	const enxutas = marcas.filter((v) => {
		const m = v / 10 ** Math.floor(Math.log10(v) + 1e-9);
		return Math.abs(m - 1) < 1e-9 || Math.abs(m - 5) < 1e-9;
	});
	return enxutas.length >= 2 ? enxutas : marcas;
}

/** Limite simétrico múltiplo de 10 pp, para que a metade (marca intermediária) seja redonda. */
export function limiteSimetrico(valores, folga = 1.2) {
	const pico = Math.max(...valores.map(Math.abs)) * folga;
	return Math.max(0.1, Math.ceil(pico * 10 - 1e-9) / 10);
}
