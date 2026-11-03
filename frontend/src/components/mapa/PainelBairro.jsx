import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { numero, pct, reais } from "../../features/conteudo/formato";
import {
	BAIRROS_POR_NOME,
	BAIRRO_POR_ID,
	MAPA,
	reaisM2,
} from "../../features/conteudo/mapa";
import { Card, CardContent } from "../ui/card";
import { ExemploAnuncio } from "./ExemploAnuncio";

const ROTULO_CONFIANCA = { alta: "Alta", média: "Média", baixa: "Baixa" };

function Numero({ rotulo, valor, nota }) {
	return (
		<div className="min-w-0 rounded-lg bg-muted/40 p-2.5 sm:p-3">
			<dt className="text-xs text-muted-foreground">{rotulo}</dt>
			<dd className="mt-0.5 text-base font-bold tabular-nums sm:text-lg">
				{valor}
			</dd>
			{nota && <dd className="text-xs text-muted-foreground">{nota}</dd>}
		</div>
	);
}

export function PainelBairro({
	id,
	negocio,
	rotuloNegocio,
	sufixo,
	onSelecionar,
}) {
	const bairro = BAIRRO_POR_ID[id];
	const d = bairro[negocio];
	const p = MAPA.padrao;
	const { agregado, exemplo } = MAPA.minimos;

	return (
		<Card className="h-full min-w-0 border-border/40">
			<CardContent className="space-y-6 p-6">
				<div>
					<label
						htmlFor="bairro-mapa"
						className="text-xs font-medium text-muted-foreground"
					>
						Bairro
					</label>
					<select
						id="bairro-mapa"
						value={id}
						onChange={(e) => onSelecionar(e.target.value)}
						className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-lg font-bold focus:outline-none focus:ring-2 focus:ring-ring"
					>
						{BAIRROS_POR_NOME.map((b) => (
							<option key={b.id} value={b.id}>
								{b.nome}
							</option>
						))}
					</select>
					<p className="mt-2 text-sm text-muted-foreground">
						{d.imoveis === 0
							? `Nenhum anúncio de ${rotuloNegocio.toLowerCase()} na coleta.`
							: `${numero(d.imoveis)} ${d.imoveis === 1 ? "imóvel" : "imóveis"} de ${rotuloNegocio.toLowerCase()} na coleta (${numero(d.anuncios)} ${d.anuncios === 1 ? "anúncio" : "anúncios"}).`}
					</p>
				</div>

				{d.m2 !== undefined ? (
					<dl className="grid grid-cols-3 gap-2 sm:gap-3">
						<Numero
							rotulo="R$/m² pedido"
							valor={reaisM2(d.m2)}
							nota={sufixo ? "mediana, ao mês" : "mediana"}
						/>
						<Numero
							rotulo="Erro do modelo"
							valor={pct(d.erro, { casas: 0 })}
							nota="mediano"
						/>
						<Numero
							rotulo="Na faixa de 80%"
							valor={pct(d.cobertura, { casas: 0 })}
							nota="dos anúncios"
						/>
					</dl>
				) : (
					d.imoveis > 0 && (
						<p className="rounded-lg bg-muted/40 p-3 text-sm text-muted-foreground">
							Com menos de {agregado} imóveis, os números do bairro mudariam
							muito com um anúncio a mais. Por isso não são mostrados.
						</p>
					)
				)}

				<section>
					<h3 className="text-sm font-semibold">Imóvel padrão neste bairro</h3>
					<p className="text-xs text-muted-foreground">
						{p.tipo}, {p.area} m², {p.quartos} quartos, {p.banheiros} banheiros,{" "}
						{p.vagas} vaga
					</p>
					<div className="mt-3 flex flex-wrap items-baseline justify-between gap-2">
						<p className="text-2xl font-bold tracking-tight tabular-nums">
							{reais(d.padrao.minimo)} – {reais(d.padrao.maximo)}
							<span className="text-sm font-medium text-muted-foreground">
								{sufixo}
							</span>
						</p>
						<p className="text-xs text-muted-foreground">
							Confiança{" "}
							<span className="font-semibold text-foreground">
								{ROTULO_CONFIANCA[d.padrao.confianca].toLowerCase()}
							</span>
						</p>
					</div>
					<p className="text-xs text-muted-foreground">
						Estimativa central {reais(d.padrao.central)}
						{sufixo}. É o que o simulador responderia para esse imóvel.
					</p>
				</section>

				<section>
					<h3 className="text-sm font-semibold">Anúncios reais, sorteados</h3>
					{d.exemplos ? (
						<>
							<p className="mb-3 text-xs text-muted-foreground">
								Faixa calculada por um modelo que não viu o anúncio. Sorteados,
								não escolhidos: alguns ficam fora, como 1 em cada 5 no total.
								Área e preço arredondados.
							</p>
							<ul className="space-y-3">
								{d.exemplos.map((e) => (
									<ExemploAnuncio
										key={`${e.tipo}-${e.area}-${e.pedido}`}
										exemplo={e}
										sufixo={sufixo}
									/>
								))}
							</ul>
						</>
					) : (
						<p className="mt-1 text-xs text-muted-foreground">
							Só bairros com {exemplo} imóveis ou mais mostram anúncios, para
							que nenhum deles aponte para um imóvel específico.
						</p>
					)}
				</section>

				<Link
					to="/predict"
					className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
				>
					Estimar um imóvel seu
					<ArrowRight className="size-4" />
				</Link>
			</CardContent>
		</Card>
	);
}
