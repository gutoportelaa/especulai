import { useState } from "react";
import { escalaLog, marcasLog } from "../../features/conteudo/escalas";
import { numero, pct, reais } from "../../features/conteudo/formato";
import { CORES, curto } from "../../features/conteudo/graficos";
import { useLargura } from "../../hooks/useLargura";
import { DicaGrafico } from "./DicaGrafico";
import { TabelaDados } from "./TabelaDados";

const M = { topo: 16, dir: 16, base: 44, esq: 64 };

/** Previsto × pedido em 10 faixas de preço pedido, eixos em log. A diagonal é o acerto perfeito. */
export function GraficoCalibracao({ dados, sufixo }) {
	const [ref, largura] = useLargura();
	const [ativo, setAtivo] = useState(null);

	const altura = Math.round(Math.min(Math.max(largura * 0.72, 260), 380));
	const valores = dados.flatMap((d) => [
		d.pedido,
		d.previsto_p10,
		d.previsto_p90,
	]);
	const dominio = [Math.min(...valores) * 0.85, Math.max(...valores) * 1.15];
	const x = escalaLog(dominio, [M.esq, largura - M.dir]);
	const y = escalaLog(dominio, [altura - M.base, M.topo]);
	const marcas = marcasLog(dominio, largura < 420 ? 4 : 6);
	const ponta = dominio[0] * (dominio[1] / dominio[0]) ** 0.97;
	const rotulo = {
		x: x(ponta),
		y: y(ponta),
		angulo:
			(Math.atan2(
				y(dominio[1]) - y(dominio[0]),
				x(dominio[1]) - x(dominio[0]),
			) *
				180) /
			Math.PI,
	};
	const coluna = Math.max(24, (largura - M.esq - M.dir) / dados.length);

	const dica = (d, i) => ({
		x: x(d.pedido),
		y: y(d.previsto_p90),
		titulo: `Faixa ${i + 1} de ${dados.length}`,
		linhas: [
			["Pedido mediano", `${reais(d.pedido)}${sufixo}`],
			["Previsto mediano", `${reais(d.previsto)}${sufixo}`],
			["Diferença", pct(d.previsto / d.pedido - 1, { casas: 0, sinal: true })],
			["Anúncios", numero(d.n)],
		],
	});

	return (
		<div>
			<div ref={ref} className="relative w-full min-w-0">
				<svg
					className="block"
					width={largura}
					height={altura}
					role="img"
					aria-label="Preço previsto mediano contra preço pedido mediano, em 10 faixas de preço"
				>
					{marcas.map((v) => (
						<g key={v}>
							<line
								x1={x(v)}
								x2={x(v)}
								y1={M.topo}
								y2={altura - M.base}
								stroke={CORES.grade}
							/>
							<line
								x1={M.esq}
								x2={largura - M.dir}
								y1={y(v)}
								y2={y(v)}
								stroke={CORES.grade}
							/>
							<text
								x={x(v)}
								y={altura - M.base + 16}
								textAnchor="middle"
								fontSize="11"
								fill={CORES.eixo}
							>
								{curto(v)}
							</text>
							<text
								x={M.esq - 8}
								y={y(v) + 4}
								textAnchor="end"
								fontSize="11"
								fill={CORES.eixo}
							>
								{curto(v)}
							</text>
						</g>
					))}
					<text
						x={(M.esq + largura - M.dir) / 2}
						y={altura - 6}
						textAnchor="middle"
						fontSize="12"
						fill={CORES.eixo}
					>
						Preço pedido (R${sufixo})
					</text>
					<text
						transform={`translate(14 ${(M.topo + altura - M.base) / 2}) rotate(-90)`}
						textAnchor="middle"
						fontSize="12"
						fill={CORES.eixo}
					>
						Previsto (R$)
					</text>

					<line
						x1={x(dominio[0])}
						y1={y(dominio[0])}
						x2={x(dominio[1])}
						y2={y(dominio[1])}
						stroke={CORES.referencia}
					/>
					{/* Rótulo deitado sobre a diagonal, logo acima dela, para a linha não cortar o texto. */}
					<text
						transform={`translate(${rotulo.x} ${rotulo.y}) rotate(${rotulo.angulo})`}
						dy={-6}
						textAnchor="end"
						fontSize="11"
						fill={CORES.eixo}
					>
						previsto = pedido
					</text>

					{dados.map((d, i) => (
						<g
							key={d.pedido}
							tabIndex={0}
							aria-label={`Faixa ${i + 1}: pedido ${reais(d.pedido)}, previsto ${reais(d.previsto)}`}
							onPointerEnter={() => setAtivo(dica(d, i))}
							onPointerLeave={() => setAtivo(null)}
							onFocus={() => setAtivo(dica(d, i))}
							onBlur={() => setAtivo(null)}
							className="cursor-default outline-none [&:focus-visible>circle]:stroke-foreground"
						>
							<rect
								x={x(d.pedido) - coluna / 2}
								y={M.topo}
								width={coluna}
								height={altura - M.base - M.topo}
								fill="transparent"
							/>
							<line
								x1={x(d.pedido)}
								x2={x(d.pedido)}
								y1={y(d.previsto_p10)}
								y2={y(d.previsto_p90)}
								stroke={CORES.serie}
								strokeOpacity={
									ativo?.titulo === `Faixa ${i + 1} de ${dados.length}`
										? 0.7
										: 0.3
								}
								strokeWidth={2}
								strokeLinecap="round"
							/>
							<circle
								cx={x(d.pedido)}
								cy={y(d.previsto)}
								r={5}
								fill={CORES.serie}
								stroke="#ffffff"
								strokeWidth={2}
							/>
						</g>
					))}
				</svg>
				<DicaGrafico ativo={ativo} largura={largura} />
			</div>

			<TabelaDados
				legenda="Previsto contra pedido por faixa de preço"
				colunas={[
					"Faixa",
					"Pedido mediano",
					"Previsto mediano",
					"80% das previsões",
					"Anúncios",
				]}
				linhas={dados.map((d, i) => [
					`${i + 1}`,
					reais(d.pedido),
					reais(d.previsto),
					`${curto(d.previsto_p10)} – ${curto(d.previsto_p90)}`,
					numero(d.n),
				])}
			/>
		</div>
	);
}
