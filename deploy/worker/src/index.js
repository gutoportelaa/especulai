// Entrada do Worker: liga os segredos e o armazenamento do Cloudflare ao handler.
// Os pesos chegam cifrados no bundle (modelos/*.enc); só a chave MODEL_KEY, um segredo do
// Worker que não está no código, os abre, e apenas na memória do isolate.

import { DurableObject } from "cloudflare:workers";
import aluguelEnc from "../modelos/aluguel.enc";
import vendaEnc from "../modelos/venda.enc";
import { criarHandler } from "./handler";
import { decifrar } from "./inferencia";
import { decidir, PADRAO } from "./limite";

const CIFRADOS = { venda: vendaEnc, aluguel: aluguelEnc };
const abertos = {};

const numero = (valor, padrao) => (Number.isFinite(Number(valor)) && valor ? Number(valor) : padrao);

export class Limitador extends DurableObject {
	async liberar(ip, limites) {
		if (!(await this.ctx.storage.getAlarm())) {
			await this.ctx.storage.setAlarm(Date.now() + 2 * 3_600_000);
		}
		return decidir(this.ctx.storage, ip, Date.now(), limites);
	}

	// Janelas fixas velhas não servem mais: zera o armazenamento a cada 2 h.
	async alarm() {
		await this.ctx.storage.deleteAll();
	}
}

export default {
	async fetch(req, env) {
		const limites = {
			porMinuto: numero(env.LIMITE_POR_MINUTO, PADRAO.porMinuto),
			porHora: numero(env.LIMITE_POR_HORA, PADRAO.porHora),
			globalPorHora: numero(env.LIMITE_GLOBAL_POR_HORA, PADRAO.globalPorHora),
		};
		const handler = criarHandler({
			abrirModelo: (negocio) => {
				abertos[negocio] ??= decifrar(CIFRADOS[negocio], env.MODEL_KEY).catch((erro) => {
					delete abertos[negocio];
					throw erro;
				});
				return abertos[negocio];
			},
			liberar: (ip) => env.LIMITADOR.get(env.LIMITADOR.idFromName("global")).liberar(ip, limites),
			origens: (env.ALLOWED_ORIGINS ?? "").split(",").map((o) => o.trim()).filter(Boolean),
		});
		return handler(req);
	},
};
