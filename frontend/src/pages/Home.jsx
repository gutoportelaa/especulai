import { Header } from '../components/layout/Header'
import { Footer } from '../components/layout/Footer'
import { HeroSection } from '../components/sections/HeroSection'
import { FeaturesSection } from '../components/sections/FeaturesSection'
import { HowItWorksSection } from '../components/sections/HowItWorksSection'
import { CTASection } from '../components/sections/CTASection'
import { FAQSection } from '../components/sections/FAQSection'

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
  )
}

