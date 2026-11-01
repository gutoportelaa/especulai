import { describe, expect, test } from "bun:test";
import { escalaLinear, escalaLog, limiteSimetrico, marcasLog } from "./escalas";
import { pct, reaisCompacto } from "./formato";

describe("escalas", () => {
	test("log leva os extremos aos extremos e a média geométrica ao meio", () => {
		const x = escalaLog([100, 10000], [0, 200]);
		expect(x(100)).toBe(0);
		expect(x(10000)).toBeCloseTo(200);
		expect(x(1000)).toBeCloseTo(100);
	});

	test("linear", () => {
		expect(escalaLinear([-0.2, 0.2], [100, 0])(0)).toBe(50);
	});

	test("marcas 1-2-5 dentro do domínio, enxugadas quando são muitas", () => {
		expect(marcasLog([150, 1200])).toEqual([200, 500, 1000]);
		const muitas = marcasLog([60000, 9000000]);
		expect(muitas.length).toBeLessThanOrEqual(6);
		expect(muitas).toContain(100000);
		expect(muitas).toContain(1000000);
	});

	test("limite simétrico cobre o maior desvio com folga", () => {
		expect(limiteSimetrico([0.173, -0.161])).toBe(0.3);
		expect(limiteSimetrico([0.259, -0.198])).toBe(0.4);
		expect(limiteSimetrico([0.01])).toBe(0.1);
	});
});

describe("formato", () => {
	test("reais compactos", () => {
		expect(reaisCompacto(1800)).toBe("R$ 1.800");
		expect(reaisCompacto(450000)).toBe("R$ 450 mil");
		expect(reaisCompacto(1200000)).toBe("R$ 1,2 mi");
	});

	test("percentual com sinal e menos tipográfico", () => {
		expect(pct(0.814)).toBe("81,4%");
		expect(pct(21.06, { pp: true })).toBe("21,1%");
		expect(pct(0.173, { casas: 0, sinal: true })).toBe("+17%");
		expect(pct(-0.161, { casas: 0 })).toBe("−16%");
	});
});
