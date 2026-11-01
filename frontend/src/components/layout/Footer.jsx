import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import logoEspeculai from "../../assets/solo_logo_Especulai.png";
import { RELATORIO_URL, REPO_URL } from "../../features/conteudo/metodologia";

// `to` vira Link do router (respeita o basename); `href` é link externo.
const COLUNAS = [
	{
		titulo: "Produto",
		links: [
			{ rotulo: "Recursos", to: { pathname: "/", hash: "#features" } },
			{ rotulo: "Estimar preço", to: "/predict" },
			{ rotulo: "Como Funciona", to: "/como-funciona" },
		],
	},
	{
		titulo: "Saiba mais",
		links: [
			{ rotulo: "FAQ", to: "/faq" },
			{
				rotulo: "Resultados do modelo",
				to: { pathname: "/como-funciona", hash: "#resultados" },
			},
			{ rotulo: "Relatório completo", href: RELATORIO_URL },
		],
	},
	{
		titulo: "Projeto",
		links: [
			{ rotulo: "Privacidade", to: { pathname: "/faq", hash: "#privacidade" } },
			{ rotulo: "Código-fonte", href: REPO_URL },
			{ rotulo: "Relatar um problema", href: `${REPO_URL}/issues` },
		],
	},
];

const CLASSE_LINK =
	"inline-flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors";

export function Footer() {
	return (
		<footer className="w-full border-t bg-background/95 backdrop-blur-sm">
			<div className="container flex flex-col gap-8 px-4 py-10 md:px-6 lg:py-16">
				<div className="grid gap-8 sm:grid-cols-2 md:grid-cols-4">
					<div className="space-y-4">
						<div className="flex items-center gap-2 font-bold">
							<img src={logoEspeculai} alt="Especulai" className="h-8 w-auto" />
							<span>Especulai</span>
						</div>
						<p className="text-sm text-muted-foreground">
							Faixas de preço de venda e aluguel para imóveis em Teresina (PI),
							estimadas por machine learning a partir de anúncios.
						</p>
					</div>

					{COLUNAS.map((coluna) => (
						<div key={coluna.titulo} className="space-y-4">
							<h4 className="text-sm font-bold">{coluna.titulo}</h4>
							<ul className="space-y-2 text-sm">
								{coluna.links.map((link) => (
									<li key={link.rotulo}>
										{link.to ? (
											<Link to={link.to} className={CLASSE_LINK}>
												{link.rotulo}
											</Link>
										) : (
											<a
												href={link.href}
												target="_blank"
												rel="noreferrer"
												className={CLASSE_LINK}
											>
												{link.rotulo}
												<ArrowUpRight className="size-3" />
											</a>
										)}
									</li>
								))}
							</ul>
						</div>
					))}
				</div>

				<div className="flex flex-col gap-4 sm:flex-row justify-between items-center border-t border-border/40 pt-8">
					<p className="text-xs text-muted-foreground">
						&copy; {new Date().getFullYear()} Especulai. Estimativa de preço
						pedido, não avaliação imobiliária.
					</p>
					<Link
						to={{ pathname: "/como-funciona", hash: "#limitacoes" }}
						className="text-xs text-muted-foreground hover:text-foreground transition-colors"
					>
						Limitações do modelo
					</Link>
				</div>
			</div>
		</footer>
	);
}
