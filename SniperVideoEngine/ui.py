import gradio as gr
import asyncio
from manager import SniperDirector
import os
import json
from dotenv import load_dotenv

load_dotenv()
director = SniperDirector()

# --- Configurações Estéticas Spotify Premium ---
COR_ACCENT = "#1DB954"   # Verde Spotify
COR_BG = "#121212"       # Fundo Principal
COR_NAV = "#000000"      # Barra Lateral
COR_CARD = "#181818"     # Cards
COR_TEXT_MAIN = "#FFFFFF"
COR_TEXT_SEC = "#B3B3B3"

custom_css = f"""
/* Reset e Fundo Profundo */
:root {{ color-scheme: dark; }}
.gradio-container {{ 
    background-color: {COR_BG} !important; 
    border: none !important; 
    font-family: 'Circular', 'Inter', -apple-system, sans-serif !important; 
}}
footer {{ display: none !important; }}

/* Sidebar Estilo Spotify */
#sidebar {{ 
    background-color: {COR_NAV} !important; 
    border-right: 1px solid #282828 !important; 
    padding: 24px !important;
}}
.sidebar-item {{
    color: {COR_TEXT_SEC} !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 8px 0 !important;
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    cursor: pointer !important;
    transition: color 0.2s !important;
}}
.sidebar-item:hover {{ color: {COR_TEXT_MAIN} !important; }}

/* Painel Central */
.main-panel {{ padding: 32px 48px !important; background-color: {COR_BG} !important; }}

/* Cards sem bordas e com elevação sutil */
.card-style {{ 
    background-color: {COR_CARD} !important; 
    border-radius: 8px !important; 
    padding: 24px !important; 
    border: none !important; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
}}

/* Inputs Minimalistas */
input, textarea {{ 
    background-color: #3E3E3E !important; 
    border: none !important; 
    color: {COR_TEXT_MAIN} !important; 
    border-radius: 4px !important; 
    padding: 12px !important;
    font-size: 14px !important;
}}
input:focus, textarea:focus {{ background-color: #4A4A4A !important; }}

/* Tipografia Spotify */
h1 {{ color: {COR_TEXT_MAIN} !important; font-weight: 900 !important; font-size: 32px !important; letter-spacing: -0.04em !important; margin-bottom: 24px !important; }}
h3 {{ color: {COR_TEXT_MAIN} !important; font-weight: 800 !important; font-size: 18px !important; letter-spacing: -0.02em !important; }}
span, label {{ color: {COR_TEXT_SEC} !important; font-size: 12px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }}

/* Botão Pílula Spotify - Forçando Verde */
.btn-premium, button.btn-premium, .gr-button-primary.btn-premium {{ 
    background-color: #1DB954 !important; 
    color: #000000 !important; 
    border-radius: 500px !important; 
    border: none !important; 
    font-weight: 700 !important; 
    font-size: 14px !important;
    padding: 12px 32px !important;
    cursor: pointer !important;
    transition: transform 0.1s, background 0.1s !important;
    width: fit-content !important;
    margin-top: 10px !important;
    box-shadow: none !important;
}}
.btn-premium:hover, button.btn-premium:hover {{ 
    transform: scale(1.04); 
    background-color: #1ed760 !important; 
}}

/* Player de Vídeo */
.video-container {{ border: none !important; background: transparent !important; }}
.video-container video {{ border-radius: 8px !important; }}

/* Accordion Custom */
.gr-accordion {{ border: none !important; background: transparent !important; }}
"""

async def run_production(theme, brand, project_id, comfy_url):
    if not theme or not project_id:
        return None, "### ⚠️ Informe o tema e o nome do projeto.", ""

    try:
        if comfy_url:
            director.video_agent.comfy.server_address = comfy_url
            
        plan = await director.produce_campaign(theme, brand, project_id)
        
        video_rel_path = os.path.join("outputs", f"{project_id}_preview.mp4")
        prompts_text = "\n\n".join([f"## CENA {i+1}\n{p}" for i, p in enumerate(plan['visual_prompts'])])
        
        status_msg = f"### ✅ Produção Concluída!\n**Marca:** {brand}\n**Música:** {plan['music_prompt']}"
        
        return video_rel_path, status_msg, prompts_text
    except Exception as e:
        return None, f"### ❌ Erro na Engine\n{str(e)}", ""

# --- Interface Dashboard ---
with gr.Blocks(title="KaliFy Studio | Spotify Edition", css=custom_css) as demo:
    with gr.Row():
        # BARRA LATERAL (Biblioteca)
        with gr.Column(scale=1, elem_id="sidebar"):
            gr.HTML(f"""
                <div style="margin-bottom: 32px;">
                    <img src="file/assets/logo.png" style="width: 130px; filter: brightness(0) invert(1);">
                </div>
                <div class="sidebar-item">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12.5 3.553L5 8V21h15V8l-7.5-4.447zM19 20h-5v-5h-4v5H5V9l7-4.2L19 9v11z"/></svg>
                    Início
                </div>
                <div class="sidebar-item">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M10.533 1.279c-5.18 0-9.407 4.227-9.407 9.407s4.227 9.407 9.407 9.407a9.357 9.357 0 005.16-1.537l5.42 5.42 1.414-1.414-5.389-5.389a9.357 9.357 0 001.794-5.487c0-5.18-4.227-9.407-9.407-9.407zm0 2c4.093 0 7.407 3.314 7.407 7.407s-3.314 7.407-7.407 7.407-7.407-3.314-7.407-7.407 3.314-7.407 7.407-7.407z"/></svg>
                    Buscar
                </div>
                <div class="sidebar-item" style="margin-top: 24px; opacity: 0.7;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M3 22a1 1 0 01-1-1V3a1 1 0 012 0v18a1 1 0 01-1 1zM15.5 2.134A1 1 0 0014 3v18a1 1 0 001 1h6a1 1 0 001-1V3a1 1 0 00-1.5-.866L15.5 2.134zM20 20h-4V4l4 2.31V20z"/></svg>
                    Sua Biblioteca
                </div>
                <div style="margin-top: 40px;">
                    <span style="font-size: 11px; color: #777;">SERVIDOR COMFYUI</span>
                </div>
            """)
            comfy_url_input = gr.Textbox(show_label=False, value="127.0.0.1:8188", placeholder="URL Engine", container=False)

        # PAINEL CENTRAL
        with gr.Column(scale=4, elem_classes="main-panel"):
            gr.Markdown("# Criar Nova Campanha")
            
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Group(elem_classes="card-style"):
                        gr.Markdown("### ✍️ Briefing Criativo")
                        theme_input = gr.Textbox(
                            show_label=False, 
                            placeholder="Sobre o que é o vídeo?", 
                            lines=3
                        )
                        
                        gr.Markdown("### 🏷️ Marca")
                        brand_input = gr.Radio(
                            choices=["1Crypten", "Otto Pinturas", "Geral"], 
                            value="Geral",
                            label="",
                            container=False
                        )
                        
                        id_input = gr.Textbox(label="NOME DO PROJETO", value="campanha_01")
                        
                        btn = gr.Button("CRIAR VÍDEO", elem_classes="btn-premium")

                with gr.Column(scale=2):
                    with gr.Group(elem_classes="card-style"):
                        gr.Markdown("### 🎬 Preview")
                        video_output = gr.Video(show_label=False, elem_classes="video-container")
                        status_output = gr.Markdown("*Aguardando comando...*", elem_id="status-text")

            with gr.Accordion("📋 Detalhes da Produção", open=False):
                prompts_output = gr.Code(label="Prompts Gerados", language="markdown")

    btn.click(
        fn=run_production,
        inputs=[theme_input, brand_input, id_input, comfy_url_input],
        outputs=[video_output, status_output, prompts_output]
    )

if __name__ == "__main__":
    demo.launch(share=False, server_port=7870)
