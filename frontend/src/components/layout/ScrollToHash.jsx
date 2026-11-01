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
		document
			.getElementById(decodeURIComponent(hash.slice(1)))
			?.scrollIntoView({ behavior: "smooth", block: "start" });
	}, [pathname, hash]);

	return null;
}
