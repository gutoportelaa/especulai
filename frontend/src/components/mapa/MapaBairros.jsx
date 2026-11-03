import { useState } from "react";
import { numero } from "../../features/conteudo/formato";
import {
	BAIRRO_POR_ID,
	MAPA,
	SEM_DADOS,
	classe,
	corDaClasse,
} from "../../features/conteudo/mapa";
import { useLargura } from "../../hooks/useLargura";
import { DicaGrafico } from "../metodologia/DicaGrafico";

const idDoAlvo = (evento) => evento.target?.dataset?.id;

/**
 * Bairros de Teresina coloridos pela métrica. O mouse mostra a dica e o clique seleciona; pelo
 * teclado, a seleção é feita na lista de bairros do painel (123 áreas tabuláveis seriam piores).
 */
export function MapaBairros({
	negocio,
	metrica,
	sufixo,
	cortes,
	selecionado,
	onSelecionar,
}) {
	const [ref, largura] = useLargura(440);
	const [sobre, setSobre] = useState(null);
	const escala = largura / MAPA.largura;
	const nClasses = cortes.length + 1;

	function cor(bairro) {
		const v = metrica.valor(bairro[negocio]);
		return v === undefined
			? "url(#sem-dados)"
			: corDaClasse(classe(v, cortes), nClasses);
	}

	function dica(id) {
		const b = BAIRRO_POR_ID[id];
		const d = b[negocio];
		const v = metrica.valor(d);
		return {
			x: b.x * escala,
			y: b.y * escala,
			titulo: b.nome,
			linhas: [
				[metrica.rotulo, v === undefined ? "—" : metrica.formato(v, sufixo)],
				["Imóveis", numero(d.imoveis)],
			],
		};
	}

	return (
		<div ref={ref} className="relative mx-auto w-full max-w-[440px]">
			<svg
				viewBox={`0 0 ${MAPA.largura} ${MAPA.altura}`}
				className="block h-auto w-full touch-manipulation"
				role="img"
				aria-label={`Mapa dos bairros de Teresina por ${metrica.rotulo.toLowerCase()}. Os valores estão na tabela abaixo do mapa.`}
				onPointerMove={(e) => {
					if (e.pointerType === "mouse") setSobre(idDoAlvo(e) ?? null);
				}}
				onPointerLeave={() => setSobre(null)}
				onPointerUp={(e) => {
					const id = idDoAlvo(e);
					if (id) onSelecionar(id);
				}}
			>
				<defs>
					<pattern
						id="sem-dados"
						width="6"
						height="6"
						patternUnits="userSpaceOnUse"
						patternTransform="rotate(45)"
					>
						<rect width="6" height="6" fill={SEM_DADOS} />
						<line
							x1="0"
							y1="0"
							x2="0"
							y2="6"
							stroke="#d4d4d8"
							strokeWidth="1.5"
						/>
					</pattern>
				</defs>
				{MAPA.bairros.map((b) => (
					<path
						key={b.id}
						data-id={b.id}
						d={b.d}
						fill={cor(b)}
						fillRule="evenodd"
						stroke="#ffffff"
						strokeWidth={1}
						strokeLinejoin="round"
						vectorEffect="non-scaling-stroke"
						className="cursor-pointer"
					/>
				))}
				<path
					d={MAPA.contorno}
					fill="none"
					stroke="#a1a1aa"
					strokeWidth={1}
					vectorEffect="non-scaling-stroke"
					pointerEvents="none"
				/>
				{[
					["sobre", sobre !== selecionado && sobre, 1.5],
					["selecionado", selecionado, 2.5],
				].map(
					([papel, id, espessura]) =>
						id && (
							<path
								key={papel}
								d={BAIRRO_POR_ID[id].d}
								fill="none"
								fillRule="evenodd"
								stroke="#18181b"
								strokeWidth={espessura}
								strokeLinejoin="round"
								vectorEffect="non-scaling-stroke"
								pointerEvents="none"
							/>
						),
				)}
			</svg>
			<DicaGrafico ativo={sobre ? dica(sobre) : null} largura={largura} />
		</div>
	);
}
