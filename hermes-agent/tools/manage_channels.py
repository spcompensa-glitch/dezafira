#!/usr/bin/env python3
"""
Dezafira Tool: Manage Channels
Executado pelo Nous Hermes Agent via Shell.
"""
import sys
import os
import json

sys.path.insert(0, '/app')

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "list"

    try:
        from modules.database import get_db_channels, create_db_channel, delete_db_channel

        if action == "list":
            channels = get_db_channels()
            print(f"[Dezafira] Canais encontrados: {len(channels)}")
            result = []
            for ch in channels:
                ch_data = {"id": ch.id, "name": ch.name, "niche": getattr(ch, 'niche', 'N/A')}
                result.append(ch_data)
                print(f"  - {ch.name} (ID: {ch.id})")
            print(json.dumps(result, ensure_ascii=False))

        elif action == "create":
            if len(sys.argv) < 3:
                print("Uso: python manage_channels.py create <name> [niche]")
                sys.exit(1)
            name = sys.argv[2]
            niche = sys.argv[3] if len(sys.argv) > 3 else "general"
            ch = create_db_channel(name, niche=niche)
            print(f"[Dezafira] Canal criado: {ch.name} (ID: {ch.id})")
            print(json.dumps({"success": True, "id": ch.id, "name": ch.name}))

        elif action == "delete":
            if len(sys.argv) < 3:
                print("Uso: python manage_channels.py delete <channel_id>")
                sys.exit(1)
            channel_id = sys.argv[2]
            delete_db_channel(channel_id)
            print(f"[Dezafira] Canal deletado: {channel_id}")
            print(json.dumps({"success": True, "deleted": channel_id}))

        else:
            print(f"[Dezafira] Ação desconhecida: {action}")
            print("Ações disponíveis: list, create, delete")
            sys.exit(1)

    except Exception as e:
        print(f"[Dezafira] ERRO: {e}", file=sys.stderr)
        output = {"success": False, "error": str(e)}
        print(json.dumps(output))
        sys.exit(1)

if __name__ == "__main__":
    main()
