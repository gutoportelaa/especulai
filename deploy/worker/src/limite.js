// Limite de consultas por IP (minuto e hora) e global (hora), em janelas fixas. Contra extração
// do modelo por consulta repetida: não impede, encarece. `decidir` é puro; o Durable Object
// (Limitador, em index.js) só fornece o armazenamento, que sobrevive a reinícios.

export const PADRAO = { porMinuto: 20, porHora: 200, globalPorHora: 3000 };

const MINUTO = 60_000;
const HORA = 3_600_000;

/**
 * @param {{get(k:string):Promise<number|undefined>, put(k:string,v:number):Promise<void>}} armazem
 * @returns {Promise<{ok:true}|{ok:false, espera:number}>} espera em segundos
 */
export async function decidir(armazem, ip, agora, limites = PADRAO) {
	const m = Math.floor(agora / MINUTO);
	const h = Math.floor(agora / HORA);
	const chaves = { minuto: `m:${ip}:${m}`, hora: `h:${ip}:${h}`, global: `g:${h}` };
	const uso = {
		minuto: (await armazem.get(chaves.minuto)) ?? 0,
		hora: (await armazem.get(chaves.hora)) ?? 0,
		global: (await armazem.get(chaves.global)) ?? 0,
	};
	const segundosAte = (fim) => Math.max(1, Math.ceil((fim - agora) / 1000));

	if (uso.minuto >= limites.porMinuto) return { ok: false, espera: segundosAte((m + 1) * MINUTO) };
	if (uso.hora >= limites.porHora) return { ok: false, espera: segundosAte((h + 1) * HORA) };
	if (uso.global >= limites.globalPorHora) {
		return { ok: false, espera: segundosAte((h + 1) * HORA) };
	}
	await armazem.put(chaves.minuto, uso.minuto + 1);
	await armazem.put(chaves.hora, uso.hora + 1);
	await armazem.put(chaves.global, uso.global + 1);
	return { ok: true };
}
