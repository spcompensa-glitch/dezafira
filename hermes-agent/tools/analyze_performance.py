#!/usr/bin/env python3
"""
Dezafira Tool: Analyze Performance
Executado pelo Nous Hermes Agent via Shell.
"""
import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, '/app')

def main():
    period = sys.argv[1] if len(sys.argv) > 1 else "week"
    print(f"[Dezafira] Analisando performance: período={period}")

    try:
        from modules.database import SessionLocal, AutomationTask

        db = SessionLocal()
        try:
            # Filtrar por período
            if period == "week":
                since = datetime.now() - timedelta(days=7)
            elif period == "month":
                since = datetime.now() - timedelta(days=30)
            else:
                since = datetime.min

            tasks = db.query(AutomationTask).filter(
                AutomationTask.created_at >= since
            ).all()

            total = len(tasks)
            completed = sum(1 for t in tasks if t.status == "ready")
            failed = sum(1 for t in tasks if t.status == "failed")
            running = sum(1 for t in tasks if t.status in ["writing", "SEO", "production"])

            print(f"[Dezafira] Resultados:")
            print(f"  Total: {total} tarefas")
            print(f"  Concluídas: {completed}")
            print(f"  Falharam: {failed}")
            print(f"  Em andamento: {running}")

            if total > 0:
                success_rate = (completed / total) * 100
                print(f"  Taxa de sucesso: {success_rate:.1f}%")

            output = {
                "success": True,
                "period": period,
                "total": total,
                "completed": completed,
                "failed": failed,
                "running": running,
                "success_rate": round((completed / total) * 100, 1) if total > 0 else 0
            }
            print(json.dumps(output))

        finally:
            db.close()

    except Exception as e:
        print(f"[Dezafira] ERRO: {e}", file=sys.stderr)
        output = {"success": False, "error": str(e)}
        print(json.dumps(output))
        sys.exit(1)

if __name__ == "__main__":
    main()
