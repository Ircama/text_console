import sys
import re
import tkinter as tk
from tkinter import Menu, messagebox
import tkinter.font as tkfont
from code import InteractiveConsole
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from .history import History
from .__version__ import __version__


class BaseTextConsole(tk.Text):
    """Base class for the text console with customizable attributes"""
    
    # Class attributes that can be overridden by subclasses
    history_file = ".console_history"
    console_locals = {}
    context_menu_items = [
        ("Cut", "cut"),
        ("Copy", "copy"),
        ("Paste", "paste"),
        ("Clear", "clear")
    ]
    show_about_message = "Python Console v" + __version__
    show_help_content = "Welcome to the Python Console"
    
    def __init__(self, main, master, **kw):
        kw.setdefault('width', 50)
        kw.setdefault('wrap', 'word')
        kw.setdefault('prompt1', '>>> ')
        kw.setdefault('prompt2', '... ')
        self._prompt1 = kw.pop('prompt1')
        self._prompt2 = kw.pop('prompt2')
        banner = kw.pop('banner', 'Python %s\n' % sys.version)
        
        super().__init__(master, **kw)
        
        # Initialize console with merged locals
        merged_locals = {
            "self": main,
            "master": master,
            "kw": kw,
            "local": self
        }
        merged_locals.update(self.console_locals)
        self._console = InteractiveConsole(locals=merged_locals)
        
        # Initialize history
        self.history = History(self.history_file)
        self._hist_item = 0
        self._hist_match = ''
        
        self.setup_tags()
        self.setup_bindings()
        self.setup_context_menu()
        self.create_menu(main, master)
        
        # Initialize console display
        self.insert('end', banner, 'banner')
        self.prompt()
        self.mark_set('input', 'insert')
        self.mark_gravity('input', 'left')

    def setup_tags(self):
        """Set up text tags for styling"""
        font_obj = tkfont.nametofont(self.cget("font"))
        font_size = font_obj.actual("size")
        
        self.tag_configure(
            "errors",
            foreground="red",
            font=("Courier", font_size - 2)
        )
        self.tag_configure(
            "banner",
            foreground="darkred",
            font=("Courier", font_size - 2)
        )
        self.tag_configure(
            "prompt",
            foreground="green",
            font=("Courier", font_size - 2)
        )
        self.tag_configure("input_color", foreground="blue")

    def setup_bindings(self):
        """Set up key bindings"""
        self.bind('<Control-Return>', self.on_ctrl_return)
        self.bind('<Shift-Return>', self.on_shift_return)
        self.bind('<KeyPress>', self.on_key_press)
        self.bind('<KeyRelease>', self.on_key_release)
        self.bind('<Tab>', self.on_tab)
        self.bind('<Down>', self.on_down)
        self.bind('<Up>', self.on_up)
        self.bind('<Return>', self.on_return)
        self.bind('<BackSpace>', self.on_backspace)
        self.bind('<Control-c>', self.on_ctrl_c)
        self.bind('<<Paste>>', self.on_paste)
        self.bind("<Button-3>", self.show_context_menu)

    def setup_context_menu(self):
        """Set up the context menu"""
        self.context_menu = Menu(self, tearoff=0)
        for label, command in self.context_menu_items:
            if label == "-":
                self.context_menu.add_separator()
            else:
                self.context_menu.add_command(
                    label=label, command=getattr(self, command)
                )

    def create_menu(self, main, master):
        """Create the menu bar - can be overridden by subclasses"""
        menu_bar = Menu(master)
        master.config(menu=menu_bar)

        # File menu
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Clear Console", command=self.clear_console)
        file_menu.add_command(label="History", command=self.dump_history)
        if master != main:
            file_menu.add_command(label="Close Window", command=master.destroy)
        file_menu.add_command(label="Quit Application", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Cut", command=self.cut)
        edit_menu.add_command(label="Copy", command=self.copy)
        edit_menu.add_command(label="Paste", command=self.paste)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        # Help menu
        help_menu = Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Help", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

    def show_about(self):
        """Show about dialog - can be overridden by subclasses"""
        messagebox.showinfo("About", self.show_about_message)

    def show_help(self):
        """Show help window - can be overridden by subclasses"""
        help_window = tk.Toplevel(self)
        help_window.title("Help")
        help_window.geometry("600x400")

        # Add a scrollbar and text widget
        scrollbar = tk.Scrollbar(help_window)
        scrollbar.pack(side="right", fill="y")

        help_text = tk.Text(
            help_window,
            wrap="word",
            yscrollcommand=scrollbar.set
        )
        help_text.tag_configure("title", foreground="purple")
        help_text.tag_configure("section", foreground="blue")

        help_text.insert(
            tk.END,
            self.show_help_content + '\n\n',
            "title"
        )
        help_text.insert(
            tk.END,
            'Features:\n\n',
            "section"
        )
        help_text.insert(
            tk.END,
            (
                "- Clear Console: Clears all text in the console.\n"
                "- Context Menu: Right-click for cut, copy, paste, or clear.\n"
                "- Help: Provides this text.\n\n"
            )
        )
        help_text.insert(
            tk.END,
            'Tokens:\n\n',
            "section"
        )
        help_text.insert(
            tk.END,
            (
                "self: Master self\n"
                "master: TextConsole widget\n"
                "kw: kw dictionary ({'width': 50, 'wrap': 'word'})\n"
                "local: TextConsole self\n\n"
            )
        )
        help_text.config(state="disabled")  # Make the text read-only
        help_text.pack(fill="both", expand=True)
        scrollbar.config(command=help_text.yview)

    def clear_console(self):
        """Clear the text in the console."""
        self.clear()

    def show_context_menu(self, event):
        """Show the context menu at the cursor position."""
        self.context_menu.post(event.x_root, event.y_root)

    def cut(self):
        """Cut the selected text to the clipboard."""
        try:
            self.event_generate("<<Cut>>")
        except tk.TclError:
            pass

    def copy(self):
        """Copy the selected text to the clipboard."""
        try:
            self.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def paste(self):
        """Paste text from the clipboard."""
        try:
            self.event_generate("<<Paste>>")
        except tk.TclError:
            pass

    def clear(self):
        """Clear all text from the console."""
        self.delete("1.0", "end")
        self.insert("1.0", self._prompt1)  # Reinsert the prompt
        self.delete('input', 'insert lineend')

    def dump_history(self):
        """Open a separate window with the output of the history."""
        history_window = tk.Toplevel(self)
        history_window.title("History")
        history_window.geometry("1000x400")

        # Add a scrollbar and text widget
        scrollbar = tk.Scrollbar(history_window)
        scrollbar.pack(side="right", fill="y")

        history_txt = tk.Text(
            history_window, wrap="word", yscrollcommand=scrollbar.set
        )
        history_txt.tag_configure("title", foreground="red")
        history_txt.tag_configure("counter", foreground="blue")
        for i, command in enumerate(self.history):
            history_txt.insert('end', f"{i + 1}\t| ", "counter")
            history_txt.insert('end', f"{command}\n")
        history_txt.config(state="disabled")  # Make the text read-only
        history_txt.pack(fill="both", expand=True)
        scrollbar.config(command=history_txt.yview)

    def on_ctrl_c(self, event):
        """Copy selected code, removing prompts first"""
        sel = self.tag_ranges('sel')
        if sel:
            txt = self.get('sel.first', 'sel.last').splitlines()
            lines = []
            for i, line in enumerate(txt):
                if line.startswith(self._prompt1):
                    lines.append(line[len(self._prompt1):])
                elif line.startswith(self._prompt2):
                    lines.append(line[len(self._prompt2):])
                else:
                    lines.append(line)
            self.clipboard_clear()
            self.clipboard_append('\n'.join(lines))
        return 'break'

    def on_paste(self, event):
        """Paste commands"""
        if self.compare('insert', '<', 'input'):
            return "break"
        sel = self.tag_ranges('sel')
        if sel:
            self.delete('sel.first', 'sel.last')
        txt = self.clipboard_get()
        self.insert("insert", txt)
        self.insert_cmd(self.get("input", "end"))
        return 'break'

    def prompt(self, result=False):
        """Insert a prompt"""
        if result:
            self.insert('end', self._prompt2, 'prompt')
        else:
            self.insert('end', self._prompt1, 'prompt')
        self.mark_set('input', 'end-1c')

    def on_key_press(self, event):
        """Prevent text insertion in command history"""
        if self.compare('insert', '<', 'input') and event.keysym not in ['Left', 'Right']:
            self._hist_item = len(self.history)
            if not event.char.isalnum():
                return 'break'
        else:
            if event.keysym not in ['Return']:
                self.tag_add("input_color", "input", "insert lineend")

    def on_key_release(self, event):
        """Reset history scrolling"""
        if self.compare('insert', '<', 'input') and event.keysym not in ['Left', 'Right']:
            self._hist_item = len(self.history)
            return 'break'
        else:
            if event.keysym not in ['Return']:
                self.tag_add("input_color", "input", "insert lineend")

    def on_up(self, event):
        """Handle up arrow key press"""
        # Handle cursor position outside the input area
        if self.compare('insert', '<', 'input'):
            self.mark_set('insert', 'end')
            return 'break'

        # Check if at the start of the input line
        elif self.index('input linestart') == self.index('insert linestart'):
            # Get the current input line for partial matching
            line = self.get('input', 'insert')
            self._hist_match = line

            # Save the current history index and move one step back
            hist_item = self._hist_item
            self._hist_item -= 1

            # Search for a matching history entry
            while self._hist_item >= 0:
                # Convert the current history item to a string
                item = self.history[self._hist_item]
                if item.startswith(line):  # Match the current input
                    break
                self._hist_item -= 1

            if self._hist_item >= 0:
                # Found a match: insert the command
                index = self.index('insert')
                self.insert_cmd(item)  # Update input with the matched command
                self.mark_set('insert', index)
            else:
                # No match: use the last history item
                self._hist_item = len(self.history) - 1
                if self._hist_item >= 0:
                    item = self.history[self._hist_item]
                    index = self.index('insert')
                    self.insert_cmd(item)  # Update input with the last command
                    self.mark_set('insert', index)
                else:
                    # No history at all, do nothing
                    self._hist_item = hist_item

            return 'break'

    def on_down(self, event):
        """Handle down arrow key press"""
        # Handle cursor position outside the input area
        if self.compare('insert', '<', 'input'):
            self.mark_set('insert', 'end')
            return 'break'

        # Check if at the end of the last input line
        elif self.compare('insert lineend', '==', 'end-1c'):
            # Get the prefix to match (from the previous navigation step)
            line = self._hist_match

            # Move one step forward in history
            self._hist_item += 1

            # Search for a matching history entry
            while self._hist_item < len(self.history):
                # Convert the current history item to a string
                item = self.history[self._hist_item]
                if item.startswith(line):  # Match the prefix
                    break
                self._hist_item += 1

            if self._hist_item < len(self.history):
                # Found a match: insert the command
                self.insert_cmd(item)
                self.mark_set('insert', 'input+%ic' % len(self._hist_match))
            else:
                # No match: reset to the end of the history
                self._hist_item = len(self.history)
                self.delete('input', 'end')
                self.insert('insert', line)

            return 'break'

    def on_tab(self, event):
        """Handle tab key press"""
        if self.compare('insert', '<', 'input'):
            self.mark_set('insert', 'input lineend')
            return "break"
        # indent code
        sel = self.tag_ranges('sel')
        if sel:
            start = str(self.index('sel.first'))
            end = str(self.index('sel.last'))
            start_line = int(start.split('.')[0])
            end_line = int(end.split('.')[0]) + 1
            for line in range(start_line, end_line):
                self.insert('%i.0' % line, '    ')
        else:
            txt = self.get('insert-1c')
            if not txt.isalnum() and txt != '.':
                self.insert('insert', '    ')
        return "break"

    def on_shift_return(self, event):
        """Handle Shift+Return key press"""
        if self.compare('insert', '<', 'input'):
            self.mark_set('insert', 'input lineend')
            return 'break'
        else: # execute commands
            self.mark_set('insert', 'end')
            self.insert('insert', '\n')
            self.insert('insert', self._prompt2, 'prompt')
            self.eval_current(True)

    def on_return(self, event=None):
        """Handle Return key press"""
        if self.compare('insert', '<', 'input'):
            self.mark_set('insert', 'input lineend')
            return 'break'
        else:
            self.eval_current(True)
            self.see('end')
            self.history.save()
        return 'break'

    def on_ctrl_return(self, event=None):
        """Handle Ctrl+Return key press"""
        self.insert('insert', '\n' + self._prompt2, 'prompt')
        return 'break'

    def on_backspace(self, event):
        """Handle delete key press"""
        if self.compare('insert', '<=', 'input'):
            self.mark_set('insert', 'input lineend')
            return 'break'
        sel = self.tag_ranges('sel')
        if sel:
            self.delete('sel.first', 'sel.last')
        else:
            linestart = self.get('insert linestart', 'insert')
            if re.search(r'    $', linestart):
                self.delete('insert-4c', 'insert')
            else:
                self.delete('insert-1c')
        return 'break'

    def insert_cmd(self, cmd):
        """Insert lines of code, adding prompts"""
        input_index = self.index('input')
        self.delete('input', 'end')
        lines = cmd.splitlines()
        if lines:
            indent = len(re.search(r'^( )*', lines[0]).group())
            self.insert('insert', lines[0][indent:])
            for line in lines[1:]:
                line = line[indent:]
                self.insert('insert', '\n')
                self.prompt(True)
                self.insert('insert', line)
                self.mark_set('input', input_index)
        self.see('end')

    def eval_current(self, auto_indent=False):
        """Evaluate code"""
        index = self.index('input')
        lines = self.get('input', 'insert lineend').splitlines() # commands to execute
        self.mark_set('insert', 'insert lineend')
        #self.tag_add("input_color", "input", "insert lineend")
        if lines:  # there is code to execute
            # remove prompts
            lines = [lines[0].rstrip()] + [line[len(self._prompt2):].rstrip() for line in lines[1:]]
            for i, l in enumerate(lines):
                if l.endswith('?'):
                    lines[i] = 'help(%s)' % l[:-1]
            cmds = '\n'.join(lines)
            self.insert('insert', '\n')
            out = StringIO()  # command output
            err = StringIO()  # command error traceback
            with redirect_stderr(err):     # redirect error traceback to err
                with redirect_stdout(out): # redirect command output
                    # execute commands in interactive console
                    res = self._console.push(cmds)
                    # if res is True, this is a partial command, e.g. 'def test():' and we need to wait for the rest of the code
            errors = err.getvalue()
            if errors:  # there were errors during the execution
                self.insert('end', errors, 'errors')  # display the traceback
                self.mark_set('input', 'end')
                self.see('end')
                self.prompt() # insert new prompt
            else:
                output = out.getvalue()  # get output
                if output:
                    self.insert('end', output, 'output')
                self.mark_set('input', 'end')
                self.see('end')
                if not res and self.compare('insert linestart', '>', 'insert'):
                    self.insert('insert', '\n')
                self.prompt(res)
                if auto_indent and lines:
                    # insert indentation similar to previous lines
                    indent = re.search(r'^( )*', lines[-1]).group()
                    line = lines[-1].strip()
                    if line and line[-1] == ':':
                        indent = indent + '    '
                    self.insert('insert', indent)
                self.see('end')
                if res:
                    self.mark_set('input', index)
                    self._console.resetbuffer()  # clear buffer since the whole command will be retrieved from the text widget
                elif lines:
                    if not self.history or [self.history[-1]] != lines:
                        self.history.append(lines)  # Add commands to history
                        self._hist_item = len(self.history)
            out.close()
            err.close()
        else:
            self.insert('insert', '\n')
            self.prompt()

class TextConsole(BaseTextConsole):
    """Default implementation of the console"""
    pass
