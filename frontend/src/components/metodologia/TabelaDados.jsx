/** Versão em tabela de um gráfico: todo valor fica acessível sem passar o mouse. */
export function TabelaDados({ colunas, linhas, legenda }) {
	return (
		<details className="mt-4 text-sm">
			<summary className="cursor-pointer font-medium text-primary hover:underline">
				Ver dados em tabela
			</summary>
			<div className="mt-3 overflow-x-auto">
				<table className="w-full text-left">
					<caption className="sr-only">{legenda}</caption>
					<thead>
						<tr className="border-b border-border/60 text-muted-foreground">
							{colunas.map((c, i) => (
								<th
									key={c}
									className={`py-2 pr-3 font-medium ${i > 0 ? "text-right" : ""}`}
								>
									{c}
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{linhas.map((linha) => (
							<tr key={linha[0]} className="border-b border-border/30">
								{linha.map((celula, i) => (
									<td
										key={`${linha[0]}-${colunas[i]}`}
										className={`py-1.5 pr-3 ${i > 0 ? "text-right tabular-nums" : ""}`}
									>
										{celula}
									</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</details>
	);
}
