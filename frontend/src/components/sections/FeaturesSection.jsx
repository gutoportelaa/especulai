import { motion } from 'framer-motion'
import { Zap, BarChart, Shield, TrendingUp, Clock, Target } from 'lucide-react'
import { Badge } from '../ui/badge'
import { Card, CardContent } from '../ui/card'

export function FeaturesSection() {
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  }

  const features = [
    {
      title: "Análise Rápida",
      description: "Obtenha estimativas de preços em segundos com nossa tecnologia avançada de IA.",
      icon: <Zap className="size-5" />,
    },
    {
      title: "Dados Precisos",
      description: "Baseado em dados reais do mercado imobiliário para maior confiabilidade.",
      icon: <BarChart className="size-5" />,
    },
    {
      title: "Seguro e Confiável",
      description: "Seus dados são protegidos com as melhores práticas de segurança.",
      icon: <Shield className="size-5" />,
    },
    {
      title: "Tendências de Mercado",
      description: "Acompanhe as tendências e variações de preços no mercado imobiliário.",
      icon: <TrendingUp className="size-5" />,
    },
    {
      title: "Resultados Instantâneos",
      description: "Não precisa esperar. Receba sua predição imediatamente após preencher os dados.",
      icon: <Clock className="size-5" />,
    },
    {
      title: "Alta Precisão",
      description: "Algoritmos avançados garantem estimativas com alto nível de precisão.",
      icon: <Target className="size-5" />,
    },
  ]

  return (
    <section id="features" className="w-full py-20 md:py-32">
      <div className="container px-4 md:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center justify-center space-y-4 text-center mb-12"
        >
          <Badge className="rounded-full px-4 py-1.5 text-sm font-medium" variant="secondary">
            Recursos
          </Badge>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Tudo que Você Precisa para Tomar Decisões Inteligentes
          </h2>
          <p className="max-w-[800px] text-muted-foreground md:text-lg">
            Nossa plataforma oferece todas as ferramentas necessárias para você obter 
            estimativas precisas e tomar decisões informadas no mercado imobiliário.
          </p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature, i) => (
            <motion.div key={i} variants={item}>
              <Card className="h-full overflow-hidden border-border/40 bg-gradient-to-b from-background to-muted/10 backdrop-blur transition-all hover:shadow-md">
                <CardContent className="p-6 flex flex-col h-full">
                  <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-4">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-bold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

