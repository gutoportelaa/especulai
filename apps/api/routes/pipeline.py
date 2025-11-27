"""
Endpoints da API para orquestração do pipeline ML.

Endpoints:
  POST /api/v1/pipeline/run          - Inicia pipeline completo
  GET  /api/v1/pipeline/status       - Status atual
  GET  /api/v1/pipeline/logs         - Histórico de logs
  POST /api/v1/pipeline/reset        - Reseta pipeline para recomeçar
  GET  /api/v1/pipeline/info         - Info sobre modelo treinado
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncio

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = WORKSPACE_ROOT / "dados_imoveis_teresina"
STATUS_FILE = DATA_ROOT / "pipeline_status.json"
LOG_FILE = DATA_ROOT / "pipeline_orchestrator.log"
ORCHESTRATOR_LOG_FILE = DATA_ROOT / "pipeline_log.txt"

# ============================================================================
# SCHEMAS
# ============================================================================

class PipelineRunRequest(BaseModel):
    """Requisição para executar pipeline."""
    num_pages_venda: int = 5
    num_pages_aluguel: int = 5
    clear_previous: bool = False
    force_all: bool = False


class PipelineStatusResponse(BaseModel):
    """Resposta de status do pipeline."""
    status: str
    current_stage: str
    completed_stages: List[str]
    errors: List[str]
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class PipelineInfoResponse(BaseModel):
    """Informações sobre o modelo treinado."""
    model_exists: bool
    model_path: Optional[str] = None
    trained_at: Optional[str] = None
    features_count: Optional[int] = None
    dataset_size: Optional[int] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_pipeline_status() -> Dict[str, Any]:
    """Lê status do pipeline do arquivo."""
    if STATUS_FILE.exists():
        try:
            with STATUS_FILE.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        "status": "not_started",
        "current_stage": "idle",
        "completed_stages": [],
        "errors": [],
        "started_at": None,
        "finished_at": None
    }


async def _run_pipeline_background(
    num_pages_venda: int,
    num_pages_aluguel: int,
    clear_previous: bool,
    force_all: bool
):
    """Executa pipeline em background."""
    try:
        from especulai.ml.pipeline.orchestrator import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator()
        orchestrator.run(
            num_scrape_pages_venda=num_pages_venda,
            num_scrape_pages_aluguel=num_pages_aluguel,
            clear_previous=clear_previous,
            force_all=force_all
        )
        
    except Exception as e:
        print(f"[API] Erro durante execução do pipeline: {e}")
        # Status já foi atualizado pelo orchestrator


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/run")
async def run_pipeline(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Inicia execução do pipeline em background.
    
    Pipeline stages:
      1. Scraping OLX (venda + aluguel)
      2. Enriquecimento Geoespacial
      3. Enriquecimento Econômico
      4. Preparação de Dataset
      5. Treinamento do Modelo
    
    Args:
        request: Parâmetros do pipeline
        background_tasks: Tarefa background do FastAPI
    
    Returns:
        Status inicial da execução
    
    Raises:
        HTTPException 409: Se pipeline já está rodando
    """
    status = _get_pipeline_status()
    
    # Validação: não permite duas execuções simultâneas
    if status.get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail="Pipeline já está em execução. Aguarde conclusão."
        )
    
    # Agenda execução em background
    background_tasks.add_task(
        _run_pipeline_background,
        num_pages_venda=request.num_pages_venda,
        num_pages_aluguel=request.num_pages_aluguel,
        clear_previous=request.clear_previous,
        force_all=request.force_all
    )
    
    return {
        "status": "queued",
        "message": "Pipeline iniciado em background. Verifique /status para acompanhar.",
        "started_at": datetime.now().isoformat(),
        "parameters": {
            "num_pages_venda": request.num_pages_venda,
            "num_pages_aluguel": request.num_pages_aluguel,
            "clear_previous": request.clear_previous,
            "force_all": request.force_all
        }
    }


@router.get("/status")
async def pipeline_status() -> PipelineStatusResponse:
    """
    Retorna status atual do pipeline.
    
    Returns:
        Status detalhado incluindo estágio atual e histórico
    """
    status = _get_pipeline_status()
    
    return PipelineStatusResponse(
        status=status.get("status", "unknown"),
        current_stage=status.get("current_stage", "idle"),
        completed_stages=status.get("completed_stages", []),
        errors=status.get("errors", []),
        started_at=status.get("started_at"),
        finished_at=status.get("finished_at")
    )


@router.get("/logs")
async def pipeline_logs(lines: int = 100) -> Dict[str, List[str]]:
    """
    Retorna últimas linhas de log do pipeline.
    
    Args:
        lines: Número de linhas a retornar (default 100)
    
    Returns:
        Lista de linhas de log
    """
    logs = []
    
    log_files = [LOG_FILE, ORCHESTRATOR_LOG_FILE]
    
    for log_file in log_files:
        if log_file.exists():
            try:
                with log_file.open('r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    logs.extend(all_lines[-lines:])
            except Exception:
                pass
    
    if not logs:
        logs = ["[INFO] Nenhum log disponível ainda"]
    
    return {
        "logs": logs,
        "count": len(logs),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/reset")
async def reset_pipeline() -> Dict[str, str]:
    """
    Reseta pipeline para começar do zero.
    
    ⚠️  AVISO: Remove informações de status anterior.
    
    Returns:
        Confirmação de reset
    """
    try:
        from especulai.ml.pipeline.orchestrator import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator()
        orchestrator.reset()
        
        return {
            "status": "success",
            "message": "Pipeline resetado com sucesso",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao resetar pipeline: {str(e)}"
        )


@router.get("/info")
async def pipeline_info() -> PipelineInfoResponse:
    """
    Retorna informações sobre o modelo treinado.
    
    Returns:
        Metadados do modelo (se existir)
    """
    artifact_dir = Path(__file__).resolve().parents[2] / "artifacts"
    model_path = artifact_dir / "modelo_definitivo.joblib"
    
    if not model_path.exists():
        return PipelineInfoResponse(
            model_exists=False,
            model_path=None,
            trained_at=None,
            features_count=None,
            dataset_size=None
        )
    
    try:
        import joblib
        
        artifact = joblib.load(model_path)
        metadata = artifact.get("metadata", {})
        
        return PipelineInfoResponse(
            model_exists=True,
            model_path=str(model_path),
            trained_at=metadata.get("trained_at"),
            features_count=metadata.get("dataset_shape", {}).get("n_features"),
            dataset_size=metadata.get("dataset_shape", {}).get("n_samples")
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao carregar informações do modelo: {str(e)}"
        )


@router.get("/stages")
async def pipeline_stages() -> Dict[str, List[str]]:
    """
    Retorna lista de estágios do pipeline.
    
    Returns:
        Descrição de cada estágio
    """
    return {
        "stages": [
            "scraping_olx",
            "enriquecimento_geo",
            "enriquecimento_economico",
            "preparacao_dataset",
            "treinamento_modelo"
        ],
        "descriptions": {
            "scraping_olx": "Coleta dados de anúncios da OLX (venda + aluguel)",
            "enriquecimento_geo": "Enriquece com dados geoespaciais e POI",
            "enriquecimento_economico": "Enriquece com dados econômicos (FipeZap)",
            "preparacao_dataset": "Limpeza, Feature Engineering, One-Hot Encoding",
            "treinamento_modelo": "Treina modelo Gradient Boosting final"
        }
    }
