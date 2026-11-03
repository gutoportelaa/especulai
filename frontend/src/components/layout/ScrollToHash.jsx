import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// O BrowserRouter não rola até a âncora nem volta ao topo ao trocar de página. Links com
// href="/#faq" contornavam isso, mas ignoravam o basename e davam 404 no GitHub Pages.
export function ScrollToHash() {
	const { pathname, hash } = useLocation();

	// biome-ignore lint/correctness/useExhaustiveDependencies: rola de novo a cada troca de página
	useEffect(() => {
		if (!hash) {
			window.scrollTo(0, 0);
			return;
		}
		const id = decodeURIComponent(hash.slice(1));
		const rolar = (el) =>
			el.scrollIntoView({ behavior: "smooth", block: "start" });
		const el = document.getElementById(id);
		if (el) {
			rolar(el);
			return;
		}
		// Seção carregada sob demanda (o mapa): ainda não está na página, espera aparecer.
		const obs = new MutationObserver(() => {
			const alvo = document.getElementById(id);
			if (alvo) {
				obs.disconnect();
				rolar(alvo);
			}
		});
		obs.observe(document.body, { childList: true, subtree: true });
		const limite = setTimeout(() => obs.disconnect(), 5000);
		return () => {
			obs.disconnect();
			clearTimeout(limite);
		};
	}, [pathname, hash]);

	return null;
}
