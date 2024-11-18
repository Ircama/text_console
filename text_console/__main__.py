import sys
import argparse
import tkinter as tk
import webbrowser

from . import TextConsole
from .__version__ import __version__


class TkTextConsole(TextConsole):

    """Subclass that adds the second element to the Help menu."""
    def create_menu(self, main, master):
        """Extend the menu creation logic."""
        # Call the parent class implementation
        super().create_menu(main, master)
        
        # Add "Web Site" to the Help menu
        menu_bar = master.nametowidget(master.cget('menu'))  # Get the menu widget
        help_menu = list(menu_bar.children.values())[2]  # Access the Help menu (third = 2)
        help_menu.insert_command(
            help_menu.index("end"),
            label="Web Site",
            command=self.open_help_browser
        )

    def open_help_browser(self):
        # Opens a web browser to a help URL
        url = "https://ircama.github.io/text_console"
        try:
            ret = webbrowser.open(url)
        except Exception as e:
            pass


class TkConsole(tk.Tk):
    """Main application class for the Tkinter console."""
    def __init__(self):
        super().__init__()
        self.title("Python Console v" + __version__)
        self.geometry("800x400")

        # Initialize the TkTextConsole widget
        console = TkTextConsole(self, self)
        console.pack(fill='both', expand=True)

        # Configure grid resizing for the main window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)


def main():
    parser = argparse.ArgumentParser(
        prog='Python Console',
        epilog='A customizable Tkinter-based text console widget.')
    parser.add_argument(
        '-V',
        "--version",
        dest='version',
        action='store_true',
        help="Print version and exit")

    args, unknown = parser.parse_known_args()
    if args.version:
        print(f'Python Console version {__version__}')
        sys.exit(0)

    app = TkConsole()
    app.mainloop()


if __name__ == "__main__":
    main()
