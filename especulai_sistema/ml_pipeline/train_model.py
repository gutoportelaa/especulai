"""
Pipeline de Treinamento de Machine Learning para predição de preços de imóveis.
Este script carrega, processa dados e treina um modelo LightGBM.
"""

import pandas as pd
from sqlalchemy import create_engine
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from lightgbm import LGBMRegressor
import joblib
from typing import Tuple
import warnings
import os

warnings.filterwarnings('ignore')


class ImovelMLPipeline:
    """
    Pipeline completo para processamento de dados e treinamento de modelo.
    """
    
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_columns = []
    
    def load_data(self) -> pd.DataFrame:
        """
        Carrega dados do banco de dados PostgreSQL.
        
        Returns:
            DataFrame com os dados carregados
        """
        print("Carregando dados do PostgreSQL...")
        db_connection_str = os.environ.get("DATABASE_URL", "postgresql://user:password@db:5432/especulai_db")
        db_connection = create_engine(db_connection_str)
        df = pd.read_sql("SELECT * FROM imoveis_raw", db_connection)
        print(f"✓ {len(df)} registros carregados do PostgreSQL")
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpa e trata valores ausentes e outliers.
        
        Args:
            df: DataFrame com dados brutos
            
        Returns:
            DataFrame limpo
        """
        print("\nLimpando dados...")
        
        # Remove duplicatas
        df = df.drop_duplicates()
        
        # Converte colunas numéricas
        numeric_cols = ['preco', 'area', 'quartos', 'banheiros']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove valores ausentes
        df = df.dropna()
        
        # Remove outliers usando IQR
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
        
        print(f"✓ Dados limpos: {len(df)} registros restantes")
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Realiza engenharia de features.
        
        Args:
            df: DataFrame com dados limpos
            
        Returns:
            DataFrame com features processadas
        """
        print("\nRealizando engenharia de features...")
        
        # Cria feature de preço por metro quadrado
        df['preco_por_m2'] = df['preco'] / df['area']
        
        # Cria feature de densidade de cômodos
        df['densidade_comodos'] = (df['quartos'] + df['banheiros']) / df['area']
        
        # Codifica variáveis categóricas
        categorical_cols = ['tipo', 'bairro', 'cidade']
        for col in categorical_cols:
            le = LabelEncoder()
            df[f'{col}_encoded'] = le.fit_transform(df[col])
            self.label_encoders[col] = le
        
        print(f"✓ Features criadas: {df.shape[1]} colunas")
        return df
    
    def prepare_train_test(self, df: pd.DataFrame, test_size: float = 0.2) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepara dados para treino e teste.
        
        Args:
            df: DataFrame com features processadas
            test_size: Proporção dos dados para teste
            
        Returns:
            Tupla com X_train, X_test, y_train, y_test
        """
        print("\nPreparando dados para treino e teste...")
        
        # Define features e target
        self.feature_columns = ['area', 'quartos', 'banheiros', 'preco_por_m2', 
                                'densidade_comodos', 'tipo_encoded', 'bairro_encoded', 
                                'cidade_encoded']
        
        X = df[self.feature_columns].values
        y = df['preco'].values
        
        # Divide em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Normaliza features
        X_train = self.scaler.fit_transform(X_train)
        X_test = self.scaler.transform(X_test)
        
        print(f"✓ Treino: {X_train.shape[0]} amostras | Teste: {X_test.shape[0]} amostras")
        return X_train, X_test, y_train, y_test
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """
        Treina o modelo LightGBM.
        
        Args:
            X_train: Features de treino
            y_train: Target de treino
        """
        print("\nTreinando modelo LightGBM...")
        
        # Configura modelo com parâmetros otimizados para velocidade
        self.model = LGBMRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            num_leaves=31,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        
        # Treina modelo
        self.model.fit(X_train, y_train)
        
        print("✓ Modelo treinado com sucesso")
    
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> None:
        """
        Avalia o desempenho do modelo.
        
        Args:
            X_test: Features de teste
            y_test: Target de teste
        """
        print("\nAvaliando modelo...")
        
        # Faz predições
        y_pred = self.model.predict(X_test)
        
        # Calcula métricas
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        print(f"\n=== Métricas de Desempenho ===")
        print(f"MAE (Erro Absoluto Médio): R$ {mae:,.2f}")
        print(f"RMSE (Raiz do Erro Quadrático Médio): R$ {rmse:,.2f}")
        print(f"R² (Coeficiente de Determinação): {r2:.4f}")
    
    def save_artifacts(self, model_path: str = 'model.joblib', 
                      preprocessor_path: str = 'preprocessor.joblib') -> None:
        """
        Salva o modelo e pré-processadores.
        
        Args:
            model_path: Caminho para salvar o modelo
            preprocessor_path: Caminho para salvar o pré-processador
        """
        print("\nSalvando artefatos...")
        
        # Salva modelo
        joblib.dump(self.model, model_path)
        print(f"✓ Modelo salvo em {model_path}")
        
        # Salva pré-processadores
        preprocessor = {
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns
        }
        joblib.dump(preprocessor, preprocessor_path)
        print(f"✓ Pré-processador salvo em {preprocessor_path}")


def main():
    """
    Função principal para execução do pipeline de treinamento.
    """
    print("=== Especulai - Pipeline de Treinamento de ML ===\n")
    
    # Inicializa pipeline
    pipeline = ImovelMLPipeline()
    
    # Carrega e processa dados
    df = pipeline.load_data()
    # Converte colunas para tipo numérico antes de clean_data
    numeric_cols = ['preco', 'area', 'quartos', 'banheiros']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = pipeline.clean_data(df)
    df = pipeline.engineer_features(df)
    
    # Prepara dados para treino
    X_train, X_test, y_train, y_test = pipeline.prepare_train_test(df)
    
    # Treina modelo
    pipeline.train_model(X_train, y_train)
    
    # Avalia modelo
    pipeline.evaluate_model(X_test, y_test)
    
    # Salva artefatos (na pasta atual: especulai_sistema/ml_pipeline)
    pipeline.save_artifacts()
    
    print("\n✓ Pipeline de treinamento concluído com sucesso!")


if __name__ == "__main__":
    main()


