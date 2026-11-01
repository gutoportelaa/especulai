import { motion } from "framer-motion";
import { Ban, Check, Minus, X } from "lucide-react";
import { HIPOTESES } from "../../features/conteudo/metodologia";

const VEREDITOS = {
	ajudou: { icone: Check, classe: "bg-primary text-primary-foreground" },
	"sem ganho": {
		icone: Minus,
		classe: "bg-secondary text-secondary-foreground",
	},
	piorou: { icone: X, classe: "bg-secondary text-secondary-foreground" },
	fora: { icone: Ban, classe: "border border-border text-muted-foreground" },
};

export function HipotesesTestadas() {
	return (
		<ul className="max-w-3xl mx-auto divide-y divide-border/40 rounded-lg border border-border/40 bg-background">
			{HIPOTESES.map((h, i) => {
				const { icone: Icone, classe } = VEREDITOS[h.veredito];
				return (
					<motion.li
						key={h.hipotese}
						initial={{ opacity: 0, y: 10 }}
						whileInView={{ opacity: 1, y: 0 }}
						viewport={{ once: true }}
						transition={{ duration: 0.3, delay: i * 0.05 }}
						className="flex flex-col sm:flex-row sm:items-start gap-3 p-5"
					>
						<span
							className={`inline-flex w-fit shrink-0 items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold sm:w-28 sm:justify-center ${classe}`}
						>
							<Icone className="size-3.5" />
							{h.veredito}
						</span>
						<div>
							<p className="font-medium">{h.hipotese}</p>
							<p className="text-sm text-muted-foreground">{h.detalhe}</p>
						</div>
					</motion.li>
				);
			})}
		</ul>
	);
}
