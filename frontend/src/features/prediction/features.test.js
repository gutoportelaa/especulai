// Trava o contrato entre o JS e o código de treino (matriz + X_com).
// Fixtures: tests/test_web_export_parity.py — regere com `make export-web && uv run pytest tests/`.

import { describe, expect, test } from "bun:test";

import aluguel from "../../../public/model/especulai-aluguel.json";
import venda from "../../../public/model/especulai-venda.json";
import fixtures from "./__fixtures__/parity.json";
import {
	buildFeatureVector,
	nivelConfianca,
	normalizeBairro,
	resolveBairro,
	resolveTipo,
} from "./features";

const modelos = { venda, aluguel };

describe("normalizeBairro", () => {
	test("ignora acento, caixa e separadores", () => {
		expect(normalizeBairro("Fátima")).toBe("fatima");
		expect(normalizeBairro("São João")).toBe("saojoao");
		expect(normalizeBairro("Jóquei-Clube")).toBe("joqueiclube");
	});

	test("entrada vazia vira string vazia", () => {
		expect(normalizeBairro("")).toBe("");
		expect(normalizeBairro(null)).toBe("");
		expect(normalizeBairro(undefined)).toBe("");
	});
});

describe("resolveBairro e resolveTipo", () => {
	test("casa bairro conhecido independente de acento", () => {
		expect(resolveBairro("fatima", venda.feature_columns)?.nome).toBe(
			resolveBairro("Fátima", venda.feature_columns)?.nome,
		);
		expect(resolveBairro("Fátima", venda.feature_columns)).not.toBeNull();
	});

	test("bairro fora do treino ou vazio não casa", () => {
		expect(
			resolveBairro("Bairro Inexistente", venda.feature_columns),
		).toBeNull();
		expect(resolveBairro("", venda.feature_columns)).toBeNull();
	});

	test("tipo casa por nome normalizado", () => {
		expect(
			resolveTipo("casa de condominio", venda.feature_columns)?.coluna,
		).toBe("Tipo_Imovel_Casa de Condomínio");
		expect(resolveTipo("Mansão", venda.feature_columns)).toBeNull();
	});
});

describe("paridade com o código de treino", () => {
	for (const negocio of Object.keys(modelos)) {
		test.each(
			fixtures[negocio].map((f) => [
				`${f.entrada.bairro} ${f.entrada.area}m2`,
				f,
			]),
		)(`${negocio}: vetor bate: %s`, (_nome, fixture) => {
			const { vetor } = buildFeatureVector(fixture.entrada, modelos[negocio]);
			expect(vetor).toHaveLength(fixture.vetor.length);
			for (let i = 0; i < vetor.length; i++) {
				expect(vetor[i]).toBeCloseTo(fixture.vetor[i], 9);
			}
		});
	}
});

describe("vagas", () => {
	test("sem vagas informadas: Vagas_informado = 0; com vagas: 1", () => {
		const base = {
			area: 80,
			quartos: 2,
			banheiros: 1,
			tipo: "Apartamento",
			bairro: "Centro",
		};
		const i = venda.feature_columns.indexOf("Vagas_informado");
		expect(buildFeatureVector(base, venda).vetor[i]).toBe(0);
		expect(buildFeatureVector({ ...base, vagas: 0 }, venda).vetor[i]).toBe(1);
	});
});

describe("nivelConfianca", () => {
	const ok = { bairro: { nome: "x" }, tipo: { nome: "y" }, n: 100, area: 90 };

	test("bairro desconhecido é baixa", () => {
		expect(nivelConfianca({ ...ok, bairro: null })).toBe("baixa");
	});

	test("bairro raro, tipo desconhecido ou área extrema é média", () => {
		expect(nivelConfianca({ ...ok, n: 3 })).toBe("média");
		expect(nivelConfianca({ ...ok, tipo: null })).toBe("média");
		expect(nivelConfianca({ ...ok, area: 5000 })).toBe("média");
	});

	test("bairro comum com entrada típica é alta", () => {
		expect(nivelConfianca(ok)).toBe("alta");
	});
});
