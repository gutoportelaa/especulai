import { Header } from '../components/layout/Header'
import { Footer } from '../components/layout/Footer'
import { usePrediction } from '../hooks/usePrediction'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { motion } from 'framer-motion'
import { TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react'

export function Predict() {
  const {
    formData,
    prediction,
    loading,
    error,
    handleChange,
    handleSubmit,
    reset
  } = usePrediction()

  return (
    <div className="flex min-h-[100dvh] flex-col">
      <Header />
      <main className="flex-1 py-12 md:py-20">
        <div className="container px-4 md:px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-3xl mx-auto"
          >
            <div className="text-center mb-8">
              <Badge className="mb-4 rounded-full px-4 py-1.5 text-sm font-medium" variant="secondary">
                Predição de Preços
              </Badge>
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
                Estime o Valor do Seu Imóvel
              </h1>
              <p className="text-muted-foreground md:text-lg">
                Preencha os dados abaixo para obter uma estimativa precisa do valor do imóvel
              </p>
            </div>

            <Card className="mb-8">
              <CardHeader>
                <CardTitle>Informações do Imóvel</CardTitle>
                <CardDescription>
                  Preencha todos os campos para obter a melhor estimativa
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <label htmlFor="area" className="text-sm font-medium">
                        Área (m²) *
                      </label>
                      <input
                        id="area"
                        name="area"
                        type="number"
                        step="0.01"
                        value={formData.area}
                        onChange={handleChange}
                        placeholder="Ex: 100.50"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <label htmlFor="quartos" className="text-sm font-medium">
                        Quartos *
                      </label>
                      <input
                        id="quartos"
                        name="quartos"
                        type="number"
                        min="0"
                        value={formData.quartos}
                        onChange={handleChange}
                        placeholder="Ex: 3"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <label htmlFor="banheiros" className="text-sm font-medium">
                        Banheiros *
                      </label>
                      <input
                        id="banheiros"
                        name="banheiros"
                        type="number"
                        min="0"
                        value={formData.banheiros}
                        onChange={handleChange}
                        placeholder="Ex: 2"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <label htmlFor="tipo" className="text-sm font-medium">
                        Tipo *
                      </label>
                      <input
                        id="tipo"
                        name="tipo"
                        type="text"
                        value={formData.tipo}
                        onChange={handleChange}
                        placeholder="Ex: Casa, Apartamento"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <label htmlFor="bairro" className="text-sm font-medium">
                        Bairro *
                      </label>
                      <input
                        id="bairro"
                        name="bairro"
                        type="text"
                        value={formData.bairro}
                        onChange={handleChange}
                        placeholder="Ex: Centro"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <label htmlFor="cidade" className="text-sm font-medium">
                        Cidade *
                      </label>
                      <input
                        id="cidade"
                        name="cidade"
                        type="text"
                        value={formData.cidade}
                        onChange={handleChange}
                        placeholder="Ex: São Paulo"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        required
                      />
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <Button
                      type="submit"
                      disabled={loading}
                      className="flex-1 rounded-full"
                      size="lg"
                    >
                      {loading ? 'Processando...' : 'Calcular Preço'}
                    </Button>
                    {prediction && (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={reset}
                        className="rounded-full"
                        size="lg"
                      >
                        Limpar
                      </Button>
                    )}
                  </div>
                </form>
              </CardContent>
            </Card>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-8"
              >
                <Card className="border-destructive">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-3 text-destructive">
                      <AlertCircle className="size-5" />
                      <div>
                        <p className="font-medium">Erro ao processar predição</p>
                        <p className="text-sm text-muted-foreground">{error}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {prediction && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-8"
              >
                <Card className="border-primary/50 bg-gradient-to-br from-primary/5 to-primary/10">
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-4">
                      <div className="rounded-full bg-primary/10 p-3">
                        <TrendingUp className="size-6 text-primary" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <CheckCircle2 className="size-5 text-primary" />
                          <h3 className="text-xl font-bold">Predição Concluída</h3>
                        </div>
                        <div className="space-y-2">
                          <div>
                            <p className="text-sm text-muted-foreground">Preço Estimado</p>
                            <p className="text-3xl font-bold text-primary">
                              R$ {prediction.preco_estimado?.toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                              })}
                            </p>
                          </div>
                          {prediction.confianca && (
                            <div>
                              <p className="text-sm text-muted-foreground">Nível de Confiança</p>
                              <Badge variant="secondary" className="mt-1">
                                {prediction.confianca}
                              </Badge>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  )
}

