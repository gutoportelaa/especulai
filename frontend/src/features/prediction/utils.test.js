import { describe, expect, test } from "bun:test";

import { normalizePredictionPayload } from "./utils";

describe("normalizePredictionPayload", () => {
	const base = {
		area: "90.5",
		quartos: "3",
		banheiros: "2",
		tipo: "Casa",
		bairro: "fÁtima",
	};

	test("converte números, tipo e bairro", () => {
		expect(normalizePredictionPayload(base)).toEqual({
			negocio: "venda",
			area: 90.5,
			quartos: 3,
			banheiros: 2,
			vagas: null,
			tipo: "casa",
			bairro: "Fátima",
		});
	});

	test("vagas vazias viram null (não informadas); zero é informado", () => {
		expect(normalizePredictionPayload({ ...base, vagas: "" }).vagas).toBeNull();
		expect(normalizePredictionPayload({ ...base, vagas: "0" }).vagas).toBe(0);
	});

	test("negócio desconhecido cai em venda", () => {
		expect(normalizePredictionPayload({ ...base, negocio: "x" }).negocio).toBe(
			"venda",
		);
		expect(
			normalizePredictionPayload({ ...base, negocio: "aluguel" }).negocio,
		).toBe("aluguel");
	});
});
