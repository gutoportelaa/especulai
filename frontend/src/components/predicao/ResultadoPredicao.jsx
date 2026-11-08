import { motion } from "framer-motion";
import { Info } from "lucide-react";
import logo from "../../assets/solo_logo_Especulai.png";
import { Card, CardContent } from "../ui/card";

const COR_CONFIANCA = {
	alta: "bg-emerald-100 text-emerald-800",
	média: "bg-amber-100 text-amber-800",
	baixa: "bg-red-100 text-red-800",
};

const variacao = (de, para) => {
	const p = Math.round((para / de - 1) * 100);
	return `${p > 0 ? "+" : "−"}${Math.abs(p)}%`;
};

/**
 * O valor estimado é a resposta; a margem fica logo abaixo, menor, como aviso de quanto ele pode
 * variar. A marca na barra usa escala log, a mesma em que a margem é simétrica.
 */
export function ResultadoPredicao({ prediction, moeda }) {
	const {
		preco_estimado: valor,
		minimo,
		maximo,
		nivel,
		confianca,
	} = prediction;
	const aluguel = prediction.negocio === "aluguel";
	const posicao = (Math.log(valor / minimo) / Math.log(maximo / minimo)) * 100;

	return (
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			className="mb-8"
		>
			<Card className="overflow-hidden border-primary/40 bg-gradient-to-b from-primary/5 to-background">
				<CardContent className="space-y-6 p-6 text-center md:p-10">
					<div className="flex items-center justify-center gap-2">
						<img src={logo} alt="" className="size-6" />
						<p className="text-sm font-medium text-muted-foreground">
							{aluguel ? "Aluguel mensal estimado" : "Valor de venda estimado"}
						</p>
					</div>

					<motion.p
						initial={{ scale: 0.9, opacity: 0 }}
						animate={{ scale: 1, opacity: 1 }}
						transition={{ type: "spring", stiffness: 260, damping: 18 }}
						className="text-5xl font-bold tracking-tight text-primary tabular-nums md:text-6xl"
					>
						{moeda(valor)}
						{aluguel && (
							<span className="text-2xl font-medium text-muted-foreground">
								/mês
							</span>
						)}
					</motion.p>

					{confianca && (
						<span
							className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${COR_CONFIANCA[confianca] ?? "bg-muted text-foreground"}`}
						>
							Confiança {confianca}
						</span>
					)}

					<div className="mx-auto max-w-md space-y-2 pt-2">
						<p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
							Margem de erro
						</p>
						<div className="relative h-1.5 rounded-full bg-gradient-to-r from-primary/15 via-primary/50 to-primary/15">
							<div
								className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary shadow"
								style={{ left: `${posicao}%` }}
							/>
						</div>
						<div className="flex justify-between text-sm tabular-nums">
							<span className="text-left">
								<span className="block text-muted-foreground">
									{moeda(minimo)}
								</span>
								<span className="text-xs text-muted-foreground/80">
									{variacao(valor, minimo)}
								</span>
							</span>
							<span className="text-right">
								<span className="block text-muted-foreground">
									{moeda(maximo)}
								</span>
								<span className="text-xs text-muted-foreground/80">
									{variacao(valor, maximo)}
								</span>
							</span>
						</div>
					</div>

					<p className="mx-auto flex max-w-md items-start justify-center gap-1.5 text-left text-xs text-muted-foreground">
						<Info className="mt-0.5 size-3.5 shrink-0" />
						<span>
							Em {Math.round(nivel * 100)}% dos anúncios parecidos, o preço
							pedido ficou dentro da margem. É uma especulação a partir de
							anúncios, não uma avaliação do imóvel.
						</span>
					</p>
				</CardContent>
			</Card>
		</motion.div>
	);
}
