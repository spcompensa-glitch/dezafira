import { t } from '../lib/i18n.js';

export function FactoryStudio() {
    const container = document.createElement('div');
    container.className = 'w-full h-full flex flex-col bg-app-bg text-white overflow-y-auto p-6 md:p-8 custom-scrollbar';

    // 1. Header da Página
    const header = document.createElement('div');
    header.className = 'w-full max-w-6xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8';
    header.innerHTML = `
        <div>
            <div class="text-xs font-bold text-primary tracking-[0.2em] uppercase mb-1">AUTOMATION ENGINE</div>
            <h1 class="text-3xl md:text-5xl font-black tracking-tight text-white uppercase select-none">Fábrica de Canais</h1>
            <p class="text-secondary text-sm opacity-60">Gere roteiros, narração, legendagem dinâmica e publique no YouTube automaticamente.</p>
        </div>
    `;
    container.appendChild(header);

    // 2. Grid Central
    const mainGrid = document.createElement('div');
    mainGrid.className = 'w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-5 gap-8';
    container.appendChild(mainGrid);

    // 2.1 Coluna da Esquerda (Formulário de Entrada) - Ocupa 3/5 da largura
    const formCol = document.createElement('div');
    formCol.className = 'lg:col-span-3 flex flex-col gap-6';
    mainGrid.appendChild(formCol);

    // Card de Briefing
    const cardBriefing = document.createElement('div');
    cardBriefing.className = 'bg-[#141414] border border-white/5 rounded-3xl p-6 shadow-2xl flex flex-col gap-4';
    cardBriefing.innerHTML = `
        <h3 class="text-lg font-bold text-white tracking-wide">✍️ Configurar Vídeo</h3>
        <div class="flex flex-col gap-2">
            <label class="text-[10px] font-bold text-white/40 tracking-widest uppercase">Tema Principal do Vídeo</label>
            <textarea id="factory-theme" class="w-full bg-white/5 border border-white/10 rounded-xl p-4 text-white text-sm focus:outline-none focus:border-primary/50 transition-colors resize-none" rows="3" placeholder="Sobre o que será o vídeo? Ex: 3 Segredos do Dropshipping que ninguém te conta..."></textarea>
        </div>
        <div class="flex flex-col gap-2">
            <label class="text-[10px] font-bold text-white/40 tracking-widest uppercase">Ideias Brutas / Tópicos (Opcional)</label>
            <textarea id="factory-dump" class="w-full bg-white/5 border border-white/10 rounded-xl p-4 text-white text-sm focus:outline-none focus:border-primary/50 transition-colors resize-none" rows="2" placeholder="Coloque aqui ideias avulsas ou links de referência..."></textarea>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
                <label class="text-[10px] font-bold text-white/40 tracking-widest uppercase">Nicho do Canal</label>
                <select id="factory-brand" class="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white text-sm focus:outline-none focus:border-primary/50">
                    <option value="Geral" class="bg-[#141414]">Geral / Canal Padrão</option>
                    <option value="Dropshipping" class="bg-[#141414]">Dropshipping / E-commerce</option>
                    <option value="Cripto" class="bg-[#141414]">Finanças & Criptomoedas</option>
                </select>
            </div>
            <div class="flex flex-col gap-2">
                <label class="text-[10px] font-bold text-white/40 tracking-widest uppercase">Tipo de Voz</label>
                <select id="factory-voice" class="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white text-sm focus:outline-none focus:border-primary/50">
                    <option value="pt-BR-AntonioNeural" class="bg-[#141414]">Antônio (Masculino pt-BR)</option>
                    <option value="pt-BR-FranciscaNeural" class="bg-[#141414]">Francisca (Feminino pt-BR)</option>
                    <option value="pt-BR-ThalitaNeural" class="bg-[#141414]">Thalita (Feminino pt-BR)</option>
                </select>
            </div>
        </div>
        <div class="flex items-center gap-4 mt-2">
            <label class="flex items-center gap-2 cursor-pointer select-none text-xs font-bold text-white/80">
                <input type="checkbox" id="factory-post-yt" class="rounded bg-white/5 border-white/10 text-primary focus:ring-0">
                Postar automaticamente no YouTube
            </label>
        </div>
        <button id="factory-generate-btn" class="w-full py-4 rounded-xl bg-primary text-black font-black uppercase text-sm tracking-widest hover:scale-[1.02] hover:bg-[#1ed760] transition-all flex items-center justify-center gap-2 mt-2">
            <span>Iniciar Automação ✨</span>
        </button>
    `;
    formCol.appendChild(cardBriefing);

    // 2.2 Coluna da Direita (Painel de Status e Preview) - Ocupa 2/5
    const previewCol = document.createElement('div');
    previewCol.className = 'lg:col-span-2 flex flex-col gap-6';
    mainGrid.appendChild(previewCol);

    // Card de Preview do Vídeo
    const cardPreview = document.createElement('div');
    cardPreview.className = 'bg-[#141414] border border-white/5 rounded-3xl p-6 shadow-2xl flex flex-col gap-4 min-h-[300px] justify-between';
    cardPreview.innerHTML = `
        <h3 class="text-lg font-bold text-white tracking-wide">🎬 Vídeo Renderizado</h3>
        <div id="factory-video-container" class="w-full aspect-[9/16] max-h-[450px] bg-black/40 border border-white/5 rounded-2xl flex items-center justify-center relative overflow-hidden">
            <div id="factory-video-placeholder" class="flex flex-col items-center gap-3 text-white/30 text-xs font-bold uppercase tracking-widest p-4 text-center">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-40">
                    <rect x="2" y="2" width="20" height="20" rx="4"/>
                    <path d="M12 18V6l-5 4 5-4 5 4"/>
                </svg>
                <span>Aguardando Geração</span>
            </div>
            <video id="factory-video-player" class="hidden w-full h-full object-cover" controls></video>
        </div>
        <div id="factory-status" class="w-full bg-white/5 border border-white/10 rounded-xl p-4 text-xs font-medium text-white/60">
            Status: Pronto para iniciar.
        </div>
    `;
    previewCol.appendChild(cardPreview);

    // 3. Adicionar Lógica do Frontend para chamar a API
    const themeInput = cardBriefing.querySelector('#factory-theme');
    const dumpInput = cardBriefing.querySelector('#factory-dump');
    const brandSelect = cardBriefing.querySelector('#factory-brand');
    const voiceSelect = cardBriefing.querySelector('#factory-voice');
    const postYtCheckbox = cardBriefing.querySelector('#factory-post-yt');
    const generateBtn = cardBriefing.querySelector('#factory-generate-btn');

    const videoContainer = cardPreview.querySelector('#factory-video-container');
    const videoPlaceholder = cardPreview.querySelector('#factory-video-placeholder');
    const videoPlayer = cardPreview.querySelector('#factory-video-player');
    const statusBox = cardPreview.querySelector('#factory-status');

    let pollingInterval = null;

    const updateStatus = (text) => {
        statusBox.textContent = `Status: ${text}`;
    };

    const pollResult = (predictionId) => {
        const url = `http://127.0.0.1:8000/api/v1/predictions/${predictionId}/result`;
        
        pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(url);
                if (!response.ok) return;

                const data = await response.json();
                const status = data.status?.toLowerCase();

                if (status === 'processing') {
                    updateStatus('Gerando roteiro, narração e renderizando vídeo...');
                } else if (status === 'completed') {
                    clearInterval(pollingInterval);
                    updateStatus('Concluído com sucesso!');
                    
                    const videoUrl = `http://127.0.0.1:8000${data.url}`;
                    videoPlaceholder.classList.add('hidden');
                    videoPlayer.src = videoUrl;
                    videoPlayer.classList.remove('hidden');
                    
                    generateBtn.disabled = false;
                    generateBtn.querySelector('span').textContent = 'Iniciar Automação ✨';
                } else if (status === 'failed') {
                    clearInterval(pollingInterval);
                    updateStatus(`Falha na renderização: ${data.error || 'Erro desconhecido'}`);
                    generateBtn.disabled = false;
                    generateBtn.querySelector('span').textContent = 'Iniciar Automação ✨';
                }
            } catch (err) {
                console.error('Erro de polling:', err);
            }
        }, 3000);
    };

    generateBtn.onclick = async () => {
        const theme = themeInput.value.strip ? themeInput.value.strip() : themeInput.value;
        if (!theme) {
            alert('Por favor, defina um tema para o vídeo.');
            return;
        }

        generateBtn.disabled = true;
        generateBtn.querySelector('span').textContent = 'Processando...';
        updateStatus('Enviando solicitação para o servidor...');

        // Ocultar player de vídeo anterior se houver
        videoPlayer.classList.add('hidden');
        videoPlaceholder.classList.remove('hidden');

        try {
            const payload = {
                prompt: theme,
                dump: dumpInput.value,
                brand: brandSelect.value,
                voice: voiceSelect.value,
                post_to_youtube: postYtCheckbox.checked
            };

            const response = await fetch('http://127.0.0.1:8000/api/v1/predictions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error('Falha ao registrar tarefa no servidor.');
            }

            const data = await response.json();
            updateStatus('Tarefa registrada! Iniciando geração...');
            pollResult(data.id);

        } catch (err) {
            updateStatus(`Erro: ${err.message}`);
            generateBtn.disabled = false;
            generateBtn.querySelector('span').textContent = 'Iniciar Automação ✨';
        }
    };

    return container;
}
