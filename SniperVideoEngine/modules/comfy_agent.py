import websocket
import uuid
import json
import urllib.request
import urllib.parse
import os
from dotenv import load_dotenv

load_dotenv()

class ComfyAgent:
    def __init__(self, server_address=None):
        self.server_address = server_address or os.getenv("COMFYUI_SERVER", "127.0.0.1:8188")
        self.client_id = str(uuid.uuid4())
        self.outputs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{self.server_address}/view?{url_values}") as response:
            return response.read()

    def get_history(self, prompt_id):
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def generate_video(self, workflow_json, prompts_mapping):
        """
        Executa um workflow do ComfyUI substituindo os prompts.
        prompts_mapping: dicionário com node_id: texto do prompt
        """
        # 1. Preparar o workflow (substituir textos)
        prompt = json.loads(workflow_json)
        for node_id, text in prompts_mapping.items():
            if node_id in prompt:
                # Assume que o campo de texto está em [inputs][text] ou similar
                # Isso depende do workflow específico
                if "text" in prompt[node_id]["inputs"]:
                    prompt[node_id]["inputs"]["text"] = text
        
        # 2. Conectar WebSocket para monitorar
        ws = websocket.WebSocket()
        try:
            ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
            print(f"[ComfyAgent] Conectado ao servidor {self.server_address}")
        except Exception as e:
            print(f"[ComfyAgent] Erro ao conectar ao servidor: {e}")
            return None

        # 3. Enviar para a fila
        prompt_id = self.queue_prompt(prompt)['prompt_id']
        print(f"[ComfyAgent] Prompt enviado! ID: {prompt_id}")

        # 4. Esperar conclusão
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break # Concluído!
            else:
                continue # Binary data (preview images)

        # 5. Buscar resultado no histórico
        history = self.get_history(prompt_id)[prompt_id]
        results = []
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                    output_file = os.path.join(self.outputs_dir, image['filename'])
                    with open(output_file, "wb") as f:
                        f.write(image_data)
                    results.append(output_file)
            
            # Suporte para vídeos (ComfyUI-VideoHelperSuite por exemplo)
            if 'gifs' in node_output:
                for video in node_output['gifs']:
                    video_data = self.get_image(video['filename'], video['subfolder'], video['type'])
                    output_file = os.path.join(self.outputs_dir, video['filename'])
                    with open(output_file, "wb") as f:
                        f.write(video_data)
                    results.append(output_file)

        ws.close()
        return results

if __name__ == "__main__":
    # Teste de conexão (apenas verifica se o servidor está online)
    agent = ComfyAgent()
    print(f"Testando conexão com {agent.server_address}...")
    # Aqui precisaria de um workflow JSON real para testar a geração
