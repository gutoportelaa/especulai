import { ShieldAlert } from "lucide-react";
import { Footer } from "../../components/layout/Footer";
import { Header } from "../../components/layout/Header";
import { MapaSection } from "../../components/sections/MapaSection";

/**
 * Painel interno: os dados que alimentaram o modelo e os erros dele, bairro a bairro, com anúncios
 * reais comparados à faixa. Só existe no ambiente de desenvolvimento (ver `rotasInternas.jsx`).
 */
export function AdminDados() {
	return (
		<div className="flex min-h-[100dvh] flex-col">
			<Header />
			<main className="flex-1">
				<div className="container mx-auto mt-6 px-4 md:px-6">
					<div className="mx-auto flex max-w-6xl items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
						<ShieldAlert className="mt-0.5 size-5 shrink-0" />
						<p>
							<strong>Página interna.</strong> Só aparece em{" "}
							<code>make web-dev</code>; o build publicado no GitHub Pages não
							contém esta rota nem os exemplos de anúncios. Os anúncios são de
							outubro de 2026 e podem não estar mais à venda.
						</p>
					</div>
				</div>
				<MapaSection />
			</main>
			<Footer />
		</div>
	);
}
