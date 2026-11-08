import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { Link } from "react-router-dom";
import logoEspeculai from "../../assets/solo_logo_Especulai.png";
import { useMobileMenu } from "../../hooks/useMobileMenu";
import { useScroll } from "../../hooks/useScroll";
import { Button } from "../ui/button";

// Link do router, e não <a href="/#...">: o href cru ignora o basename e, no GitHub Pages,
// mandava para a raiz do domínio (404).
const NAV = [
	{ to: { pathname: "/", hash: "#features" }, rotulo: "Recursos" },
	{ to: "/como-funciona", rotulo: "Como Funciona" },
	{ to: "/faq", rotulo: "FAQ" },
];

export function Header() {
	const isScrolled = useScroll();
	const { mobileMenuOpen, toggleMenu, closeMenu } = useMobileMenu();

	return (
		<header
			className={`sticky top-0 z-50 w-full backdrop-blur-lg transition-all duration-300 ${
				isScrolled ? "bg-background/80 shadow-sm" : "bg-transparent"
			}`}
		>
			<div className="container flex h-16 items-center justify-between">
				<Link to="/" className="flex items-center gap-2 font-bold">
					<img src={logoEspeculai} alt="Especulai" className="h-8 w-auto" />
					<span className="text-xl">Especulai</span>
				</Link>

				<nav className="hidden md:flex gap-8">
					{NAV.map((item) => (
						<Link
							key={item.rotulo}
							to={item.to}
							className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
						>
							{item.rotulo}
						</Link>
					))}
				</nav>

				<div className="hidden md:flex gap-4 items-center">
					<Link to="/predict">
						<Button className="rounded-full">Fazer Predição</Button>
					</Link>
				</div>

				<div className="flex items-center gap-4 md:hidden">
					<Button
						variant="ghost"
						size="icon"
						onClick={toggleMenu}
						className="rounded-full"
					>
						{mobileMenuOpen ? (
							<X className="size-5" />
						) : (
							<Menu className="size-5" />
						)}
						<span className="sr-only">Toggle menu</span>
					</Button>
				</div>
			</div>

			{/* Mobile menu */}
			<AnimatePresence>
				{mobileMenuOpen && (
					<motion.div
						initial={{ opacity: 0, y: -20 }}
						animate={{ opacity: 1, y: 0 }}
						exit={{ opacity: 0, y: -20 }}
						className="md:hidden absolute top-16 inset-x-0 bg-background/95 backdrop-blur-lg border-b"
					>
						<div className="container py-4 flex flex-col gap-4">
							{NAV.map((item) => (
								<Link
									key={item.rotulo}
									to={item.to}
									className="py-2 text-sm font-medium"
									onClick={closeMenu}
								>
									{item.rotulo}
								</Link>
							))}
							<div className="flex flex-col gap-2 pt-2 border-t">
								<Link to="/predict" onClick={closeMenu}>
									<Button className="rounded-full w-full">
										Fazer Predição
									</Button>
								</Link>
							</div>
						</div>
					</motion.div>
				)}
			</AnimatePresence>
		</header>
	);
}
