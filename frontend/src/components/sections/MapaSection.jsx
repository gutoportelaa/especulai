import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { numero, pct, reais } from "../../features/conteudo/formato";
import {
	BAIRROS_POR_NOME,
	MAPA,
	METRICAS_MAPA,
	cortesQuantil,
	precoM2,
} from "../../features/conteudo/mapa";
import { NEGOCIOS } from "../../features/conteudo/modelo";
import { LegendaMapa } from "../mapa/LegendaMapa";
import { MapaBairros } from "../mapa/MapaBairros";
import { PainelBairro } from "../mapa/PainelBairro";
import { TabelaDados } from "../metodologia/TabelaDados";
import { SectionHeading } from "./SectionHeading";

function Alternador({ legenda, opcoes, valor, onMudar }) {
	return (
		<fieldset className="inline-flex flex-wrap justify-center gap-1 rounded-3xl border border-border/60 bg-muted/40 p-1">
			<legend className="sr-only">{legenda}</legend>
			{opcoes.map((o) => (
				<button
					key={o.id}
					type="button"
					aria-pressed={valor === o.id}
					onClick={() => onMudar(o.id)}
					className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
						valor === o.id
							? "bg-primary text-primary-foreground shadow"
							: "text-muted-foreground hover:text-foreground"
					}`}
				>
					{o.rotulo}
				</button>
			))}
		</fieldset>
	);
}

/** Bairro com mais imóveis no negócio: o painel nunca abre vazio. */
function maisAnunciado(negocio) {
	return MAPA.bairros.reduce((a, b) =>
		b[negocio].imoveis > a[negocio].imoveis ? b : a,
	).id;
}

export function MapaSection() {
	const [negocio, setNegocio] = useState("venda");
	const [idMetrica, setIdMetrica] = useState("m2");
	const [selecionado, setSelecionado] = useState(() => maisAnunciado("venda"));
	const { rotulo, sufixo } = NEGOCIOS.find((n) => n.id === negocio);
	const metrica = METRICAS_MAPA.find((m) => m.id === idMetrica);
	const cortes = useMemo(
		() => cortesQuantil(MAPA.bairros.map((b) => metrica.valor(b[negocio]))),
		[metrica, negocio],
	);
	const semNumero =
		idMetrica === "imoveis"
			? "sem anúncios"
			: `menos de ${MAPA.minimos.agregado} imóveis`;

	return (
		<section id="mapa" className="w-full py-12 md:py-16">
			<div className="container mx-auto px-4 md:px-6">
				<SectionHeading
					badge="Interno"
					titulo="Dados de treino e erros do modelo, bairro a bairro"
				>
					Preço pedido, quantidade de anúncios e o desempenho do modelo nos{" "}
					{MAPA.bairros.length} bairros de Teresina. Escolha um bairro para ver
					o imóvel padrão e anúncios reais comparados com a faixa do modelo.
				</SectionHeading>

				<motion.div
					initial={{ opacity: 0, y: 20 }}
					whileInView={{ opacity: 1, y: 0 }}
					viewport={{ once: true }}
					transition={{ duration: 0.5 }}
					className="mx-auto max-w-6xl"
				>
					<div className="mb-8 flex flex-col items-center gap-3">
						<Alternador
							legenda="Negócio"
							opcoes={NEGOCIOS}
							valor={negocio}
							onMudar={setNegocio}
						/>
						<Alternador
							legenda="O que o mapa mostra"
							opcoes={METRICAS_MAPA}
							valor={idMetrica}
							onMudar={setIdMetrica}
						/>
					</div>

					<div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-2">
						<div className="min-w-0">
							<MapaBairros
								negocio={negocio}
								metrica={metrica}
								sufixo={sufixo}
								cortes={cortes}
								selecionado={selecionado}
								onSelecionar={setSelecionado}
							/>
							<LegendaMapa
								metrica={metrica}
								sufixo={sufixo}
								cortes={cortes}
								minimo={semNumero}
							/>
							<p className="mt-3 text-xs text-muted-foreground">
								Anúncios de outubro de 2026; números do modelo medidos fora da
								amostra (cada anúncio previsto por um modelo que não o viu).
								Limites de bairro: {MAPA.fonte}.{" "}
								{MAPA.fora_da_malha[negocio] > 0 &&
									`${numero(MAPA.fora_da_malha[negocio])} anúncios com bairro fora da malha não aparecem.`}
							</p>
						</div>

						<PainelBairro
							id={selecionado}
							negocio={negocio}
							rotuloNegocio={rotulo}
							sufixo={sufixo}
							onSelecionar={setSelecionado}
						/>
					</div>

					<TabelaDados
						legenda={`Bairros de Teresina, ${rotulo.toLowerCase()}`}
						colunas={[
							"Bairro",
							"Imóveis",
							"R$/m² pedido",
							"Erro do modelo",
							"Imóvel padrão",
						]}
						linhas={BAIRROS_POR_NOME.map((b) => {
							const d = b[negocio];
							return [
								b.nome,
								numero(d.imoveis),
								d.m2 === undefined ? "—" : precoM2(d.m2, sufixo),
								d.erro === undefined ? "—" : pct(d.erro, { casas: 0 }),
								`${reais(d.padrao.central)}${sufixo}`,
							];
						})}
					/>
				</motion.div>
			</div>
		</section>
	);
}
