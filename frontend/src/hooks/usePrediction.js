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
	const [bairros, setBairros] = useState([]);

	const negocio = formData.negocio;

	// O modelo roda no cliente: puxa os ~200 KB do negócio escolhido assim que a página
	// abre, para que o primeiro cálculo não espere o download.
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

		try {
			const payload = normalizePredictionPayload(formData);
			const data = await predictImovel(payload.negocio, payload);
			setPrediction(data);
		} catch (err) {
			setError(err.message || "Não foi possível obter a predição");
		} finally {
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
		error,
		bairros,
		handleChange,
		handleSubmit,
		reset,
	};
}
