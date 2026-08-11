// Paridade de PREÇO entre o JS e o sklearn. features.test.js cobre a montagem
// do vetor; aqui a conta que transforma o vetor em reais.
//
// As fixtures vêm de tests/test_web_export_parity.py — regere com
// `make export-web && uv run pytest tests/`.

import { describe, expect, test } from "bun:test";

import modelo from "../../../public/model/especulai.json";
import fixtures from "./__fixtures__/parity.json";
import { buildFeatureVector } from "./features";
import { predictFromVector } from "./model";

describe("predictFromVector", () => {
	test.each(
		fixtures.map((f) => [`${f.entrada.bairro} ${f.entrada.area}m2`, f]),
	)("preço bate com o sklearn: %s", (_nome, fixture) => {
		const preco = predictFromVector(fixture.vetor, modelo);
		// Só o arredondamento das folhas (4 casas) separa os dois.
		expect(preco).toBeCloseTo(fixture.preco, 2);
	});

	test("bairro conhecido e desconhecido dão preços diferentes", () => {
		const base = { area: 90, quartos: 3, banheiros: 2, tipo: "apartamento" };
		const comBairro = buildFeatureVector({ ...base, bairro: "Fátima" }, modelo);
		const semBairro = buildFeatureVector(
			{ ...base, bairro: "Nao Existe" },
			modelo,
		);

		expect(predictFromVector(comBairro.vetor, modelo)).not.toBeCloseTo(
			predictFromVector(semBairro.vetor, modelo),
			2,
		);
	});

	test("área maior no mesmo bairro não reduz o preço", () => {
		const base = {
			quartos: 3,
			banheiros: 2,
			tipo: "apartamento",
			bairro: "Fátima",
		};
		const precos = [50, 100, 200, 400].map((area) =>
			predictFromVector(
				buildFeatureVector({ ...base, area }, modelo).vetor,
				modelo,
			),
		);

		for (let i = 1; i < precos.length; i++) {
			expect(precos[i]).toBeGreaterThanOrEqual(precos[i - 1]);
		}
	});

	test("todo preço é finito e positivo", () => {
		for (const bairro of modelo.bairros) {
			const { vetor } = buildFeatureVector(
				{ area: 90, quartos: 3, banheiros: 2, tipo: "apartamento", bairro },
				modelo,
			);
			const preco = predictFromVector(vetor, modelo);
			expect(Number.isFinite(preco)).toBe(true);
			expect(preco).toBeGreaterThan(0);
		}
	});
});

describe("integridade do modelo exportado", () => {
	test("uma raiz por árvore do GradientBoosting", () => {
		expect(modelo.trees.roots).toHaveLength(200);
		expect(modelo.learning_rate).toBeCloseTo(0.1, 10);
	});

	test("arrays de nós têm o mesmo comprimento", () => {
		const { left, right, feature, threshold, value } = modelo.trees;
		const n = left.length;
		expect(right).toHaveLength(n);
		expect(feature).toHaveLength(n);
		expect(threshold).toHaveLength(n);
		expect(value).toHaveLength(n);
	});

	test("scaler cobre todas as features", () => {
		expect(modelo.scaler.mean).toHaveLength(modelo.feature_columns.length);
		expect(modelo.scaler.scale).toHaveLength(modelo.feature_columns.length);
		expect(modelo.scaler.scale.every((s) => s > 0)).toBe(true);
	});
});
