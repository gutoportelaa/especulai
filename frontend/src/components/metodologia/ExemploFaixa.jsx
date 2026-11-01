import { motion } from "framer-motion";
import { reais, reaisCompacto } from "../../features/conteudo/formato";
import { EXEMPLOS_FAIXA } from "../../features/conteudo/metodologia";
import { Card, CardContent } from "../ui/card";

export function ExemploFaixa() {
	return (
		<div className="grid gap-6 md:grid-cols-2 max-w-4xl mx-auto">
			{EXEMPLOS_FAIXA.map((ex, i) => (
				<motion.div
					key={ex.id}
					initial={{ opacity: 0, y: 20 }}
					whileInView={{ opacity: 1, y: 0 }}
					viewport={{ once: true }}
					transition={{ duration: 0.5, delay: i * 0.1 }}
				>
					<Card className="h-full border-border/40 bg-gradient-to-b from-background to-muted/10">
						<CardContent className="p-6 space-y-6">
							<div>
								<p className="text-sm font-semibold text-primary">
									{ex.rotulo}
								</p>
								<p className="text-sm text-muted-foreground">
									Estimativa central de {reaisCompacto(ex.central)}
									{ex.sufixo}, o preço pedido mediano do mercado
								</p>
							</div>

							<div className="text-center">
								<p className="text-xs uppercase tracking-wide text-muted-foreground">
									Faixa provável (80%)
								</p>
								<p className="text-2xl md:text-3xl font-bold tracking-tight">
									{reais(ex.minimo)} – {reais(ex.maximo)}
									<span className="text-base font-medium text-muted-foreground">
										{ex.sufixo}
									</span>
								</p>
							</div>

							<div className="relative h-3 rounded-full bg-gradient-to-r from-primary/20 via-primary to-primary/20">
								{/* A faixa é simétrica em log, então em reais a central fica à esquerda do meio. */}
								<div
									className="absolute top-1/2 size-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-background bg-primary shadow"
									style={{
										left: `${((ex.central - ex.minimo) / (ex.maximo - ex.minimo)) * 100}%`,
									}}
								/>
							</div>
							<div className="flex justify-between text-xs text-muted-foreground">
								<span>{reais(ex.minimo)}</span>
								<span className="font-semibold text-foreground">
									central {reais(ex.central)}
								</span>
								<span>{reais(ex.maximo)}</span>
							</div>
						</CardContent>
					</Card>
				</motion.div>
			))}
		</div>
	);
}
