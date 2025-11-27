"""
Orquestrador central do pipeline ML.

Fluxo linear e claro:
  1. Scraping OLX (raw_olx.csv)
  2. Enriquecimento Geoespacial (enriched_geo_olx.csv)
  3. Enriquecimento Econômico (enriched_economic_olx.csv)
  4. Preparação de Dataset (dataset_treino_olx_final.csv)
  5. Treinamento do Modelo (modelo_definitivo.joblib)

Responsabilidades:
  - Orquestração linear dos estágios
  - Validação de pré-requisitos
  - Logging estruturado
  - Status tracking (para API)
  - Tratamento de erros com recuperação
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import json
import sys
import logging
from enum import Enum

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../especulai
WORKSPACE_ROOT = PROJECT_ROOT.parent
DATA_ROOT = WORKSPACE_ROOT / "dados_imoveis_teresina"
STATUS_FILE = DATA_ROOT / "pipeline_status.json"
LOG_FILE = DATA_ROOT / "pipeline_orchestrator.log"

# Garante que os módulos sejam importáveis
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT))

# ============================================================================
# ENUMS E CONSTANTS
# ============================================================================

class PipelineStage(Enum):
    """Estágios do pipeline."""
    IDLE = "idle"
    SCRAPING_OLX = "scraping_olx"
    ENRIQUECIMENTO_GEO = "enriquecimento_geo"
    ENRIQUECIMENTO_ECONOMICO = "enriquecimento_economico"
    PREPARACAO_DATASET = "preparacao_dataset"
    TREINAMENTO_MODELO = "treinamento_modelo"
    COMPLETED = "completed"
    ERROR = "error"


class PipelineStatus(Enum):
    """Status do pipeline."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# ============================================================================
# LOGGING ESTRUTURADO
# ============================================================================

def setup_logging():
    """Configura logging para arquivo e console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()

# ============================================================================
# ORCHESTRATOR
# ============================================================================

class PipelineOrchestrator:
    """Orquestrador central do pipeline ML OLX."""
    
    def __init__(self):
        """Inicializa orquestrador."""
        self.status = {
            "version": "1.0.0",
            "status": PipelineStatus.NOT_STARTED.value,
            "started_at": None,
            "finished_at": None,
            "current_stage": PipelineStage.IDLE.value,
            "completed_stages": [],
            "failed_stage": None,
            "errors": [],
        }
        self._load_status()
    
    def _load_status(self):
        """Carrega status anterior do pipeline, se existir."""
        if STATUS_FILE.exists():
            try:
                with STATUS_FILE.open('r', encoding='utf-8') as f:
                    saved_status = json.load(f)
                logger.info("[INIT] Status anterior carregado")
                # Merge com status padrão (mantém novos campos se adicionar)
                self.status.update(saved_status)
            except Exception as e:
                logger.warning(f"[INIT] Erro ao carregar status anterior: {e}")
    
    def _save_status(self):
        """Persiste status atual para recuperação."""
        try:
            with STATUS_FILE.open('w', encoding='utf-8') as f:
                json.dump(self.status, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[SAVE_STATUS] Erro ao salvar status: {e}")
    
    def _log_stage(self, message: str, level: str = "INFO"):
        """Log estruturado com timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        
        if level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
        elif level == "SUCCESS":
            logger.info(f"✓ {message}")
    
    def run(
        self,
        num_scrape_pages_venda: int = 5,
        num_scrape_pages_aluguel: int = 5,
        clear_previous: bool = False,
        force_all: bool = False
    ) -> bool:
        """
        Executa pipeline completo.
        
        Args:
            num_scrape_pages_venda: Páginas OLX venda para scraping
            num_scrape_pages_aluguel: Páginas OLX aluguel para scraping
            clear_previous: Se True, ignora dados anteriores
            force_all: Se True, executa todos os estágios mesmo se alguns completados
        
        Returns:
            True se sucesso, False se erro
        """
        print()
        print("=" * 80)
        print("=== ESPECULAI - PIPELINE ML (OLX) ===")
        print("=" * 80)
        print()
        
        self.status["status"] = PipelineStatus.RUNNING.value
        self.status["started_at"] = datetime.now().isoformat()
        self.status["current_stage"] = PipelineStage.SCRAPING_OLX.value
        self._save_status()
        
        self._log_stage("Pipeline iniciado", "INFO")
        self._log_stage(f"Modo force_all: {force_all}", "INFO")
        
        # Stage 1: Scraping OLX
        if force_all or PipelineStage.SCRAPING_OLX.value not in self.status["completed_stages"]:
            if not self._run_stage(
                PipelineStage.SCRAPING_OLX,
                self._stage_scraping_olx,
                num_pages_venda=num_scrape_pages_venda,
                num_pages_aluguel=num_scrape_pages_aluguel,
                clear_previous=clear_previous
            ):
                return False
        else:
            self._log_stage(f"Estágio {PipelineStage.SCRAPING_OLX.value} já completo, pulando...", "INFO")
        
        # Stage 2: Enriquecimento Geoespacial
        # Se estiver marcado como completo, garantimos que o arquivo de entrada exista;
        # caso contrário, consideramos que não está completo (re-executa o estágio).
        if PipelineStage.ENRIQUECIMENTO_GEO.value in self.status["completed_stages"] and not self._prereqs_ok(PipelineStage.ENRIQUECIMENTO_GEO):
            # Remove marcação de completo para forçar reexecução
            self._log_stage(f"Estágio {PipelineStage.ENRIQUECIMENTO_GEO.value} marcado como completo, mas pré-requisitos faltam. Re-executando.", "WARNING")
            try:
                self.status["completed_stages"].remove(PipelineStage.ENRIQUECIMENTO_GEO.value)
            except ValueError:
                pass

        if force_all or PipelineStage.ENRIQUECIMENTO_GEO.value not in self.status["completed_stages"]:
            if not self._run_stage(
                PipelineStage.ENRIQUECIMENTO_GEO,
                self._stage_enriquecimento_geo
            ):
                return False
        else:
            self._log_stage(f"Estágio {PipelineStage.ENRIQUECIMENTO_GEO.value} já completo, pulando...", "INFO")
        
        # Stage 3: Enriquecimento Econômico
        if PipelineStage.ENRIQUECIMENTO_ECONOMICO.value in self.status["completed_stages"] and not self._prereqs_ok(PipelineStage.ENRIQUECIMENTO_ECONOMICO):
            self._log_stage(f"Estágio {PipelineStage.ENRIQUECIMENTO_ECONOMICO.value} marcado como completo, mas pré-requisitos faltam. Re-executando.", "WARNING")
            try:
                self.status["completed_stages"].remove(PipelineStage.ENRIQUECIMENTO_ECONOMICO.value)
            except ValueError:
                pass

        if force_all or PipelineStage.ENRIQUECIMENTO_ECONOMICO.value not in self.status["completed_stages"]:
            if not self._run_stage(
                PipelineStage.ENRIQUECIMENTO_ECONOMICO,
                self._stage_enriquecimento_economico
            ):
                return False
        else:
            self._log_stage(f"Estágio {PipelineStage.ENRIQUECIMENTO_ECONOMICO.value} já completo, pulando...", "INFO")
        
        # Stage 4: Preparação de Dataset
        if PipelineStage.PREPARACAO_DATASET.value in self.status["completed_stages"] and not self._prereqs_ok(PipelineStage.PREPARACAO_DATASET):
            self._log_stage(f"Estágio {PipelineStage.PREPARACAO_DATASET.value} marcado como completo, mas pré-requisitos faltam. Re-executando.", "WARNING")
            try:
                self.status["completed_stages"].remove(PipelineStage.PREPARACAO_DATASET.value)
            except ValueError:
                pass

        if force_all or PipelineStage.PREPARACAO_DATASET.value not in self.status["completed_stages"]:
            if not self._run_stage(
                PipelineStage.PREPARACAO_DATASET,
                self._stage_preparacao_dataset
            ):
                return False
        else:
            self._log_stage(f"Estágio {PipelineStage.PREPARACAO_DATASET.value} já completo, pulando...", "INFO")
        
        # Stage 5: Treinamento do Modelo
        if PipelineStage.TREINAMENTO_MODELO.value in self.status["completed_stages"] and not self._prereqs_ok(PipelineStage.TREINAMENTO_MODELO):
            self._log_stage(f"Estágio {PipelineStage.TREINAMENTO_MODELO.value} marcado como completo, mas pré-requisitos faltam. Re-executando.", "WARNING")
            try:
                self.status["completed_stages"].remove(PipelineStage.TREINAMENTO_MODELO.value)
            except ValueError:
                pass

        if force_all or PipelineStage.TREINAMENTO_MODELO.value not in self.status["completed_stages"]:
            if not self._run_stage(
                PipelineStage.TREINAMENTO_MODELO,
                self._stage_treinamento_modelo
            ):
                return False
        else:
            self._log_stage(f"Estágio {PipelineStage.TREINAMENTO_MODELO.value} já completo, pulando...", "INFO")
        
        # Sucesso!
        self.status["status"] = PipelineStatus.SUCCESS.value
        self.status["finished_at"] = datetime.now().isoformat()
        self.status["current_stage"] = PipelineStage.COMPLETED.value
        self._save_status()
        
        self._log_stage("Pipeline concluído com sucesso!", "SUCCESS")
        print()
        print("=" * 80)
        print("[OK] Pipeline OLX executado com sucesso!")
        print(f"[OK] Estágios completados: {', '.join(self.status['completed_stages'])}")
        print("=" * 80)
        print()
        
        return True
    
    def _run_stage(self, stage: PipelineStage, stage_func, **kwargs) -> bool:
        """
        Executa um estágio com tratamento de erro.
        
        Args:
            stage: Estágio a executar
            stage_func: Função que implementa o estágio
            **kwargs: Argumentos para a função
        
        Returns:
            True se sucesso, False se erro
        """
        try:
            self.status["current_stage"] = stage.value
            self._log_stage(f"Iniciando estágio: {stage.value}", "INFO")
            self._save_status()
            
            # Executa o estágio
            stage_func(**kwargs)
            
            # Marca como completo
            if stage.value not in self.status["completed_stages"]:
                self.status["completed_stages"].append(stage.value)
            
            self._log_stage(f"Estágio concluído: {stage.value}", "SUCCESS")
            self._save_status()
            return True
            
        except Exception as e:
            error_msg = f"Erro no estágio {stage.value}: {str(e)}"
            self._log_stage(error_msg, "ERROR")
            self.status["errors"].append(error_msg)
            self.status["failed_stage"] = stage.value
            self.status["status"] = PipelineStatus.FAILED.value
            self.status["current_stage"] = PipelineStage.ERROR.value
            self.status["finished_at"] = datetime.now().isoformat()
            self._save_status()
            return False

    def _prereqs_ok(self, stage: PipelineStage) -> bool:
        """
        Verifica se os arquivos de entrada necessários para um estágio existem.
        Retorna True se os pré-requisitos existirem, False caso contrário.
        """
        # Mapear estágios para arquivos de entrada esperados
        prereq_map = {
            PipelineStage.ENRIQUECIMENTO_GEO: DATA_ROOT / "raw_olx.csv",
            PipelineStage.ENRIQUECIMENTO_ECONOMICO: DATA_ROOT / "enriched_geo_olx.csv",
            PipelineStage.PREPARACAO_DATASET: DATA_ROOT / "enriched_economic_olx.csv",
            PipelineStage.TREINAMENTO_MODELO: DATA_ROOT / "dataset_treino_olx_final.csv",
        }

        expected = prereq_map.get(stage)
        if expected is None:
            # Estágios sem pré-requisito explícito (p.ex. scraping) retornam True
            return True

        if not expected.exists():
            self._log_stage(f"Arquivo de entrada não encontrado: {expected}", "ERROR")
            return False

        return True
    
    # ========================================================================
    # IMPLEMENTAÇÃO DOS ESTÁGIOS
    # ========================================================================
    
    def _stage_scraping_olx(self, num_pages_venda: int, num_pages_aluguel: int, clear_previous: bool):
        """Stage 1: Scraping OLX."""
        from especulai.apps.scraper.scraper_olx import main as scrape_olx_main
        
        scrape_olx_main(
            num_pages_venda=num_pages_venda,
            num_pages_aluguel=num_pages_aluguel,
            clear_previous=clear_previous
        )
    
    def _stage_enriquecimento_geo(self):
        """Stage 2: Enriquecimento Geoespacial."""
        from especulai.ml.pipeline.modules.enriquecimento_geoespacial import main as enrich_geo_main
        
        # Entrada: raw_olx.csv
        # Saída: enriched_geo_olx.csv
        enrich_geo_main()
    
    def _stage_enriquecimento_economico(self):
        """Stage 3: Enriquecimento Econômico."""
        from especulai.ml.pipeline.modules.enriquecimento_economico import main as enrich_eco_main
        
        # Entrada: enriched_geo_olx.csv
        # Saída: enriched_economic_olx.csv
        enrich_eco_main()
    
    def _stage_preparacao_dataset(self):
        """Stage 4: Preparação de Dataset."""
        from especulai.ml.pipeline.prepare_dataset import main as prepare_main

        # Entrada: enriched_economic_olx.csv
        # Saída: dataset_treino_olx_final.csv
        prepare_main()
    
    def _stage_treinamento_modelo(self):
        """Stage 5: Treinamento do Modelo."""
        from especulai.ml.pipeline.train_model import main as train_model_main
        
        train_model_main()
    
    def reset(self):
        """Reseta o status do pipeline para recomeçar do zero."""
        self.status["status"] = PipelineStatus.NOT_STARTED.value
        self.status["current_stage"] = PipelineStage.IDLE.value
        self.status["completed_stages"] = []
        self.status["errors"] = []
        self.status["failed_stage"] = None
        self.status["started_at"] = None
        self.status["finished_at"] = None
        self._save_status()
        self._log_stage("Pipeline resetado", "INFO")


# ============================================================================
# MAIN
# ============================================================================

def main(
    num_pages_venda: int = 5,
    num_pages_aluguel: int = 5,
    clear_previous: bool = False,
    force_all: bool = False
):
    """
    Entry point do orchestrator.
    
    Args:
        num_pages_venda: Páginas OLX venda
        num_pages_aluguel: Páginas OLX aluguel
        clear_previous: Limpar dados anteriores
        force_all: Forçar execução de todos os estágios
    """
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    
    orchestrator = PipelineOrchestrator()
    success = orchestrator.run(
        num_scrape_pages_venda=num_pages_venda,
        num_scrape_pages_aluguel=num_pages_aluguel,
        clear_previous=clear_previous,
        force_all=force_all
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main(
        num_pages_venda=5,
        num_pages_aluguel=0,
        clear_previous=False,
        force_all=False
    )
