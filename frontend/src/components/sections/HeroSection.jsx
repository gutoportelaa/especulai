import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Check } from 'lucide-react'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'

export function HeroSection() {
  return (
    <section className="w-full py-20 md:py-32 lg:py-40 overflow-hidden">
      <div className="container px-4 md:px-6 relative">
        <div className="absolute inset-0 -z-10 h-full w-full bg-white bg-[linear-gradient(to_right,#f0f0f0_1px,transparent_1px),linear-gradient(to_bottom,#f0f0f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_110%)]"></div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center max-w-3xl mx-auto mb-12"
        >
          <Badge className="mb-4 rounded-full px-4 py-1.5 text-sm font-medium" variant="secondary">
            Predição Inteligente de Preços
          </Badge>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
            Descubra o Valor Real do Seu Imóvel
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Utilize inteligência artificial para obter estimativas precisas de preços imobiliários. 
            Análise rápida, confiável e baseada em dados reais do mercado.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/predict">
              <Button size="lg" className="rounded-full h-12 px-8 text-base">
                Fazer Predição Agora
                <ArrowRight className="ml-2 size-4" />
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="rounded-full h-12 px-8 text-base">
              Saiba Mais
            </Button>
          </div>
          <div className="flex items-center justify-center gap-4 mt-6 text-sm text-muted-foreground flex-wrap">
            <div className="flex items-center gap-1">
              <Check className="size-4 text-primary" />
              <span>Brasileiro</span>
            </div>
            <div className="flex items-center gap-1">
              <Check className="size-4 text-primary" />
              <span>Resultados instantâneos</span>
            </div>
            <div className="flex items-center gap-1">
              <Check className="size-4 text-primary" />
              <span>Baseado em dados reais</span>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="relative mx-auto max-w-5xl"
        >
          <div className="rounded-xl overflow-hidden shadow-2xl border border-border/40 bg-gradient-to-b from-background to-muted/20">
            <div className="aspect-video bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
              <div className="text-center p-8">
                <h3 className="text-2xl font-bold mb-4">Interface Intuitiva</h3>
                <p className="text-muted-foreground">
                  Preencha os dados do imóvel e receba uma estimativa precisa em segundos
                </p>
              </div>
            </div>
            <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-black/10"></div>
          </div>
          <div className="absolute -bottom-6 -right-6 -z-10 h-[300px] w-[300px] rounded-full bg-gradient-to-br from-primary/30 to-primary/20 blur-3xl opacity-70"></div>
          <div className="absolute -top-6 -left-6 -z-10 h-[300px] w-[300px] rounded-full bg-gradient-to-br from-primary/20 to-primary/30 blur-3xl opacity-70"></div>
        </motion.div>
      </div>
    </section>
  )
}

