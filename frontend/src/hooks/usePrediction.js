import { useEffect, useState } from "react";
import { PREDICTION_DEFAULTS } from "../features/prediction/constants";
import { listarBairros, predictImovel } from "../features/prediction/model";
import { normalizePredictionPayload } from "../features/prediction/utils";

const createDefaultForm = () => ({ ...PREDICTION_DEFAULTS });

export function usePrediction() {
	const [formData, setFormData] = useState(() => createDefaultForm());
	const [prediction, setPrediction] = useState(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);
	const [demorando, setDemorando] = useState(false);
	const [bairros, setBairros] = useState([]);

	const negocio = formData.negocio;

	// A lista de bairros é estática (só nomes); a estimativa vem do servidor.
	useEffect(() => {
		let ativo = true;
		listarBairros(negocio)
			.then((lista) => {
				if (ativo) setBairros(lista);
			})
			.catch(() => {
				// Silencioso: só vira erro visível se o usuário tentar calcular.
			});
		return () => {
			ativo = false;
		};
	}, [negocio]);

	const handleChange = (e) => {
		const { name, value } = e.target;
		setFormData((prev) => ({ ...prev, [name]: value }));
	};

	const handleSubmit = async (e) => {
		e.preventDefault();
		setLoading(true);
		setError(null);
		setPrediction(null);
		// Servidor ocioso leva alguns segundos para acordar: avisa em vez de parecer travado.
		const aviso = setTimeout(() => setDemorando(true), 4000);

		try {
			const payload = normalizePredictionPayload(formData);
			const data = await predictImovel(payload.negocio, payload);
			// A API não ecoa o negócio; o card precisa dele para dizer "aluguel" e "/mês".
			setPrediction({ ...data, negocio: payload.negocio });
		} catch (err) {
			setError(err.message || "Não foi possível obter a predição");
		} finally {
			clearTimeout(aviso);
			setDemorando(false);
			setLoading(false);
		}
	};

	const reset = () => {
		setFormData(createDefaultForm());
		setPrediction(null);
		setError(null);
	};

	return {
		formData,
		prediction,
		loading,
		demorando,
		error,
		bairros,
		handleChange,
		handleSubmit,
		reset,
	};
}
