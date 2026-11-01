// Gerado por `ml/pipeline/export_web.py` (make export-web) a partir do modelo publicado.
// Não edite à mão: `tests/test_metricas_site.py` falha se o arquivo divergir do modelo.
import dados from "./metricas-modelo.json";

export const NEGOCIOS = [
	{ id: "venda", rotulo: "Venda", sufixo: "" },
	{ id: "aluguel", rotulo: "Aluguel", sufixo: "/mês" },
];

export const MODELO = dados;

/** Números de cabeçalho de um negócio, já como frações (0,814) ou contagens. */
export function resumo(negocio) {
	const { teste, corpus } = dados[negocio];
	return {
		nTeste: teste.n_teste,
		erroMediano: teste.metricas["MdAPE%"] / 100,
		dentro20: teste.metricas["dentro20%"] / 100,
		r2Log: teste.metricas.R2_log,
		cobertura: teste.cobertura,
		porTerco: teste.cobertura_por_faixa,
		razao: teste.razao_media_hi_lo,
		imoveis: corpus.imoveis,
		anuncios: corpus.anuncios,
		ligadosIbge: corpus.ligados_ibge,
	};
}

export const VENDA = resumo("venda");
export const ALUGUEL = resumo("aluguel");
