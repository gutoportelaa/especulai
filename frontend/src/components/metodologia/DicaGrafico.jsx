/** Tooltip de um gráfico: posicionado pelo ponto ativo, preso dentro da largura do contêiner. */
export function DicaGrafico({ ativo, largura }) {
	if (!ativo) return null;
	const meia = 96;
	const x = Math.min(Math.max(ativo.x, meia), largura - meia);
	return (
		<div
			aria-hidden="true"
			className="pointer-events-none absolute z-10 w-48 -translate-x-1/2 -translate-y-full rounded-lg border border-border/60 bg-background px-3 py-2 text-xs shadow-md"
			style={{ left: x, top: ativo.y - 10 }}
		>
			<p className="mb-1 font-semibold text-foreground">{ativo.titulo}</p>
			{ativo.linhas.map(([rotulo, valor]) => (
				<p
					key={rotulo}
					className="flex justify-between gap-3 text-muted-foreground"
				>
					<span>{rotulo}</span>
					<span className="font-semibold text-foreground tabular-nums">
						{valor}
					</span>
				</p>
			))}
		</div>
	);
}
