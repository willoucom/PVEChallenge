"""The window: pick a preset and apply it to the client.

It covers lobby creation only. `discover` stays a command-line tool: it
observes, it is not an everyday feature.

Tkinter cannot be driven from any thread but the one running its event loop.
The network work therefore runs in a separate thread that touches no widget: it
drops its messages into a queue, which the window drains periodically from its
own thread.
"""

import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, font as tkfont, ttk

from .champions import ChampionError
from .client import LcuClient, LcuError, check_connection
from .config import ConfigError, load_config, set_lockfile
from .lobby import (
    LobbyError,
    PresetError,
    available_presets,
    builtin_presets,
    run_lobby,
    user_presets,
)
from .i18n import t
from .lockfile import LockfileError, read_credentials
from .paths import user_presets_dir
from .version import app_version

TITLE = "PVE Challenge"

#: Notice required by Riot Games' « Legal Jibber Jabber » policy, which
#: demands that it be displayed conspicuously. Its wording is fixed by Riot: it
#: is neither reworded nor translated.
DISCLAIMER = (
    "PVE Challenge was created under Riot Games' \"Legal Jibber Jabber\" policy "
    "using assets owned by Riot Games. Riot Games does not endorse or sponsor "
    "this project."
)

#: Project repository, shown at the foot of the window: it signs the work, and
#: gives whoever runs an unsigned binary somewhere to check where it came from.
REPO_URL = "https://github.com/willoucom/PVEChallenge"

#: Link blue, kept apart from the status colours: it announces an action, not a state.
LINK_COLOR = "#0b5cad"

#: Window icon. It lives in the package rather than in `assets/`, so that it
#: travels into the executable with it and stays reachable through `__file__`.
ICON_PATH = Path(__file__).resolve().parent / "icon.ico"

#: The Windows interface font, and the monospaced font of the log.
UI_FONT = ("Segoe UI", 10)
LOG_FONT = ("Consolas", 9)

#: Status bar colours. They carry information, never decoration: each hue maps
#: to a state the user must be able to tell apart at a glance.
STATUS_COLORS = {
    "neutre": "#3c3c3c",
    "en cours": "#8a6100",
    "succes": "#1a7f37",
    "erreur": "#b42318",
}

#: Window padding and gutter between blocks, in pixels at 100 % scaling.
PAD = 12
GAP = 8


def enable_dpi_awareness() -> None:
    """Declare the process display-density aware, before any window exists.

    Without this, Windows stretches a Tk window designed for 96 dpi, and the
    whole rendering is blurry on a scaled display. It is the most visible
    cosmetic flaw of a Tkinter application, and the cheapest one to fix.
    """
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError, OSError):
        pass


def apply_window_icon(root: tk.Tk) -> None:
    """Set the icon of the title bar and of the taskbar.

    This is distinct from the executable's icon, set at build time: without this
    call Tk shows its default feather, whatever icon the file carries. `default`
    also applies it to child windows, such as dialogs.

    A missing icon must not stop the tool from opening.
    """
    try:
        # `default` covers future child windows, the bare call this window itself.
        root.iconbitmap(default=str(ICON_PATH))
        root.iconbitmap(str(ICON_PATH))
    except tk.TclError:
        pass


def apply_native_style(root: tk.Misc) -> None:
    """Apply the native Windows theme and the system font."""
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name).configure(family=UI_FONT[0], size=UI_FONT[1])


class App(ttk.Frame):
    """Main window."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, padding=PAD)
        self.root = root
        self.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        #: Queue fed by the worker thread, drained by `_drain`.
        self._messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self._worker: threading.Thread | None = None
        #: Short name -> path, as displayed by the list.
        self._presets: dict[str, Path] = {}

        self._build_header()
        self._build_presets()
        self._build_log()
        self._build_options()
        self._build_status()
        self._build_disclaimer()
        self._build_pied()

        self.refresh_presets()
        self._load_configured_lockfile()

        #: Handle of the periodic callback, so it can be cancelled on close.
        self._drain_id: str | None = self.root.after(100, self._drain)
        self.root.bind("<Destroy>", self._arreter_drain, add="+")

    # ----------------------------------------------------------------- views

    def _build_header(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, GAP))
        ttk.Label(header, text=TITLE, font=(UI_FONT[0], 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=t("gui.subtitle"),
            foreground=STATUS_COLORS["neutre"],
        ).grid(row=1, column=0, sticky="w")

    def _build_presets(self) -> None:
        block = ttk.LabelFrame(self, text=t("gui.preset.frame"), padding=GAP)
        block.grid(row=1, column=0, sticky="ew", pady=(0, GAP))
        block.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(block, columns=("source",), height=5, selectmode="browse")
        self.tree.heading("#0", text=t("gui.preset.name"))
        self.tree.heading("source", text=t("gui.preset.source"))
        self.tree.column("#0", width=220, anchor="w")
        self.tree.column("source", width=120, anchor="w")
        self.tree.grid(row=0, column=0, sticky="ew")
        self.tree.bind("<Double-1>", lambda _event: self.apply_selected())

        scroll = ttk.Scrollbar(block, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        actions = ttk.Frame(block)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(GAP, 0))
        # The last column absorbs the remaining space: that is what pushes its
        # button to the right, whatever the width of the window.
        actions.columnconfigure(2, weight=1)

        self.apply_button = ttk.Button(actions, text=t("gui.button.apply"), command=self.apply_selected)
        self.apply_button.grid(row=0, column=0)
        ttk.Button(actions, text=t("gui.button.refresh"), command=self.refresh_presets).grid(
            row=0, column=1, padx=(GAP, 0)
        )
        ttk.Button(
            actions, text=t("gui.button.open_presets"), command=self.open_presets_dir
        ).grid(
            row=0, column=2, padx=(GAP, 0), sticky="e"
        )

        # The inventory gets its own line under the buttons: it describes the
        # list, not the state of the application. The bar at the bottom stays
        # reserved for what is currently happening.
        self.inventaire_var = tk.StringVar()
        ttk.Label(
            block, textvariable=self.inventaire_var, foreground=STATUS_COLORS["neutre"]
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(GAP, 0))

    def _build_log(self) -> None:
        block = ttk.LabelFrame(self, text=t("gui.log.frame"), padding=GAP)
        block.grid(row=2, column=0, sticky="nsew", pady=(0, GAP))
        block.columnconfigure(0, weight=1)
        block.rowconfigure(0, weight=1)

        self.log = tk.Text(block, height=10, wrap="word", font=LOG_FONT, state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(block, orient="vertical", command=self.log.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scroll.set)
        self.log.tag_configure("erreur", foreground=STATUS_COLORS["erreur"])

    def _build_options(self) -> None:
        block = ttk.LabelFrame(self, text=t("gui.options.frame"), padding=GAP)
        block.grid(row=3, column=0, sticky="ew", pady=(0, GAP))
        block.columnconfigure(1, weight=1)

        ttk.Label(block, text=t("gui.options.lockfile")).grid(row=0, column=0, sticky="w", padx=(0, GAP))
        self.lockfile_var = tk.StringVar()
        ttk.Entry(block, textvariable=self.lockfile_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(block, text=t("gui.button.browse"), command=self.browse_lockfile).grid(
            row=0, column=2, padx=(GAP, 0)
        )
        ttk.Button(block, text=t("gui.button.save"), command=self.save_lockfile).grid(
            row=0, column=3, padx=(GAP, 0)
        )
        
        ttk.Label(
            block,
            text=t("gui.options.hint"),
            foreground=STATUS_COLORS["neutre"],
        ).grid(row=1, column=1, columnspan=3, sticky="w", pady=(4, 0))


    def _build_pied(self) -> None:
        """Footer: repository link on the left, version on the right.

        Tk has no link widget: an underlined blue label, with the hand cursor,
        and the browser opened on click.

        The version comes from what the build stamped into the package, so the
        window shows exactly what the file properties announce. From the sources
        there is nothing to stamp, and it reads `dev`.
        """
        pied = ttk.Frame(self)
        pied.grid(row=6, column=0, sticky="ew", pady=(4, 0))
        pied.columnconfigure(0, weight=1)

        lien = ttk.Label(
            pied,
            text=REPO_URL,
            font=(UI_FONT[0], 8, "underline"),
            foreground=LINK_COLOR,
            cursor="hand2",
        )
        lien.grid(row=0, column=0, sticky="w")
        lien.bind("<Button-1>", lambda _event: webbrowser.open(REPO_URL))

        self.version_label = ttk.Label(
            pied,
            text=app_version(),
            font=(UI_FONT[0], 8),
            foreground=STATUS_COLORS["neutre"],
        )
        self.version_label.grid(row=0, column=1, sticky="e")

    def _build_disclaimer(self) -> None:
        ttk.Label(
            self,
            text=DISCLAIMER,
            font=(UI_FONT[0], 8),
            foreground=STATUS_COLORS["neutre"],
            wraplength=600,
            justify="left",
        ).grid(row=5, column=0, sticky="ew", pady=(GAP, 0))

    def _build_status(self) -> None:
        self.status_var = tk.StringVar(value=t("gui.status.ready"))
        self.status = ttk.Label(
            self, textvariable=self.status_var, foreground=STATUS_COLORS["neutre"]
        )
        self.status.grid(row=4, column=0, sticky="w")

    # --------------------------------------------------------------- actions

    def set_status(self, kind: str, message: str) -> None:
        self.status_var.set(message)
        self.status.configure(foreground=STATUS_COLORS[kind])

    def write(self, message: str, tag: str = "") -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def refresh_presets(self) -> None:
        """Re-read both sources and fill the list."""
        self.tree.delete(*self.tree.get_children())
        try:
            self._presets = available_presets()
            perso = set(user_presets())
            collisions = sorted(set(builtin_presets()) & perso)
        except OSError as exc:
            self.set_status("erreur", t("gui.error.presets_unreadable", error=exc))
            return

        for name in sorted(self._presets):
            source = t("gui.preset.source.user") if name in perso else t("gui.preset.source.builtin")
            self.tree.insert("", "end", iid=name, text=name, values=(source,))

        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])

        self.inventaire_var.set(t("gui.status.available", count=len(self._presets)))

        if collisions:
            noms = ", ".join(repr(name) for name in collisions)
            self.set_status(
                "erreur",
                t("gui.status.unusable", names=noms),
            )
            self.write(t("gui.log.discarded", names=noms), "erreur")
            self.write(t("gui.log.folder", path=user_presets_dir()), "erreur")
        else:
            self.set_status("neutre", t("gui.status.ready"))

    def browse_lockfile(self) -> None:
        current = Path(self.lockfile_var.get() or "")
        chosen = filedialog.askopenfilename(
            parent=self.root,
            title=t("gui.dialog.lockfile"),
            initialdir=str(current.parent) if current.name else None,
        )
        if chosen:
            self.lockfile_var.set(str(Path(chosen)))

    def save_lockfile(self) -> None:
        try:
            path = set_lockfile(self.lockfile_var.get().strip() or None)
        except ConfigError as exc:
            self.set_status("erreur", str(exc))
            self.write(str(exc), "erreur")
            return
        self.set_status("succes", t("gui.status.saved", path=path))

    def open_presets_dir(self) -> None:
        directory = user_presets_dir()
        try:
            directory.mkdir(parents=True, exist_ok=True)
            os.startfile(directory)
        except (OSError, AttributeError) as exc:
            self.set_status("erreur", t("gui.error.open_folder", path=directory, error=exc))

    def apply_selected(self) -> None:
        """Start applying the selected preset, in a separate thread."""
        if self._worker is not None and self._worker.is_alive():
            return
        selection = self.tree.selection()
        if not selection:
            self.set_status("erreur", t("gui.status.no_selection"))
            return

        name = selection[0]
        self.apply_button.state(["disabled"])
        self.set_status("en cours", t("gui.status.applying", name=repr(name)))
        self.write("")
        self.write(f"--- {name} ---")
        self._worker = threading.Thread(target=self._run, args=(name,), daemon=True)
        self._worker.start()

    # -------------------------------------------------------- worker thread

    def _run(self, preset_name: str) -> None:
        """Runs outside the interface thread: touches no widget."""

        def emit(message: str) -> None:
            self._messages.put(("log", message))

        try:
            credentials = read_credentials()
            emit(t("lockfile.lockfile_label", path=credentials.source))
            with LcuClient(credentials) as client:
                summoner = check_connection(client)
                name = summoner.get("gameName") or summoner.get("displayName") or t("gui.unknown_summoner")
                emit(t("gui.connected_as", name=name))
                run_lobby(client, preset_name, report=emit)
            self._messages.put(("succes", t("gui.status.lobby_ready")))
        except (ConfigError, LockfileError, PresetError, LobbyError, ChampionError, LcuError) as exc:
            self._messages.put(("erreur", str(exc)))
        except Exception as exc:  # connexion refusee, TLS, timeout...
            self._messages.put(("erreur", t("gui.error.lcu_unreachable", error=repr(exc))))

    def _drain(self) -> None:
        """Drain the worker thread's queue. Runs in the interface thread."""
        try:
            while True:
                kind, message = self._messages.get_nowait()
                if kind == "log":
                    self.write(message)
                elif kind == "succes":
                    self.set_status("succes", message)
                    self.apply_button.state(["!disabled"])
                else:
                    self.write(message, "erreur")
                    self.set_status("erreur", message.splitlines()[0])
                    self.apply_button.state(["!disabled"])
        except queue.Empty:
            pass
        self._drain_id = self.root.after(100, self._drain)

    def _arreter_drain(self, event: "tk.Event") -> None:
        """Cancel the periodic callback when the window goes away.

        Without this, the pending `after` fires after the Tk interpreter has
        been destroyed and surfaces `invalid command name ..._drain`. The
        executable being built without a console, that error would go nowhere:
        never seen, but there all the same.
        """
        if event.widget is not self.root or self._drain_id is None:
            return
        try:
            self.root.after_cancel(self._drain_id)
        except tk.TclError:
            pass
        self._drain_id = None

    # ------------------------------------------------------------- start-up

    def _load_configured_lockfile(self) -> None:
        try:
            self.lockfile_var.set(load_config().lockfile or "")
        except ConfigError as exc:
            self.set_status("erreur", str(exc))
            self.write(str(exc), "erreur")


def build(root: tk.Tk) -> App:
    """Build the window. Kept apart from `main` so it stays testable without a loop."""
    apply_native_style(root)
    apply_window_icon(root)
    root.title(TITLE)
    root.minsize(640, 660)
    return App(root)


def main() -> int:
    enable_dpi_awareness()
    root = tk.Tk()
    build(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
