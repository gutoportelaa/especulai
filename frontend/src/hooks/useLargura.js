import { useEffect, useRef, useState } from "react";

/** Largura do elemento em px, atualizada ao redimensionar; os gráficos desenham nela. */
export function useLargura(inicial = 600) {
	const ref = useRef(null);
	const [largura, setLargura] = useState(inicial);

	useEffect(() => {
		const el = ref.current;
		if (!el) return;
		setLargura(el.clientWidth || inicial);
		const obs = new ResizeObserver(([entrada]) => {
			setLargura(Math.round(entrada.contentRect.width));
		});
		obs.observe(el);
		return () => obs.disconnect();
	}, [inicial]);

	return [ref, largura];
}
