

from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.timer import Timer
from textual.events import Key
from rich.panel import Panel

import requests
import datetime as dt
import webbrowser
from zoneinfo import ZoneInfo   # Python ≥ 3.9

# ----------- НАЛАШТУВАННЯ -----------
TOKEN = ""
REFRESH_EVERY = 30          # секунд
KYIV_TZ = ZoneInfo("Europe/Kyiv")
# ------------------------------------

class AlertPanel(Static):
    """Віджет-контейнер з панеллю Rich."""
    def show_text(self, text: str, style: str = "green") -> None:
        self.update(Panel(text, title="Повітряні тривоги", border_style=style))


class AirAlertApp(App):
    """Textual-додаток: тривоги з тривалістю, сортування за зростанням,
    виключення для Луганської області та АР Крим, повне фарбування рядків."""
    CSS = """
    Screen { layout: vertical; padding: 1; }
    #panel  { width: 100%; height: 100%; }
    """
    BINDINGS = [("q", "quit", "Вихід")]

    timer: Timer | None = None

    def compose(self) -> ComposeResult:
        self.panel = AlertPanel("", id="panel")
        yield self.panel

    def on_mount(self) -> None:
        # перший запит
        self.refresh_alerts()
        # далі за таймером
        self.timer = self.set_interval(REFRESH_EVERY, self.refresh_alerts)

    def refresh_alerts(self) -> None:
        url = f"https://api.alerts.in.ua/v1/alerts/active.json?token={TOKEN}"

        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            alerts = resp.json().get("alerts", [])
        except Exception as e:
            self.panel.show_text(f"[bold red]⚠ Помилка API[/]\n{e}", style="red")
            return

        now_utc   = dt.datetime.now(dt.timezone.utc)
        now_local = dt.datetime.now(KYIV_TZ).strftime("%H:%M:%S")

        # Збираємо статуси: область → (код, started_at_iso)
        statuses: dict[str, tuple[str, str]] = {}
        for alert in alerts:
            oblast = alert.get("location_oblast") or alert.get("location_title")
            if not oblast:
                continue
            code = "A" if alert.get("location_type") == "oblast" else "P"
            started = alert["started_at"]

            prev = statuses.get(oblast)
            if prev:
                # якщо вже була повна тривога — лишаємо
                if prev[0] == "A":
                    continue
                # якщо нова повна — оновлюємо
                if code == "A":
                    statuses[oblast] = (code, started)
            else:
                statuses[oblast] = (code, started)

        # Розподіляємо на записи з часом та виключення
        timed_entries: list[tuple[str, str, int]] = []
        no_time_entries: list[tuple[str, str]] = []
        for oblast, (code, started_iso) in statuses.items():
            if oblast in ("Луганська область", "Автономна Республіка Крим"):
                no_time_entries.append((oblast, code))
            else:
                start_dt = dt.datetime.fromisoformat(started_iso.replace("Z", "+00:00"))
                minutes = int((now_utc - start_dt).total_seconds() // 60)
                timed_entries.append((oblast, code, minutes))

        # Сортуємо за зростанням тривалості
        timed_entries.sort(key=lambda x: x[2])

        # Формуємо текст рядків — повністю фарбуємо в потрібний колір
        lines: list[str] = []
        for oblast, code, minutes in timed_entries:
            text = f"{oblast} — {'🚨 ТРИВОГА' if code=='A' else '⚠ ЧАСТКОВА'} {minutes} хв"
            if code == "A":
                lines.append(f"[bold red]{text}[/]")
            else:
                lines.append(f"[yellow]{text}[/]")

        # Додаємо виключення (без часу)
        for oblast, code in no_time_entries:
            text = f"{oblast} — {'🚨 ТРИВОГА' if code=='A' else '⚠ ЧАСТКОВА'}"
            if code == "A":
                lines.append(f"[bold red]{text}[/]")
            else:
                lines.append(f"[yellow]{text}[/]")

        # Виводимо список або повідомлення про відсутність тривог
        if lines:
            content = "\n".join(lines) + f"\n\n[i]Оновлено {now_local}"
            self.panel.show_text(content, style="red")
        else:
            self.panel.show_text(
                f"[green]Немає активних тривог[/]\n\n[i]Оновлено {now_local}",
                style="green"
            )

    def on_key(self, event: Key) -> None:
        # m/M відкриває карту
        if event.key.lower() == "m":
            webbrowser.open("https://alerts.in.ua/")


if __name__ == "__main__":
    AirAlertApp().run()
