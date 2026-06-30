import React from 'react';

const CREATIVE_TOOLS = [
  {
    id: 'image',
    name: 'Image Studio',
    description: 'Gere e edite imagens hiper-realistas com modelos avançados como Flux e SDXL na nuvem ou local.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
    ),
    badge: 'Popular'
  },
  {
    id: 'video',
    name: 'Video Studio',
    description: 'Transforme textos e imagens em vídeos cinematográficos estáveis de alta consistência temporal.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-400">
        <polygon points="23 7 16 12 23 17 23 7"/>
        <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
      </svg>
    ),
    badge: 'Alta Resolução'
  },
  {
    id: 'audio',
    name: 'Audio Studio',
    description: 'Crie efeitos sonoros, vozes clonadas e trilhas sonoras orquestradas em alta definição.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-400">
        <path d="M9 18V5l12-2v13"/>
        <circle cx="6" cy="18" r="3"/>
        <circle cx="18" cy="16" r="3"/>
      </svg>
    )
  },
  {
    id: 'lipsync',
    name: 'Lip Sync Studio',
    description: 'Sincronize perfeitamente o movimento dos lábios de qualquer personagem com o áudio da narração.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-rose-400">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
    )
  },
  {
    id: 'cinema',
    name: 'Cinema Studio',
    description: 'O estúdio cinematográfico autônomo (Higgsfield clone) para criar roteiros e curtas metragens unificados.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-yellow-400">
        <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
        <line x1="7" y1="2" x2="7" y2="22"/>
        <line x1="17" y1="2" x2="17" y2="22"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <line x1="2" y1="7" x2="7" y2="7"/>
        <line x1="2" y1="17" x2="7" y2="17"/>
        <line x1="17" y1="17" x2="22" y2="17"/>
        <line x1="17" y1="7" x2="22" y2="7"/>
      </svg>
    ),
    badge: 'Pro'
  },
  {
    id: 'clipping',
    name: 'AI Clipping',
    description: 'Corte vídeos longos ou downloads do YouTube em pequenos cortes virais formatados em 9:16.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-400">
        <circle cx="6" cy="6" r="3"/>
        <circle cx="6" cy="18" r="3"/>
        <line x1="20" y1="4" x2="8.12" y2="15.88"/>
        <line x1="14.47" y1="14.48" x2="20" y2="20"/>
        <line x1="8.12" y1="8.12" x2="12" y2="12"/>
      </svg>
    )
  },
  {
    id: 'vibe-motion',
    name: 'Vibe Motion',
    description: 'Adicione micro-movimentos e animações estéticas em imagens estáticas mantendo o realismo.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-pink-400">
        <path d="m22 8-6 4 6 4V8Z"/>
        <rect x="2" y="6" width="14" height="12" rx="2" ry="2"/>
        <path d="M6 12h4"/>
      </svg>
    )
  },
  {
    id: 'marketing',
    name: 'Marketing Studio',
    description: 'Crie anúncios de conversão rápida e copies voltadas para viralização no TikTok e Shorts.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyan-400">
        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
      </svg>
    )
  },
  {
    id: 'workflows',
    name: 'Workflows (ComfyUI)',
    description: 'Monte e execute fluxos gráficos de inteligência artificial de forma nativa e personalizada.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-teal-400">
        <rect x="3" y="3" width="7" height="9" rx="1"/>
        <rect x="14" y="3" width="7" height="5" rx="1"/>
        <rect x="14" y="12" width="7" height="9" rx="1"/>
        <rect x="3" y="16" width="7" height="5" rx="1"/>
        <path d="M7 8h7M10 18h4"/>
      </svg>
    )
  },
  {
    id: 'agents',
    name: 'AI Agents',
    description: 'Crie e configure agentes conversacionais autônomos dedicados a tarefas do seu negócio.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-400">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M12 2v9M8 5h8"/>
      </svg>
    )
  },
  {
    id: 'design-agent',
    name: 'Design Agent',
    description: 'Gere interfaces visuais e layouts elegantes de forma automatizada por IA.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-orange-400">
        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"/>
        <path d="M12 6V12L16 14"/>
      </svg>
    )
  }
];

export default function CreativeStudio({ onSelectStudio }) {
  return (
    <div className="w-full h-full flex flex-col bg-app-bg text-white overflow-y-auto p-6 md:p-8 custom-scrollbar">
      {/* Header */}
      <div className="w-full max-w-6xl mx-auto mb-8">
        <div className="text-xs font-bold text-primary tracking-[0.2em] uppercase mb-1">HIGGSFIELD ENGINE</div>
        <h1 className="text-3xl md:text-5xl font-black tracking-tight text-white uppercase select-none">Estúdio Criativo</h1>
        <p className="text-secondary text-sm opacity-60">Explore as ferramentas clássicas de geração autônoma de mídia do Higgsfield.</p>
      </div>

      {/* Grid de Ferramentas */}
      <div className="w-full max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {CREATIVE_TOOLS.map((tool) => (
          <button
            key={tool.id}
            onClick={() => onSelectStudio(tool.id)}
            className="text-left bg-[#101010]/80 border border-white/5 hover:border-white/10 rounded-2xl p-6 shadow-xl transition-all duration-300 hover:scale-[1.02] hover:bg-[#141414] relative group flex flex-col justify-between min-h-[190px]"
          >
            <div>
              {/* Header do Card */}
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-white/5 rounded-xl border border-white/5 group-hover:bg-white/10 transition-colors">
                  {tool.icon}
                </div>
                {tool.badge && (
                  <span className="text-[10px] font-black uppercase tracking-wider bg-white/10 text-white/80 px-2 py-0.5 rounded-full">
                    {tool.badge}
                  </span>
                )}
              </div>

              {/* Título & Descrição */}
              <h3 className="text-lg font-bold text-white mb-2 tracking-wide group-hover:text-primary transition-colors">
                {tool.name}
              </h3>
              <p className="text-xs text-white/50 leading-relaxed font-medium line-clamp-3">
                {tool.description}
              </p>
            </div>

            {/* Link indicador no rodapé do Card */}
            <div className="flex items-center gap-1.5 text-[11px] font-bold text-white/40 group-hover:text-primary transition-colors mt-4">
              <span>Abrir ferramenta</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transform group-hover:translate-x-1 transition-transform">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12 5 19 12 12 19"/>
              </svg>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
