import { Footer } from "../components/layout/Footer";
import { Header } from "../components/layout/Header";
import { CTASection } from "../components/sections/CTASection";
import { FAQSection } from "../components/sections/FAQSection";
import { FeaturesSection } from "../components/sections/FeaturesSection";
import { HeroSection } from "../components/sections/HeroSection";
import { HowItWorksSection } from "../components/sections/HowItWorksSection";

export function Home() {
	return (
		<div className="flex min-h-[100dvh] flex-col">
			<Header />
			<main className="flex-1">
				<HeroSection />
				<FeaturesSection />
				<HowItWorksSection />
				<CTASection />
				<FAQSection />
			</main>
			<Footer />
		</div>
	);
}
