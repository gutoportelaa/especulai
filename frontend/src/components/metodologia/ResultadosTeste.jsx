import { motion } from "framer-motion";
import { pct } from "../../features/conteudo/formato";
import { RESULTADOS, TERCOS } from "../../features/conteudo/metodologia";
import { Card, CardContent } from "../ui/card";

// Escala das barras de cobertura: de 60% a 100%, para a diferença ao redor de 80% ficar visível.
const PISO = 0.6;
const largura = (fracao) => `${((fracao - PISO) / (1 - PISO)) * 100}%`;

export function ResultadosTeste() {
	return (
		<div className="grid gap-6 md:grid-cols-2 max-w-5xl mx-auto">
			{RESULTADOS.map((r, i) => (
				<motion.div
					key={r.id}
					initial={{ opacity: 0, y: 20 }}
					whileInView={{ opacity: 1, y: 0 }}
					viewport={{ once: true }}
					transition={{ duration: 0.5, delay: i * 0.1 }}
				>
					<Card className="h-full border-border/40">
						<CardContent className="p-6 space-y-6">
							<div className="flex items-baseline justify-between">
								<h3 className="text-2xl font-bold">{r.titulo}</h3>
								<span className="text-sm text-muted-foreground">
									{r.n} anúncios de teste
								</span>
							</div>

							<div className="rounded-xl bg-gradient-to-br from-primary to-primary/80 p-5 text-primary-foreground">
								<p className="text-sm text-primary-foreground/80">
									Preço pedido dentro da faixa de 80%
								</p>
								<p className="text-4xl font-bold">{pct(r.cobertura)}</p>
							</div>

							<dl className="grid grid-cols-2 gap-4">
								{r.metricas.map((m) => (
									<div key={m.rotulo}>
										<dt className="text-xs text-muted-foreground">
											{m.rotulo}
										</dt>
										<dd className="text-xl font-bold">{m.valor}</dd>
									</div>
								))}
							</dl>

							<div className="space-y-3">
								<p className="text-sm font-medium">
									Acerto da faixa por terço de preço
								</p>
								{r.porTerco.map((fracao, t) => (
									<div key={TERCOS[t]} className="space-y-1">
										<div className="flex justify-between text-xs text-muted-foreground">
											<span>{TERCOS[t]}</span>
											<span className="font-semibold text-foreground">
												{pct(fracao, { casas: 0 })}
											</span>
										</div>
										<div className="relative h-2 rounded-full bg-muted">
											<div
												className="h-2 rounded-full bg-primary"
												style={{ width: largura(fracao) }}
											/>
											<div
												className="absolute -top-1 h-4 w-0.5 bg-foreground/40"
												style={{ left: largura(0.8) }}
												title="Meta: 80%"
											/>
										</div>
									</div>
								))}
								<p className="text-xs text-muted-foreground">
									O traço marca a meta de 80%. A escala começa em{" "}
									{pct(PISO, { casas: 0 })}.
								</p>
							</div>
						</CardContent>
					</Card>
				</motion.div>
			))}
		</div>
	);
}
