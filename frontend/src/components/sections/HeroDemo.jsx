import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import logo from "../../assets/solo_logo_Especulai.png";
import { NEGOCIO_DEMO, sortearPins } from "../../features/conteudo/demo";
import demo from "../../features/conteudo/demo-hero.json";
import { reais, reaisCompacto } from "../../features/conteudo/formato";

const PENSA_MS = 900;
const MOSTRA_MS = 1500;
const PAUSA_MS = 3200;
const L = 72; // lado do ícone, em unidades do mapa
const HASTE = 16;
const TOPO = -HASTE - L;
const PRIMARIA = "hsl(var(--primary))";
const { padrao } = demo;
const descricao = `${padrao.tipo}, ${padrao.area} m², ${padrao.quartos} quartos, ${padrao.vagas} vaga`;

/** Pin: "?" enquanto o bairro espera, o ícone do Especulai quando o modelo responde. */
function Pin({ pin, estado, ativo, etiqueta }) {
	const resolvido = estado === "resolvido";
	const texto = etiqueta(pin.central);
	const largura = texto.length * 17 + 36;
	return (
		<motion.g
			initial={{ opacity: 0, y: -60 }}
			animate={{ opacity: 1, y: 0 }}
			transition={{ type: "spring", stiffness: 260, damping: 18 }}
			style={{ cursor: "pointer" }}
			data-nome={pin.nome}
		>
			<g transform={`translate(${pin.x} ${pin.y})`}>
				{estado === "pensando" && (
					<motion.rect
						x={-L / 2}
						y={TOPO}
						width={L}
						height={L}
						rx={L / 4}
						fill={PRIMARIA}
						initial={{ opacity: 0.45, scale: 1 }}
						animate={{ opacity: 0, scale: 1.9 }}
						transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY }}
						style={{ transformOrigin: `0px ${TOPO + L / 2}px` }}
					/>
				)}
				<path
					d={`M-9 ${-HASTE - 2} L0 0 L9 ${-HASTE - 2} Z`}
					fill={resolvido ? PRIMARIA : "#a1a1aa"}
				/>
				<AnimatePresence mode="wait" initial={false}>
					{resolvido ? (
						<motion.image
							key="logo"
							href={logo}
							x={-L * 0.58}
							y={TOPO - L * 0.08}
							width={L * 1.16}
							height={L * 1.16}
							initial={{ scale: 0.3, opacity: 0 }}
							animate={{ scale: 1, opacity: 1 }}
							transition={{ type: "spring", stiffness: 420, damping: 16 }}
							style={{ transformOrigin: `0px ${TOPO + L / 2}px` }}
						/>
					) : (
						<motion.g key="?" exit={{ opacity: 0, scale: 0.6 }}>
							<rect
								x={-L / 2}
								y={TOPO}
								width={L}
								height={L}
								rx={L / 4}
								fill="#ffffff"
								stroke="#a1a1aa"
								strokeWidth={3}
								strokeDasharray="8 6"
							/>
							<text
								y={TOPO + L / 2 + 2}
								textAnchor="middle"
								dominantBaseline="central"
								fontSize={L * 0.62}
								fontWeight={700}
								fill="#71717a"
							>
								?
							</text>
						</motion.g>
					)}
				</AnimatePresence>
				{resolvido && (
					<motion.g
						initial={{ opacity: 0, y: 8 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ delay: 0.15 }}
					>
						<rect
							x={-largura / 2}
							y={10}
							width={largura}
							height={48}
							rx={24}
							fill="#ffffff"
							stroke={ativo ? PRIMARIA : "#e4e4e7"}
							strokeWidth={ativo ? 4 : 2}
						/>
						<text
							y={35}
							textAnchor="middle"
							dominantBaseline="central"
							fontSize={30}
							fontWeight={700}
							fill="#18181b"
						>
							{texto}
						</text>
					</motion.g>
				)}
			</g>
		</motion.g>
	);
}

function novoCiclo(negocio) {
	return { negocio, pins: sortearPins(negocio), passo: 0, fase: "pensa" };
}

/**
 * Demonstração do que o Especulai faz: o mesmo imóvel colocado em bairros sorteados de Teresina e
 * o valor que o modelo especula para cada um, alternando venda e aluguel a cada ciclo. Um clique
 * num pin fixa aquele bairro.
 */
export function HeroDemo() {
	const reduzir = useReducedMotion();
	const [ciclo, setCiclo] = useState(() => {
		const c = novoCiclo("venda");
		return reduzir ? { ...c, passo: c.pins.length } : c;
	});
	const [fixo, setFixo] = useState(null);
	const { negocio, pins, passo, fase } = ciclo;
	const { rotulo, sufixo, etiqueta } = NEGOCIO_DEMO[negocio];

	useEffect(() => {
		if (reduzir || fixo) return;
		const fim = passo >= pins.length;
		const espera = fim ? PAUSA_MS : fase === "pensa" ? PENSA_MS : MOSTRA_MS;
		const t = setTimeout(() => {
			if (fim) {
				setCiclo(novoCiclo(negocio === "venda" ? "aluguel" : "venda"));
			} else if (fase === "pensa") {
				setCiclo((c) => ({ ...c, fase: "mostra" }));
			} else {
				setCiclo((c) => ({ ...c, passo: c.passo + 1, fase: "pensa" }));
			}
		}, espera);
		return () => clearTimeout(t);
	}, [negocio, pins, passo, fase, fixo, reduzir]);

	function estado(i) {
		if (fixo || i < passo) return "resolvido";
		if (i > passo) return "espera";
		return fase === "pensa" ? "pensando" : "resolvido";
	}
	const fixado = fixo && pins.find((p) => p.nome === fixo);
	const emCurso = !fixo && passo < pins.length ? pins[passo] : null;
	const atual = fixado || (emCurso && fase === "mostra" ? emCurso : null);
	const acesos = new Set(
		pins.filter((_, i) => estado(i) === "resolvido").map((p) => p.id),
	);

	return (
		<div className="grid h-full grid-cols-1 items-center gap-4 p-4 sm:p-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:gap-8 md:p-8">
			<div className="relative mx-auto h-[340px] w-full sm:h-[380px] md:h-[480px]">
				<svg
					viewBox={`-70 -100 ${demo.largura + 140} ${demo.altura + 170}`}
					className="h-full w-full"
					role="img"
					aria-label={`Teresina com o mesmo imóvel estimado em vários bairros, ${rotulo.toLowerCase()}: ${pins.map((p) => `${p.nome}, ${reais(p.central)}${sufixo}`).join("; ")}`}
					onPointerUp={(e) => {
						const nome = e.target.closest?.("[data-nome]")?.dataset.nome;
						if (nome) setFixo(nome === fixo ? null : nome);
					}}
				>
					<path d={demo.contorno} fill="hsl(var(--primary) / 0.05)" />
					{demo.bairros.map((b) => (
						<path
							key={b.id}
							d={b.d}
							fillRule="evenodd"
							fill={acesos.has(b.id) ? "hsl(var(--primary) / 0.3)" : "none"}
							stroke="hsl(var(--primary) / 0.22)"
							strokeWidth={1}
							vectorEffect="non-scaling-stroke"
							strokeLinejoin="round"
							style={{ transition: "fill .5s" }}
						/>
					))}
					<motion.path
						d={demo.contorno}
						fill="none"
						stroke="hsl(var(--primary) / 0.5)"
						strokeWidth={2}
						vectorEffect="non-scaling-stroke"
						strokeLinejoin="round"
						initial={reduzir ? false : { pathLength: 0 }}
						animate={{ pathLength: 1 }}
						transition={{ duration: 1.6, ease: "easeInOut" }}
					/>
					{pins.map((p, i) => (
						<Pin
							key={`${negocio}-${p.id}`}
							pin={p}
							estado={estado(i)}
							ativo={atual?.nome === p.nome}
							etiqueta={etiqueta}
						/>
					))}
				</svg>
			</div>

			<div className="mx-auto w-full max-w-sm text-left">
				<div className="rounded-2xl border border-border/60 bg-background/90 p-5 shadow-lg backdrop-blur">
					<div className="flex items-center justify-between gap-2">
						<p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
							O mesmo imóvel, bairro a bairro
						</p>
						<AnimatePresence mode="wait">
							<motion.span
								key={negocio}
								initial={{ opacity: 0, scale: 0.8 }}
								animate={{ opacity: 1, scale: 1 }}
								exit={{ opacity: 0, scale: 0.8 }}
								className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary"
							>
								{rotulo}
							</motion.span>
						</AnimatePresence>
					</div>
					<p className="mt-1 text-sm text-foreground">{descricao}</p>
					<div className="mt-4 min-h-[112px]">
						<AnimatePresence mode="wait">
							{atual ? (
								<motion.div
									key={`${negocio}-${atual.nome}`}
									initial={{ opacity: 0, y: 8 }}
									animate={{ opacity: 1, y: 0 }}
									exit={{ opacity: 0, y: -8 }}
									transition={{ duration: 0.25 }}
								>
									<p className="text-sm font-semibold text-primary">
										{atual.nome}
									</p>
									<p className="text-3xl font-bold tracking-tight tabular-nums md:text-4xl">
										{reais(atual.central)}
										<span className="text-base font-medium text-muted-foreground">
											{sufixo}
										</span>
									</p>
									<p className="mt-1 text-xs text-muted-foreground">
										Pode variar de {reaisCompacto(atual.minimo)} a{" "}
										{reaisCompacto(atual.maximo)}
										{sufixo} · confiança alta
									</p>
								</motion.div>
							) : emCurso ? (
								<Especulando
									key={`pensa-${negocio}-${emCurso.nome}`}
									nome={emCurso.nome}
								/>
							) : (
								<Resumo key={`resumo-${negocio}`} pins={pins} sufixo={sufixo} />
							)}
						</AnimatePresence>
					</div>
					<Link
						to="/predict"
						className="mt-4 inline-flex items-center text-sm font-medium text-primary hover:underline"
					>
						Especule o seu imóvel
						<ArrowRight className="ml-1 size-4" />
					</Link>
				</div>
				<p className="mt-3 px-1 text-xs text-muted-foreground">
					{fixo
						? "Toque no pin de novo para voltar à animação."
						: "Toque num pin para fixar o bairro."}{" "}
					Valores do modelo para o preço pedido.
				</p>
			</div>
		</div>
	);
}

function Resumo({ pins, sufixo }) {
	const valores = pins.map((p) => p.central);
	return (
		<motion.div
			initial={{ opacity: 0, y: 8 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0 }}
		>
			<p className="text-sm font-semibold text-primary">
				{pins.length} bairros, o mesmo imóvel
			</p>
			<p className="text-3xl font-bold tracking-tight tabular-nums md:text-4xl">
				{reaisCompacto(Math.min(...valores))} a{" "}
				{reaisCompacto(Math.max(...valores))}
				<span className="text-base font-medium text-muted-foreground">
					{sufixo}
				</span>
			</p>
			<p className="mt-1 text-xs text-muted-foreground">
				A localização sozinha muda o valor estimado.
			</p>
		</motion.div>
	);
}

function Especulando({ nome }) {
	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
		>
			<p className="text-sm font-semibold text-muted-foreground">{nome}</p>
			<p className="flex items-center gap-2 text-3xl font-bold text-muted-foreground/60 md:text-4xl">
				<Sparkles className="size-6 animate-pulse text-primary" />
				Especulando…
			</p>
		</motion.div>
	);
}
