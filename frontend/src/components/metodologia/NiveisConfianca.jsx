import { motion } from "framer-motion";
import { NIVEIS_CONFIANCA } from "../../features/conteudo/metodologia";
import { Card, CardContent } from "../ui/card";

const BARRAS = { alta: 3, média: 2, baixa: 1 };

export function NiveisConfianca() {
	return (
		<div className="grid gap-6 md:grid-cols-3 max-w-5xl mx-auto">
			{NIVEIS_CONFIANCA.map((n, i) => (
				<motion.div
					key={n.nivel}
					initial={{ opacity: 0, y: 20 }}
					whileInView={{ opacity: 1, y: 0 }}
					viewport={{ once: true }}
					transition={{ duration: 0.5, delay: i * 0.1 }}
				>
					<Card className="h-full border-border/40 bg-gradient-to-b from-background to-muted/10">
						<CardContent className="p-6 space-y-4">
							<div className="flex items-end gap-1" aria-hidden="true">
								{[1, 2, 3].map((b) => (
									<span
										key={b}
										className={`w-2 rounded-sm ${b <= BARRAS[n.nivel] ? "bg-primary" : "bg-muted"}`}
										style={{ height: `${b * 8}px` }}
									/>
								))}
							</div>
							<h3 className="text-xl font-bold">
								Confiança {n.titulo.toLowerCase()}
							</h3>
							<p className="text-muted-foreground">{n.regra}</p>
						</CardContent>
					</Card>
				</motion.div>
			))}
		</div>
	);
}
