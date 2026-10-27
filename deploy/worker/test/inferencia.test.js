import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

import {
	arredondar,
	chaveNormalizada,
	confianca,
	decifrar,
	estimar,
	intervalo,
	montarVetor,
	preverLog,
} from "../src/inferencia";

const RAIZ = join(import.meta.dir, "..", "..", "..");
const FIXTURES = join(RAIZ, "tests", "fixtures", "parity.json");
const pesos = (n) => join(RAIZ, "ml", "artifacts", "web", `especulai-${n}.json`);
const CHAVE = join(homedir(), "especulai-dados-privados", "modelo.key");

const temModelos = existsSync(FIXTURES) && existsSync(pesos("venda")) && existsSync(pesos("aluguel"));
const comModelos = test.skipIf(!temModelos);
const modelo = (n) => JSON.parse(readFileSync(pesos(n), "utf8"));

describe("paridade com o treino (sklearn)", () => {
	for (const negocio of ["venda", "aluguel"]) {
		comModelos(`${negocio}: vetor e log-preço batem com as fixtures`, () => {
			const m = modelo(negocio);
			for (const caso of JSON.parse(readFileSync(FIXTURES, "utf8"))[negocio]) {
				const { vetor } = montarVetor(caso.entrada, m);
				expect(vetor).toHaveLength(caso.vetor.length);
				for (let i = 0; i < vetor.length; i++) expect(vetor[i]).toBeCloseTo(caso.vetor[i], 9);
				// Só o arredondamento das folhas (6 casas) separa os dois.
				expect(preverLog(vetor, m)).toBeCloseTo(caso.log_preco, 4);
			}
		});
	}

	comModelos("todo bairro conhecido dá preço finito e positivo", () => {
		for (const negocio of ["venda", "aluguel"]) {
			const m = modelo(negocio);
			for (const bairro of m.bairros) {
				const r = estimar(
					negocio,
					{ area: 90, quartos: 3, banheiros: 2, tipo: "Apartamento", bairro },
					m,
				);
				expect(r.minimo).toBeGreaterThan(0);
				expect(r.minimo).toBeLessThan(r.maximo);
			}
		}
	});

	comModelos("venda custa muito mais que aluguel e o tipo muda o preço", () => {
		const e = { area: 90, quartos: 3, banheiros: 2, tipo: "Apartamento", bairro: "Fátima" };
		const v = estimar("venda", e, modelo("venda"));
		const a = estimar("aluguel", e, modelo("aluguel"));
		expect(v.preco_estimado).toBeGreaterThan(50 * a.preco_estimado);
		const casa = estimar("venda", { ...e, tipo: "Casa", area: 150 }, modelo("venda"));
		const apto = estimar("venda", { ...e, area: 150 }, modelo("venda"));
		expect(casa.preco_estimado).not.toBe(apto.preco_estimado);
	});
});

describe("entrada", () => {
	comModelos("bairro e tipo casam sem acento nem caixa; vagas informadas ligam o indicador", () => {
		const m = modelo("venda");
		const base = { area: 80, quartos: 2, banheiros: 1, tipo: "casa de condominio", bairro: "fatima" };
		const i = m.feature_columns.indexOf("Vagas_informado");
		const semVagas = montarVetor(base, m);
		expect(semVagas.achouBairro && semVagas.achouTipo).toBe(true);
		expect(semVagas.vetor[i]).toBe(0);
		expect(montarVetor({ ...base, vagas: 0 }, m).vetor[i]).toBe(1);
	});

	comModelos("bairro desconhecido usa -1 e não casa", () => {
		const m = modelo("venda");
		const r = montarVetor({ area: 80, quartos: 2, banheiros: 1, tipo: "casa", bairro: "Nao Existe" }, m);
		expect(r.achouBairro).toBe(false);
		expect(r.vetor[m.feature_columns.indexOf("Renda_bairro")]).toBe(-1);
		expect(r.vetor[m.feature_columns.indexOf("IBGE_casou")]).toBe(0);
	});

	test("normalização", () => {
		expect(chaveNormalizada("Fátima")).toBe("fatima");
		expect(chaveNormalizada("Jóquei-Clube")).toBe("joqueiclube");
		expect(chaveNormalizada(null)).toBe("");
	});
});

describe("intervalo, arredondamento e confiança", () => {
	const iv = { cortes: [100, 200], meia_largura: [0.1, 0.2, 0.3] };

	test("faixa escolhida pelo preço; o corte pertence à de baixo (np.searchsorted)", () => {
		expect(intervalo(50, iv)[1]).toBeCloseTo(50 * Math.exp(0.1), 9);
		expect(intervalo(100, iv)[1]).toBeCloseTo(100 * Math.exp(0.1), 9);
		expect(intervalo(150, iv)[1]).toBeCloseTo(150 * Math.exp(0.2), 9);
		expect(intervalo(900, iv)[1]).toBeCloseTo(900 * Math.exp(0.3), 9);
	});

	test("simétrico em log", () => {
		const [lo, hi] = intervalo(300, iv);
		expect(lo * hi).toBeCloseTo(300 * 300, 6);
	});

	test("arredondamento", () => {
		expect(arredondar(1234)).toBe(1230);
		expect(arredondar(456_789)).toBe(457_000);
	});

	test("confiança", () => {
		const ok = { achouBairro: true, achouTipo: true, n: 100, area: 90 };
		expect(confianca({ ...ok, achouBairro: false })).toBe("baixa");
		expect(confianca({ ...ok, n: 3 })).toBe("média");
		expect(confianca({ ...ok, achouTipo: false })).toBe("média");
		expect(confianca({ ...ok, area: 5000 })).toBe("média");
		expect(confianca(ok)).toBe("alta");
	});
});

describe("cifragem (AES-256-GCM)", () => {
	const temChave = existsSync(CHAVE) && existsSync(join(RAIZ, "deploy", "worker", "modelos", "venda.enc"));
	const comChave = test.skipIf(!temChave || !temModelos);
	const enc = () => readFileSync(join(RAIZ, "deploy", "worker", "modelos", "venda.enc"));
	const chave = () => readFileSync(CHAVE, "utf8").trim();

	comChave("abre o arquivo gerado pelo Python (compatibilidade entre linguagens)", async () => {
		const aberto = await decifrar(enc(), chave());
		expect(aberto.init).toBe(modelo("venda").init);
		expect(aberto.negocio).toBe("venda");
	});

	comChave("o arquivo cifrado não contém o modelo legível", () => {
		const texto = enc().toString("latin1");
		expect(texto.includes("trees") || texto.includes("Bairro_")).toBe(false);
	});

	comChave("rejeita chave errada, adulteração, magic inválido e chave malformada", async () => {
		await expect(decifrar(enc(), "00".repeat(32))).rejects.toThrow();
		const adulterado = new Uint8Array(enc());
		adulterado[adulterado.length - 1] ^= 1;
		await expect(decifrar(adulterado, chave())).rejects.toThrow();
		const outro = new Uint8Array(enc());
		outro[0] = 0;
		await expect(decifrar(outro, chave())).rejects.toThrow("inválido");
		await expect(decifrar(enc(), "curta")).rejects.toThrow("MODEL_KEY");
		await expect(decifrar(enc(), undefined)).rejects.toThrow("MODEL_KEY");
	});
});
