"use client";
import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function MissionControl() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/v1/factory/monitor-stats');
        setStats(res.data);
      } catch (err) {
        console.error("Erro ao consultar o Mission Control:", err);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 3000); // Atualiza a cada 3 segundos
    return () => clearInterval(interval);
  }, []);

  if (!stats) return <p style={{ padding: '20px', color: '#fff' }}>Carregando Central de Controle...</p>;

  return (
    <div style={{ padding: '40px', background: '#0f172a', color: '#fff', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <h2 style={{ fontSize: '28px', marginBottom: '20px', fontWeight: 'bold' }}>🛸 Dezafira Mission Control</h2>
      
      {/* Contadores do topo */}
      <div style={{ display: 'flex', gap: '20px', marginBottom: '40px' }}>
        <div style={{ background: '#1e293b', padding: '25px', borderRadius: '12px', flex: 1, boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <h3 style={{ margin: 0, color: '#94a3b8', fontSize: '14px', textTransform: 'uppercase' }}>Na Fila (Triage)</h3>
          <p style={{ margin: '10px 0 0 0', fontSize: '36px', fontWeight: 'bold', color: '#6366f1' }}>{stats.total_queued}</p>
        </div>
        <div style={{ background: '#1e293b', padding: '25px', borderRadius: '12px', flex: 1, boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <h3 style={{ margin: 0, color: '#94a3b8', fontSize: '14px', textTransform: 'uppercase' }}>Processando (Esteira Ativa)</h3>
          <p style={{ margin: '10px 0 0 0', fontSize: '36px', fontWeight: 'bold', color: '#eab308' }}>{stats.total_processing}</p>
        </div>
        <div style={{ background: '#1e293b', padding: '25px', borderRadius: '12px', flex: 1, boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <h3 style={{ margin: 0, color: '#94a3b8', fontSize: '14px', textTransform: 'uppercase' }}>Prontos para Revisão</h3>
          <p style={{ margin: '10px 0 0 0', fontSize: '36px', fontWeight: 'bold', color: '#22c55e' }}>{stats.total_ready}</p>
        </div>
      </div>

      {/* Monitor do Enxame Ativo */}
      <h3 style={{ fontSize: '20px', marginBottom: '15px' }}>🤖 Agentes em Ação</h3>
      <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
        {stats.active_tasks.length === 0 ? (
          <p style={{ color: '#94a3b8', margin: 0 }}>Nenhum agente processando no momento. Fábrica ociosa.</p>
        ) : (
          stats.active_tasks.map((task) => (
            <div key={task.id} style={{ borderBottom: '1px solid #334155', padding: '15px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ color: '#e2e8f0' }}>Task #{task.id}</strong>
                <span style={{ color: '#94a3b8', marginLeft: '10px' }}>- Sugestão: {task.title_suggestion || "Aguardando definição..."}</span>
              </div>
              <span style={{
                padding: '6px 12px', 
                borderRadius: '6px', 
                background: task.status === 'writing' ? '#854d0e' : (task.status === 'SEO' ? '#0f766e' : '#1e1b4b'),
                color: '#fff',
                fontSize: '12px',
                fontWeight: 'bold',
                letterSpacing: '0.05em'
              }}>
                {task.status.toUpperCase()}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
