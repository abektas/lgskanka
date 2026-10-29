#!/usr/bin/env python3
"""
Token Traffic Monitor — Live dashboard for Evren/OpenRouter/Ollama usage.
Run: python3 token_monitor.py
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.layout import Layout
    from rich.text import Text
except ImportError:
    print("Installing rich...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.layout import Layout
    from rich.text import Text


console = Console()

# ─── Config ──────────────────────────────────────────────
EVREN_API_KEY = os.getenv("EVREN_API_KEY") or os.getenv("FAL_KEY")  # fallback
EVREN_QUOTA_URL = "https://evren-llmapi.ssyz.org.tr/v1/quota"
OPENROUTER_QUOTA_URL = "https://openrouter.ai/api/v1/auth/key"
REFRESH_SEC = 30
HISTORY_FILE = Path.home() / ".hermes" / "token_history.jsonl"
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# ─── Helpers ─────────────────────────────────────────────
def fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)

def fmt_pct(ratio: float) -> str:
    return f"{ratio*100:.1f}%"

def human_delta(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h: parts.append(f"{h}sa")
    if m: parts.append(f"{m}dk")
    if s or not parts: parts.append(f"{s}sn")
    return " ".join(parts)

def load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text().strip().split("\n")
    return [json.loads(l) for l in lines[-100:]]

def save_history(entry: dict):
    with HISTORY_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")

# ─── Providers ───────────────────────────────────────────
def fetch_evren() -> dict | None:
    if not EVREN_API_KEY:
        return {"error": "EVREN_API_KEY not set"}
    try:
        r = requests.get(EVREN_QUOTA_URL, headers={"Authorization": f"Bearer {EVREN_API_KEY}"}, timeout=10)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_openrouter() -> dict | None:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return {"error": "OPENROUTER_API_KEY not set"}
    try:
        r = requests.get(OPENROUTER_QUOTA_URL, headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # OpenRouter returns: data.usage, data.limit, data.is_free_tier
            return data.get("data", {})
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_ollama() -> dict:
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            return {"models": [m["name"] for m in models], "status": "running"}
        return {"status": "error", "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "stopped", "error": str(e)}

# ─── UI ──────────────────────────────────────────────────
def build_layout(evren: dict, openrouter: dict, ollama: dict, history: list) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=4),
    )
    layout["main"].split_row(
        Layout(name="evren", ratio=2),
        Layout(name="others", ratio=1),
    )
    layout["others"].split_column(
        Layout(name="openrouter"),
        Layout(name="ollama"),
    )

    # Header
    now = datetime.now().strftime("%H:%M:%S")
    layout["header"].update(Panel(f"[bold cyan]🔐 Token Traffic Monitor[/]  │  {now}  │  Refresh: {REFRESH_SEC}s", style="cyan"))

    # Evren panel
    if "error" in evren:
        evren_content = f"[red]Evren: {evren['error']}[/]"
    else:
        daily_used = evren.get("daily_used_tokens", 0)
        daily_limit = evren.get("daily_limit_tokens", 15_000_000)
        daily_rem = evren.get("daily_remaining_tokens", 0)
        daily_pct = daily_used / daily_limit if daily_limit else 0
        window_used = evren.get("used_tokens", 0)
        window_cap = evren.get("cap", 2_500_000)
        window_pct = window_used / window_cap if window_cap else 0
        reset_at = evren.get("daily_reset_at", "")
        if reset_at:
            reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
            delta = int((reset_dt - datetime.now(timezone.utc)).total_seconds())
            reset_str = f"Sıfırlama: {human_delta(delta)}"
        else:
            reset_str = "Sıfırlama: —"

        prog = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        task1 = prog.add_task("Günlük", total=daily_limit, completed=daily_used)
        task2 = prog.add_task("5dk penceresi", total=window_cap, completed=window_used)

        evren_content = Panel(
            f"[bold]Evren (Günlük)[/]\n"
            f"  Kullanılan: [yellow]{fmt_num(daily_used)}[/] / {fmt_num(daily_limit)} ({fmt_pct(daily_pct)})\n"
            f"  Kalan: [green]{fmt_num(daily_rem)}[/]\n"
            f"  {reset_str}\n\n"
            f"[bold]5dk Sliding Window[/]\n"
            f"  Kullanılan: [yellow]{fmt_num(window_used)}[/] / {fmt_num(window_cap)} ({fmt_pct(window_pct)})\n\n"
            f"{prog}",
            title="🌐 Evren",
            border_style="green" if daily_pct < 0.8 else "yellow" if daily_pct < 0.95 else "red",
        )
    layout["evren"].update(evren_content)

    # OpenRouter panel
    if "error" in openrouter:
        or_content = f"[red]OpenRouter: {openrouter['error']}[/]"
    elif openrouter:
        usage = openrouter.get("usage", 0)
        limit = openrouter.get("limit", 0)
        pct = usage / limit if limit else 0
        is_free = openrouter.get("is_free_tier", False)
        or_content = Panel(
            f"[bold]OpenRouter[/] {'(Free tier)' if is_free else ''}\n"
            f"  Kullanım: [yellow]{fmt_num(usage)}[/] / {fmt_num(limit)} ({fmt_pct(pct)})\n"
            f"  Kalan: [green]{fmt_num(limit - usage)}[/]",
            title="🔑 OpenRouter",
            border_style="blue",
        )
    else:
        or_content = Panel("[dim]OpenRouter: API key not configured[/]", title="🔑 OpenRouter", border_style="dim")
    layout["openrouter"].update(or_content)

    # Ollama panel
    if ollama.get("status") == "running":
        models = ", ".join(ollama.get("models", [])[:5])
        if len(ollama.get("models", [])) > 5:
            models += f" … (+{len(ollama['models'])-5} more)"
        ollama_content = Panel(
            f"[green]● Running[/]\nModeller: {models}\n[dim]Kota: Yok (yerel)[/]",
            title="🦙 Ollama",
            border_style="green",
        )
    else:
        ollama_content = Panel(
            f"[red]● Stopped[/]\n{ollama.get('error', 'Ollama not reachable')}\n[dim]systemctl --user start ollama-serve.service[/]",
            title="🦙 Ollama",
            border_style="red",
        )
    layout["ollama"].update(ollama_content)

    # Footer - recent history sparkline
    if history:
        recent = history[-20:]
        spark = "".join("▁▂▃▄▅▆▇█"[min(7, int(h.get("daily_pct", 0)*8))] for h in recent)
        footer_text = f"Son 20 ölçüm (günlük %): {spark}"
    else:
        footer_text = "Henüz geçmiş yok — önce ölçüm bekleniyor..."
    layout["footer"].update(Panel(footer_text, title="📈 Trend", border_style="dim"))

    return layout


def main():
    console.clear()
    console.print("[cyan]Token Monitor başlatılıyor...[/]")
    console.print(f"[dim]Geçmiş dosyası: {HISTORY_FILE}[/]")
    console.print(f"[dim]EVREN_API_KEY: {'set' if EVREN_API_KEY else 'NOT SET'}[/]")
    console.print(f"[dim]OPENROUTER_API_KEY: {'set' if os.getenv('OPENROUTER_API_KEY') else 'NOT SET'}[/]")
    console.print("[dim]Ctrl+C ile çık[/]\n")

    with Live(console=console, refresh_per_second=1/REFRESH_SEC, screen=True) as live:
        while True:
            evren = fetch_evren()
            openrouter = fetch_openrouter()
            ollama = fetch_ollama()

            # Save to history
            if "error" not in evren:
                daily_used = evren.get("daily_used_tokens", 0)
                daily_limit = evren.get("daily_limit_tokens", 15_000_000)
                save_history({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "daily_used": daily_used,
                    "daily_limit": daily_limit,
                    "daily_pct": daily_used / daily_limit if daily_limit else 0,
                })

            history = load_history()
            layout = build_layout(evren, openrouter, ollama, history)
            live.update(layout)
            time.sleep(REFRESH_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor durduruldu.[/]")