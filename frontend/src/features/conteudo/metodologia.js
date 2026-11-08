import { decimal, numero, pct } from "./formato";
import { ALUGUEL, MODELO, NEGOCIOS, VENDA } from "./modelo";

// Números que mudam com o modelo vêm de `modelo.js` (gerado no export). Os que ficam escritos
// aqui descrevem experimentos e regras fixas (docs/relatorio-coleta.md), não o modelo publicado.

export const REPO_URL = "https://github.com/gutoportelaa/especulai";
export const RELATORIO_URL = `${REPO_URL}/blob/main/docs/relatorio-coleta.md`;

export const COLETA = {
	periodo: "24 e 25 de outubro de 2026",
	fontes: "VivaReal e Chaves na Mão",
};

// Meia-largura do terço em que cai o preço pedido mediano de cada mercado.
export const EXEMPLOS_FAIXA = NEGOCIOS.map(({ id, rotulo, sufixo }) => ({
	id,
	rotulo,
	sufixo,
	...MODELO[id].exemplo_faixa,
}));

export const ETAPAS = [
	{
		id: "coleta",
		titulo: "Coleta de anúncios",
		resumo: `Anúncios residenciais de Teresina no ${COLETA.fontes}, coletados em ${COLETA.periodo}.`,
		detalhe:
			"A OLX bloqueou o acesso automatizado e não foi forçada. ZAP Imóveis tem o mesmo estoque do VivaReal, então ficou de fora. Os coletores esperam entre páginas e respeitam o Retry-After dos portais.",
		numeros: [
			{ valor: numero(VENDA.imoveis), rotulo: "imóveis de venda" },
			{ valor: numero(ALUGUEL.imoveis), rotulo: "imóveis de aluguel" },
		],
	},
	{
		id: "limpeza",
		titulo: "Limpeza e agrupamento",
		resumo:
			"Só imóveis residenciais com área, bairro e preço plausível. Anúncios do mesmo imóvel, inclusive repetidos nos dois portais, formam um grupo.",
		detalhe:
			"A separação entre treino, validação e teste (70/15/15) é feita por grupo. Assim o modelo nunca é avaliado num imóvel que já viu no treino, que era o que inflava os números da primeira versão do projeto.",
		numeros: [
			{ valor: "70/15/15", rotulo: "treino, validação, teste" },
			{ valor: "R$ 300–25 mil", rotulo: "faixa aceita no aluguel" },
		],
	},
	{
		id: "bairro",
		titulo: "O bairro, com o Censo",
		resumo:
			"Cada bairro recebe a renda média do responsável pelo domicílio e a densidade de moradores, do Censo 2022 do IBGE.",
		detalhe: `Teresina tem 123 bairros oficiais, e ${pct(VENDA.ligadosIbge, { casas: 0 })} dos anúncios casam com um deles. A renda ajuda mais onde há poucos anúncios: ali o modelo não tem como aprender o bairro só pelos preços.`,
		numeros: [
			{
				valor: pct(VENDA.ligadosIbge, { casas: 0 }),
				rotulo: "anúncios ligados ao IBGE",
			},
			{ valor: "0,47", rotulo: "correlação renda × R$/m² (venda)" },
		],
	},
	{
		id: "modelos",
		titulo: "Dois modelos, venda e aluguel",
		resumo:
			"Um imóvel à venda custa centenas de milhares de reais; um aluguel, alguns milhares por mês. Num modelo só, o aluguel viraria ruído.",
		detalhe:
			"Cada modelo é um gradient boosting de 200 árvores treinado sobre o logaritmo do preço, para que errar 10% num aluguel pese o mesmo que errar 10% numa venda. Entram área, quartos, banheiros, vagas, tipo, bairro e os dados do Censo.",
		numeros: [
			{ valor: "200", rotulo: "árvores por modelo" },
			{ valor: "6", rotulo: "campos do formulário" },
		],
	},
	{
		id: "faixa",
		titulo: "Valor e margem de 80%",
		resumo:
			"Além do valor estimado, a resposta traz a margem que contém o preço pedido em 80% dos casos.",
		detalhe:
			"A largura vem dos erros do próprio modelo em anúncios que ele não viu, separada por terço de preço previsto. Com uma largura única, a faixa acertava 80% no total, mas só 75% nos imóveis caros.",
		numeros: [
			{ valor: "3", rotulo: "larguras, por terço de preço" },
			{ valor: "75% → 79%", rotulo: "acerto no terço caro (validação)" },
		],
	},
	{
		id: "teste",
		titulo: "Teste aberto uma única vez",
		resumo:
			"Os anúncios de teste ficaram guardados até o fim e foram usados uma vez, depois de todas as escolhas feitas.",
		detalhe:
			"Nada foi ajustado depois de ver o resultado. Por isso os números abaixo são uma estimativa honesta de como o modelo se sai com um imóvel novo.",
		numeros: [
			{ valor: numero(VENDA.nTeste), rotulo: "anúncios de venda no teste" },
			{ valor: numero(ALUGUEL.nTeste), rotulo: "anúncios de aluguel no teste" },
		],
	},
];

export const RESULTADOS = NEGOCIOS.map(({ id, rotulo }) => {
	const r = id === "venda" ? VENDA : ALUGUEL;
	return {
		id,
		titulo: rotulo,
		n: r.nTeste,
		metricas: [
			{ rotulo: "Erro mediano", valor: pct(r.erroMediano) },
			{ rotulo: "Estimativa a ±20% do pedido", valor: pct(r.dentro20) },
			{ rotulo: "Faixa: superior ÷ inferior", valor: `${decimal(r.razao)}×` },
			{ rotulo: "R² em log", valor: decimal(r.r2Log, 3) },
		],
		cobertura: r.cobertura,
		porTerco: r.porTerco,
	};
});

export const TERCOS = ["Mais baratos", "Do meio", "Mais caros"];

// Espelha confianca() em deploy/worker/src/inferencia.js.
export const NIVEIS_CONFIANCA = [
	{
		nivel: "alta",
		titulo: "Alta",
		regra:
			"O bairro tem pelo menos 15 anúncios no treino, o tipo é conhecido e a área está entre 15 e 1.000 m².",
	},
	{
		nivel: "média",
		titulo: "Média",
		regra:
			"O bairro é conhecido, mas tem menos de 15 anúncios, ou o tipo não aparece no treino, ou a área foge de 15 a 1.000 m².",
	},
	{
		nivel: "baixa",
		titulo: "Baixa",
		regra:
			"O bairro não aparece nos anúncios de treino. O modelo se apoia só na renda e na densidade do Censo e nos atributos do imóvel.",
	},
];

export const HIPOTESES = [
	{
		hipotese: "Renda e densidade do bairro (IBGE)",
		veredito: "ajudou",
		detalhe: "Ganho consistente, maior nos bairros com poucos anúncios.",
	},
	{
		hipotese: "Coordenadas de rua além do bairro",
		veredito: "sem ganho",
		detalhe:
			"O ganho mudava de sinal com 35 anúncios a mais. O bairro já carrega a localização.",
	},
	{
		hipotese: "Tirar anúncios atípicos do treino",
		veredito: "piorou",
		detalhe:
			"Na venda, os atípicos eram em boa parte casas caras legítimas. Eles são só sinalizados.",
	},
	{
		hipotese: "Campo “mobiliado” no aluguel",
		veredito: "fora",
		detalhe: "Ganho pequeno e só um dos portais informa. Ficou fora do modelo.",
	},
	{
		hipotese: "Valor do condomínio",
		veredito: "sem ganho",
		detalhe:
			"Não mostrou ganho claro e só metade dos anúncios do VivaReal o informa.",
	},
];

export const LIMITACOES = [
	"O alvo é o preço pedido no anúncio, não o de fechamento, que costuma ser menor.",
	"Um único momento de coleta (outubro de 2026), sem sazonalidade. O aluguel em Teresina subiu cerca de 22% em 2025 (FipeZap).",
	"Só Teresina e só imóveis residenciais: nada de salas, lojas ou terrenos.",
	`O aluguel tem ${numero(ALUGUEL.imoveis)} imóveis contra ${numero(VENDA.imoveis)} da venda e erra mais; o teste de aluguel, com ${numero(ALUGUEL.nTeste)} anúncios, tem incerteza grande.`,
	"Estado de conservação, andar, vista, lazer e mobília não são conhecidos pelo modelo.",
];

export const PROTECOES = [
	{
		titulo: "Nada pessoal",
		texto:
			"O formulário pede só características do imóvel. Nome, endereço exato e contato nunca são pedidos, e a API não grava as entradas.",
	},
	{
		titulo: "Modelo no servidor",
		texto:
			"O cálculo acontece numa API própria. O navegador recebe só o valor e a margem, arredondados, e nunca o modelo.",
	},
	{
		titulo: "Pesos cifrados",
		texto:
			"Os modelos ficam cifrados com AES-256-GCM. A chave é um segredo do servidor, fora do código.",
	},
	{
		titulo: "Limite de consultas",
		texto:
			"20 por minuto e 200 por hora por conexão. Isso mantém o serviço gratuito no ar e dificulta copiar o modelo por consultas em massa.",
	},
];
