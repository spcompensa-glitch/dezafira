import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE_URL = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_API_URL || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : 'https://backend-production-fc8b.up.railway.app'))
  : 'https://backend-production-fc8b.up.railway.app';

export default function FactoryStudio({ apiKey }) {
  // Estados da Fábrica de Vídeos
  const [theme, setTheme] = useState('');
  const [dump, setDump] = useState('');
  const [postToYoutube, setPostToYoutube] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [status, setStatus] = useState('Pronto para iniciar.');
  const [videoUrl, setVideoUrl] = useState(null);
  
  // Pipeline de Automação
  const [currentStep, setCurrentStep] = useState(0); // 0: Inativo, 1: Trend Hunting, 2: Roteiro, 3: Narração, 4: Edição, 5: SEO, 6: Concluído
  const steps = [
    { name: 'Trend Hunting', desc: 'Minerando tendências virais e de alto CPM (Scrapling)' },
    { name: 'Roteirização', desc: 'Escrevendo roteiro autoral focado em retenção (Nvidia NIM API)' },
    { name: 'Clonagem de Voz', desc: 'Gerando locução de alta fidelidade via clonagem vocal (OmniVoice)' },
    { name: 'Avatar Falante', desc: 'Sincronizando lábio, cabeça e corpo do apresentador (InfiniteTalk)' },
    { name: 'Edição Visual', desc: 'Montando o corte 9:16 final de alto engajamento (MoviePy/LTX-2)' },
    { name: 'SEO & Publicação', desc: 'Upload seguro e estruturação de SEO (Playwright Stealth)' }
  ];

  // Estados de Canais
  const [channels, setChannels] = useState([]);
  const [chanName, setChanName] = useState('');
  const [chanNicho, setChanNicho] = useState('Geral');
  const [chanLang, setChanLang] = useState('PT');
  const [isAddingChannel, setIsAddingChannel] = useState(false);

  // Estados do Chat do Hermes
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Olá! Eu sou o Hermes, o agente orquestrador da Fábrica de Canais. Como posso te ajudar hoje?' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isHermesTyping, setIsHermesTyping] = useState(false);

  const [trends, setTrends] = useState([]);
  const [isLoadingTrends, setIsLoadingTrends] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState('default');
  const [frequency, setFrequency] = useState('daily');
  const [isAutopilot, setIsAutopilot] = useState(false);
  const [logs, setLogs] = useState([]);
  const [activeVideoTab, setActiveVideoTab] = useState('shorts');

  // Estados de Login Stealth do Agente (Dezafira)
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [loginMethod, setLoginMethod] = useState('cookies'); // 'cookies' ou 'credentials'
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginCookiesRaw, setLoginCookiesRaw] = useState('');
  const [loginVerificationCode, setLoginVerificationCode] = useState('');
  const [loginStatus, setLoginStatus] = useState('idle'); // idle, typing_email, typing_password, awaiting_2fa, connected, failed
  const [loginError, setLoginError] = useState(null);
  const loginPollingRef = useRef(null);

  // Estados dos Canais Criados por IA (Dezafira Autônoma)
  const [aiChannels, setAiChannels] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  const handleConnectYouTube = () => {
    if (selectedChannel === 'default') {
      alert('Por favor, selecione uma Conta Google cadastrada no painel antes de vincular.');
      return;
    }
    setLoginEmail('');
    setLoginPassword('');
    setLoginCookiesRaw('');
    setLoginVerificationCode('');
    setLoginStatus('idle');
    setLoginMethod('cookies');
    setLoginError(null);
    setIsLoginModalOpen(true);
  };

  const handleStartStealthLogin = async (e) => {
    e.preventDefault();
    if (!loginEmail.trim() || !loginPassword.trim()) {
      alert('Por favor, preencha o e-mail e a senha.');
      return;
    }
    setLoginStatus('typing_email');
    setLoginError(null);
    try {
      await axios.post(`${API_BASE_URL}/api/v1/channels/${selectedChannel}/login-stealth`, {
        email: loginEmail,
        password: loginPassword
      });
      
      // Inicia polling para monitorar status do robô
      startLoginStatusPolling();
    } catch (err) {
      console.error(err);
      setLoginStatus('failed');
      setLoginError('Falha ao iniciar o agente de login. Verifique se o backend está ativo.');
    }
  };

  const handleImportCookies = async (e) => {
    e.preventDefault();
    if (!loginCookiesRaw.trim()) {
      alert('Por favor, cole o JSON de cookies extraído do YouTube.');
      return;
    }
    if (loginPollingRef.current) clearInterval(loginPollingRef.current);
    setLoginStatus('importing_cookies');
    setLoginError(null);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/v1/channels/${selectedChannel}/login-stealth`, {
        cookies_raw: loginCookiesRaw
      });
      if (res.data.warning) {
        alert(res.data.warning);
      }
      setLoginStatus('connected');
      fetchChannels();
      setTimeout(() => {
        setIsLoginModalOpen(false);
      }, 3000);
    } catch (err) {
      console.error(err);
      setLoginStatus('failed');
      setLoginError(err.response?.data?.detail || 'Os cookies informados são inválidos ou expiraram.');
    }
  };

  const startLoginStatusPolling = () => {
    if (loginPollingRef.current) clearInterval(loginPollingRef.current);
    
    loginPollingRef.current = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/v1/channels/${selectedChannel}/connection-status`);
        const { connection_status, connection_error } = res.data;
        setLoginStatus(connection_status);
        
        if (connection_status === 'connected') {
          if (loginPollingRef.current) clearInterval(loginPollingRef.current);
          fetchChannels();
          setTimeout(() => {
            setIsLoginModalOpen(false);
          }, 2500);
        } else if (connection_status === 'failed') {
          if (loginPollingRef.current) clearInterval(loginPollingRef.current);
          setLoginError(connection_error || 'Falha no login do Google.');
        }
      } catch (err) {
        console.error('Erro de polling de login:', err);
      }
    }, 2000);
  };

  const handleSubmit2FA = async (e) => {
    e.preventDefault();
    if (!loginVerificationCode.trim()) return;
    try {
      await axios.post(`${API_BASE_URL}/api/v1/channels/${selectedChannel}/submit-2fa`, {
        code: loginVerificationCode
      });
      setLoginVerificationCode('');
      setLoginStatus('typing_password'); // Volta a mostrar carregamento enquanto processa
    } catch (err) {
      console.error(err);
      alert('Falha ao enviar código de verificação.');
    }
  };

  const handleToggleAutopilot = (e) => {
    const active = e.target.checked;
    setIsAutopilot(active);
    if (active) {
      setStatus(`Piloto automático Dezafira ATIVADO (${frequency === 'daily' ? 'Diário' : 'Alternado'}).`);
    } else {
      setStatus('Piloto automático desativado.');
    }
  };

  const renderMarkdown = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      if (line.startsWith('### ')) {
        return <h3 key={i} className="text-sm font-bold text-white mt-3 mb-1.5 uppercase tracking-wide">{line.replace('### ', '')}</h3>;
      }
      const boldRegex = /\*\*(.*?)\*\*/g;
      const parts = [];
      let lastIndex = 0;
      let match;
      while ((match = boldRegex.exec(line)) !== null) {
        parts.push(line.substring(lastIndex, match.index));
        parts.push(<strong key={match.index} className="text-primary font-bold">{match[1]}</strong>);
        lastIndex = boldRegex.lastIndex;
      }
      parts.push(line.substring(lastIndex));
      
      return <p key={i} className="text-xs text-white/70 leading-relaxed mb-2">{parts.length > 1 ? parts : line}</p>;
    });
  };

  const pollingIntervalRef = useRef(null);
  const chatBottomRef = useRef(null);

  // Inicialização e Carregamento
  useEffect(() => {
    fetchChannels();
    fetchHermesHistory();
    fetchTrends('Dropshipping');
    fetchLogs();
    const logsInterval = setInterval(fetchLogs, 2500);
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
      clearInterval(logsInterval);
    };
  }, []);

  const fetchLogs = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/v1/logs`);
      setLogs(res.data.logs || []);
    } catch (err) {
      console.error('Erro ao buscar logs:', err);
    }
  };

  // Rolar chat para o final ao receber novas mensagens
  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isHermesTyping]);

  const fetchTrends = async (nicho) => {
    setIsLoadingTrends(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/api/v1/trends?query=${nicho}`);
      setTrends(res.data);
    } catch (err) {
      console.error('Erro ao buscar tendências:', err);
    } finally {
      setIsLoadingTrends(false);
    }
  };

  const fetchChannels = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/v1/channels`);
      setChannels(res.data);
      
      const aiRes = await axios.get(`${API_BASE_URL}/api/v1/ai-channels`);
      setAiChannels(aiRes.data);
    } catch (err) {
      console.error('Erro ao buscar canais:', err);
    }
  };

  const fetchHermesHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/v1/hermes/history`);
      if (res.data.history) {
        setChatMessages(res.data.history);
      }
    } catch (err) {
      console.error('Erro ao buscar histórico do Hermes:', err);
    }
  };

  const handleAddChannel = async (e) => {
    e.preventDefault();
    if (!chanName.trim()) return;
    setIsAddingChannel(true);
    try {
      await axios.post(`${API_BASE_URL}/api/v1/channels`, {
        name: chanName,
        nicho: chanNicho,
        lang: chanLang
      });
      setChanName('');
      fetchChannels();
    } catch (err) {
      console.error('Erro ao cadastrar canal:', err);
    } finally {
      setIsAddingChannel(false);
    }
  };

  const handleDeleteChannel = async (id) => {
    if (!confirm('Deseja realmente remover este canal?')) return;
    try {
      await axios.delete(`${API_BASE_URL}/api/v1/channels/${id}`);
      fetchChannels();
    } catch (err) {
      console.error('Erro ao remover canal:', err);
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
        content: 'Desculpe, ocorreu um erro ao me comunicar com o servidor backend.' 
      }]);
    } finally {
      setIsHermesTyping(false);
    }
  };

  const handleClearChat = async () => {
    if (!confirm('Deseja iniciar uma nova conversa e limpar o histórico do Hermes?')) return;
    try {
      const res = await axios.post(`${API_BASE_URL}/api/v1/hermes/clear`);
      setChatMessages(res.data.history);
    } catch (err) {
      console.error(err);
      alert('Falha ao reiniciar conversa.');
    }
  };

  const pollResult = (predictionId) => {
    const url = `${API_BASE_URL}/api/v1/predictions/${predictionId}/result`;
    
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await axios.get(url);
        const data = response.data;
        const currentStatus = data.status?.toLowerCase();

        if (currentStatus === 'processing') {
          setStatus('Processando campanha...');
          setCurrentStep(2); // Entra na fase de roteiro
        } else if (currentStatus === 'uploading') {
          setStatus('Postando vídeo no YouTube Studio...');
          setCurrentStep(5); // Entra na fase de postagem
        } else if (currentStatus === 'completed') {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setStatus('Vídeo gerado e publicado com sucesso!');
          setCurrentStep(6); // Concluído
          setVideoUrl(`${API_BASE_URL}${data.url}`);
          setIsProcessing(false);
          fetchHermesHistory(); // Atualizar histórico de logs que o Hermes inseriu
        } else if (currentStatus === 'failed') {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setStatus(`Falha na renderização: ${data.error || 'Erro desconhecido'}`);
          setCurrentStep(0);
          setIsProcessing(false);
        }
      } catch (err) {
        console.error('Erro de polling:', err);
      }
    }, 3000);
  };

  const handleStartAutomation = async () => {
    if (!theme.trim()) {
      alert('Por favor, defina um tema para iniciar a automação.');
      return;
    }

    setIsProcessing(true);
    setStatus('Iniciando ciclo da esteira...');
    setCurrentStep(1); // Trend hunting / Preparação
    setVideoUrl(null);

    try {
      const payload = {
        prompt: theme,
        dump: dump,
        post_to_youtube: postToYoutube,
        channel_id: selectedChannel
      };

      const response = await axios.post(`${API_BASE_URL}/api/v1/predictions`, payload);
      setStatus('Iniciando roteirização e narração...');
      setCurrentStep(2);
      pollResult(response.data.id);
    } catch (err) {
      setStatus(`Erro: ${err.message || 'Falha ao conectar com o servidor.'}`);
      setIsProcessing(false);
      setCurrentStep(0);
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-app-bg text-white overflow-hidden p-6 md:p-8">
      <style>{`
        @keyframes rotate-border {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        .luxury-card {
          position: relative;
          background: rgba(10, 10, 10, 0.85) !important;
          border: 1px solid rgba(255, 255, 255, 0.05) !important;
          backdrop-filter: blur(16px);
          transition: all 0.3s ease;
        }
        .luxury-card:hover {
          border-color: rgba(30, 144, 255, 0.2) !important;
          box-shadow: 0 0 25px rgba(30, 144, 255, 0.1) !important;
        }
        .diamond-border-anim {
          position: relative;
          border: 1px solid transparent !important;
          background-image: linear-gradient(rgba(12, 12, 12, 0.95), rgba(12, 12, 12, 0.95)), 
                            linear-gradient(90deg, #00f2fe, #4facfe, #0000ff, #00f2fe);
          background-origin: border-box;
          background-clip: padding-box, border-box;
          background-size: 300% 300%;
          animation: rotate-border 8s infinite linear;
        }
        .zafira-text {
          background: linear-gradient(135deg, #00f2fe 0%, #4facfe 50%, #8b5cf6 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          text-shadow: 0 0 25px rgba(79, 172, 254, 0.2);
        }
        .chat-bubble-user {
          background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%) !important;
          color: #000000 !important;
          font-weight: 600;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 99px;
        }
      `}</style>
      {/* Title / Banner Executivo Dezafira */}
      <div className="w-full mb-6 bg-gradient-to-r from-primary/10 via-purple-500/5 to-transparent border border-white/5 rounded-3xl p-6 shadow-2xl relative overflow-hidden">
        <div className="absolute right-6 top-6 opacity-5 animate-pulse">
          <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div className="text-xs font-bold text-primary tracking-[0.2em] uppercase mb-1">PLATAFORMA DEZAFIRA</div>
        <h1 className="text-3xl md:text-5xl font-black tracking-tight text-white uppercase select-none">DEZAFIRA</h1>
        <p className="text-secondary text-sm opacity-60 mt-1">Automação Global & Foco em Monetização</p>
      </div>

      {/* Grid Ultrawide de 3 Colunas */}
      <div className="flex-1 w-full grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-y-auto lg:overflow-hidden custom-scrollbar pr-0 lg:pr-2">
        
        {/* COLUNA 1: Contas Google Conectadas */}
        <div className="flex flex-col gap-6 lg:h-full lg:overflow-y-auto custom-scrollbar pr-0 lg:pr-2">
          {/* Gerenciar Contas Google */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2">🔑 Contas Google</h3>
            
            {/* Lista de Contas com Status de Conexão */}
            <div className="flex flex-col gap-3 max-h-[220px] overflow-y-auto custom-scrollbar">
              {channels.map((chan) => (
                <div key={chan.id} className="flex flex-col bg-white/5 border border-white/5 rounded-xl p-3.5 gap-2.5 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${
                        chan.connection_status === 'connected' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-amber-500 animate-pulse'
                      }`} />
                      <div className="flex flex-col">
                        <span className="font-bold text-white/90">{chan.name}</span>
                        <span className="text-[10px] text-white/40">
                          {chan.connection_status === 'connected' ? 'Ativa (Sessão Salva)' : 'Aguardando Login 🔑'}
                        </span>
                      </div>
                    </div>
                    <button 
                      onClick={() => handleDeleteChannel(chan.id)}
                      className="text-white/30 hover:text-red-400 p-1 transition-colors"
                      title="Remover Conta"
                    >
                      ✕
                    </button>
                  </div>

                  {/* Detalhes de Erro se houver */}
                  {chan.connection_error && (
                    <div className="text-[10px] text-red-400 bg-red-500/5 border border-red-500/10 p-2 rounded-lg">
                      ⚠️ {chan.connection_error}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Vincular Nova Conta */}
            <form onSubmit={handleAddChannel} className="flex flex-col gap-2.5 pt-2 border-t border-white/5">
              <input
                type="email"
                value={chanName}
                onChange={(e) => setChanName(e.target.value)}
                placeholder="E-mail da Nova Conta Google..."
                className="bg-white/5 border border-white/10 rounded-lg p-2.5 text-xs text-white placeholder-white/30 focus:outline-none focus:border-primary/50"
                required
              />
              <div className="grid grid-cols-1">
                <button
                  type="submit"
                  disabled={isAddingChannel}
                  className="bg-primary hover:bg-[#1ed760] text-black text-xs font-bold py-2.5 rounded-lg transition-colors select-none"
                >
                  {isAddingChannel ? 'Registrando...' : 'Registrar Conta Google'}
                </button>
              </div>
            </form>
          </div>

          {/* Trendings (Mapeador Scrapling) */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex-1 flex flex-col gap-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2 flex items-center justify-between">
              <span>🔥 Trend Hunter (Scrapling)</span>
              {isLoadingTrends ? (
                <span className="text-[9px] text-primary animate-pulse">Garimpando...</span>
              ) : (
                <span className="text-[9px] bg-emerald-500/10 text-emerald-400 font-bold px-2 py-0.5 rounded-full">Ativo</span>
              )}
            </h3>
            
            <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-2 text-xs pr-1">
              {trends.length > 0 ? (
                trends.map((tr, idx) => (
                  <a
                    key={idx}
                    href={tr.link || '#'}
                    target={tr.link ? "_blank" : "_self"}
                    rel="noopener noreferrer"
                    className="bg-white/5 border-l-2 border-primary hover:bg-white/10 p-2.5 rounded-r-xl transition-all block group"
                  >
                    <div className="font-bold text-white/90 group-hover:text-primary transition-colors">{tr.title}</div>
                    <div className="text-[10px] text-white/40 mt-1">{tr.metric}</div>
                  </a>
                ))
              ) : (
                <div className="text-center text-white/35 py-8">Nenhuma tendência garimpada no momento.</div>
              )}
            </div>
          </div>

          {/* Console de Logs de Operação */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex-1 flex flex-col overflow-hidden min-h-[220px] luxury-card">
            <h3 className="text-xs font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
              <span>📂 Dezafira Console (Logs)</span>
            </h3>
            <div className="flex-1 overflow-y-auto custom-scrollbar my-3 font-mono text-[10px] text-emerald-400 bg-black/40 p-3 rounded-xl flex flex-col gap-1.5 min-h-[140px]">
              {logs.length > 0 ? (
                logs.map((logLine, idx) => (
                  <div key={idx} className="leading-relaxed border-b border-white/[0.02] pb-1">&gt; {logLine}</div>
                ))
              ) : (
                <div className="text-white/30 text-center py-8">Aguardando logs da esteira...</div>
              )}
            </div>
          </div>
        </div>

        {/* COLUNA 2: Fábrica Autônoma de Canais (Criação de Canais por IA) */}
        <div className="flex flex-col gap-6 lg:h-full lg:overflow-y-auto custom-scrollbar pr-0 lg:pr-2">
          {/* Canais Autônomos Criados por IA */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2">🤖 Canais Criados por IA</h3>
            
            <div className="flex flex-col gap-3 max-h-[350px] overflow-y-auto custom-scrollbar">
              {aiChannels.length > 0 ? (
                aiChannels.map((sub) => (
                  <div key={sub.id} className="flex flex-col bg-white/5 border border-white/5 rounded-xl p-3.5 gap-2.5 text-xs relative group animate-fade-in-up">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="bg-primary/10 text-[9px] font-black px-1.5 py-0.5 rounded text-primary">
                          {sub.lang}
                        </span>
                        <div className="flex flex-col">
                          <span className="font-bold text-white/90">{sub.name}</span>
                          <span className="text-[10px] text-white/40">{sub.nicho}</span>
                        </div>
                      </div>
                      <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded-full">
                        Ativo
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[10px] text-white/50 bg-black/20 p-2 rounded-lg">
                      <div className="flex flex-col">
                        <span className="text-[8px] uppercase tracking-wider text-white/30">Inscritos</span>
                        <span className="font-bold text-white/80">{sub.subscribers.toLocaleString()} 👥</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[8px] uppercase tracking-wider text-white/30">Vídeos Postados</span>
                        <span className="font-bold text-white/80">{sub.videos_posted} 🎬</span>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        setSelectedReport(sub);
                        setIsReportModalOpen(true);
                      }}
                      className="w-full mt-1 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-[10px] font-bold py-2 rounded-lg transition-all"
                    >
                      Ver Relatório Estratégico 📋
                    </button>
                  </div>
                ))
              ) : (
                <div className="text-center text-white/35 py-12 text-xs">
                  Nenhum canal autônomo criado ainda. Aguardando orquestração do Hermes...
                </div>
              )}
            </div>
          </div>

          {/* Chat do Hermes (NVIDIA NIM) */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex-1 flex flex-col overflow-hidden min-h-[280px]">
            <div className="flex flex-col gap-2 border-b border-white/5 pb-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold uppercase tracking-wider text-white/80">💬 Conversar com Hermes</h3>
                <span className="text-[9px] bg-primary/10 text-primary font-bold px-2 py-0.5 rounded-full">Nvidia NIM API</span>
              </div>
              {/* Botões de Conversa */}
              <div className="flex gap-2">
                <button
                  onClick={handleClearChat}
                  className="flex-1 bg-white/5 hover:bg-red-500/10 border border-white/10 hover:border-red-500/20 text-white/70 hover:text-red-400 text-[9px] font-bold py-1 rounded-lg transition-all"
                  title="Iniciar nova conversa do zero"
                >
                  🧹 Iniciar Nova Conversa
                </button>
                <button
                  onClick={fetchHermesHistory}
                  className="flex-1 bg-white/5 hover:bg-primary/10 border border-white/10 hover:border-primary/20 text-white/70 hover:text-primary text-[9px] font-bold py-1 rounded-lg transition-all"
                  title="Sincronizar histórico salvo"
                >
                  📂 Conversas Anteriores
                </button>
              </div>
            </div>
            
            {/* Corpo das Mensagens */}
            <div className="flex-1 overflow-y-auto custom-scrollbar my-3 space-y-3 pr-1 text-xs">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`max-w-[85%] p-3 rounded-2xl ${
                    msg.role === 'user' 
                      ? 'chat-bubble-user rounded-tr-none' 
                      : 'bg-white/5 text-white/80 rounded-tl-none border border-white/5'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isHermesTyping && (
                <div className="flex flex-col items-start">
                  <div className="bg-white/5 text-white/40 border border-white/5 rounded-2xl rounded-tl-none p-3 max-w-[80%] flex items-center gap-1.5 animate-pulse">
                    <span>Hermes está digitando</span>
                    <span className="flex gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-white/40 animate-bounce"></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-white/40 animate-bounce delay-100"></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-white/40 animate-bounce delay-200"></span>
                    </span>
                  </div>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Input do Chat */}
            <form onSubmit={handleSendChatMessage} className="flex gap-2 mt-auto">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ordene ao Hermes..."
                className="flex-1 bg-white/5 border border-white/10 rounded-xl p-2.5 text-xs text-white placeholder-white/30 focus:outline-none focus:border-primary/50"
                disabled={isHermesTyping}
              />
              <button
                type="submit"
                disabled={isHermesTyping || !chatInput.trim()}
                className="bg-primary text-black px-4 rounded-xl font-bold text-xs hover:scale-[1.02] hover:bg-[#1ed760] transition-all flex items-center justify-center"
              >
                Enviar
              </button>
            </form>
          </div>
        </div>

        {/* COLUNA 3: Galeria & Auto-SEO */}
        {/* COLUNA 3: Galeria & Auto-SEO */}
        <div className="flex flex-col gap-6 lg:h-full lg:overflow-y-auto custom-scrollbar pr-0 lg:pr-2">
          {/* Configuração Rápida & Lançamento */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col gap-4 luxury-card diamond-border-anim">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2 zafira-text">✍️ Gestão & Disparo</h3>
            
            <div className="flex flex-col gap-3.5">
              {/* Seleção de Conta Google e Conexão */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] font-bold text-white/40 tracking-widest uppercase">Conta Google Mãe</label>
                <div className="flex gap-2">
                  <select
                    value={selectedChannel}
                    onChange={(e) => setSelectedChannel(e.target.value)}
                    className="flex-1 bg-[#0c0c0c] border border-white/10 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-primary/50"
                    disabled={isProcessing}
                  >
                    <option value="default">Selecione a Conta Google...</option>
                    {channels.map((chan) => (
                      <option key={chan.id} value={chan.id}>
                        {chan.name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleConnectYouTube}
                    disabled={isProcessing}
                    className="bg-primary/15 hover:bg-primary/30 border border-primary/30 text-primary text-[10px] font-bold px-3 rounded-xl transition-all shadow-[0_0_10px_rgba(30,144,255,0.15)]"
                    title="Iniciar login interativo com o agente"
                  >
                    Vincular 🔑
                  </button>
                </div>
              </div>

              {/* Configurações de Frequência e Piloto Automático */}
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3.5 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white/80">Piloto Automático Dezafira</span>
                  <label className="relative inline-flex items-center cursor-pointer select-none">
                    <input 
                      type="checkbox" 
                      checked={isAutopilot}
                      onChange={handleToggleAutopilot}
                      className="sr-only peer" 
                    />
                    <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white/40 after:border-white/10 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[8px] font-bold text-white/40 tracking-widest uppercase">Frequência da Esteira</label>
                  <select
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="bg-[#0c0c0c] border border-white/10 rounded-lg p-2 text-xs text-white focus:outline-none"
                    disabled={!isAutopilot}
                  >
                    <option value="daily">Postagem Diária (Todo dia)</option>
                    <option value="alternate">Dia sim / Dia não (Alternado)</option>
                    <option value="weekly">Semanal (2x por semana)</option>
                  </select>
                </div>
                
                {isAutopilot && (
                  <div className="text-[9px] text-primary font-bold tracking-wider uppercase bg-primary/5 border border-primary/10 rounded px-2.5 py-1 text-center animate-pulse">
                    🔥 Agendamento Ativo no Servidor
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] font-bold text-white/40 tracking-widest uppercase">Tema do Vídeo</label>
                <input
                  type="text"
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  placeholder="Ex: 3 curiosidades sobre o universo"
                  className="bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-primary/50 transition-colors"
                  disabled={isProcessing}
                />
              </div>

              <div className="grid grid-cols-1 gap-3">
                <label className="flex items-center gap-2 cursor-pointer select-none text-xs font-semibold text-white/80 my-1">
                  <input
                    type="checkbox"
                    checked={postToYoutube}
                    onChange={(e) => setPostToYoutube(e.target.checked)}
                    className="rounded bg-white/5 border-white/10 text-primary focus:ring-0"
                    disabled={isProcessing}
                  />
                  Postar automaticamente no YouTube (Playwright)
                </label>
              </div>

              <button
                onClick={handleStartAutomation}
                disabled={isProcessing}
                className={`w-full py-3.5 rounded-xl font-black uppercase text-xs tracking-widest transition-all flex items-center justify-center gap-2 ${
                  isProcessing
                    ? 'bg-white/10 text-white/40 cursor-not-allowed'
                    : 'bg-primary text-black hover:scale-[1.02] hover:bg-[#1ed760] shadow-[0_0_15px_rgba(34,211,238,0.2)]'
                }`}
              >
                <span>{isProcessing ? 'Executando Automação...' : 'Iniciar Ciclo ✨'}</span>
              </button>
            </div>
          </div>

          {/* Vídeo Gerado & Visualizador Avançado */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex-1 flex flex-col gap-4">
            <div className="flex flex-col gap-2 border-b border-white/5 pb-2">
              <h3 className="text-sm font-bold uppercase tracking-wider text-white/80">🎬 Visualizador de Conteúdo</h3>
              {/* Abas Diamante */}
              <div className="flex bg-black/40 border border-white/5 p-1 rounded-xl">
                <button
                  onClick={() => setActiveVideoTab('shorts')}
                  className={`flex-1 text-[10px] font-bold py-1.5 rounded-lg transition-all ${
                    activeVideoTab === 'shorts' ? 'bg-primary text-black' : 'text-white/40 hover:text-white'
                  }`}
                >
                  Shorts (9:16)
                </button>
                <button
                  onClick={() => setActiveVideoTab('horizontal')}
                  className={`flex-1 text-[10px] font-bold py-1.5 rounded-lg transition-all ${
                    activeVideoTab === 'horizontal' ? 'bg-primary text-black' : 'text-white/40 hover:text-white'
                  }`}
                >
                  Horizontal (16:9)
                </button>
              </div>
            </div>

            <div className={`w-full bg-black/40 border border-white/5 rounded-xl flex items-center justify-center relative overflow-hidden transition-all duration-300 ${
              activeVideoTab === 'shorts' ? 'aspect-[9/16] max-h-[320px]' : 'aspect-[16/9] max-h-[220px]'
            }`}>
              {videoUrl ? (
                activeVideoTab === 'shorts' ? (
                  <video
                    src={videoUrl}
                    className="w-full h-full object-cover"
                    controls
                    autoPlay
                  />
                ) : (
                  <video
                    src={videoUrl}
                    className="w-full h-full object-contain"
                    controls
                    autoPlay
                  />
                )
              ) : (
                <div className="flex flex-col items-center gap-3 text-white/30 text-xs font-bold uppercase tracking-widest p-4 text-center">
                  <svg width="35" height="35" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="opacity-30">
                    <rect x="2" y="2" width="20" height="20" rx="4"/>
                    <path d="M12 18V6l-5 4 5-4 5 4"/>
                  </svg>
                  <span>{isProcessing ? 'Renderizando formato...' : 'Aguardando Geração'}</span>
                </div>
              )}
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-xs font-medium text-white/60">
              Status: {status}
            </div>
          </div>
        </div>

      </div>

      {/* MODAL DE LOGIN ASSISTIDO POR AGENTE (DEZAFIRA STEALTH) */}
      {isLoginModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="w-full max-w-md bg-[#0a0a0a] border border-white/10 rounded-3xl p-6 shadow-2xl flex flex-col gap-5 relative">
            <button 
              onClick={() => {
                if (loginPollingRef.current) clearInterval(loginPollingRef.current);
                setIsLoginModalOpen(false);
              }}
              className="absolute right-4 top-4 text-white/40 hover:text-white transition-all text-lg font-bold"
            >
              ✕
            </button>

            <div className="flex flex-col gap-1">
              <h2 className="text-lg font-bold text-white">Vincular Conta Google 🔑</h2>
              <p className="text-[10px] text-white/50">Ative o acesso seguro de postagem no YouTube.</p>
            </div>

            {loginStatus === 'idle' && (
              <div className="flex flex-col gap-4">
                {/* Abas */}
                <div className="flex bg-black/40 border border-white/5 p-1 rounded-xl">
                  <button
                    onClick={() => setLoginMethod('cookies')}
                    className={`flex-1 text-[10px] font-bold py-2 rounded-lg transition-all ${
                      loginMethod === 'cookies' ? 'bg-primary text-black' : 'text-white/40 hover:text-white'
                    }`}
                  >
                    Importar Cookies ⚡
                  </button>
                  <button
                    onClick={() => setLoginMethod('credentials')}
                    className={`flex-1 text-[10px] font-bold py-2 rounded-lg transition-all ${
                      loginMethod === 'credentials' ? 'bg-primary text-black' : 'text-white/40 hover:text-white'
                    }`}
                  >
                    Digitar E-mail/Senha
                  </button>
                </div>

                {loginMethod === 'cookies' ? (
                  <form onSubmit={handleImportCookies} className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <label className="text-[9px] font-bold text-white/40 tracking-widest uppercase">Colar Cookies (JSON)</label>
                        <span className="text-[8px] text-primary/70 font-semibold">100% de Sucesso na Nuvem</span>
                      </div>
                      <textarea
                        value={loginCookiesRaw}
                        onChange={(e) => setLoginCookiesRaw(e.target.value)}
                        required
                        rows="5"
                        placeholder='[{"name": "SID", "value": "xxxx", "domain": ".youtube.com"}, ...]'
                        className="bg-black border border-white/10 rounded-xl p-3 text-[10px] font-mono text-white focus:outline-none focus:border-primary/50 custom-scrollbar"
                      />
                    </div>
                    <div className="text-[9px] text-white/40 leading-relaxed bg-white/[0.02] border border-white/5 p-3 rounded-xl">
                      💡 <strong>Dica</strong>: Acesse o YouTube Studio, clique em uma extensão como a <em>EditThisCookie</em> ou <em>Get cookies.txt</em> no seu Chrome, exporte os cookies em formato JSON e cole-os no campo acima!
                    </div>
                    <button
                      type="submit"
                      className="w-full bg-primary hover:bg-[#1ed760] text-black text-xs font-bold p-3 rounded-xl transition-all shadow-lg shadow-primary/10"
                    >
                      Importar Cookies
                    </button>
                  </form>
                ) : (
                  <form onSubmit={handleStartStealthLogin} className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] font-bold text-white/40 tracking-widest uppercase">E-mail do Google</label>
                      <input
                        type="email"
                        value={loginEmail}
                        onChange={(e) => setLoginEmail(e.target.value)}
                        required
                        className="bg-black border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-red-500/50"
                        placeholder="exemplo@gmail.com"
                      />
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] font-bold text-white/40 tracking-widest uppercase">Senha do Google</label>
                      <input
                        type="password"
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        required
                        className="bg-black border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-red-500/50"
                        placeholder="Sua senha"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-red-600 hover:bg-red-500 text-white text-xs font-bold p-3 rounded-xl transition-all shadow-lg shadow-red-600/10"
                    >
                      Conectar Conta
                    </button>
                  </form>
                )}
              </div>
            )}

            {(loginStatus === 'typing_email' || loginStatus === 'typing_password' || loginStatus === 'importing_cookies') && (
              <div className="flex flex-col items-center justify-center py-8 gap-4 text-center">
                <div className="w-10 h-10 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                <div className="flex flex-col gap-1 w-full">
                  <span className="text-xs font-bold text-white">
                    {loginStatus === 'importing_cookies' ? 'Validando Sessão com Robô 🤖' : 'Agente conectando ao Google...'}
                  </span>
                  <span className="text-[10px] text-white/40">
                    {loginStatus === 'importing_cookies' 
                      ? 'Dezafira abrindo o Chrome em background e verificando acesso ao Studio...'
                      : loginStatus === 'typing_email' ? 'Digitando e-mail de acesso...' : 'Digitando credencial de senha...'}
                  </span>
                  {loginStatus === 'importing_cookies' && (
                    <div className="mt-3 text-left font-mono text-[9px] text-white/30 bg-black/40 border border-white/5 p-3 rounded-lg flex flex-col gap-1">
                      <div>&gt; Iniciando navegador Chromium Headless...</div>
                      <div>&gt; Injetando cookies de segurança...</div>
                      <div>&gt; Carregando studio.youtube.com...</div>
                      <div className="animate-pulse">&gt; Aguardando resposta do painel...</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {loginStatus === 'awaiting_2fa' && (
              <form onSubmit={handleSubmit2FA} className="flex flex-col gap-4">
                <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-3 text-center text-xs font-medium text-yellow-400">
                  ⚠️ Google exige Verificação em Duas Etapas!
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] font-bold text-white/40 tracking-widest uppercase">Código de Verificação (SMS / App)</label>
                  <input 
                    type="text" 
                    value={loginVerificationCode}
                    onChange={(e) => setLoginVerificationCode(e.target.value)}
                    required
                    className="bg-black border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-yellow-500/50 text-center font-bold tracking-widest"
                    placeholder="Digite o código (ex: G-123456)"
                  />
                </div>

                <button 
                  type="submit"
                  className="w-full bg-gradient-to-r from-yellow-500 to-amber-500 text-black text-xs font-bold p-3 rounded-xl transition-all shadow-lg shadow-yellow-500/10"
                >
                  Confirmar Código 2FA
                </button>
              </form>
            )}

            {loginStatus === 'connected' && (
              <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
                <div className="w-12 h-12 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full flex items-center justify-center text-xl font-bold animate-pulse">
                  ✓
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-bold text-white">Canal Vinculado!</span>
                  <span className="text-[10px] text-green-400/70 font-semibold">Sessão salva com segurança na Dezafira.</span>
                </div>
              </div>
            )}

            {loginStatus === 'failed' && (
              <div className="flex flex-col gap-4 text-center py-2">
                <div className="text-red-500/80 border border-red-500/20 bg-red-500/5 rounded-xl p-3 text-xs font-medium">
                  {loginError || 'Ocorreu um erro ao conectar ao canal.'}
                </div>
                <button 
                  onClick={() => setLoginStatus('idle')}
                  className="w-full bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-bold p-3 rounded-xl transition-all"
                >
                  Tentar Novamente
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL DE RELATÓRIO ESTRATÉGICO DA IA */}
      {isReportModalOpen && selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="w-full max-w-lg bg-[#0a0a0a] border border-white/10 rounded-3xl p-6 shadow-2xl flex flex-col gap-4 relative">
            <button 
              onClick={() => {
                setIsReportModalOpen(false);
                setSelectedReport(null);
              }}
              className="absolute right-4 top-4 text-white/40 hover:text-white transition-all text-lg font-bold"
            >
              ✕
            </button>

            <div className="flex flex-col gap-1 border-b border-white/5 pb-3">
              <span className="text-[9px] font-bold text-primary uppercase tracking-widest">Análise de Mercado autônoma</span>
              <h2 className="text-lg font-black text-white">{selectedReport.name}</h2>
            </div>

            <div className="max-h-[300px] overflow-y-auto custom-scrollbar pr-2">
              {renderMarkdown(selectedReport.creation_reason)}
            </div>

            <div className="flex gap-2.5 pt-2 border-t border-white/5 mt-2">
              <button 
                onClick={() => {
                  setIsReportModalOpen(false);
                  setSelectedReport(null);
                }}
                className="flex-1 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-bold p-3 rounded-xl transition-all"
              >
                Fechar Relatório
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
