import { motion } from "framer-motion";
import { KeyRound, Server, ShieldCheck, Timer } from "lucide-react";
import { PROTECOES } from "../../features/conteudo/metodologia";
import { Card, CardContent } from "../ui/card";

const ICONES = [ShieldCheck, Server, KeyRound, Timer];

export function ProtecaoDados() {
	return (
		<div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
			{PROTECOES.map((p, i) => {
				const Icone = ICONES[i];
				return (
					<motion.div
						key={p.titulo}
						initial={{ opacity: 0, y: 20 }}
						whileInView={{ opacity: 1, y: 0 }}
						viewport={{ once: true }}
						transition={{ duration: 0.5, delay: i * 0.1 }}
					>
						<Card className="h-full border-border/40 bg-gradient-to-b from-background to-muted/10 transition-all hover:shadow-md">
							<CardContent className="p-6">
								<div className="size-10 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-4">
									<Icone className="size-5" />
								</div>
								<h3 className="text-lg font-bold mb-2">{p.titulo}</h3>
								<p className="text-sm text-muted-foreground">{p.texto}</p>
							</CardContent>
						</Card>
					</motion.div>
				);
			})}
		</div>
	);
}
