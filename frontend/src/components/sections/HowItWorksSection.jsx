import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "../ui/badge";

export function HowItWorksSection() {
	const steps = [
		{
			step: "01",
			title: "Preencha os Dados",
			description:
				"Informe o negócio (venda ou aluguel), a área, os quartos, os banheiros, o tipo e o bairro.",
		},
		{
			step: "02",
			title: "Comparação com anúncios",
			description:
				"O modelo compara com anúncios de Teresina coletados em outubro de 2026 e com a renda do bairro (Censo 2022).",
		},
		{
			step: "03",
			title: "Receba a Estimativa",
			description:
				"Veja a faixa de preço provável, a estimativa central e o nível de confiança, que depende do quanto o modelo conhece o bairro.",
		},
	];

	return (
		<section
			id="como-funciona"
			className="w-full py-20 md:py-32 bg-muted/30 relative overflow-hidden"
		>
			<div className="absolute inset-0 -z-10 h-full w-full bg-white bg-[linear-gradient(to_right,#f0f0f0_1px,transparent_1px),linear-gradient(to_bottom,#f0f0f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,#000_40%,transparent_100%)]" />

			<div className="container px-4 md:px-6 relative">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					whileInView={{ opacity: 1, y: 0 }}
					viewport={{ once: true }}
					transition={{ duration: 0.5 }}
					className="flex flex-col items-center justify-center space-y-4 text-center mb-16"
				>
					<Badge
						className="rounded-full px-4 py-1.5 text-sm font-medium"
						variant="secondary"
					>
						Como Funciona
					</Badge>
					<h2 className="text-3xl md:text-4xl font-bold tracking-tight">
						Processo Simples, Resultados Poderosos
					</h2>
					<p className="max-w-[800px] text-muted-foreground md:text-lg">
						Em apenas três passos, você obtém uma faixa de preço para o seu
						imóvel.
					</p>
				</motion.div>

				<div className="grid md:grid-cols-3 gap-8 md:gap-12 relative">
					<div className="hidden md:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-border to-transparent -translate-y-1/2 z-0" />

					{steps.map((step, i) => (
						<motion.div
							key={step.title}
							initial={{ opacity: 0, y: 20 }}
							whileInView={{ opacity: 1, y: 0 }}
							viewport={{ once: true }}
							transition={{ duration: 0.5, delay: i * 0.1 }}
							className="relative z-10 flex flex-col items-center text-center space-y-4"
						>
							<div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-primary-foreground text-xl font-bold shadow-lg">
								{step.step}
							</div>
							<h3 className="text-xl font-bold">{step.title}</h3>
							<p className="text-muted-foreground">{step.description}</p>
						</motion.div>
					))}
				</div>

				<div className="mt-14 text-center">
					<Link
						to="/como-funciona"
						className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
					>
						Ver a metodologia, os resultados e as limitações
						<ArrowRight className="size-4" />
					</Link>
				</div>
			</div>
		</section>
	);
}
