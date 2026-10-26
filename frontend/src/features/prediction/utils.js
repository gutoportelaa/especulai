const TITLE_CASE_EXCEPTIONS = ["do", "da", "dos", "das", "de"];

const toNumber = (value, parser = Number.parseFloat) => {
	const num = parser(value);
	return Number.isFinite(num) ? num : 0;
};

const titleCase = (value) => {
	return value
		.toLowerCase()
		.split(" ")
		.filter(Boolean)
		.map((word, index) => {
			if (index !== 0 && TITLE_CASE_EXCEPTIONS.includes(word)) return word;
			return word.charAt(0).toUpperCase() + word.slice(1);
		})
		.join(" ");
};

export function normalizePredictionPayload(formData) {
	const vagas = String(formData.vagas ?? "").trim();

	return {
		negocio: formData.negocio === "aluguel" ? "aluguel" : "venda",
		area: toNumber(formData.area),
		quartos: toNumber(formData.quartos, Number.parseInt),
		banheiros: toNumber(formData.banheiros, Number.parseInt),
		vagas: vagas === "" ? null : toNumber(vagas, Number.parseInt),
		tipo: (formData.tipo || "apartamento").toLowerCase(),
		bairro: titleCase(formData.bairro || ""),
	};
}
