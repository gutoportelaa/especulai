import { Check, X } from "lucide-react";
import { reais } from "../../features/conteudo/formato";

/** Um anúncio sorteado: o preço pedido contra a faixa que o modelo deu sem tê-lo visto. */
export function ExemploAnuncio({ exemplo: e, sufixo }) {
	// Escala log, com folga nas pontas, para o pedido aparecer mesmo fora da faixa.
	const lo = Math.log(Math.min(e.minimo, e.pedido)) - 0.08;
	const hi = Math.log(Math.max(e.maximo, e.pedido)) + 0.08;
	const pos = (v) => `${((Math.log(v) - lo) / (hi - lo)) * 100}%`;
	const quartos =
		e.quartos == null
			? ""
			: ` · ${e.quartos} ${e.quartos === 1 ? "quarto" : "quartos"}`;

	return (
		<li className="rounded-lg border border-border/50 p-3">
			<div className="flex items-start justify-between gap-3 text-sm">
				<p className="font-medium">
					{e.tipo} · {e.area} m²{quartos}
				</p>
				<p
					className={`flex shrink-0 items-center gap-1 text-xs font-semibold ${
						e.dentro ? "text-primary" : "text-muted-foreground"
					}`}
				>
					{e.dentro ? (
						<Check className="size-3.5" />
					) : (
						<X className="size-3.5" />
					)}
					{e.dentro ? "dentro da faixa" : "fora da faixa"}
				</p>
			</div>

			<div
				className="relative my-3 h-2 rounded-full bg-muted"
				aria-hidden="true"
			>
				<div
					className="absolute inset-y-0 rounded-full bg-primary/30"
					style={{
						left: pos(e.minimo),
						width: `calc(${pos(e.maximo)} - ${pos(e.minimo)})`,
					}}
				/>
				<div
					className="absolute top-1/2 h-3 w-0.5 -translate-x-1/2 -translate-y-1/2 bg-primary"
					style={{ left: pos(e.central) }}
				/>
				<div
					className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-zinc-900"
					style={{ left: pos(e.pedido) }}
				/>
			</div>

			<dl className="flex flex-wrap justify-between gap-x-4 gap-y-2 text-xs">
				<div>
					<dt className="text-muted-foreground">Pedido no anúncio</dt>
					<dd className="font-semibold tabular-nums">
						{reais(e.pedido)}
						{sufixo}
					</dd>
				</div>
				<div className="sm:text-right">
					<dt className="text-muted-foreground">Faixa do modelo</dt>
					<dd className="font-semibold tabular-nums">
						<span className="whitespace-nowrap">{reais(e.minimo)}</span> –{" "}
						<span className="whitespace-nowrap">{reais(e.maximo)}</span>
					</dd>
				</div>
			</dl>
		</li>
	);
}
