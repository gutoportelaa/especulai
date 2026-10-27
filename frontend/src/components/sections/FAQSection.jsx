import { motion } from "framer-motion";
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from "../ui/accordion";
import { Badge } from "../ui/badge";

export function FAQSection() {
	const faqs = [
		{
			question: "Como funciona a predição de preços?",
			answer:
				"Dois modelos de machine learning (venda e aluguel), treinados com anúncios de imóveis de Teresina, estimam o preço a partir de área, quartos, banheiros, vagas, tipo e bairro. O bairro entra também com a renda e a densidade do Censo 2022 do IBGE. O resultado é uma faixa de preço, com 80% de chance de conter o preço anunciado.",
		},
		{
			question: "A predição é gratuita?",
			answer:
				"Sim, nossa plataforma é completamente gratuita. Você pode fazer quantas predições quiser sem custo algum.",
		},
		{
			question: "Quão precisa é a estimativa?",
			answer:
				"Em testes com anúncios que o modelo nunca viu, a faixa contém o preço anunciado em cerca de 80% dos casos, mas é larga: o limite superior é, em média, 2,3 vezes o inferior na venda e 2,6 vezes no aluguel. Menos da metade das estimativas centrais fica a ±20% do preço anunciado. Por isso mostramos a faixa, e não só um número.",
		},
		{
			question: "Quais informações são necessárias?",
			answer:
				"Para fazer uma predição, você precisa informar: área do imóvel (m²), número de quartos, número de banheiros, tipo do imóvel (apartamento, casa, sobrado, etc.) e bairro. Vagas de garagem são opcionais. Só Teresina é coberta.",
		},
		{
			question: "Meus dados são seguros?",
			answer:
				"Pedimos apenas as características do imóvel, nunca nome, endereço exato ou contato.",
		},
		{
			question: "Posso usar a predição para vender meu imóvel?",
			answer:
				"A estimativa se baseia em preços pedidos em anúncios, não em preços de fechamento, que costumam ser menores. Serve como referência inicial, não como avaliação. Antes de decidir, consulte um corretor ou avaliador.",
		},
	];

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
						{faqs.map((faq, i) => (
							<motion.div
								key={faq.question}
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
										{faq.question}
									</AccordionTrigger>
									<AccordionContent
										className="text-muted-foreground"
										value={`item-${i}`}
									>
										{faq.answer}
									</AccordionContent>
								</AccordionItem>
							</motion.div>
						))}
					</Accordion>
				</div>
			</div>
		</section>
	);
}
