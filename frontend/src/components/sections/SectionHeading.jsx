import { motion } from "framer-motion";
import { Badge } from "../ui/badge";

export function SectionHeading({ badge, titulo, children, as: Titulo = "h2" }) {
	return (
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			whileInView={{ opacity: 1, y: 0 }}
			viewport={{ once: true }}
			transition={{ duration: 0.5 }}
			className="flex flex-col items-center justify-center space-y-4 text-center mb-12"
		>
			{badge && (
				<Badge
					className="rounded-full px-4 py-1.5 text-sm font-medium"
					variant="secondary"
				>
					{badge}
				</Badge>
			)}
			<Titulo className="text-3xl md:text-4xl font-bold tracking-tight">
				{titulo}
			</Titulo>
			{children && (
				<p className="max-w-[800px] text-muted-foreground md:text-lg">
					{children}
				</p>
			)}
		</motion.div>
	);
}
