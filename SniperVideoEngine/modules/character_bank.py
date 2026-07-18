"""
Character Bank — Gerenciamento de personagens e referências visuais
===================================================================
Carrega characters.json, fornece prompts para geração de imagens,
e gerencia character references para consistência visual.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, List

BRAND_DIR = Path(__file__).parent.parent / "brand_config" / "canal_jesus_lua"
CHARACTERS_JSON = BRAND_DIR / "characters.json"
ASSETS_DIR = Path(__file__).parent.parent / "assets" / "characters"


class CharacterBank:
    """Banco de personagens com prompts e seeds para geração visual."""

    def __init__(self, canal: str = "canal_jesus_lua"):
        self.canal = canal
        self.brand_dir = Path(__file__).parent.parent / "brand_config" / canal
        self.characters_file = self.brand_dir / "characters.json"
        self.assets_dir = Path(__file__).parent.parent / "assets" / "characters"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.characters = self._load_characters()

    def _load_characters(self) -> Dict:
        if not self.characters_file.exists():
            raise FileNotFoundError(
                f"Characters.json não encontrado: {self.characters_file}"
            )
        with open(self.characters_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {c["id"]: c for c in data.get("characters", [])}

    def get_character(self, char_id: str) -> Optional[Dict]:
        return self.characters.get(char_id)

    def get_prompt(self, char_id: str, variant: str = "base") -> Optional[str]:
        char = self.get_character(char_id)
        if not char:
            return None
        prompts = char.get("prompts", {})
        return prompts.get(variant) or prompts.get("base")

    def get_seed(self, char_id: str) -> Optional[int]:
        char = self.get_character(char_id)
        return char.get("seed") if char else None

    def get_negative_prompt(self, char_id: str) -> Optional[str]:
        char = self.get_character(char_id)
        return char.get("negative_prompt") if char else None

    def get_voice_config(self, char_id: str) -> Optional[Dict]:
        char = self.get_character(char_id)
        return char.get("voice_profile") if char else None

    def list_characters(self) -> List[Dict]:
        return list(self.characters.values())

    def get_reference_path(self, char_id: str, variant: str = "base") -> Path:
        return self.assets_dir / f"{char_id}_{variant}.png"

    def has_reference(self, char_id: str, variant: str = "base") -> bool:
        return self.get_reference_path(char_id, variant).exists()

    def generate_all_references(self, flux_client=None) -> Dict[str, str]:
        """Gera todas as character references usando FLUX.2 Klein.

        Returns:
            Dict com character_id -> caminho da imagem gerada
        """
        if flux_client is None:
            from modules.flux_klein_gen import FluxKleinClient
            flux_client = FluxKleinClient()

        results = {}
        for char_id, char in self.characters.items():
            prompts = char.get("prompts", {})
            seed = char.get("seed")
            negative = char.get("negative_prompt", "")

            for variant, prompt in prompts.items():
                output_path = str(self.get_reference_path(char_id, variant))
                if os.path.exists(output_path):
                    print(f"[CharacterBank] Já existe: {char_id}_{variant}.png")
                    results[f"{char_id}_{variant}"] = output_path
                    continue

                full_prompt = f"{prompt}, {negative}" if negative else prompt
                print(f"[CharacterBank] Gerando: {char_id}_{variant}...")
                result = flux_client.generate(
                    prompt=full_prompt,
                    output_path=output_path,
                    width=1920,
                    height=1080,
                    seed=seed,
                )
                if result:
                    results[f"{char_id}_{variant}"] = result
                    print(f"[CharacterBank] OK: {char_id}_{variant}")
                else:
                    print(f"[CharacterBank] FALHOU: {char_id}_{variant}")

        return results

    def build_scene_prompt(
        self,
        scene_type: str = "moon_sitting",
        characters: Optional[List[str]] = None,
        extra_details: str = "",
    ) -> str:
        """Monta prompt composto para cena com múltiplos personagens.

        Args:
            scene_type: Tipo de cena (moon_sitting, wide_shot, etc.)
            characters: Lista de IDs dos personagens na cena
            extra_details: Detalhes extras para adicionar ao prompt
        """
        if characters is None:
            characters = ["jesus", "pedrinho", "livia"]

        parts = []
        for char_id in characters:
            char = self.get_character(char_id)
            if char:
                prompt = char.get("prompts", {}).get(scene_type, "")
                if prompt:
                    parts.append(prompt)

        # Adicionar cenário se existir
        cenario = self.get_character("cenario_lua")
        if cenario:
            cenario_prompt = cenario.get("prompts", {}).get(scene_type, "")
            if cenario_prompt:
                parts.append(cenario_prompt)

        if extra_details:
            parts.append(extra_details)

        return ", ".join(parts) if parts else ""


# Instância global singleton
_bank_instance = None


def get_character_bank(canal: str = "canal_jesus_lua") -> CharacterBank:
    global _bank_instance
    if _bank_instance is None or _bank_instance.canal != canal:
        _bank_instance = CharacterBank(canal)
    return _bank_instance
