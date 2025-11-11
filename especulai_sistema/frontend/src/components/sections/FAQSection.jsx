import { motion } from 'framer-motion'
import { Badge } from '../ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion'

export function FAQSection() {
  const faqs = [
    {
      question: "Como funciona a predição de preços?",
      answer:
        "Nossa plataforma utiliza inteligência artificial e machine learning para analisar as características do imóvel (área, quartos, banheiros, tipo, localização) e compará-las com dados reais do mercado imobiliário, gerando uma estimativa precisa do valor.",
    },
    {
      question: "A predição é gratuita?",
      answer:
        "Sim, nossa plataforma é completamente gratuita. Você pode fazer quantas predições quiser sem custo algum.",
    },
    {
      question: "Quão precisa é a estimativa?",
      answer:
        "Nossa IA foi treinada com dados reais do mercado imobiliário e oferece um nível de confiança para cada predição. A precisão varia conforme a disponibilidade de dados similares na região analisada.",
    },
    {
      question: "Quais informações são necessárias?",
      answer:
        "Para fazer uma predição, você precisa informar: área do imóvel (m²), número de quartos, número de banheiros, tipo do imóvel (casa, apartamento, etc.), bairro e cidade.",
    },
    {
      question: "Meus dados são seguros?",
      answer:
        "Sim, levamos a segurança dos seus dados muito a sério. Todas as informações são processadas de forma segura e não são compartilhadas com terceiros.",
    },
    {
      question: "Posso usar a predição para vender meu imóvel?",
      answer:
        "A predição é uma estimativa baseada em dados do mercado e pode ser útil como referência. No entanto, recomendamos sempre consultar um profissional do mercado imobiliário para uma avaliação completa antes de tomar decisões importantes.",
    },
  ]

  return (
    <section id="faq" className="w-full py-20 md:py-32">
      <div className="container px-4 md:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center justify-center space-y-4 text-center mb-12"
        >
          <Badge className="rounded-full px-4 py-1.5 text-sm font-medium" variant="secondary">
            FAQ
          </Badge>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Perguntas Frequentes
          </h2>
          <p className="max-w-[800px] text-muted-foreground md:text-lg">
            Encontre respostas para as dúvidas mais comuns sobre nossa plataforma.
          </p>
        </motion.div>

        <div className="mx-auto max-w-3xl">
          <Accordion type="single" collapsible className="w-full">
            {faqs.map((faq, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
              >
                <AccordionItem value={`item-${i}`} className="border-b border-border/40 py-2">
                  <AccordionTrigger className="text-left font-medium hover:no-underline" value={`item-${i}`}>
                    {faq.question}
                  </AccordionTrigger>
                  <AccordionContent className="text-muted-foreground" value={`item-${i}`}>
                    {faq.answer}
                  </AccordionContent>
                </AccordionItem>
              </motion.div>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  )
}

