"""
Serviço responsável por carregar modelo e pré-processador e realizar predições.
"""

import os
import joblib
import numpy as np
from pathlib import Path
from typing import Dict


class ModelService:
    def __init__(self, model_path: str = None, preprocessor_path: str = None):
        # Obtém o diretório raiz do projeto (especulai/)
        # __file__ está em especulai/apps/api/services/model_service.py
        # parents[3] = especulai/
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[3]
        
        # Se não encontrar, tenta caminho alternativo (caso esteja rodando de outro diretório)
        if not (project_root / "ml" / "artifacts").exists():
            # Tenta encontrar o diretório especulai no caminho atual
            for parent in current_file.parents:
                if (parent / "ml" / "artifacts").exists():
                    project_root = parent
                    break
        
        # Define caminhos padrão baseados no diretório do projeto
        default_model_path = project_root / "ml" / "artifacts" / "modelo_definitivo.joblib"
        default_preprocessor_path = project_root / "ml" / "artifacts" / "preprocessador.joblib"
        
        # Converte para string absoluta
        model_path_str = model_path or os.environ.get("MODEL_PATH", str(default_model_path))
        preprocessor_path_str = preprocessor_path or os.environ.get("PREPROCESSOR_PATH", str(default_preprocessor_path))
        
        # Normaliza o caminho (resolve caminhos relativos)
        self.model_path = str(Path(model_path_str).resolve()) if model_path_str else str(default_model_path.resolve())
        self.preprocessor_path = str(Path(preprocessor_path_str).resolve()) if preprocessor_path_str else str(default_preprocessor_path.resolve())
        self.model = None
        self.preprocessor = None
        self.feature_columns = []
        self.reference_values: Dict[str, float] = {}

    def load(self) -> None:
        # Se o caminho configurado não existir, tenta resolver pegando o modelo mais recente da pasta artifacts
        if not os.path.exists(self.model_path):
            artifacts_dir = Path(self.model_path).parent
            if artifacts_dir.exists():
                # Procura arquivos .joblib ordenados por data de modificação (desc)
                candidates = sorted(artifacts_dir.glob('*.joblib'), key=lambda p: p.stat().st_mtime, reverse=True)
                if candidates:
                    self.model_path = str(candidates[0].resolve())
                    print(f"[INFO] Modelo não encontrado no caminho padrão. Usando modelo mais recente: {self.model_path}")
                else:
                    print(f"[AVISO] Nenhum artefato .joblib encontrado em {artifacts_dir}")
                    return
            else:
                print(f"[AVISO] Modelo nao encontrado em {self.model_path}")
                return

        try:
            try:
                artifact = joblib.load(self.model_path)
            except Exception as e:
                print(f"[ERRO] Erro ao carregar modelo em {self.model_path}: {e}")
                # Tenta carregar o modelo mais recente disponível na pasta artifacts
                artifacts_dir = Path(self.model_path).parent
                candidates = sorted(artifacts_dir.glob('*.joblib'), key=lambda p: p.stat().st_mtime, reverse=True)
                # Remove o caminho atual da lista, se presente
                candidates = [p for p in candidates if str(p.resolve()) != str(Path(self.model_path).resolve())]
                loaded = False
                for cand in candidates:
                    try:
                        print(f"[INFO] Tentando carregar candidato: {cand}")
                        artifact = joblib.load(str(cand))
                        # Aceitamos apenas artefatos que contenham um modelo (dict com key 'model')
                        # ou objetos que não sejam apenas pré-processadores (não-dict).
                        is_model_artifact = (isinstance(artifact, dict) and 'model' in artifact) or (not isinstance(artifact, dict))
                        if not is_model_artifact:
                            print(f"[INFO] Candidato {cand} não parece conter um modelo - ignorando.")
                            continue
                        self.model_path = str(cand.resolve())
                        loaded = True
                        break
                    except Exception as e2:
                        print(f"[ERRO] Falha ao carregar {cand}: {e2}")
                        continue
                if not loaded:
                    raise

            if isinstance(artifact, dict) and "model" in artifact:
                # Modelo salvo como dicionário completo (formato do train_model.py)
                self.model = artifact["model"]
                self.preprocessor = artifact.get("preprocessor")
                metadata = artifact.get("metadata", {})
                self.feature_columns = metadata.get("feature_columns", [])
                self.reference_values = metadata.get("reference_values", {})
            else:
                # Modelo salvo apenas como modelo (formato antigo)
                self.model = artifact

            # Se o preprocessor não veio no artifact, tenta carregar separadamente
            if self.preprocessor is None and os.path.exists(self.preprocessor_path):
                self.preprocessor = joblib.load(self.preprocessor_path)
            # Se ainda não tem preprocessor, tenta construir um básico compatível
            if self.preprocessor is None:
                print("[AVISO] Preprocessor nao encontrado. Vai criar um preprocessor basico compativel...")
                from sklearn.preprocessing import StandardScaler, LabelEncoder

                # Feature columns padrão
                self.feature_columns = [
                    'area', 'quartos', 'banheiros', 'densidade_comodos',
                    'tipo_encoded', 'bairro_encoded', 'cidade_encoded'
                ]

                # Cria label encoders básicos
                label_encoders = {}
                for col in ['tipo', 'bairro', 'cidade']:
                    encoder = LabelEncoder()
                    # Valores padrão comuns
                    if col == 'tipo':
                        encoder.fit(['apartamento', 'casa', 'sobrado', 'terreno'])
                    elif col == 'bairro':
                        encoder.fit(['centro', 'norte', 'sul', 'leste', 'oeste'])
                    elif col == 'cidade':
                        encoder.fit(['teresina'])
                    label_encoders[col] = encoder

                # Cria scaler básico (será ajustado na primeira predição se necessário)
                scaler = StandardScaler()
                import numpy as np
                dummy_data = np.array([[100, 3, 2, 0.05, 0, 0, 0]])  # valores padrão
                scaler.fit(dummy_data)

                self.preprocessor = {
                    'scaler': scaler,
                    'label_encoders': label_encoders,
                    'feature_columns': self.feature_columns,
                    'reference_values': {'preco_por_m2_median': 5000.0}
                }
                self.reference_values = self.preprocessor['reference_values']
                print("[OK] Preprocessor basico criado")

            # Se veio um preprocessor parcial (ex: sem label_encoders), garante chaves mínimas
            # e cria fallbacks quando necessário.
            if self.preprocessor is not None:
                # garantir scaler
                if 'scaler' not in self.preprocessor:
                    from sklearn.preprocessing import StandardScaler
                    scaler = StandardScaler()
                    import numpy as np
                    scaler.fit(np.zeros((1, 1)))
                    self.preprocessor['scaler'] = scaler

                # garantir feature_columns
                if 'feature_columns' not in self.preprocessor:
                    self.preprocessor['feature_columns'] = self.feature_columns

                # garantir label_encoders
                if 'label_encoders' not in self.preprocessor:
                    print('[INFO] label_encoders ausente no preprocessor - criando encoders basicos')
                    from sklearn.preprocessing import LabelEncoder
                    label_encoders = {}
                    for col in ['tipo', 'bairro', 'cidade']:
                        encoder = LabelEncoder()
                        if col == 'tipo':
                            encoder.fit(['apartamento', 'casa', 'sobrado', 'terreno'])
                        elif col == 'bairro':
                            encoder.fit(['centro', 'norte', 'sul', 'leste', 'oeste'])
                        elif col == 'cidade':
                            encoder.fit(['teresina'])
                        label_encoders[col] = encoder
                    self.preprocessor['label_encoders'] = label_encoders

                # garantir reference_values
                if 'reference_values' not in self.preprocessor:
                    self.preprocessor['reference_values'] = {'preco_por_m2_median': 5000.0}
                self.reference_values = self.preprocessor.get('reference_values', {})

            if self.preprocessor:
                self.feature_columns = self.preprocessor.get("feature_columns", self.feature_columns)
                self.reference_values = self.preprocessor.get("reference_values", self.reference_values)
                
                print(f"[OK] Modelo carregado com sucesso de {self.model_path}")
                print(f"  Tipo do modelo: {type(self.model).__name__}")
        except Exception as e:
            print(f"[ERRO] Erro ao carregar modelo: {e}")
            import traceback
            traceback.print_exc()

    def is_ready(self) -> bool:
        # O modelo está pronto se tiver modelo e preprocessor
        return self.model is not None and self.preprocessor is not None

    def predict(self, features_dict: Dict) -> Dict:
        # Detecta o tipo de modelo e obtém as features esperadas
        model_type = type(self.model).__name__
        
        # Se for XGBRegressor, obtém as feature names do booster
        if model_type == 'XGBRegressor':
            try:
                booster = self.model.get_booster()
                expected_features = booster.feature_names if hasattr(booster, 'feature_names') else None
                if expected_features:
                    return self._predict_xgboost(features_dict, expected_features)
            except Exception as e:
                print(f"[AVISO] Erro ao obter features do XGBRegressor: {e}")
        
        # Para outros modelos (GradientBoostingRegressor, etc.), usa o método padrão
        return self._predict_standard(features_dict)
    
    def _predict_xgboost(self, features_dict: Dict, expected_features: list) -> Dict:
        """Predição para modelo XGBRegressor com features enriquecidas"""
        area = max(float(features_dict.get('area', 100)), 1.0)
        quartos = int(features_dict.get('quartos', 2))
        banheiros = int(features_dict.get('banheiros', 1))
        
        # Mapeia features do input para as features esperadas pelo modelo
        feature_map = {
            'Area_m2': area,
            'Quartos': quartos,
            'Banheiros': banheiros,
            # Features de localização (valores padrão para Teresina)
            'Latitude': features_dict.get('latitude', -5.0892),  # Teresina
            'Longitude': features_dict.get('longitude', -42.8014),  # Teresina
            # Features de distância (valores padrão médios)
            'distancia_farmacias': features_dict.get('distancia_farmacias', 500.0),
            'distancia_escolas': features_dict.get('distancia_escolas', 800.0),
            'distancia_mercados': features_dict.get('distancia_mercados', 600.0),
            'distancia_hospitais': features_dict.get('distancia_hospitais', 1500.0),
            'score_comercial': features_dict.get('score_comercial', 0.5),
            # Features FipeZap (valores padrão baseados na área)
            'FipeZap_m2': features_dict.get('FipeZap_m2', 5000.0),
            'FipeZap_Diferenca_m2': features_dict.get('FipeZap_Diferenca_m2', 0.0),
        }
        
        # Cria o vetor de features na ordem esperada pelo modelo
        feature_vector = [feature_map.get(feat, 0.0) for feat in expected_features]
        features = np.array([feature_vector])
        
        # XGBRegressor não precisa de scaler (ele normaliza internamente)
        prediction = self.model.predict(features)[0]
        
        confianca = "alta"
        if area < 20 or quartos == 0:
            confianca = "média"
        
        return {"preco_estimado": float(prediction), "confianca": confianca}
    
    def _predict_standard(self, features_dict: Dict) -> Dict:
        """Predição para modelos padrão (GradientBoostingRegressor, etc.)"""
        scaler = self.preprocessor['scaler']
        label_encoders = self.preprocessor['label_encoders']

        area = max(float(features_dict['area']), 1.0)
        quartos = int(features_dict['quartos'])
        banheiros = int(features_dict['banheiros'])
        tipo_val = str(features_dict['tipo']).lower().strip()
        bairro_val = str(features_dict['bairro']).strip()
        cidade_val = str(features_dict['cidade']).strip()

        densidade_comodos = (quartos + banheiros) / area
        preco_por_m2_ref = float(self.reference_values.get('preco_por_m2_median', 5000.0))

        def encode_value(encoder_key: str, raw_value: str) -> int:
            encoder = label_encoders.get(encoder_key)
            if encoder is None:
                return 0
            try:
                return int(encoder.transform([raw_value])[0])
            except Exception:
                return 0

        tipo_encoded = encode_value('tipo', tipo_val)
        bairro_encoded = encode_value('bairro', bairro_val)
        cidade_encoded = encode_value('cidade', cidade_val)

        feature_map = {
            'area': area,
            'quartos': quartos,
            'banheiros': banheiros,
            'densidade_comodos': densidade_comodos,
            'preco_por_m2': preco_por_m2_ref,
            'tipo_encoded': tipo_encoded,
            'bairro_encoded': bairro_encoded,
            'cidade_encoded': cidade_encoded
        }

        ordered_columns = self.feature_columns or [
            'area',
            'quartos',
            'banheiros',
            'densidade_comodos',
            'tipo_encoded',
            'bairro_encoded',
            'cidade_encoded'
        ]

        feature_vector = [feature_map.get(col, 0.0) for col in ordered_columns]
        features = np.array([feature_vector])
        if features.size == 0:
            raise ValueError("Nenhuma feature disponível para predição.")

        features_scaled = scaler.transform(features)
        prediction = self.model.predict(features_scaled)[0]

        confianca = "alta"
        if (tipo_encoded == 0 and tipo_val not in ['apartamento', 'casa']) or \
           bairro_encoded == 0 or cidade_encoded == 0:
            confianca = "média"

        return {"preco_estimado": float(prediction), "confianca": confianca}


