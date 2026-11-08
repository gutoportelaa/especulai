import { Database, Gauge, HandCoins, ShieldCheck, Target } from "lucide-react";
import { decimal, numero, pct } from "./formato";
import { ALUGUEL, VENDA } from "./modelo";

// `destaque` escolhe as perguntas que aparecem também na Home.
export const FAQ_CATEGORIAS = [
	{
		id: "estimativa",
		titulo: "A estimativa",
		icone: Target,
		perguntas: [
			{
				pergunta: "O que o Especulai estima?",
				resposta:
					"O preço pedido em anúncios de imóveis residenciais em Teresina, para venda ou aluguel. A resposta é um valor estimado, com a margem de erro ao lado e um nível de confiança.",
				destaque: true,
			},
			{
				pergunta: "Por que o valor vem com uma margem?",
				resposta: `Porque o valor é uma especulação, e é honesto dizer o quanto ela erra. Em anúncios que o modelo nunca viu, ${pct(VENDA.dentro20, { casas: 0 })} dos valores estimados de venda e ${pct(ALUGUEL.dentro20, { casas: 0 })} dos de aluguel ficaram a até 20% do preço pedido. A margem mostrada contém o preço pedido em cerca de 80% dos casos.`,
				destaque: true,
			},
			{
				pergunta: "O que quer dizer “80% de chance”?",
				resposta: `Que, em 100 imóveis parecidos com o seu, o preço anunciado de cerca de 80 cairia dentro da margem e o de 20 ficaria fora, acima ou abaixo. Medimos isso no conjunto de teste: ${pct(VENDA.cobertura)} na venda e ${pct(ALUGUEL.cobertura)} no aluguel.`,
			},
			{
				pergunta: "Por que preço pedido, e não o preço de venda?",
				resposta:
					"Os anúncios são a única fonte pública de preços de imóveis em Teresina. O preço de fechamento costuma ser menor e não é publicado. Um pedido de acesso à informação sobre os dados de ITBI da Prefeitura está em andamento; se for atendido, o modelo poderá ser comparado com transações reais.",
			},
			{
				pergunta: "Posso usar a estimativa para vender ou alugar meu imóvel?",
				resposta:
					"Como referência inicial, sim; como avaliação, não. A estimativa não conhece estado de conservação, andar, vista ou lazer do condomínio. Antes de decidir, consulte um corretor ou um avaliador.",
				destaque: true,
			},
		],
	},
	{
		id: "precisao",
		titulo: "Precisão e confiança",
		icone: Gauge,
		perguntas: [
			{
				pergunta: "Quão precisa é a estimativa?",
				resposta: `Na venda, o erro mediano da estimativa central é de ${pct(VENDA.erroMediano, { casas: 0 })}; no aluguel, de ${pct(ALUGUEL.erroMediano, { casas: 0 })}. A faixa é larga: o limite superior é, em média, ${decimal(VENDA.razao, 1)} vezes o inferior na venda e ${decimal(ALUGUEL.razao, 1)} vezes no aluguel. Os números vêm de anúncios separados no início e usados uma única vez, no fim.`,
				destaque: true,
			},
			{
				pergunta: "O que significa o nível de confiança?",
				resposta:
					"Diz o quanto o modelo conhece imóveis como o seu. Alta: o bairro tem pelo menos 15 anúncios no treino, o tipo é conhecido e a área está entre 15 e 1.000 m². Média: falta uma dessas condições. Baixa: o bairro não aparece nos anúncios, e o modelo depende só dos dados do Censo.",
			},
			{
				pergunta: "Por que o aluguel é menos preciso que a venda?",
				resposta: `Há menos anúncios de aluguel (${numero(ALUGUEL.imoveis)} imóveis contra ${numero(VENDA.imoveis)} de venda), e o preço do aluguel depende de coisas que os anúncios nem sempre informam, como mobília e condomínio incluso.`,
			},
			{
				pergunta:
					"Meu imóvel é muito caro, ou muito barato. A estimativa vale?",
				resposta:
					"Vale com mais cautela. Nos extremos, a estimativa central tende a puxar para o meio do mercado. A largura da faixa é calibrada separadamente para imóveis baratos, médios e caros, justamente para compensar isso.",
			},
		],
	},
	{
		id: "dados",
		titulo: "Os dados",
		icone: Database,
		perguntas: [
			{
				pergunta: "De onde vêm os dados?",
				resposta:
					"De anúncios do VivaReal e do Chaves na Mão, coletados em 24 e 25 de outubro de 2026, e do Censo 2022 do IBGE, que dá a renda e a densidade de cada bairro. Anúncios repetidos do mesmo imóvel contam como um só.",
			},
			{
				pergunta: "Por que a OLX não está entre as fontes?",
				resposta:
					"A OLX bloqueia acesso automatizado. A coleta parou ali, sem tentar contornar o bloqueio. Outros portais também bloqueiam ou repetem o estoque do VivaReal.",
			},
			{
				pergunta: "Os dados são atualizados?",
				resposta:
					"Ainda não. O modelo reflete o mercado de outubro de 2026. Preços mudam: o aluguel em Teresina subiu cerca de 22% em 2025, segundo o FipeZap. Consultas feitas muito depois dessa data tendem a ficar abaixo do mercado.",
			},
			{
				pergunta: "Quais bairros e tipos de imóvel são cobertos?",
				resposta:
					"Os bairros que aparecem no formulário, todos de Teresina. Tipos: apartamento, casa, casa de condomínio, sobrado, cobertura, kitnet e flat. Imóveis comerciais e terrenos não são cobertos.",
			},
			{
				pergunta: "O endereço exato não melhoraria a estimativa?",
				resposta:
					"Testamos. Com coordenadas de rua, o ganho foi pequeno e mudava de sinal com algumas dezenas de anúncios a mais. Com esta amostra, o bairro já carrega quase toda a informação de localização.",
			},
			{
				pergunta: "Por que vagas de garagem é opcional?",
				resposta:
					"Porque um dos portais não informa vagas. O modelo aprendeu a lidar com a ausência: deixar em branco é melhor do que chutar um número.",
			},
		],
	},
	{
		id: "privacidade",
		titulo: "Privacidade e segurança",
		icone: ShieldCheck,
		perguntas: [
			{
				pergunta: "Meus dados são seguros?",
				resposta:
					"Pedimos apenas características do imóvel, nunca nome, endereço exato ou contato. A API calcula o valor e não grava o que você digitou.",
				destaque: true,
			},
			{
				pergunta: "Os anúncios coletados são publicados?",
				resposta:
					"Não. Os anúncios brutos têm nome de anunciante e endereço, e ficam num repositório privado. O que é público é o código, a metodologia e as métricas.",
			},
			{
				pergunta: "Por que existe limite de consultas?",
				resposta:
					"São 20 consultas por minuto e 200 por hora por conexão. O limite mantém o serviço gratuito no ar e torna caro copiar o modelo por meio de milhares de consultas.",
			},
		],
	},
	{
		id: "uso",
		titulo: "Uso e custo",
		icone: HandCoins,
		perguntas: [
			{
				pergunta: "A estimativa é gratuita?",
				resposta:
					"Sim. Não há cadastro nem cobrança; o único limite é o de consultas por hora.",
			},
			{
				pergunta: "Funciona fora de Teresina?",
				resposta:
					"Não. O modelo só conhece os bairros de Teresina, e preços de outras cidades seguem outra lógica.",
			},
			{
				pergunta: "Posso conferir como o modelo foi feito?",
				resposta:
					"Sim. O código é aberto, e o relatório da coleta e dos experimentos, com o que foi testado e descartado, está no repositório do projeto.",
				link: "repositorio",
			},
		],
	},
];

export const FAQ_DESTAQUES = FAQ_CATEGORIAS.flatMap((c) => c.perguntas).filter(
	(p) => p.destaque,
);
