"""
WebSocket Hub
Hub central para comunicação em tempo real.
"""
import asyncio
import json
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket


class WebSocketHub:
    """
    Hub central para gerenciar conexões WebSocket.
    
    Permite broadcast de atualizações para todos os clientes conectados.
    """

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._global_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, task_id: str = None):
        """
        Conecta um novo cliente WebSocket.
        
        Args:
            websocket: Conexão WebSocket
            task_id: ID da tarefa (opcional)
        """
        await websocket.accept()
        
        if task_id:
            if task_id not in self._connections:
                self._connections[task_id] = set()
            self._connections[task_id].add(websocket)
            print(f"[WebSocket] Cliente conectado para task: {task_id}")
        else:
            self._global_connections.add(websocket)
            print("[WebSocket] Cliente global conectado")

    def disconnect(self, websocket: WebSocket, task_id: str = None):
        """
        Desconecta um cliente.
        
        Args:
            websocket: Conexão WebSocket
            task_id: ID da tarefa (opcional)
        """
        if task_id and task_id in self._connections:
            self._connections[task_id].discard(websocket)
            if not self._connections[task_id]:
                del self._connections[task_id]
            print(f"[WebSocket] Cliente desconectado de task: {task_id}")
        else:
            self._global_connections.discard(websocket)
            print("[WebSocket] Cliente global desconectado")

    async def broadcast(self, event_type: str, data: Dict[str, Any], task_id: str = None):
        """
        Envia mensagem para todos os clientes conectados.
        
        Args:
            event_type: Tipo do evento
            data: Dados do evento
            task_id: ID da tarefa (opcional)
        """
        message = json.dumps({
            "type": event_type,
            "data": data,
        })
        
        targets = set()
        
        if task_id and task_id in self._connections:
            targets.update(self._connections[task_id])
        
        targets.update(self._global_connections)
        
        disconnected = set()
        for connection in targets:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"[WebSocket] Erro ao enviar mensagem: {e}")
                disconnected.add(connection)
        
        for conn in disconnected:
            self._global_connections.discard(conn)
            for tid in list(self._connections.keys()):
                self._connections[tid].discard(conn)

    async def send_to_task(self, task_id: str, event_type: str, data: Dict[str, Any]):
        """
        Envia mensagem apenas para clientes de uma tarefa específica.
        
        Args:
            task_id: ID da tarefa
            event_type: Tipo do evento
            data: Dados do evento
        """
        await self.broadcast(event_type, data, task_id)

    def get_connected_clients(self, task_id: str = None) -> int:
        """
        Retorna número de clientes conectados.
        
        Args:
            task_id: ID da tarefa (opcional)
            
        Returns:
            Número de clientes conectados
        """
        if task_id:
            return len(self._connections.get(task_id, set()))
        return len(self._global_connections)

    def get_all_tasks(self) -> list:
        """Retorna lista de todas as tasks com conexões."""
        return list(self._connections.keys())
