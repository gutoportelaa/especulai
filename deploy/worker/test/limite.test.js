import { describe, expect, test } from "bun:test";

import { decidir } from "../src/limite";

const armazem = () => {
	const m = new Map();
	return { get: async (k) => m.get(k), put: async (k, v) => void m.set(k, v), tamanho: () => m.size };
};
const L = { porMinuto: 3, porHora: 5, globalPorHora: 8 };
const T0 = Date.UTC(2026, 0, 1, 12, 0, 10); // 10 s depois da virada de minuto e de hora

describe("decidir", () => {
	test("libera até o limite por minuto e depois manda esperar até o minuto virar", async () => {
		const a = armazem();
		for (let i = 0; i < 3; i++) expect((await decidir(a, "1.1.1.1", T0, L)).ok).toBe(true);
		const r = await decidir(a, "1.1.1.1", T0, L);
		expect(r).toEqual({ ok: false, espera: 50 });
		expect((await decidir(a, "1.1.1.1", T0 + 60_000, L)).ok).toBe(true);
	});

	test("limite por hora vale mesmo com o minuto livre", async () => {
		const a = armazem();
		for (let m = 0; m < 2; m++) {
			for (let i = 0; i < 3 && m * 3 + i < 5; i++) {
				expect((await decidir(a, "2.2.2.2", T0 + m * 60_000, L)).ok).toBe(true);
			}
		}
		const r = await decidir(a, "2.2.2.2", T0 + 2 * 60_000, L);
		expect(r.ok).toBe(false);
		expect(r.espera).toBeGreaterThan(60);
	});

	test("IPs são independentes", async () => {
		const a = armazem();
		for (let i = 0; i < 3; i++) await decidir(a, "3.3.3.3", T0, L);
		expect((await decidir(a, "4.4.4.4", T0, L)).ok).toBe(true);
	});

	test("teto global bloqueia IPs novos", async () => {
		const a = armazem();
		for (let ip = 0; ip < 8; ip++) {
			expect((await decidir(a, `9.9.9.${ip}`, T0, L)).ok).toBe(true);
		}
		expect((await decidir(a, "9.9.9.99", T0, L)).ok).toBe(false);
	});

	test("consulta recusada não consome cota", async () => {
		const a = armazem();
		for (let i = 0; i < 3; i++) await decidir(a, "5.5.5.5", T0, L);
		const antes = await a.get(`m:5.5.5.5:${Math.floor(T0 / 60_000)}`);
		await decidir(a, "5.5.5.5", T0, L);
		expect(await a.get(`m:5.5.5.5:${Math.floor(T0 / 60_000)}`)).toBe(antes);
	});
});
