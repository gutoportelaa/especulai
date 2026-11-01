import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { FaqCategoria } from "../components/faq/FaqCategoria";
import { Footer } from "../components/layout/Footer";
import { Header } from "../components/layout/Header";
import { CTASection } from "../components/sections/CTASection";
import { PageHero } from "../components/sections/PageHero";
import { FAQ_CATEGORIAS } from "../features/conteudo/faq";

export function Faq() {
	return (
		<div className="flex min-h-[100dvh] flex-col">
			<Header />
			<main className="flex-1">
				<PageHero badge="FAQ" titulo="Perguntas Frequentes">
					O que a estimativa diz, o quanto ela acerta, de onde vêm os dados e o
					que fazemos com o que você digita.
				</PageHero>

				<div className="container px-4 md:px-6 pb-20 md:pb-32">
					<div className="grid gap-10 lg:grid-cols-[220px_1fr] max-w-5xl mx-auto">
						<nav
							aria-label="Categorias"
							className="lg:sticky lg:top-24 lg:self-start"
						>
							<ul className="flex flex-wrap gap-2 lg:flex-col lg:gap-1">
								{FAQ_CATEGORIAS.map(({ id, titulo, icone: Icone }) => (
									<li key={id}>
										<Link
											to={{ hash: `#${id}` }}
											className="inline-flex items-center gap-2 rounded-full border border-border/40 px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-muted lg:w-full lg:border-transparent"
										>
											<Icone className="size-4 text-primary" />
											{titulo}
										</Link>
									</li>
								))}
							</ul>
							<Link
								to="/como-funciona"
								className="mt-6 hidden lg:inline-flex items-center gap-1 px-4 text-sm font-medium text-primary hover:underline"
							>
								Ver a metodologia
								<ArrowRight className="size-4" />
							</Link>
						</nav>

						<div className="space-y-14">
							{FAQ_CATEGORIAS.map((categoria) => (
								<FaqCategoria key={categoria.id} categoria={categoria} />
							))}
						</div>
					</div>
				</div>

				<CTASection
					secundario={{ to: "/como-funciona", rotulo: "Como Funciona" }}
				/>
			</main>
			<Footer />
		</div>
	);
}
