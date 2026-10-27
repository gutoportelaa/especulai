// A estimativa é calculada no servidor (deploy/space): os pesos do modelo não chegam ao
// navegador. Aqui ficam só a chamada à API e a lista de bairros para o autocomplete.

import { apiFetch } from "../../api/client";

export const NEGOCIOS = ["venda", "aluguel"];

const BAIRROS_URL = `${import.meta.env.BASE_URL}model/bairros.json`;

let bairrosPorNegocio = null;

/** Bairros que o modelo conhece (só nomes) — alimenta o autocomplete. */
export async function listarBairros(negocio = "venda") {
	if (!bairrosPorNegocio) {
		const r = await fetch(BAIRROS_URL);
		if (!r.ok)
			throw new Error(`Lista de bairros indisponível (HTTP ${r.status})`);
		bairrosPorNegocio = await r.json();
	}
	return bairrosPorNegocio[negocio] ?? [];
}

/**
 * @param {"venda"|"aluguel"} negocio
 * @param {{area:number, quartos:number, banheiros:number, tipo:string, bairro:string, vagas?:number|null}} entrada
 * @returns {Promise<{negocio:string, preco_estimado:number, minimo:number, maximo:number, nivel:number, confianca:string}>}
 */
export function predictImovel(negocio, entrada) {
	const { area, quartos, banheiros, vagas, tipo, bairro } = entrada;
	return apiFetch("/estimar", {
		method: "POST",
		body: JSON.stringify({
			negocio,
			area,
			quartos,
			banheiros,
			vagas,
			tipo,
			bairro,
		}),
	});
}
