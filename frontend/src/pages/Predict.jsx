import { motion } from "framer-motion";
import { AlertCircle } from "lucide-react";
import { Footer } from "../components/layout/Footer";
import { Header } from "../components/layout/Header";
import { ResultadoPredicao } from "../components/predicao/ResultadoPredicao";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import {
	NEGOCIO_OPTIONS,
	TIPO_OPTIONS,
} from "../features/prediction/constants";
import { usePrediction } from "../hooks/usePrediction";

// Faixas de preço pedido não merecem centavos: arredonda a milhar (venda) ou a dezena (aluguel).
const moeda = (valor) => {
	const passo = valor >= 10000 ? 1000 : 10;
	return `R$ ${(Math.round(valor / passo) * passo).toLocaleString("pt-BR")}`;
};

export function Predict() {
	const {
		formData,
		prediction,
		loading,
		demorando,
		error,
		bairros,
		handleChange,
		handleSubmit,
		reset,
	} = usePrediction();

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
							<Badge
								className="mb-4 rounded-full px-4 py-1.5 text-sm font-medium"
								variant="secondary"
							>
								Predição de Preços
							</Badge>
							<h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
								Estime o Preço de Venda ou Aluguel
							</h1>
							<p className="text-muted-foreground md:text-lg">
								Valor estimado para imóveis em Teresina (PI), com a{" "}
								<strong>margem de erro</strong> ao lado. É o preço{" "}
								<strong>pedido nos anúncios</strong>, não o de fechamento.
							</p>
						</div>

						<Card className="mb-8">
							<CardHeader>
								<CardTitle>Informações do Imóvel</CardTitle>
								<CardDescription>
									Os campos com * são obrigatórios
								</CardDescription>
							</CardHeader>
							<CardContent>
								<form onSubmit={handleSubmit} className="space-y-6">
									<div className="grid gap-4 sm:grid-cols-2">
										<div className="space-y-2">
											<label htmlFor="negocio" className="text-sm font-medium">
												Negócio *
											</label>
											<select
												id="negocio"
												name="negocio"
												value={formData.negocio}
												onChange={handleChange}
												className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
											>
												{NEGOCIO_OPTIONS.map((option) => (
													<option key={option.value} value={option.value}>
														{option.label}
													</option>
												))}
											</select>
										</div>

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
											<label
												htmlFor="banheiros"
												className="text-sm font-medium"
											>
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
											<select
												id="tipo"
												name="tipo"
												value={formData.tipo}
												onChange={handleChange}
												className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
												required
											>
												{TIPO_OPTIONS.map((option) => (
													<option key={option.value} value={option.value}>
														{option.label}
													</option>
												))}
											</select>
										</div>

										<div className="space-y-2">
											<label htmlFor="bairro" className="text-sm font-medium">
												Bairro *
											</label>
											<input
												id="bairro"
												name="bairro"
												type="text"
												list="bairros-conhecidos"
												value={formData.bairro}
												onChange={handleChange}
												placeholder="Ex: Centro"
												className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
												required
											/>
											{/* Bairro fora do treino derruba a confiança para "baixa";
											    a lista evita que o usuário caia nisso por digitação. */}
											<datalist id="bairros-conhecidos">
												{bairros.map((nome) => (
													<option key={nome} value={nome} />
												))}
											</datalist>
										</div>

										<div className="space-y-2">
											<label htmlFor="vagas" className="text-sm font-medium">
												Vagas de garagem
											</label>
											<input
												id="vagas"
												name="vagas"
												type="number"
												min="0"
												value={formData.vagas}
												onChange={handleChange}
												placeholder="Opcional"
												className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
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
											{loading
												? demorando
													? "Acordando o servidor..."
													: "Processando..."
												: "Calcular Preço"}
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
												<p className="font-medium">
													Erro ao processar predição
												</p>
												<p className="text-sm text-muted-foreground">{error}</p>
											</div>
										</div>
									</CardContent>
								</Card>
							</motion.div>
						)}

						{prediction && (
							<ResultadoPredicao prediction={prediction} moeda={moeda} />
						)}
					</motion.div>
				</div>
			</main>
			<Footer />
		</div>
	);
}
