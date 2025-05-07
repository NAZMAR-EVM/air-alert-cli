#!/usr/bin/env python3

from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.reactive import reactive
from textual.timer import Timer
from textual.events import Key
from rich.panel import Panel
import requests
import datetime as dt
import webbrowser

# ----------- НАСТРОЙКИ -----------
TOKEN = ""
REFRESH_EVERY = 30          # секунд
# ---------------------------------

OBLASTS = [
    "Автономная Республика Крым", "Волынская область", "Винницкая область",
    "Днепропетровская область", "Донецкая область", "Житомирская область",
    "Закарпатская область", "Запорожская область", "Ивано-Франковская область",
    "г. Киев", "Киевская область", "Кировоградская область",
    "Луганская область", "Львовская область", "Николаевская область",
    "Одесская область", "Полтавская область", "Ровненская область",
    "г. Севастополь", "Сумская область", "Тернопольская область",
    "Харьковская область", "Херсонская область", "Хмельницкая область",
    "Черкасская область", "Черновицкая область", "Черниговская область"
]

class AlertPanel(Static):
    """Виджет-контейнер с панелью Rich."""
    def show_text(self, text: str, style: str = "green") -> None:
        self.update(Panel(text, title="Воздушные тревоги", border_style=style))

class AirAlertApp(App):
    """Основное Textual-приложение."""
    CSS = """
    Screen {
        layout: vertical;
        padding: 1;
    }
    #panel {
        width: 100%;
        height: 100%;
    }
    """
    BINDINGS = [("q", "quit", "Выход")]

    alerts = reactive("-- загрузка…")
    timer: Timer | None = None

    def compose(self) -> ComposeResult:
        self.panel = AlertPanel("", id="panel")
        yield self.panel

    def on_mount(self) -> None:
        self.refresh_alerts()                                 # первый запрос
        self.timer = self.set_interval(REFRESH_EVERY, self.refresh_alerts)

    def refresh_alerts(self) -> None:
        url = (
            "https://api.alerts.in.ua/v1/iot/active_air_raid_alerts_by_oblast.json"
            f"?token={TOKEN}"
        )
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()  # строка вида "ANNNPN..."
        except Exception as e:
            self.panel.show_text(f"[bold red]⚠ Ошибка API[/]\n{e}", style="red")
            return

        now = dt.datetime.now().strftime("%H:%M:%S")
        lines: list[str] = []
        for status, oblast in zip(data, OBLASTS):
            if status == "A":
                lines.append(f"[bold red]{oblast}[/] — [red]🚨 ТРИВОГА[/]")
            elif status == "P":
                lines.append(f"[yellow]{oblast}[/] — [yellow]⚠ ЧАСТКОВА[/]")

        if lines:
            txt = "\n".join(lines) + f"\n\n[i]Обновлено {now}"
            self.panel.show_text(txt, style="red")
        else:
            self.panel.show_text(f"[green]Нет активных тревог[/]\n\n[i]Обновлено {now}", style="green")

    def on_key(self, event: Key) -> None:
        # Нажатие m/M открывает карту
        if event.key.lower() == "m":
            webbrowser.open('https://alerts.in.ua/')

if __name__ == "__main__":
    AirAlertApp().run()
