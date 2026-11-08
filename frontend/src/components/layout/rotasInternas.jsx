import { lazy } from "react";

// Rotas internas (back-office). `import.meta.env.DEV` é substituído por `false` no build de
// produção, e o Rollup elimina o ramo morto: o import dinâmico some e o pedaço da página nem é
// gerado. Esconder o link não bastaria, porque tudo que vai para um site estático é público.
const AdminDados = import.meta.env.DEV
	? lazy(() =>
			import("../../pages/admin/AdminDados").then((m) => ({
				default: m.AdminDados,
			})),
		)
	: null;

export const ROTAS_INTERNAS = AdminDados
	? [{ path: "/admin/dados", Pagina: AdminDados }]
	: [];
