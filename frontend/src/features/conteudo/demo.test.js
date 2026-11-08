import { describe, expect, test } from "bun:test";
import { N_PINS, afastados, sortearPins } from "./demo";

function semente(inicial) {
	let s = inicial;
	return () => {
		s = (s * 16807) % 2147483647;
		return s / 2147483647;
	};
}

describe("sortearPins", () => {
	for (const negocio of ["venda", "aluguel"]) {
		test(`${negocio}: pins afastados e com valor do negócio`, () => {
			for (let s = 1; s < 50; s++) {
				const pins = sortearPins(negocio, semente(s));
				expect(pins.length).toBeGreaterThanOrEqual(negocio === "venda" ? 6 : 5);
				expect(pins.length).toBeLessThanOrEqual(N_PINS);
				for (const p of pins) {
					expect(p.minimo).toBeLessThan(p.central);
					expect(p.central).toBeLessThan(p.maximo);
				}
				for (let i = 0; i < pins.length; i++)
					for (let j = i + 1; j < pins.length; j++)
						expect(afastados(pins[i], pins[j])).toBe(true);
			}
		});
	}

	test("o sorteio muda entre ciclos", () => {
		const a = sortearPins("venda", semente(1)).map((p) => p.id);
		const b = sortearPins("venda", semente(7)).map((p) => p.id);
		expect(a).not.toEqual(b);
	});
});
