// Rotas da API, sem dependência de Cloudflare: tudo que vem de fora (modelos abertos, limitador,
// configuração) é injetado, então test/handler.test.js cobre validação, CORS e 429 sem rede.

import { estimar } from "./inferencia";

const NEGOCIOS = ["venda", "aluguel"];

const inteiro = (v, min, max) => Number.isInteger(v) && v >= min && v <= max;
const texto = (v, max) => typeof v === "string" && v.trim().length > 0 && v.length <= max;

/** @returns {string|null} mensagem do primeiro problema, ou null se a entrada é válida */
export function validar(e) {
	if (!e || typeof e !== "object") return "Corpo inválido.";
	if (!NEGOCIOS.includes(e.negocio)) return "Negócio deve ser venda ou aluguel.";
	if (typeof e.area !== "number" || !(e.area >= 10 && e.area <= 2000)) {
		return "Área deve estar entre 10 e 2000 m².";
	}
	if (!inteiro(e.quartos, 0, 20)) return "Quartos deve estar entre 0 e 20.";
	if (!inteiro(e.banheiros, 0, 20)) return "Banheiros deve estar entre 0 e 20.";
	if (e.vagas !== null && e.vagas !== undefined && !inteiro(e.vagas, 0, 20)) {
		return "Vagas deve estar entre 0 e 20.";
	}
	if (!texto(e.tipo, 40)) return "Tipo inválido.";
	if (!texto(e.bairro, 80)) return "Bairro inválido.";
	return null;
}

function json(corpo, status, extra = {}) {
	return new Response(JSON.stringify(corpo), {
		status,
		headers: { "content-type": "application/json; charset=utf-8", ...extra },
	});
}

/**
 * @param {{
 *   abrirModelo: (negocio: string) => Promise<object>,
 *   liberar: (ip: string) => Promise<{ok: boolean, espera?: number}>,
 *   origens: string[],
 * }} deps
 */
export function criarHandler({ abrirModelo, liberar, origens }) {
	return async function handler(req) {
		const origem = req.headers.get("Origin");
		const cors = {
			vary: "Origin",
			...(origem && origens.includes(origem)
				? {
						"access-control-allow-origin": origem,
						"access-control-allow-methods": "GET, POST, OPTIONS",
						"access-control-allow-headers": "content-type",
					}
				: {}),
		};
		const { pathname } = new URL(req.url);

		if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

		if (pathname === "/saude" && req.method === "GET") {
			try {
				await Promise.all(NEGOCIOS.map(abrirModelo));
				return json({ ok: true, modelos: [...NEGOCIOS].sort() }, 200, cors);
			} catch {
				return json({ ok: false }, 503, cors);
			}
		}

		if (pathname !== "/estimar") return json({ detail: "Não encontrado." }, 404, cors);
		if (req.method !== "POST") return json({ detail: "Use POST." }, 405, { ...cors, allow: "POST" });

		const ip = req.headers.get("CF-Connecting-IP") ?? "desconhecido";
		let decisao;
		try {
			decisao = await liberar(ip);
		} catch {
			// Sem limitador não há como conter a extração: falha fechada.
			return json({ detail: "Serviço indisponível." }, 503, cors);
		}
		if (!decisao.ok) {
			return json({ detail: "Muitas consultas. Tente de novo em instantes." }, 429, {
				...cors,
				"retry-after": String(decisao.espera),
			});
		}

		let entrada;
		try {
			entrada = await req.json();
		} catch {
			return json({ detail: "Corpo inválido." }, 422, cors);
		}
		const problema = validar(entrada);
		if (problema) return json({ detail: problema }, 422, cors);

		try {
			const modelo = await abrirModelo(entrada.negocio);
			return json(estimar(entrada.negocio, entrada, modelo), 200, cors);
		} catch {
			// Nunca devolve o motivo: mensagem de erro de decifragem também vaza informação.
			return json({ detail: "Serviço indisponível." }, 503, cors);
		}
	};
}
