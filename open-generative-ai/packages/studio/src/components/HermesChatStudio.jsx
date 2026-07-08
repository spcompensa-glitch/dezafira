import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE_URL = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_API_URL || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : 'https://backend-production-fc8b.up.railway.app'))
  : 'https://backend-production-fc8b.up.railway.app';

export default function HermesChatStudio({ apiKey }) {
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Olá! Sou o Hermes, o cérebro orquestrador do Dezafira. Como posso ajudar?' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isHermesTyping, setIsHermesTyping] = useState(false);
  const [llmLogs, setLlmLogs] = useState([]);
  const [activeProvider, setActiveProvider] = useState('none');
  const chatBottomRef = useRef(null);

  useEffect(() => {
    fetchHermesHistory();
    fetchLLMLogs();
    const logsInterval = setInterval(fetchLLMLogs, 3000);
    return () => clearInterval(logsInterval);
  }, []);

  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isHermesTyping]);

  const fetchHermesHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/v1/hermes/history`);
      if (res.data.history) {
        setChatMessages(res.data.history);
      }
    } catch (err) {
      console.error('Erro ao buscar histórico:', err);
    }
  };

  const fetchLLMLogs = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/v1/llm/logs`);
      if (res.data.logs) {
        setLlmLogs(res.data.logs);
        if (res.data.active_provider) {
          setActiveProvider(res.data.active_provider);
        }
      }
    } catch (err) {
      // Endpoint pode não existir ainda
    }
  };

  const handleSendChatMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isHermesTyping) return;

    const userMsg = chatInput;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsHermesTyping(true);

    try {
      const res = await axios.post(`${API_BASE_URL}/api/v1/hermes/chat`, {
        message: userMsg
      });
      setChatMessages(res.data.history);
      if (res.data.active_provider) {
        setActiveProvider(res.data.active_provider);
      }
    } catch (err) {
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Desculpe, ocorreu um erro ao me comunicar com o servidor.' 
      }]);
    } finally {
      setIsHermesTyping(false);
    }
  };

  const handleClearChat = async () => {
    if (!confirm('Deseja iniciar uma nova conversa?')) return;
    try {
      const res = await axios.post(`${API_BASE_URL}/api/v1/hermes/clear`);
      setChatMessages(res.data.history);
    } catch (err) {
      alert('Falha ao reiniciar conversa.');
    }
  };

  const getProviderColor = (provider) => {
    switch(provider) {
      case 'nvidia': return 'text-green-400 bg-green-500/10';
      case 'deepseek': return 'text-blue-400 bg-blue-500/10';
      case 'openrouter': return 'text-purple-400 bg-purple-500/10';
      default: return 'text-white/40 bg-white/5';
    }
  };

  return (
    <div className="w-full h-full flex bg-[#050505] text-white overflow-hidden">
      {/* Chat Principal */}
      <div className="flex-1 flex flex-col h-full">
        {/* Header */}
        <div className="flex-shrink-0 p-4 border-b border-white/5 bg-[#0a0a0a]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Hermes</h2>
                <p className="text-[10px] text-white/40">Orquestrador Inteligente</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${getProviderColor(activeProvider)}`}>
                {activeProvider.toUpperCase()}
              </span>
              <button
                onClick={handleClearChat}
                className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                title="Nova conversa"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                  <path d="M3 3v5h5"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {chatMessages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[70%] p-3 rounded-2xl ${
                msg.role === 'user' 
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-br-none' 
                  : 'bg-white/5 text-white/90 rounded-bl-none border border-white/5'
              }`}>
                <p className="text-sm leading-relaxed">{msg.content}</p>
              </div>
            </div>
          ))}
          {isHermesTyping && (
            <div className="flex justify-start">
              <div className="bg-white/5 border border-white/5 rounded-2xl rounded-bl-none p-3 flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-white/40 rounded-full animate-bounce"></span>
                  <span className="w-2 h-2 bg-white/40 rounded-full animate-bounce delay-100"></span>
                  <span className="w-2 h-2 bg-white/40 rounded-full animate-bounce delay-200"></span>
                </div>
              </div>
            </div>
          )}
          <div ref={chatBottomRef} />
        </div>

        {/* Input */}
        <div className="flex-shrink-0 p-4 border-t border-white/5 bg-[#0a0a0a]">
          <form onSubmit={handleSendChatMessage} className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Digite sua mensagem..."
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus:border-cyan-500/50"
              disabled={isHermesTyping}
            />
            <button
              type="submit"
              disabled={isHermesTyping || !chatInput.trim()}
              className="bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-6 py-3 rounded-xl font-bold text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              Enviar
            </button>
          </form>
        </div>
      </div>

      {/* Painel LLM Logs */}
      <div className="w-80 border-l border-white/5 bg-[#0a0a0a] flex flex-col h-full">
        <div className="p-4 border-b border-white/5">
          <h3 className="text-sm font-bold text-white/80 flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            Logs LLM
          </h3>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {llmLogs.length > 0 ? (
            llmLogs.map((log, i) => (
              <div key={i} className="bg-white/5 rounded-lg p-2 text-[11px] border border-white/5">
                <div className="flex items-center justify-between mb-1">
                  <span className={`font-bold ${getProviderColor(log.provider).split(' ')[0]}`}>
                    {log.provider.toUpperCase()}
                  </span>
                  <span className="text-white/30">{log.time}</span>
                </div>
                <p className="text-white/60 truncate">{log.message}</p>
                {log.tokens && (
                  <span className="text-[9px] text-white/30">{log.tokens} tokens</span>
                )}
              </div>
            ))
          ) : (
            <div className="text-center text-white/30 text-xs py-8">
              Nenhum log ainda
            </div>
          )}
        </div>

        {/* Provider Status */}
        <div className="p-3 border-t border-white/5">
          <div className="text-[10px] font-bold text-white/40 mb-2 uppercase tracking-wider">Provedores</div>
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-white/60">NVIDIA</span>
              <span className="text-green-400 font-bold">Primary</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-white/60">DeepSeek</span>
              <span className="text-blue-400 font-bold">Fallback</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
