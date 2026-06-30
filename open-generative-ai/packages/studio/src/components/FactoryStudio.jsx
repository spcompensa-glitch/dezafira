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

  // Estados de Login Stealth do Agente (Dezafira)
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginVerificationCode, setLoginVerificationCode] = useState('');
  const [loginStatus, setLoginStatus] = useState('idle'); // idle, typing_email, typing_password, awaiting_2fa, connected, failed
  const [loginError, setLoginError] = useState(null);
  const loginPollingRef = useRef(null);

  const handleConnectYouTube = () => {
    if (selectedChannel === 'default') {
      alert('Por favor, selecione um canal cadastrado para conectar.');
      return;
    }
    setLoginEmail('');
    setLoginPassword('');
    setLoginVerificationCode('');
    setLoginStatus('idle');
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

  const pollingIntervalRef = useRef(null);
  const chatBottomRef = useRef(null);

  // Inicialização e Carregamento
  useEffect(() => {
    fetchChannels();
    fetchHermesHistory();
    fetchTrends('Dropshipping');
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

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
        
        {/* COLUNA 1: Canais & Tendências */}
        <div className="flex flex-col gap-6 lg:h-full lg:overflow-y-auto custom-scrollbar pr-0 lg:pr-2">
          {/* Gerenciar Canais */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2">🌐 Canais Ativos</h3>
            
            {/* Lista de Canais com Status de Monetização */}
            <div className="flex flex-col gap-3 max-h-[220px] overflow-y-auto custom-scrollbar">
              {channels.map((chan) => (
                <div key={chan.id} className="flex flex-col bg-white/5 border border-white/5 rounded-xl p-3.5 gap-2.5 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="bg-white/10 text-[9px] font-black px-1.5 py-0.5 rounded text-primary">
                        {chan.lang}
                      </span>
                      <div className="flex flex-col">
                        <span className="font-bold text-white/90">{chan.name}</span>
                        <span className="text-[10px] text-white/40">{chan.nicho}</span>
                      </div>
                    </div>
                    <button 
                      onClick={() => handleDeleteChannel(chan.id)}
                      className="text-white/30 hover:text-red-400 p-1 transition-colors"
                    >
                      ✕
                    </button>
                  </div>

                  {/* Barra de Progresso de Monetização */}
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center justify-between text-[9px] font-bold uppercase tracking-wider text-white/45">
                      <span>Mapeamento</span>
                      <span className={
                        chan.monetization_step === 'monetized' ? 'text-emerald-400 animate-pulse font-black' : 'text-white/60'
                      }>
                        {chan.monetization_step === 'setup' && 'Setup ⚙️'}
                        {chan.monetization_step === 'linked' && 'Vinculado 🔗'}
                        {chan.monetization_step === 'publishing' && 'Postagens 📈'}
                        {chan.monetization_step === 'viral' && 'Viralizando 🔥'}
                        {chan.monetization_step === 'monetized' && 'Monetizado 💰'}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${
                          chan.monetization_step === 'setup' ? 'w-[20%] bg-rose-500' :
                          chan.monetization_step === 'linked' ? 'w-[40%] bg-blue-500' :
                          chan.monetization_step === 'publishing' ? 'w-[60%] bg-purple-500' :
                          chan.monetization_step === 'viral' ? 'w-[80%] bg-cyan-500 shadow-[0_0_8px_rgba(34,211,238,0.5)]' :
                          'w-[100%] bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]'
                        }`}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Cadastro de Canais */}
            <form onSubmit={handleAddChannel} className="flex flex-col gap-2.5 pt-2 border-t border-white/5">
              <input
                type="text"
                value={chanName}
                onChange={(e) => setChanName(e.target.value)}
                placeholder="Nome do Novo Canal..."
                className="bg-white/5 border border-white/10 rounded-lg p-2.5 text-xs text-white placeholder-white/30 focus:outline-none focus:border-primary/50"
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={chanNicho}
                  onChange={(e) => setChanNicho(e.target.value)}
                  className="bg-[#0c0c0c] border border-white/10 rounded-lg p-2 text-xs text-white/80"
                >
                  <option value="Geral">Geral</option>
                  <option value="Dropshipping">Dropshipping</option>
                  <option value="Cripto">Finanças</option>
                </select>
                <select
                  value={chanLang}
                  onChange={(e) => setChanLang(e.target.value)}
                  className="bg-[#0c0c0c] border border-white/10 rounded-lg p-2 text-xs text-white/80"
                >
                  <option value="PT">PT (Português)</option>
                  <option value="EN">EN (Inglês)</option>
                  <option value="ES">ES (Espanhol)</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={isAddingChannel}
                className="w-full py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold transition-all text-white/90"
              >
                Cadastrar Canal
              </button>
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
        </div>

        {/* COLUNA 2: Hermes (O Cérebro & Chat) */}
        <div className="flex flex-col gap-6 lg:h-full overflow-hidden">
          {/* Chat do Hermes (NVIDIA NIM) */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex-1 flex flex-col overflow-hidden min-h-[350px]">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2 flex items-center justify-between">
              <span>💬 Conversar com Hermes</span>
              <span className="text-[9px] bg-primary/10 text-primary font-bold px-2 py-0.5 rounded-full">Nvidia NIM API</span>
            </h3>
            
            {/* Corpo das Mensagens */}
            <div className="flex-1 overflow-y-auto custom-scrollbar my-4 space-y-3 pr-1 text-xs">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`max-w-[85%] p-3 rounded-2xl ${
                    msg.role === 'user' 
                      ? 'bg-primary text-black rounded-tr-none font-semibold' 
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
            <form onSubmit={handleSendChatMessage} className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Pergunte ou ordene ao Hermes..."
                className="flex-1 bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white placeholder-white/30 focus:outline-none focus:border-primary/50"
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

          {/* Pipeline Neon de Status */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col gap-3">
            <h3 className="text-xs font-bold uppercase tracking-widest text-white/40">Fase Atual da Esteira</h3>
            
            <div className="grid grid-cols-6 gap-1 relative pt-2">
              {steps.map((step, index) => {
                const isActive = currentStep === index + 1;
                const isCompleted = currentStep > index + 1;
                return (
                  <div key={index} className="flex flex-col items-center text-center gap-1 relative z-10">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black border transition-all ${
                      isActive 
                        ? 'bg-primary border-primary text-black shadow-[0_0_12px_rgba(34,211,238,0.6)]' 
                        : isCompleted
                        ? 'bg-[#1ed760]/20 border-[#1ed760] text-[#1ed760]'
                        : 'bg-black border-white/10 text-white/30'
                    }`}>
                      {index + 1}
                    </div>
                    <span className={`text-[8px] font-bold uppercase tracking-wider hidden sm:block ${
                      isActive ? 'text-primary' : 'text-white/30'
                    }`}>
                      {step.name}
                    </span>
                  </div>
                );
              })}
            </div>
            
            {currentStep > 0 && currentStep <= 6 && (
              <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-[10px] text-white/60 text-center font-bold uppercase tracking-wider animate-pulse">
                ⚙️ {steps[currentStep - 1].desc}
              </div>
            )}
          </div>
        </div>

        {/* COLUNA 3: Galeria & Auto-SEO */}
        <div className="flex flex-col gap-6 lg:h-full lg:overflow-y-auto custom-scrollbar pr-0 lg:pr-2">
          {/* Configuração Rápida & Lançamento */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2">✍️ Gestão & Disparo</h3>
            
            <div className="flex flex-col gap-3.5">
              {/* Seleção do Canal e Conexão */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] font-bold text-white/40 tracking-widest uppercase">Canal de Destino</label>
                <div className="flex gap-2">
                  <select
                    value={selectedChannel}
                    onChange={(e) => setSelectedChannel(e.target.value)}
                    className="flex-1 bg-[#0c0c0c] border border-white/10 rounded-xl p-2.5 text-xs text-white focus:outline-none"
                    disabled={isProcessing}
                  >
                    <option value="default">Canal Padrão (Default)</option>
                    {channels.map((chan) => (
                      <option key={chan.id} value={chan.id}>
                        {chan.name} ({chan.lang})
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleConnectYouTube}
                    disabled={isProcessing}
                    className="bg-red-600/10 hover:bg-red-600/20 border border-red-500/20 text-red-400 text-[10px] font-bold px-3 rounded-xl transition-all"
                    title="Conectar canal logando no YouTube Studio"
                  >
                    Conectar 🔑
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

          {/* Vídeo Gerado & Status de SEO */}
          <div className="bg-[#0c0c0c] border border-white/5 rounded-2xl p-5 shadow-2xl flex-1 flex flex-col gap-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white/80 border-b border-white/5 pb-2">🎬 Último Vídeo Renderizado</h3>
            
            <div className="w-full aspect-[9/16] max-h-[300px] bg-black/40 border border-white/5 rounded-xl flex items-center justify-center relative overflow-hidden">
              {videoUrl ? (
                <video
                  src={videoUrl}
                  className="w-full h-full object-cover"
                  controls
                  autoPlay
                />
              ) : (
                <div className="flex flex-col items-center gap-3 text-white/30 text-xs font-bold uppercase tracking-widest p-4 text-center">
                  <svg width="35" height="35" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="opacity-30">
                    <rect x="2" y="2" width="20" height="20" rx="4"/>
                    <path d="M12 18V6l-5 4 5-4 5 4"/>
                  </svg>
                  <span>{isProcessing ? 'Renderizando corte...' : 'Aguardando Geração'}</span>
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
              <h2 className="text-lg font-bold text-white">Vincular Canal 🔑</h2>
              <p className="text-[10px] text-white/50">Login direto e seguro por agente de simulação.</p>
            </div>

            {loginStatus === 'idle' && (
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
                  Conectar Canal
                </button>
              </form>
            )}

            {(loginStatus === 'typing_email' || loginStatus === 'typing_password') && (
              <div className="flex flex-col items-center justify-center py-8 gap-4 text-center">
                <div className="w-10 h-10 border-2 border-red-500/20 border-t-red-500 rounded-full animate-spin"></div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-bold text-white">Agente conectando ao Google...</span>
                  <span className="text-[10px] text-white/40">
                    {loginStatus === 'typing_email' ? 'Digitando e-mail de acesso...' : 'Digitando credencial de senha...'}
                  </span>
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
    </div>
  );
}
