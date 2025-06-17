# text_console

*text_console* is a customizable, Tkinter-based interactive shell widget that lets users type commands into a console pane and have them evaluated in your application’s Python environment. It supports arrows and command history. It’s designed for embedding in GUI apps, debugging, scripting, and educational tools as an API Playground.

It can also be used as a standalone Python command interpreter.

This program is similar to [wxPython Shell](https://github.com/wxWidgets/wxPython-Classic/blob/master/wx/py/shell.py), implemented using Tkinter.

## Key Features

- **Live code execution**

  Send single- or multi-line Python code to the interpreter and see results immediately.

- **Integrated application context**

  Access and modify your app’s variables and functions via the console_locals namespace.

- **Advanced editing**
    - **Keyboard shortcuts:** all standard keyboard shortcut are allowed
    - **Multiline editing:** Single line and multiline editing is allowed, also with copy/paste features. When pressing enter within an edited line, a popup appears to ask the requested action (execute the command, add a new line, abort). Shift-Enter is also allowed.
    - **Prompt Protection:** The prompt area (`>>> ` or `... `) is protected. The cursor cannot move into or before the prompt, and editing actions (insertion, deletion) are blocked in the prompt area.
    - **Smart Arrow Navigation:** Left and right arrow keys skip over prompt tags and any protected regions, ensuring the cursor only lands in editable areas. Arrow navigation also respects line boundaries and prompt positions.
    - **Home/End Navigation:** The `Home` and `End` keys move the cursor to the beginning or end of the current line, but never into the prompt area.
    - **Undo/Redo Support:** Full undo/redo support is enabled (`Ctrl+Z`/`Ctrl+Y`), with fine-grained control for character-by-character undo.
    - **Tab and Shift+Tab:** Pressing `Tab` inserts four spaces. Pressing `Shift+Tab` removes up to four spaces.
    - **Selection Awareness:** Editing and navigation actions are aware of text selection. For example, custom arrow key logic is bypassed when a selection is active.
    - **Clear Console:** The console can be cleared with a single command, automatically restoring the prompt and positioning the cursor for new input.

- **Command history**

  Navigate previous commands with ↑/↓ arrows; history is saved to a file you choose.

- **Cut/Copy/Paste/Clear**

  Right-click context menu (and customizable via context_menu_items) for text editing.

- **Customizable UI**

  The package provides flexibility to customize:

  - `history_file`: Change the location of the history file
  - `console_locals`: Add custom variables and functions to the console's namespace
  - `context_menu_items`: Modify the right-click context menu
  - `show_about_message`: Customize the about dialog content
  - `show_help_content`: Customize the help window content
  - `create_menu`: Override to completely customize the menu bar

- **Subclass-friendly**

  Extend the TextConsole class and override any of the above to fit your needs.

## Installation

```bash
pip install text-console
```

## Playground

```
python -m text_console
```

Available options:

```
Python Console [-h] [-V]

optional arguments:
  -h, --help     show this help message and exit
  -V, --version  Print version and exit

A customizable Tkinter-based text console widget.
```

### Basic usage with default settings

```python
import tkinter as tk
from text_console import TextConsole

class TkConsole(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Python Console")
        self.geometry("800x400")

        # Initialize the TextConsole widget
        console = TextConsole(self, self)
        console.pack(fill='both', expand=True)

        # Configure grid resizing for the main window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)


app = TkConsole()
app.mainloop()
```

### Invoking TextConsole from a Master widget

```python
import tkinter as tk
from text_console import TextConsole

class TkConsole(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Python Console")
        self.geometry("100x70")

        # Add a button to launch the TextConsole
        run_console_button = tk.Button(
            self, 
            text="Debug Console", 
            command=self.run_text_console
        )
        run_console_button.pack(pady=20)  # Add some spacing around the button

        # Configure grid resizing for the main window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def run_text_console(self):
        """Launches the TextConsole in a new Toplevel window."""
        console_window = tk.Toplevel(self)
        console_window.title("Debug Console")
        console_window.geometry("800x400")

        # Initialize the TextConsole widget
        console = TextConsole(self, console_window)
        console.pack(fill='both', expand=True)

app = TkConsole()
app.mainloop()
```

### Customized console through subclassing

```python
from text_console import TextConsole

class MyCustomConsole(TextConsole):

    # Override class attributes
    history_file = "my_custom_history.txt"

    console_locals = {
        "my_var": 42,
        "my_function": lambda x: x * 2
    }

    context_menu_items = [
        ("Custom Action", "custom_action"),
        "-",  # separator
        ("Clear", "clear")
    ]

    show_about_message = "My Custom Console v1.0"
    show_help_content = "This is my custom console help content"
    
    def custom_action(self):
        print("Custom action executed!")
    
    def create_menu(self, master):
        # Override to create a custom menu
        super().create_menu(main, master)
        
        # Add "Web Site" to the Help menu
        menu_bar = master.nametowidget(master.cget('menu'))  # Get the menu widget
        help_menu = list(menu_bar.children.values())[2]  # Access the Help menu (third = 2)
        help_menu.insert_command(
            help_menu.index("end"),
            label="Web Site",
            command=self.new_action
        )

        # Override to create a custom menu
        menu_bar = Menu(master)
        master.config(menu=menu_bar)
        
        # Custom menu items
        custom_menu = Menu(menu_bar, tearoff=0)
        custom_menu.add_command(label="My Action", command=self.custom_action)
        menu_bar.add_cascade(label="Custom", menu=custom_menu)

    def new_action(self):
        pass

    """ Alternatively, override create_menu:
    def create_menu(self, master):
        # Override to create a custom menu
        menu_bar = Menu(master)
        master.config(menu=menu_bar)
        
        # Custom menu items
        custom_menu = Menu(menu_bar, tearoff=0)
        custom_menu.add_command(label="My Action", command=self.custom_action)
        menu_bar.add_cascade(label="Custom", menu=custom_menu)
    """


# Use the custom console
text_console = MyCustomConsole(main, master)
```

## Key bindings

The text_console module provides the following key bindings for efficient navigation and interaction:

- `Ctrl + Enter (<Control-Return>)`

  Submit a command while keeping the current context open.

- `Shift + Enter (<Shift-Return>)`

  Insert a newline without triggering a default submission action.

- `Tab (<Tab>)`

  Indent input.

- `Down Arrow (<Down>)`

  Next command from the history.

- `Up Arrow (<Up>)`

  Previous command from the history.

- `Right-Click (<Button-3>)`

  Displays the context menu.
