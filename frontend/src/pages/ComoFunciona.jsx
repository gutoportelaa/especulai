import { Footer } from "../components/layout/Footer";
import { Header } from "../components/layout/Header";
import { DiagnosticoModelo } from "../components/metodologia/DiagnosticoModelo";
import { EtapasPipeline } from "../components/metodologia/EtapasPipeline";
import { ExemploFaixa } from "../components/metodologia/ExemploFaixa";
import { HipotesesTestadas } from "../components/metodologia/HipotesesTestadas";
import { Limitacoes } from "../components/metodologia/Limitacoes";
import { NiveisConfianca } from "../components/metodologia/NiveisConfianca";
import { ProtecaoDados } from "../components/metodologia/ProtecaoDados";
import { ResultadosTeste } from "../components/metodologia/ResultadosTeste";
import { CTASection } from "../components/sections/CTASection";
import { PageHero } from "../components/sections/PageHero";
import { SectionHeading } from "../components/sections/SectionHeading";

const GRADE =
	"absolute inset-0 -z-10 h-full w-full bg-white bg-[linear-gradient(to_right,#f0f0f0_1px,transparent_1px),linear-gradient(to_bottom,#f0f0f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,#000_40%,transparent_100%)]";

export function ComoFunciona() {
	return (
		<div className="flex min-h-[100dvh] flex-col">
			<Header />
			<main className="flex-1">
				<PageHero badge="Como Funciona" titulo="Do anúncio à faixa de preço">
					Como o Especulai transforma milhares de anúncios de Teresina numa
					faixa de preço, quanto ela acerta e onde ela não serve.
				</PageHero>

				<section id="resultado" className="w-full pb-20 md:pb-28 scroll-mt-24">
					<div className="container px-4 md:px-6">
						<SectionHeading
							badge="O que você recebe"
							titulo="Uma faixa, não um palpite"
						>
							A estimativa central é o ponto mais provável, mas é a faixa que
							importa: ela contém o preço pedido em cerca de 80% dos casos.
							Exemplos com a largura real do modelo:
						</SectionHeading>
						<ExemploFaixa />
					</div>
				</section>

				<section
					id="etapas"
					className="w-full py-20 md:py-28 bg-muted/30 relative overflow-hidden scroll-mt-24"
				>
					<div className={GRADE} />
					<div className="container px-4 md:px-6 relative">
						<SectionHeading
							badge="Metodologia"
							titulo="Seis etapas, do dado bruto ao teste"
						>
							Cada escolha foi medida em dados de validação antes de entrar no
							modelo.
						</SectionHeading>
						<EtapasPipeline />
					</div>
				</section>

				<section id="resultados" className="w-full py-20 md:py-28 scroll-mt-24">
					<div className="container px-4 md:px-6">
						<SectionHeading badge="Resultados" titulo="Quanto o modelo acerta">
							Medido em anúncios separados no início e usados uma única vez, no
							fim. Menos da metade das estimativas centrais fica a ±20% do preço
							pedido, e é por isso que mostramos a faixa.
						</SectionHeading>
						<ResultadosTeste />
					</div>
				</section>

				<section
					id="diagnostico"
					className="w-full pb-20 md:pb-28 scroll-mt-24"
				>
					<div className="container px-4 md:px-6">
						<SectionHeading badge="Diagnóstico" titulo="Como o modelo erra">
							Onde a estimativa acerta, para que lado ela erra e o que mais pesa
							nela. Os gráficos são gerados a partir do modelo publicado e
							atualizados a cada novo treino.
						</SectionHeading>
						<DiagnosticoModelo />
					</div>
				</section>

				<section
					id="confianca"
					className="w-full py-20 md:py-28 bg-muted/30 scroll-mt-24"
				>
					<div className="container px-4 md:px-6">
						<SectionHeading
							badge="Confiança"
							titulo="O quanto o modelo conhece o seu imóvel"
						>
							Cada estimativa vem com um nível de confiança. Ele não muda a
							faixa: avisa quando ela se apoia em pouca informação.
						</SectionHeading>
						<NiveisConfianca />
					</div>
				</section>

				<section
					id="experimentos"
					className="w-full py-20 md:py-28 scroll-mt-24"
				>
					<div className="container px-4 md:px-6">
						<SectionHeading
							badge="Experimentos"
							titulo="O que testamos, e o que ficou de fora"
						>
							Nem toda ideia boa melhora o modelo. Estas foram medidas e
							decididas pelos números.
						</SectionHeading>
						<HipotesesTestadas />
					</div>
				</section>

				<section
					id="privacidade"
					className="w-full py-20 md:py-28 bg-muted/30 scroll-mt-24"
				>
					<div className="container px-4 md:px-6">
						<SectionHeading
							badge="Privacidade"
							titulo="Seus dados e o modelo, protegidos"
						/>
						<ProtecaoDados />
					</div>
				</section>

				<section id="limitacoes" className="w-full py-20 md:py-28 scroll-mt-24">
					<div className="container px-4 md:px-6">
						<SectionHeading
							badge="Limitações"
							titulo="Onde a estimativa não chega"
						>
							Saber o que o modelo não vê é parte de usá-lo bem.
						</SectionHeading>
						<Limitacoes />
					</div>
				</section>

				<CTASection
					secundario={{ to: "/faq", rotulo: "Perguntas Frequentes" }}
				/>
			</main>
			<Footer />
		</div>
	);
}
