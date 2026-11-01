import { motion } from "framer-motion";
import { useState } from "react";
import { numero } from "../../features/conteudo/formato";
import { resumoVies } from "../../features/conteudo/graficos";
import { MODELO, NEGOCIOS } from "../../features/conteudo/modelo";
import { Card, CardContent } from "../ui/card";
import { GraficoCalibracao } from "./GraficoCalibracao";
import { GraficoImportancia } from "./GraficoImportancia";
import { GraficoVies } from "./GraficoVies";

function CartaoGrafico({ titulo, children, descricao }) {
	return (
		<Card className="h-full min-w-0 border-border/40">
			<CardContent className="p-6">
				<h3 className="text-xl font-bold">{titulo}</h3>
				<p className="mt-1 mb-5 text-sm text-muted-foreground">{descricao}</p>
				{children}
			</CardContent>
		</Card>
	);
}

export function DiagnosticoModelo() {
	const [negocio, setNegocio] = useState("venda");
	const { sufixo } = NEGOCIOS.find((n) => n.id === negocio);
	const m = MODELO[negocio];
	const nAnuncios = m.calibracao.reduce((soma, d) => soma + d.n, 0);

	return (
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			whileInView={{ opacity: 1, y: 0 }}
			viewport={{ once: true }}
			transition={{ duration: 0.5 }}
			className="max-w-5xl mx-auto"
		>
			<div className="mb-6 flex flex-col items-center gap-3 text-center">
				<fieldset className="inline-flex rounded-full border border-border/60 bg-muted/40 p-1">
					<legend className="sr-only">Negócio</legend>
					{NEGOCIOS.map((n) => (
						<button
							key={n.id}
							type="button"
							aria-pressed={negocio === n.id}
							onClick={() => setNegocio(n.id)}
							className={`rounded-full px-5 py-1.5 text-sm font-medium transition-colors ${
								negocio === n.id
									? "bg-primary text-primary-foreground shadow"
									: "text-muted-foreground hover:text-foreground"
							}`}
						>
							{n.rotulo}
						</button>
					))}
				</fieldset>
				<p className="max-w-2xl text-xs text-muted-foreground">
					Previsões fora da amostra: cada um dos {numero(nAnuncios)} anúncios de
					treino e validação foi previsto por um modelo que não o viu (validação
					cruzada agrupada por imóvel). O conjunto de teste não é reaberto para
					isso.
				</p>
			</div>

			<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<CartaoGrafico
					titulo="Previsto × pedido"
					descricao="Anúncios em 10 faixas de preço pedido. O ponto é a previsão mediana e a linha, onde caem 80% das previsões da faixa. Sobre a diagonal, o modelo acerta em média."
				>
					<GraficoCalibracao dados={m.calibracao} sufixo={sufixo} />
				</CartaoGrafico>
				<CartaoGrafico
					titulo="Viés por faixa de preço"
					descricao={resumoVies(m.vies)}
				>
					<GraficoVies dados={m.vies} sufixo={sufixo} />
				</CartaoGrafico>
				<div className="lg:col-span-2">
					<CartaoGrafico
						titulo="O que pesa na estimativa"
						descricao="Quanto cada informação reduz o erro nas árvores do modelo. Bairros e tipos de imóvel aparecem somados. Mostra o que o modelo usa, não o que causa o preço."
					>
						<GraficoImportancia dados={m.importancia} />
					</CartaoGrafico>
				</div>
			</div>
		</motion.div>
	);
}
