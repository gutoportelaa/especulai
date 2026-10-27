import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { criarHandler, validar } from "../src/handler";
import { decidir } from "../src/limite";

const RAIZ = join(import.meta.dir, "..", "..", "..");
const pesos = (n) => join(RAIZ, "ml", "artifacts", "web", `especulai-${n}.json`);
const temModelos = existsSync(pesos("venda")) && existsSync(pesos("aluguel"));
const comModelos = test.skipIf(!temModelos);

const SITE = "https://gutoportelaa.github.io";
const BASE = { negocio: "venda", area: 90, quartos: 3, banheiros: 2, tipo: "Apartamento", bairro: "Fátima" };

function montar({ limites = { porMinuto: 5, porHora: 50, globalPorHora: 500 }, abrir } = {}) {
	const m = new Map();
	const armazem = { get: async (k) => m.get(k), put: async (k, v) => void m.set(k, v) };
	const modelos = {};
	const abrirModelo =
		abrir ??
		(async (n) => (modelos[n] ??= JSON.parse(readFileSync(pesos(n), "utf8"))));
	return criarHandler({
		abrirModelo,
		liberar: (ip) => decidir(armazem, ip, Date.now(), limites),
		origens: [SITE, "http://localhost:5173"],
	});
}

const post = (corpo, ip = "1.1.1.1", extra = {}) =>
	new Request("https://api.test/estimar", {
		method: "POST",
		headers: { "content-type": "application/json", "CF-Connecting-IP": ip, ...extra },
		body: typeof corpo === "string" ? corpo : JSON.stringify(corpo),
	});

describe("validar", () => {
	test("aceita a entrada típica, com e sem vagas", () => {
		expect(validar(BASE)).toBeNull();
		expect(validar({ ...BASE, vagas: 2 })).toBeNull();
		expect(validar({ ...BASE, vagas: null })).toBeNull();
	});

	test.each([
		[{ area: 5 }],
		[{ area: 99999 }],
		[{ area: "90" }],
		[{ area: Number.NaN }],
		[{ quartos: -1 }],
		[{ quartos: 2.5 }],
		[{ banheiros: 50 }],
		[{ negocio: "troca" }],
		[{ bairro: "" }],
		[{ bairro: "   " }],
		[{ tipo: "x".repeat(100) }],
		[{ vagas: 500 }],
		[{ vagas: "1" }],
	])("rejeita %j", (mudanca) => {
		expect(validar({ ...BASE, ...mudanca })).not.toBeNull();
	});

	test("rejeita corpo que não é objeto", () => {
		expect(validar(null)).not.toBeNull();
		expect(validar("texto")).not.toBeNull();
	});
});

describe("POST /estimar", () => {
	comModelos("devolve só a faixa", async () => {
		const r = await montar()(post(BASE));
		expect(r.status).toBe(200);
		const corpo = await r.json();
		expect(Object.keys(corpo).sort()).toEqual(
			["confianca", "maximo", "minimo", "negocio", "nivel", "preco_estimado"].sort(),
		);
		expect(corpo.minimo).toBeLessThan(corpo.preco_estimado);
		expect(corpo.preco_estimado).toBeLessThan(corpo.maximo);
	});

	comModelos("entrada inválida e JSON quebrado dão 422 sem gastar o modelo", async () => {
		let abriu = 0;
		const h = montar({ abrir: async () => void abriu++ });
		expect((await h(post({ ...BASE, area: 5 }))).status).toBe(422);
		expect((await h(post("{quebrado"))).status).toBe(422);
		expect(abriu).toBe(0);
	});

	comModelos("limite por minuto responde 429 com Retry-After; outro IP segue livre", async () => {
		const h = montar();
		const codigos = [];
		for (let i = 0; i < 7; i++) codigos.push((await h(post(BASE, "9.9.9.9"))).status);
		expect(codigos).toEqual([200, 200, 200, 200, 200, 429, 429]);
		const r = await h(post(BASE, "9.9.9.9"));
		expect(Number(r.headers.get("retry-after"))).toBeGreaterThanOrEqual(1);
		expect((await h(post(BASE, "8.8.8.8"))).status).toBe(200);
	});

	comModelos("X-Forwarded-For forjado não burla o limite (vale o IP do Cloudflare)", async () => {
		const h = montar();
		const codigos = [];
		for (let i = 0; i < 7; i++) {
			codigos.push((await h(post(BASE, "7.7.7.7", { "x-forwarded-for": `1.1.1.${i}` }))).status);
		}
		expect(codigos.filter((c) => c === 429)).toHaveLength(2);
	});

	test("falha ao abrir o modelo vira 503 genérico, sem vazar o motivo", async () => {
		const h = montar({
			abrir: async () => {
				throw new Error("segredo: chave 00ff... inválida");
			},
		});
		const r = await h(post(BASE));
		expect(r.status).toBe(503);
		expect(await r.text()).not.toContain("segredo");
	});

	test("limitador fora do ar: falha fechada", async () => {
		const h = criarHandler({
			abrirModelo: async () => ({}),
			liberar: async () => {
				throw new Error("DO indisponível");
			},
			origens: [SITE],
		});
		expect((await h(post(BASE))).status).toBe(503);
	});
});

describe("CORS e rotas", () => {
	const h = () => montar({ abrir: async () => ({}) });

	test("só as origens permitidas recebem o cabeçalho", async () => {
		const ok = await h()(
			new Request("https://api.test/estimar", { method: "OPTIONS", headers: { Origin: SITE } }),
		);
		expect(ok.status).toBe(204);
		expect(ok.headers.get("access-control-allow-origin")).toBe(SITE);
		const mau = await h()(
			new Request("https://api.test/estimar", {
				method: "OPTIONS",
				headers: { Origin: "https://evil.example" },
			}),
		);
		expect(mau.headers.get("access-control-allow-origin")).toBeNull();
	});

	test("rota desconhecida 404, método errado 405, sem documentação exposta", async () => {
		expect((await h()(new Request("https://api.test/openapi.json"))).status).toBe(404);
		expect((await h()(new Request("https://api.test/estimar"))).status).toBe(405);
	});

	test("/saude: 200 se os dois modelos abrem, 503 se não", async () => {
		expect((await h()(new Request("https://api.test/saude"))).status).toBe(200);
		const quebrado = montar({
			abrir: async () => {
				throw new Error("x");
			},
		});
		expect((await quebrado(new Request("https://api.test/saude"))).status).toBe(503);
	});
});
