import { useMemo, useState } from "react";
import { numero } from "../../features/conteudo/formato";
import {
	BAIRROS_POR_NOME,
	MAPA,
	METRICAS_MAPA,
	cortesQuantil,
} from "../../features/conteudo/mapa";
import { NEGOCIOS } from "../../features/conteudo/modelo";
import { LegendaMapa } from "../mapa/LegendaMapa";
import { MapaBairros } from "../mapa/MapaBairros";
import { TabelaDados } from "./TabelaDados";

const METRICA = METRICAS_MAPA.find((m) => m.id === "imoveis");
const nada = () => {};

function contar(negocio) {
	const n = (f) => MAPA.bairros.filter((b) => f(b[negocio].imoveis)).length;
	return {
		muitos: n((i) => i >= MAPA.minimos.exemplo),
		poucos: n((i) => i > 0 && i < MAPA.minimos.agregado),
		nenhum: n((i) => i === 0),
	};
}

/** Quantos imóveis o modelo viu em cada bairro: onde a estimativa tem chão e onde não tem. */
export function CoberturaBairros() {
	const [negocio, setNegocio] = useState("venda");
	const cortes = useMemo(
		() => cortesQuantil(MAPA.bairros.map((b) => METRICA.valor(b[negocio]))),
		[negocio],
	);
	const c = contar(negocio);
	const total = MAPA.bairros.length;

	return (
		<div className="mx-auto grid max-w-5xl grid-cols-1 items-center gap-8 md:grid-cols-2">
			<div className="min-w-0">
				<MapaBairros
					negocio={negocio}
					metrica={METRICA}
					sufixo=""
					cortes={cortes}
					selecionado={null}
					onSelecionar={nada}
				/>
				<LegendaMapa
					metrica={METRICA}
					sufixo=""
					cortes={cortes}
					minimo="sem anúncios"
				/>
			</div>
			<div className="space-y-4">
				<fieldset className="inline-flex gap-1 rounded-3xl border border-border/60 bg-muted/40 p-1">
					<legend className="sr-only">Negócio</legend>
					{NEGOCIOS.map((o) => (
						<button
							key={o.id}
							type="button"
							aria-pressed={negocio === o.id}
							onClick={() => setNegocio(o.id)}
							className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
								negocio === o.id
									? "bg-primary text-primary-foreground shadow"
									: "text-muted-foreground hover:text-foreground"
							}`}
						>
							{o.rotulo}
						</button>
					))}
				</fieldset>
				<ul className="space-y-3 text-sm">
					<li>
						<strong className="text-foreground">
							{c.muitos} de {total} bairros
						</strong>{" "}
						<span className="text-muted-foreground">
							têm {MAPA.minimos.exemplo} ou mais imóveis anunciados: ali o
							modelo conhece o mercado local.
						</span>
					</li>
					<li>
						<strong className="text-foreground">{c.poucos} bairros</strong>{" "}
						<span className="text-muted-foreground">
							têm menos de {MAPA.minimos.agregado}. O valor se apoia mais na
							renda e na densidade do bairro (IBGE), e a confiança cai para
							média.
						</span>
					</li>
					<li>
						<strong className="text-foreground">{c.nenhum} bairros</strong>{" "}
						<span className="text-muted-foreground">
							não tiveram nenhum anúncio na coleta. Ainda há estimativa, com
							confiança baixa.
						</span>
					</li>
				</ul>
				<p className="text-xs text-muted-foreground">
					Anúncios de outubro de 2026. Limites de bairro: {MAPA.fonte}.
				</p>
			</div>
			<div className="md:col-span-2">
				<TabelaDados
					legenda="Imóveis anunciados por bairro"
					colunas={["Bairro", "Venda", "Aluguel"]}
					linhas={BAIRROS_POR_NOME.map((b) => [
						b.nome,
						numero(b.venda.imoveis),
						numero(b.aluguel.imoveis),
					])}
				/>
			</div>
		</div>
	);
}
