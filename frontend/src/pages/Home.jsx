import { Suspense, lazy } from "react";
import { Footer } from "../components/layout/Footer";
import { Header } from "../components/layout/Header";
import { CTASection } from "../components/sections/CTASection";
import { FAQSection } from "../components/sections/FAQSection";
import { FeaturesSection } from "../components/sections/FeaturesSection";
import { HeroSection } from "../components/sections/HeroSection";
import { HowItWorksSection } from "../components/sections/HowItWorksSection";

// O mapa traz os polígonos dos bairros (~100 KB): fica num pedaço à parte do bundle.
const MapaSection = lazy(() =>
	import("../components/sections/MapaSection").then((m) => ({
		default: m.MapaSection,
	})),
);

export function Home() {
	return (
		<div className="flex min-h-[100dvh] flex-col">
			<Header />
			<main className="flex-1">
				<HeroSection />
				<FeaturesSection />
				<Suspense fallback={<div className="min-h-[900px]" />}>
					<MapaSection />
				</Suspense>
				<HowItWorksSection />
				<CTASection />
				<FAQSection />
			</main>
			<Footer />
		</div>
	);
}
