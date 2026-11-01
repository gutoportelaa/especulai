import { pct } from "../../features/conteudo/formato";
import { CORES } from "../../features/conteudo/graficos";
import { TabelaDados } from "./TabelaDados";

const rotulo = (peso) => (peso < 0.005 ? "<1%" : pct(peso, { casas: 0 }));

/** Importância por redução de erro, somada por grupo de atributo (bairros e tipos juntos). */
export function GraficoImportancia({ dados }) {
	const maior = Math.max(...dados.map((d) => d.peso));
	return (
		<div>
			<ul
				className="space-y-3"
				aria-label="Importância de cada informação no modelo"
			>
				{dados.map((d) => (
					<li
						key={d.atributo}
						className="grid grid-cols-[minmax(0,9.5rem)_1fr] items-center gap-3 sm:grid-cols-[13rem_1fr]"
					>
						<span className="text-sm text-muted-foreground">{d.atributo}</span>
						<span className="flex items-center gap-2">
							<span
								className="h-3 rounded-r"
								style={{
									width: `${(d.peso / maior) * 85}%`,
									minWidth: 2,
									background: CORES.serie,
								}}
							/>
							<span className="text-sm font-semibold tabular-nums">
								{rotulo(d.peso)}
							</span>
						</span>
					</li>
				))}
			</ul>
			<TabelaDados
				legenda="Importância de cada informação no modelo"
				colunas={["Informação", "Participação"]}
				linhas={dados.map((d) => [d.atributo, pct(d.peso)])}
			/>
		</div>
	);
}
