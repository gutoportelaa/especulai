// Paridade de PREÇO entre o JS e o sklearn. features.test.js cobre a montagem do vetor; aqui
// a conta que o transforma em reais e no intervalo. Fixtures: tests/test_web_export_parity.py.

import { describe, expect, test } from "bun:test";

import aluguel from "../../../public/model/especulai-aluguel.json";
import venda from "../../../public/model/especulai-venda.json";
import fixtures from "./__fixtures__/parity.json";
import { buildFeatureVector } from "./features";
import { intervaloDe, predictFromVector, predictLog } from "./model";

const modelos = { venda, aluguel };

describe("predictLog", () => {
	for (const negocio of Object.keys(modelos)) {
		test.each(
			fixtures[negocio].map((f) => [
				`${f.entrada.bairro} ${f.entrada.area}m2`,
				f,
			]),
		)(`${negocio}: log-preço bate com o sklearn: %s`, (_nome, fixture) => {
			// Só o arredondamento das folhas (6 casas) separa os dois.
			expect(predictLog(fixture.vetor, modelos[negocio])).toBeCloseTo(
				fixture.log_preco,
				4,
			);
		});
	}
});

describe("comportamento", () => {
	const base = {
		quartos: 3,
		banheiros: 2,
		tipo: "Apartamento",
		bairro: "Fátima",
	};

	test("todo bairro conhecido dá preço finito e positivo", () => {
		for (const [negocio, modelo] of Object.entries(modelos)) {
			for (const bairro of modelo.bairros) {
				const { vetor } = buildFeatureVector(
					{ ...base, area: 90, bairro },
					modelo,
				);
				const preco = predictFromVector(vetor, modelo);
				expect(Number.isFinite(preco), `${negocio} ${bairro}`).toBe(true);
				expect(preco).toBeGreaterThan(0);
			}
		}
	});

	test("venda custa mais que aluguel para o mesmo imóvel", () => {
		const entrada = { ...base, area: 90 };
		const v = predictFromVector(
			buildFeatureVector(entrada, venda).vetor,
			venda,
		);
		const a = predictFromVector(
			buildFeatureVector(entrada, aluguel).vetor,
			aluguel,
		);
		expect(v).toBeGreaterThan(50 * a);
	});

	test("tipo afeta o preço", () => {
		const casa = buildFeatureVector(
			{ ...base, area: 150, tipo: "Casa" },
			venda,
		);
		const apto = buildFeatureVector({ ...base, area: 150 }, venda);
		expect(predictFromVector(casa.vetor, venda)).not.toBeCloseTo(
			predictFromVector(apto.vetor, venda),
			2,
		);
	});
});

describe("intervalo", () => {
	const iv = { cortes: [100, 200], meia_largura: [0.1, 0.2, 0.3], nivel: 0.8 };

	test("faixa escolhida pelo preço previsto", () => {
		expect(intervaloDe(50, iv).maximo).toBeCloseTo(50 * Math.exp(0.1), 9);
		expect(intervaloDe(150, iv).maximo).toBeCloseTo(150 * Math.exp(0.2), 9);
		expect(intervaloDe(900, iv).maximo).toBeCloseTo(900 * Math.exp(0.3), 9);
	});

	test("corte pertence à faixa de baixo, como np.searchsorted", () => {
		expect(intervaloDe(100, iv).maximo).toBeCloseTo(100 * Math.exp(0.1), 9);
	});

	test("simétrico em log: min × max = preço²", () => {
		const { minimo, maximo } = intervaloDe(300, iv);
		expect(minimo * maximo).toBeCloseTo(300 * 300, 6);
	});
});

describe("integridade dos modelos exportados", () => {
	for (const [negocio, m] of Object.entries(modelos)) {
		test(`${negocio}: 200 árvores, arrays alinhados e intervalo de 3 faixas`, () => {
			expect(m.trees.roots).toHaveLength(200);
			expect(m.learning_rate).toBeCloseTo(0.1, 10);
			const n = m.trees.left.length;
			for (const campo of ["right", "feature", "threshold", "value"]) {
				expect(m.trees[campo]).toHaveLength(n);
			}
			expect(m.intervalo.meia_largura).toHaveLength(3);
			expect(m.intervalo.cortes).toHaveLength(2);
			expect(m.metricas_teste.cobertura).toBeGreaterThan(0.7);
		});
	}
});
