// Trava o contrato entre o JS e o `_predict_standard` do Python.
// As fixtures são geradas por tests/test_web_export_parity.py — se o pipeline
// mudar as features, regere com `make export-web && uv run pytest tests/`.

import { describe, expect, test } from "bun:test";

import meta from "../../../public/model/especulai.json";
import fixtures from "./__fixtures__/parity.json";
import {
	buildFeatureVector,
	nivelConfianca,
	normalizeBairro,
	resolveBairro,
} from "./features";

describe("normalizeBairro", () => {
	test("ignora acento, caixa e separadores", () => {
		expect(normalizeBairro("Fátima")).toBe("fatima");
		expect(normalizeBairro("FATIMA")).toBe("fatima");
		expect(normalizeBairro("São João")).toBe("saojoao");
		expect(normalizeBairro("Jóquei-Clube")).toBe("joqueiclube");
	});

	test("entrada vazia vira string vazia", () => {
		expect(normalizeBairro("")).toBe("");
		expect(normalizeBairro(null)).toBe("");
		expect(normalizeBairro(undefined)).toBe("");
	});
});

describe("resolveBairro", () => {
	test("casa bairro conhecido independente de acento", () => {
		expect(resolveBairro("fatima", meta.feature_columns)?.nome).toBe(
			resolveBairro("Fátima", meta.feature_columns)?.nome,
		);
	});

	test("bairro fora do treino não casa", () => {
		expect(
			resolveBairro("Bairro Inexistente", meta.feature_columns),
		).toBeNull();
	});

	test("bairro vazio não casa", () => {
		expect(resolveBairro("", meta.feature_columns)).toBeNull();
	});
});

describe("paridade com o Python", () => {
	test.each(
		fixtures.map((f) => [`${f.entrada.bairro} ${f.entrada.area}m2`, f]),
	)("vetor idêntico: %s", (_nome, fixture) => {
		const { vetor } = buildFeatureVector(fixture.entrada, meta);

		expect(vetor).toHaveLength(fixture.vetor.length);
		for (const [i, esperado] of fixture.vetor.entries()) {
			expect(vetor[i]).toBeCloseTo(esperado, 9);
		}
	});

	test.each(
		fixtures.map((f) => [`${f.entrada.bairro} ${f.entrada.area}m2`, f]),
	)("confiança idêntica: %s", (_nome, fixture) => {
		const { bairro, temPerfil } = buildFeatureVector(fixture.entrada, meta);
		const confianca = nivelConfianca({
			bairro,
			temPerfil,
			tipo: fixture.entrada.tipo,
			area: Math.max(Number(fixture.entrada.area), 1),
		});
		expect(confianca).toBe(fixture.confianca);
	});
});

describe("buildFeatureVector", () => {
	test("one-hot marca exatamente um bairro", () => {
		const { vetor } = buildFeatureVector(
			{
				area: 90,
				quartos: 3,
				banheiros: 2,
				tipo: "apartamento",
				bairro: "Fátima",
			},
			meta,
		);
		const marcados = meta.feature_columns.filter(
			(col, i) => col.startsWith("Bairro_") && vetor[i] === 1,
		);
		expect(marcados).toHaveLength(1);
	});

	test("bairro desconhecido zera todo o one-hot", () => {
		const { vetor } = buildFeatureVector(
			{
				area: 90,
				quartos: 3,
				banheiros: 2,
				tipo: "casa",
				bairro: "Nao Existe",
			},
			meta,
		);
		const marcados = meta.feature_columns.filter(
			(col, i) => col.startsWith("Bairro_") && vetor[i] !== 0,
		);
		expect(marcados).toHaveLength(0);
	});

	test("área zero não divide por zero", () => {
		const { vetor } = buildFeatureVector(
			{ area: 0, quartos: 2, banheiros: 1, tipo: "casa", bairro: "Centro" },
			meta,
		);
		expect(vetor.every(Number.isFinite)).toBe(true);
	});
});
