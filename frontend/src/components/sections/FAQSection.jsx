import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { FAQ_DESTAQUES } from "../../features/conteudo/faq";
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from "../ui/accordion";
import { Badge } from "../ui/badge";

export function FAQSection() {
	return (
		<section id="faq" className="w-full py-20 md:py-32">
			<div className="container px-4 md:px-6">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					whileInView={{ opacity: 1, y: 0 }}
					viewport={{ once: true }}
					transition={{ duration: 0.5 }}
					className="flex flex-col items-center justify-center space-y-4 text-center mb-12"
				>
					<Badge
						className="rounded-full px-4 py-1.5 text-sm font-medium"
						variant="secondary"
					>
						FAQ
					</Badge>
					<h2 className="text-3xl md:text-4xl font-bold tracking-tight">
						Perguntas Frequentes
					</h2>
					<p className="max-w-[800px] text-muted-foreground md:text-lg">
						Encontre respostas para as dúvidas mais comuns sobre nossa
						plataforma.
					</p>
				</motion.div>

				<div className="mx-auto max-w-3xl">
					<Accordion type="single" collapsible className="w-full">
						{FAQ_DESTAQUES.map((faq, i) => (
							<motion.div
								key={faq.pergunta}
								initial={{ opacity: 0, y: 10 }}
								whileInView={{ opacity: 1, y: 0 }}
								viewport={{ once: true }}
								transition={{ duration: 0.3, delay: i * 0.05 }}
							>
								<AccordionItem
									value={`item-${i}`}
									className="border-b border-border/40 py-2"
								>
									<AccordionTrigger
										className="text-left font-medium hover:no-underline"
										value={`item-${i}`}
									>
										{faq.pergunta}
									</AccordionTrigger>
									<AccordionContent
										className="text-muted-foreground"
										value={`item-${i}`}
									>
										{faq.resposta}
									</AccordionContent>
								</AccordionItem>
							</motion.div>
						))}
					</Accordion>
					<div className="mt-8 text-center">
						<Link
							to="/faq"
							className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
						>
							Ver todas as perguntas
							<ArrowRight className="size-4" />
						</Link>
					</div>
				</div>
			</div>
		</section>
	);
}
