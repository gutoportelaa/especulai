import { SEM_DADOS, corDaClasse } from "../../features/conteudo/mapa";

/** Uma amostra por classe, com o intervalo de valores; e a hachura dos bairros sem número. */
export function LegendaMapa({ metrica, sufixo, cortes, minimo }) {
	const n = cortes.length + 1;
	const f = (v) =>
		metrica.legenda ? metrica.legenda(v) : metrica.formato(v, sufixo);
	const rotulos = Array.from({ length: n }, (_, i) => {
		if (n === 1) return "todos";
		if (i === 0) return `abaixo de ${f(cortes[0])}`;
		if (i === n - 1) return `${f(cortes[n - 2])} ou mais`;
		return `${f(cortes[i - 1])} a ${f(cortes[i])}`;
	});

	return (
		<div className="mt-4 text-xs text-muted-foreground">
			<p className="mb-2 font-medium text-foreground">
				{metrica.titulo}
				{metrica.unidade?.(sufixo)}
			</p>
			<ul className="flex flex-wrap gap-x-4 gap-y-1.5">
				{rotulos.map((rotulo, i) => (
					<li key={rotulo} className="flex items-center gap-1.5">
						<span
							className="size-3 shrink-0 rounded-sm"
							style={{ background: corDaClasse(i, n) }}
						/>
						<span className="tabular-nums">{rotulo}</span>
					</li>
				))}
				<li className="flex items-center gap-1.5">
					<span
						className="size-3 shrink-0 rounded-sm border border-zinc-300"
						style={{
							background: `repeating-linear-gradient(45deg, ${SEM_DADOS} 0 3px, #d4d4d8 3px 4.5px)`,
						}}
					/>
					<span>{minimo}</span>
				</li>
			</ul>
		</div>
	);
}
