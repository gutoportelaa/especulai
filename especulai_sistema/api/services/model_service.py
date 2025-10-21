"""
Serviço responsável por carregar modelo e pré-processador e realizar predições.
"""

import os
import joblib
import numpy as np
from typing import Dict, Optional


class ModelService:
    def __init__(self, model_path: str = None, preprocessor_path: str = None):
        self.model_path = model_path or os.environ.get("MODEL_PATH", "../ml_pipeline/model.joblib")
        self.preprocessor_path = preprocessor_path or os.environ.get("PREPROCESSOR_PATH", "../ml_pipeline/preprocessor.joblib")
        self.model = None
        self.preprocessor = None

    def load(self) -> None:
        if not os.path.exists(self.model_path) or not os.path.exists(self.preprocessor_path):
            return
        self.model = joblib.load(self.model_path)
        self.preprocessor = joblib.load(self.preprocessor_path)

    def is_ready(self) -> bool:
        return self.model is not None and self.preprocessor is not None

    def predict(self, features_dict: Dict) -> Dict:
        scaler = self.preprocessor['scaler']
        label_encoders = self.preprocessor['label_encoders']

        preco_por_m2_estimado = 5000
        densidade_comodos = (features_dict['quartos'] + features_dict['banheiros']) / features_dict['area']

        try:
            tipo_encoded = label_encoders['tipo'].transform([features_dict['tipo'].lower()])[0]
        except Exception:
            tipo_encoded = 0
        try:
            bairro_encoded = label_encoders['bairro'].transform([features_dict['bairro']])[0]
        except Exception:
            bairro_encoded = 0
        try:
            cidade_encoded = label_encoders['cidade'].transform([features_dict['cidade']])[0]
        except Exception:
            cidade_encoded = 0

        features = np.array([[
            features_dict['area'],
            features_dict['quartos'],
            features_dict['banheiros'],
            preco_por_m2_estimado,
            densidade_comodos,
            tipo_encoded,
            bairro_encoded,
            cidade_encoded
        ]])

        features_scaled = scaler.transform(features)
        prediction = self.model.predict(features_scaled)[0]

        confianca = "alta"
        if (tipo_encoded == 0 and features_dict['tipo'].lower() not in ['apartamento', 'casa']) or \
           bairro_encoded == 0 or cidade_encoded == 0:
            confianca = "média"

        return {"preco_estimado": float(prediction), "confianca": confianca}


