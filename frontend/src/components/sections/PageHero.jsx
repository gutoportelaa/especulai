import { motion } from "framer-motion";
import { Badge } from "../ui/badge";

export function PageHero({ badge, titulo, children }) {
	return (
		<section className="w-full pt-16 pb-12 md:pt-24 md:pb-16 relative overflow-hidden">
			<div className="absolute inset-0 -z-10 h-full w-full bg-white bg-[linear-gradient(to_right,#f0f0f0_1px,transparent_1px),linear-gradient(to_bottom,#f0f0f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_0%,#000_70%,transparent_110%)]" />
			<div className="absolute -top-24 left-1/2 -z-10 h-[280px] w-[280px] -translate-x-1/2 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 blur-3xl" />

			<div className="container px-4 md:px-6">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="text-center max-w-3xl mx-auto"
				>
					<Badge
						className="mb-4 rounded-full px-4 py-1.5 text-sm font-medium"
						variant="secondary"
					>
						{badge}
					</Badge>
					<h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
						{titulo}
					</h1>
					<p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
						{children}
					</p>
				</motion.div>
			</div>
		</section>
	);
}
