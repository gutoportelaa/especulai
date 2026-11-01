import { ArrowUpRight, TriangleAlert } from "lucide-react";
import { LIMITACOES, RELATORIO_URL } from "../../features/conteudo/metodologia";

export function Limitacoes() {
	return (
		<div className="max-w-3xl mx-auto space-y-6">
			<ul className="space-y-3">
				{LIMITACOES.map((texto) => (
					<li key={texto} className="flex gap-3">
						<TriangleAlert className="mt-0.5 size-5 shrink-0 text-primary" />
						<span>{texto}</span>
					</li>
				))}
			</ul>
			<a
				href={RELATORIO_URL}
				target="_blank"
				rel="noreferrer"
				className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
			>
				Ler o relatório completo da coleta e dos experimentos
				<ArrowUpRight className="size-4" />
			</a>
		</div>
	);
}
