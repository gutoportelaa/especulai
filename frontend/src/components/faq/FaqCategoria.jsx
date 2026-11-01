import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { REPO_URL } from "../../features/conteudo/metodologia";
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from "../ui/accordion";

const LINKS = {
	repositorio: { href: REPO_URL, rotulo: "Abrir o repositório no GitHub" },
};

export function FaqCategoria({ categoria }) {
	const { id, titulo, icone: Icone, perguntas } = categoria;

	return (
		<section id={id} className="scroll-mt-24">
			<div className="flex items-center gap-3 mb-2">
				<div className="size-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
					<Icone className="size-5" />
				</div>
				<h2 className="text-2xl font-bold tracking-tight">{titulo}</h2>
			</div>

			<Accordion type="single" collapsible className="w-full">
				{perguntas.map((p, i) => {
					const valor = `${id}-${i}`;
					const link = p.link && LINKS[p.link];
					return (
						<motion.div
							key={p.pergunta}
							initial={{ opacity: 0, y: 10 }}
							whileInView={{ opacity: 1, y: 0 }}
							viewport={{ once: true }}
							transition={{ duration: 0.3, delay: i * 0.05 }}
						>
							<AccordionItem
								value={valor}
								className="border-b border-border/40 py-2"
							>
								<AccordionTrigger
									className="text-left font-medium hover:no-underline"
									value={valor}
								>
									{p.pergunta}
								</AccordionTrigger>
								<AccordionContent
									className="text-muted-foreground"
									value={valor}
								>
									<p>{p.resposta}</p>
									{link && (
										<a
											href={link.href}
											target="_blank"
											rel="noreferrer"
											className="mt-2 inline-flex items-center gap-1 font-medium text-primary hover:underline"
										>
											{link.rotulo}
											<ArrowUpRight className="size-4" />
										</a>
									)}
								</AccordionContent>
							</AccordionItem>
						</motion.div>
					);
				})}
			</Accordion>
		</section>
	);
}
