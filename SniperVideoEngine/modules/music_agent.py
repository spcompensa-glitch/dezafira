import os
import random

class MusicAgent:
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.music_dir = os.path.join(self.project_dir, "assets", "music")
        
        # Mapeamento de palavras-chave para categorias
        self.categories = {
            "tech": ["tech", "cyber", "digital", "data", "futuristic", "crypto"],
            "corporate": ["corporate", "professional", "clean", "minimal", "office", "business"],
            "energetic": ["energetic", "upbeat", "powerful", "fast", "action", "drums"],
            "relaxed": ["relaxed", "lofi", "soft", "calm", "painting", "aesthetic"]
        }

    def select_track(self, music_prompt):
        """
        Escolhe uma trilha sonora com base no prompt sugerido pelo Gemini.
        """
        prompt_lower = music_prompt.lower()
        selected_category = "corporate" # Default
        
        for category, keywords in self.categories.items():
            if any(kw in prompt_lower for kw in keywords):
                selected_category = category
                break
        
        category_path = os.path.join(self.music_dir, selected_category)
        
        if not os.path.exists(category_path):
            return None
            
        tracks = [f for f in os.listdir(category_path) if f.endswith((".mp3", ".wav"))]
        
        if not tracks:
            print(f"[MusicAgent] Nenhuma trilha encontrada em '{selected_category}'. Usando silêncio ou default.")
            return None
            
        track_name = random.choice(tracks)
        return os.path.join(category_path, track_name)

if __name__ == "__main__":
    # Teste
    agent = MusicAgent()
    prompt = "A powerful and energetic electronic track with drums"
    track = agent.select_track(prompt)
    print(f"Trilha selecionada: {track}")
