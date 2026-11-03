import { describe, expect, test } from "bun:test";
import {
	MAPA,
	RAMPA,
	classe,
	corDaClasse,
	cortesQuantil,
	precoM2,
	reaisM2,
} from "./mapa";

describe("cortesQuantil", () => {
	test("divide em classes de tamanho parecido e ignora bairros sem dado", () => {
		const v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, undefined];
		expect(cortesQuantil(v, 5)).toEqual([3, 5, 7, 9]);
	});

	test("não repete corte quando muitos bairros têm o mesmo valor", () => {
		expect(cortesQuantil([1, 1, 1, 1, 1, 1, 2, 3], 4)).toEqual([2]);
	});

	test("sem valores, sem cortes", () => {
		expect(cortesQuantil([undefined, undefined])).toEqual([]);
	});
});

describe("classe e cor", () => {
	test("um valor igual ao corte sobe de classe", () => {
		expect(classe(2.9, [3, 5])).toBe(0);
		expect(classe(3, [3, 5])).toBe(1);
		expect(classe(99, [3, 5])).toBe(2);
	});

	test("as pontas da rampa ficam com a menor e a maior classe", () => {
		expect(corDaClasse(0, 3)).toBe(RAMPA[0]);
		expect(corDaClasse(2, 3)).toBe(RAMPA[RAMPA.length - 1]);
	});
});

test("R$/m² do aluguel guarda uma casa decimal e diz que é ao mês", () => {
	expect(reaisM2(33.3)).toBe("R$ 33,3");
	expect(reaisM2(7450)).toBe("R$ 7.450");
	expect(precoM2(34.8, "/mês")).toBe("R$ 34,8/m² ao mês");
	expect(precoM2(6020, "")).toBe("R$ 6.020/m²");
});

test("todo bairro tem desenho e o imóvel padrão nos dois negócios", () => {
	for (const b of MAPA.bairros) {
		expect(b.d.startsWith("M")).toBe(true);
		for (const n of ["venda", "aluguel"]) {
			expect(b[n].padrao.minimo).toBeLessThanOrEqual(b[n].padrao.central);
			expect(b[n].padrao.central).toBeLessThanOrEqual(b[n].padrao.maximo);
		}
	}
});
