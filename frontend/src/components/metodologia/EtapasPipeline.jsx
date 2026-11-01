import { motion } from "framer-motion";
import { ETAPAS } from "../../features/conteudo/metodologia";

export function EtapasPipeline() {
	return (
		<ol className="relative max-w-3xl mx-auto space-y-10">
			<div className="absolute left-8 top-8 bottom-8 w-0.5 bg-gradient-to-b from-primary/40 via-border to-transparent hidden sm:block" />

			{ETAPAS.map((etapa, i) => (
				<motion.li
					key={etapa.id}
					id={etapa.id}
					initial={{ opacity: 0, y: 20 }}
					whileInView={{ opacity: 1, y: 0 }}
					viewport={{ once: true }}
					transition={{ duration: 0.5 }}
					className="relative flex flex-col sm:flex-row gap-4 sm:gap-6 scroll-mt-24"
				>
					<div className="relative z-10 flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-primary-foreground text-xl font-bold shadow-lg">
						{String(i + 1).padStart(2, "0")}
					</div>
					<div className="flex-1 rounded-lg border border-border/40 bg-background p-6 shadow-sm">
						<h3 className="text-xl font-bold mb-2">{etapa.titulo}</h3>
						<p className="mb-3">{etapa.resumo}</p>
						<p className="text-sm text-muted-foreground mb-5">
							{etapa.detalhe}
						</p>
						<div className="flex flex-wrap gap-3">
							{etapa.numeros.map((n) => (
								<div
									key={n.rotulo}
									className="rounded-full bg-primary/10 px-4 py-1.5 text-sm"
								>
									<span className="font-bold text-primary">{n.valor}</span>{" "}
									<span className="text-muted-foreground">{n.rotulo}</span>
								</div>
							))}
						</div>
					</div>
				</motion.li>
			))}
		</ol>
	);
}
