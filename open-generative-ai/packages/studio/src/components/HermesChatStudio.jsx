import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE_URL = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_API_URL || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : 'https://backend-production-fc8b.up.railway.app'))
  : 'https://backend-production-fc8b.up.railway.app';

export default function HermesChatStudio({ apiKey }) {
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Olá! Sou o Hermes, o orquestrador da DEZAFIRA. Controlo a fábrica de vídeos, canais YouTube e miniapps. O que deseja produzir?' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isHermesTyping, setIsHermesTyping] = useState(false);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    fetchHermesHistory();
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
    } catch (err) {
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Erro ao comunicar com o servidor.' 
      }]);
    } finally {
      setIsHermesTyping(false);
    }
  };

  const handleClearChat = async () => {
    if (!confirm('Iniciar nova conversa?')) return;
    try {
      const res = await axios.post(`${API_BASE_URL}/api/v1/hermes/clear`);
      setChatMessages(res.data.history);
    } catch (err) {
      alert('Falha ao reiniciar.');
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#050505] text-white">
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
              <p className="text-[10px] text-white/40">Orquestrador DEZAFIRA</p>
            </div>
          </div>
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatMessages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[70%] p-3 rounded-2xl ${
              msg.role === 'user' 
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-br-none' 
                : 'bg-white/5 text-white/90 rounded-bl-none border border-white/5'
            }`}>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
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
            placeholder="Comando para o Hermes..."
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
  );
}
