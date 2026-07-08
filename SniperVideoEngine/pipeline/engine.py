"""
Pipeline Engine
State machine para controle de pipeline de produção.
"""
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


class StageStatus(Enum):
    """Status de um estágio do pipeline."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class Stage:
    """Representa um estágio do pipeline."""
    name: str
    status: StageStatus = StageStatus.PENDING
    progress: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PipelineState:
    """Estado completo do pipeline."""
    task_id: str
    theme: str
    channel_id: Optional[str] = None
    video_format: str = "horizontal"
    stages: Dict[str, Stage] = field(default_factory=dict)
    current_stage: Optional[str] = None
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PipelineEngine:
    """
    Motor de pipeline com state machine para controle de produção.
    
    Estágios:
    1. research - Pesquisa de tendências
    2. script - Geração de roteiro
    3. seo - Otimização SEO
    4. produce - Produção do vídeo
    """

    STAGE_ORDER = ["research", "script", "seo", "produce"]

    def __init__(self, task_id: str, theme: str, channel_id: str = None, video_format: str = "horizontal"):
        self.state = PipelineState(
            task_id=task_id,
            theme=theme,
            channel_id=channel_id,
            video_format=video_format,
        )
        
        for stage_name in self.STAGE_ORDER:
            self.state.stages[stage_name] = Stage(name=stage_name)
        
        self.state.current_stage = self.STAGE_ORDER[0]
        self.state.status = "running"
        
        self._listeners: List[callable] = []

    def add_listener(self, callback: callable):
        """Adiciona listener para atualizações de estado."""
        self._listeners.append(callback)

    def _notify_listeners(self, event_type: str, data: Dict[str, Any]):
        """Notifica listeners sobre mudanças de estado."""
        for listener in self._listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                print(f"[PipelineEngine] Erro ao notificar listener: {e}")

    def get_current_stage(self) -> Optional[Stage]:
        """Retorna estágio atual."""
        if self.state.current_stage:
            return self.state.stages[self.state.current_stage]
        return None

    def start_stage(self, stage_name: str) -> bool:
        """
        Inicia um estágio.
        
        Args:
            stage_name: Nome do estágio
            
        Returns:
            True se iniciado com sucesso
        """
        if stage_name not in self.state.stages:
            return False
        
        stage = self.state.stages[stage_name]
        if stage.status != StageStatus.PENDING:
            return False
        
        stage.status = StageStatus.RUNNING
        stage.started_at = datetime.now().isoformat()
        stage.progress = 0
        
        self.state.current_stage = stage_name
        self.state.updated_at = datetime.now().isoformat()
        
        self._notify_listeners("stage_started", {
            "task_id": self.state.task_id,
            "stage": stage_name,
        })
        
        return True

    def update_progress(self, stage_name: str, progress: int, log: str = None) -> bool:
        """
        Atualiza progresso de um estágio.
        
        Args:
            stage_name: Nome do estágio
            progress: Progresso (0-100)
            log: Log opcional
            
        Returns:
            True se atualizado com sucesso
        """
        if stage_name not in self.state.stages:
            return False
        
        stage = self.state.stages[stage_name]
        if stage.status != StageStatus.RUNNING:
            return False
        
        stage.progress = min(max(progress, 0), 100)
        if log:
            stage.logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log}")
        
        self.state.updated_at = datetime.now().isoformat()
        
        self._notify_listeners("stage_progress", {
            "task_id": self.state.task_id,
            "stage": stage_name,
            "progress": stage.progress,
        })
        
        return True

    def request_approval(self, stage_name: str, data: Dict[str, Any] = None) -> bool:
        """
        Solicita aprovação para um estágio.
        
        Args:
            stage_name: Nome do estágio
            data: Dados para aprovação
            
        Returns:
            True se solicitado com sucesso
        """
        if stage_name not in self.state.stages:
            return False
        
        stage = self.state.stages[stage_name]
        if stage.status != StageStatus.RUNNING:
            return False
        
        stage.status = StageStatus.WAITING_APPROVAL
        if data:
            stage.data.update(data)
        
        self.state.updated_at = datetime.now().isoformat()
        
        self._notify_listeners("stage_waiting_approval", {
            "task_id": self.state.task_id,
            "stage": stage_name,
            "data": stage.data,
        })
        
        return True

    def approve_stage(self, stage_name: str) -> bool:
        """
        Aprova um estágio e avança para o próximo.
        
        Args:
            stage_name: Nome do estágio
            
        Returns:
            True se aprovado com sucesso
        """
        if stage_name not in self.state.stages:
            return False
        
        stage = self.state.stages[stage_name]
        if stage.status != StageStatus.WAITING_APPROVAL:
            return False
        
        stage.status = StageStatus.APPROVED
        stage.completed_at = datetime.now().isoformat()
        stage.progress = 100
        
        self._advance_to_next_stage()
        
        self.state.updated_at = datetime.now().isoformat()
        
        self._notify_listeners("stage_approved", {
            "task_id": self.state.task_id,
            "stage": stage_name,
        })
        
        return True

    def complete_stage(self, stage_name: str, data: Dict[str, Any] = None) -> bool:
        """
        Completa um estágio automaticamente (sem aprovação).
        
        Args:
            stage_name: Nome do estágio
            data: Dados do estágio
            
        Returns:
            True se completado com sucesso
        """
        if stage_name not in self.state.stages:
            return False
        
        stage = self.state.stages[stage_name]
        if stage.status != StageStatus.RUNNING:
            return False
        
        stage.status = StageStatus.COMPLETED
        stage.completed_at = datetime.now().isoformat()
        stage.progress = 100
        if data:
            stage.data.update(data)
        
        self._advance_to_next_stage()
        
        self.state.updated_at = datetime.now().isoformat()
        
        self._notify_listeners("stage_completed", {
            "task_id": self.state.task_id,
            "stage": stage_name,
        })
        
        return True

    def fail_stage(self, stage_name: str, error: str) -> bool:
        """
        Marca um estágio como falhou.
        
        Args:
            stage_name: Nome do estágio
            error: Mensagem de erro
            
        Returns:
            True se marcado com sucesso
        """
        if stage_name not in self.state.stages:
            return False
        
        stage = self.state.stages[stage_name]
        stage.status = StageStatus.FAILED
        stage.error = error
        stage.completed_at = datetime.now().isoformat()
        
        self.state.status = "failed"
        self.state.updated_at = datetime.now().isoformat()
        
        self._notify_listeners("stage_failed", {
            "task_id": self.state.task_id,
            "stage": stage_name,
            "error": error,
        })
        
        return True

    def _advance_to_next_stage(self):
        """Avança para o próximo estágio."""
        current_idx = self.STAGE_ORDER.index(self.state.current_stage)
        
        if current_idx + 1 < len(self.STAGE_ORDER):
            self.state.current_stage = self.STAGE_ORDER[current_idx + 1]
        else:
            self.state.current_stage = None
            self.state.status = "completed"
            self._notify_listeners("pipeline_completed", {
                "task_id": self.state.task_id,
            })

    def pause(self) -> bool:
        """Pausa o pipeline."""
        if self.state.status != "running":
            return False
        
        self.state.status = "paused"
        
        current = self.get_current_stage()
        if current and current.status == StageStatus.RUNNING:
            current.status = StageStatus.PAUSED
        
        self.state.updated_at = datetime.now().isoformat()
        self._notify_listeners("pipeline_paused", {"task_id": self.state.task_id})
        
        return True

    def resume(self) -> bool:
        """Retoma o pipeline."""
        if self.state.status != "paused":
            return False
        
        self.state.status = "running"
        
        current = self.get_current_stage()
        if current and current.status == StageStatus.PAUSED:
            current.status = StageStatus.RUNNING
        
        self.state.updated_at = datetime.now().isoformat()
        self._notify_listeners("pipeline_resumed", {"task_id": self.state.task_id})
        
        return True

    def stop(self) -> bool:
        """Para o pipeline."""
        self.state.status = "stopped"
        self.state.updated_at = datetime.now().isoformat()
        self._notify_listeners("pipeline_stopped", {"task_id": self.state.task_id})
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Converte estado para dicionário."""
        return {
            "task_id": self.state.task_id,
            "theme": self.state.theme,
            "channel_id": self.state.channel_id,
            "video_format": self.state.video_format,
            "status": self.state.status,
            "current_stage": self.state.current_stage,
            "stages": {
                name: {
                    "name": stage.name,
                    "status": stage.status.value,
                    "progress": stage.progress,
                    "data": stage.data,
                    "logs": stage.logs[-10:],
                    "started_at": stage.started_at,
                    "completed_at": stage.completed_at,
                    "error": stage.error,
                }
                for name, stage in self.state.stages.items()
            },
            "created_at": self.state.created_at,
            "updated_at": self.state.updated_at,
        }
