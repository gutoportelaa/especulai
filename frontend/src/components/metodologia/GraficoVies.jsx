import { useState } from "react";
import { escalaLinear, limiteSimetrico } from "../../features/conteudo/escalas";
import { numero, pct, reais } from "../../features/conteudo/formato";
import { CORES, rotuloFaixa } from "../../features/conteudo/graficos";
import { useLargura } from "../../hooks/useLargura";
import { DicaGrafico } from "./DicaGrafico";
import { TabelaDados } from "./TabelaDados";

const M = { topo: 24, dir: 8, base: 44, esq: 44 };
const RAIO = 4;

/** Coluna com a ponta arredondada e a base reta, crescendo a partir do zero. */
function coluna(cx, base, ponta, largura) {
	const l = cx - largura / 2;
	const r = cx + largura / 2;
	const sobe = ponta < base;
	const raio = Math.min(RAIO, Math.abs(base - ponta));
	const d = sobe ? raio : -raio;
	return `M${l},${base} V${ponta + d} Q${l},${ponta} ${l + raio},${ponta} H${r - raio} Q${r},${ponta} ${r},${ponta + d} V${base} Z`;
}

/** Viés mediano (previsto ÷ pedido − 1) por quintil de preço pedido. */
export function GraficoVies({ dados, sufixo }) {
	const [ref, largura] = useLargura();
	const [ativo, setAtivo] = useState(null);

	const altura = 280;
	const limite = limiteSimetrico(dados.map((d) => d.vies));
	const y = escalaLinear([-limite, limite], [altura - M.base, M.topo]);
	const fatia = (largura - M.esq - M.dir) / dados.length;
	const cx = (i) => M.esq + fatia * (i + 0.5);
	const espessura = Math.min(24, fatia * 0.5);
	const marcas = [-limite, -limite / 2, 0, limite / 2, limite];

	const dica = (d, i) => ({
		x: cx(i),
		y: Math.min(y(d.vies), y(0)),
		titulo: `${reais(d.de)} a ${reais(d.ate)}${sufixo}`,
		linhas: [
			["Viés mediano", pct(d.vies, { casas: 0, sinal: true })],
			["Erro mediano", pct(d.erro, { casas: 0 })],
			["Anúncios", numero(d.n)],
		],
	});

	return (
		<div>
			<div className="mb-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
				<span className="inline-flex items-center gap-1.5">
					<span
						className="size-2.5 rounded-sm"
						style={{ background: CORES.acima }}
					/>
					Previsto acima do pedido
				</span>
				<span className="inline-flex items-center gap-1.5">
					<span
						className="size-2.5 rounded-sm"
						style={{ background: CORES.abaixo }}
					/>
					Previsto abaixo do pedido
				</span>
			</div>
			<div ref={ref} className="relative w-full min-w-0">
				<svg
					className="block"
					width={largura}
					height={altura}
					role="img"
					aria-label="Viés mediano da estimativa por faixa de preço pedido"
				>
					{marcas.map((v) => (
						<g key={v}>
							<line
								x1={M.esq}
								x2={largura - M.dir}
								y1={y(v)}
								y2={y(v)}
								stroke={v === 0 ? CORES.referencia : CORES.grade}
							/>
							<text
								x={M.esq - 8}
								y={y(v) + 4}
								textAnchor="end"
								fontSize="11"
								fill={CORES.eixo}
							>
								{pct(v, { casas: 0, sinal: true })}
							</text>
						</g>
					))}

					{dados.map((d, i) => {
						const [l1, l2] = rotuloFaixa(d, i, dados.length);
						const acima = d.vies >= 0;
						return (
							<g
								key={d.de}
								tabIndex={0}
								aria-label={`${l1} ${l2}: viés ${pct(d.vies, { casas: 0, sinal: true })}`}
								onPointerEnter={() => setAtivo(dica(d, i))}
								onPointerLeave={() => setAtivo(null)}
								onFocus={() => setAtivo(dica(d, i))}
								onBlur={() => setAtivo(null)}
								className="cursor-default outline-none [&:focus-visible>path]:opacity-80"
							>
								<rect
									x={cx(i) - fatia / 2}
									y={M.topo}
									width={fatia}
									height={altura - M.base - M.topo}
									fill="transparent"
								/>
								<path
									d={coluna(cx(i), y(0), y(d.vies), espessura)}
									fill={acima ? CORES.acima : CORES.abaixo}
								/>
								<text
									x={cx(i)}
									y={acima ? y(d.vies) - 6 : y(d.vies) + 14}
									textAnchor="middle"
									fontSize="12"
									fontWeight="600"
									fill="hsl(240 10% 3.9%)"
								>
									{pct(d.vies, { casas: 0, sinal: true })}
								</text>
								<text
									x={cx(i)}
									y={altura - M.base + 18}
									textAnchor="middle"
									fontSize="11"
									fill={CORES.eixo}
								>
									<tspan x={cx(i)}>{l1}</tspan>
									<tspan x={cx(i)} dy="13">
										{l2}
									</tspan>
								</text>
							</g>
						);
					})}
				</svg>
				<DicaGrafico ativo={ativo} largura={largura} />
			</div>

			<TabelaDados
				legenda="Viés e erro medianos por faixa de preço pedido"
				colunas={["Preço pedido", "Viés mediano", "Erro mediano", "Anúncios"]}
				linhas={dados.map((d) => [
					`${reais(d.de)} a ${reais(d.ate)}`,
					pct(d.vies, { casas: 0, sinal: true }),
					pct(d.erro, { casas: 0 }),
					numero(d.n),
				])}
			/>
		</div>
	);
}
