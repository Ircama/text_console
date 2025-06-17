import sys
import re
import tkinter as tk
from tkinter import Menu, messagebox, ttk
import tkinter.font as tkfont
from code import InteractiveConsole
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from .history import History
from .__version__ import __version__


class ExecConsole(InteractiveConsole):
    """Console that tries eval first, then exec, to handle expressions properly."""
    def push(self, source):
        # Try to compile as eval first (for expressions)
        try:
            code_obj = compile(source, filename="<console>", mode="eval")
            # If successful, we have an expression - execute it and return the result
            result = eval(code_obj, self.locals)
            if result is not None:
                # Store the result for retrieval
                self._last_result = result
                return False  # Command is complete
            else:
                self._last_result = None
                return False  # Command is complete
        except SyntaxError:
            # Not a valid expression, try as exec (statements)
            # Clear the last result since we're executing a statement, not an expression
            self._last_result = None
            pass
        except Exception as e:
            # Other errors (runtime errors)
            self._last_result = None  # Clear result on error
            print(str(e), file=sys.stderr)
            return False  # Command is complete
        return self.runsource(source, filename="<console>", symbol="exec")
            
    def get_last_result(self):
        """Get the result of the last expression evaluation."""
        return getattr(self, '_last_result', None)


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

        # Enable undo/redo
        kw.setdefault('undo', True)

        super().__init__(master, **kw)
        
        # Initialize console with merged locals
        merged_locals = {
            "self": main,
            "master": master,
            "kw": kw,
            "local": self
        }
        merged_locals.update(self.console_locals)
        self._console = ExecConsole(locals=merged_locals)
        
        # Initialize history
        self.history = History(self.history_file)
        self._hist_item = len(self.history)
        self._hist_match = ''
        
        # Initialize settings
        self._save_errors_in_history = tk.BooleanVar(value=False)
        
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
        self.tag_configure("output", foreground="#00178c")

    def setup_bindings(self):
        """Set up key bindings"""
        self.bind('<Shift-Return>', self.insert_line)
        self.bind('<Control-Return>', self.go_to_end)
        self.bind('<Tab>', self.on_tab)
        self.bind("<Shift-Tab>", self.on_shift_tab)
        self.bind('<Down>', self.on_down)
        self.bind('<Up>', self.on_up)
        self.bind("<Escape>", self.on_escape)
        self.bind('<Return>', self.on_return)
        self.bind('<BackSpace>', self.on_backspace)
        self.bind('<Control-c>', self.on_ctrl_c)
        self.bind('<<Paste>>', self.on_paste)
        self.bind("<Button-3>", self.show_context_menu)
        self.bind("<Control-z>", lambda e: self._safe_undo())
        self.bind("<Control-y>", lambda e: self._safe_redo())
        self.bind("<KeyRelease>", lambda e: self.edit_separator())
        self.bind("<Left>", lambda e: self.after_idle(self._process_arrows, "Left"))
        self.bind("<Right>", lambda e: self.after_idle(self._process_arrows, "Right"))
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<Home>", lambda e: self._move_to_line_start(e))
        self.bind("<End>", lambda e: self._move_to_line_end(e))

    def _safe_undo(self):
        try:
            self.edit_undo()
        except tk.TclError:
            pass

    def _safe_redo(self):
        try:
            self.edit_redo()
        except tk.TclError:
            pass

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
        file_menu.add_command(label="Clear Console", command=self.clear)
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

        # History menu
        history_menu = Menu(menu_bar, tearoff=0)
        history_menu.add_command(
            label="List history", command=self.dump_history
        )
        history_menu.add_checkbutton(
            label="Save Errors in History",
            variable=self._save_errors_in_history,
            onvalue=True,
            offvalue=False
        )
        menu_bar.add_cascade(label="History", menu=history_menu)

        # Help menu
        help_menu = Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Usage", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

    def show_about(self):
        """Show about dialog - can be overridden by subclasses"""
        messagebox.showinfo("About", self.show_about_message)

    def show_help(self):
        """Show help window - can be overridden by subclasses"""
        help_window = tk.Toplevel(self)
        help_window.title("Usage")
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
                "- History: Open a separate window showing the list of"
                " successfully executed commands (browse the command history).\n"
                "- Context Menu: Right-click for cut, copy, paste, or clear.\n"
                "- Save Errors in History: Option to include failed commands in history.\n\n"
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
        self.insert('end', self._prompt1, 'prompt')
        self.mark_set('input', 'end-1c')
        self.edit_reset()


    def dump_history(self):
        """Open a separate window with the output of the history."""
        history_window = tk.Toplevel(self)
        history_window.title("Command History")
        history_window.geometry("600x600")
        
        # Create main frame
        main_frame = tk.Frame(history_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create fixed header frame
        header_frame = tk.Frame(main_frame, bg="white", relief="solid", bd=1)
        header_frame.pack(fill="x", pady=(0, 5))
        
        # Header label
        header_label = tk.Label(
            header_frame, 
            text="№     │ Command",
            font=("Consolas", 10, "bold"),
            fg="#000080",
            bg="white",
            anchor="w",
            padx=5,
            pady=3
        )
        header_label.pack(fill="x")
        
        # Create text widget frame
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(text_frame, orient="vertical")
        h_scrollbar = tk.Scrollbar(text_frame, orient="horizontal")
        
        # Text widget
        history_txt = tk.Text(
            text_frame, 
            wrap="none",  # No wrapping to maintain table format
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            font=("Consolas", 10),
            bg="white",
            fg="black",
            selectbackground="#cce7ff"
        )
        
        # Configure scrollbars
        v_scrollbar.config(command=history_txt.yview)
        h_scrollbar.config(command=history_txt.xview)
        
        # Pack scrollbars and text widget
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        history_txt.pack(fill="both", expand=True)
        
        # Configure text tags for styling
        history_txt.tag_configure("number", foreground="#0066cc", font=("Consolas", 10, "bold"))
        history_txt.tag_configure("separator", foreground="#888888")
        history_txt.tag_configure("command", foreground="#000000", font=("Consolas", 10))
        history_txt.tag_configure("divider", foreground="#cccccc")
        
        # Calculate column width based on window size and longest command
        def calculate_layout():
            # Get actual text widget width in characters
            try:
                # Get the actual width of the text widget in pixels
                text_width_pixels = history_txt.winfo_width()
                # Convert to approximate character width (assuming monospace font)
                char_width = 8  # Approximate width of Consolas 10pt character
                widget_width = max(80, text_width_pixels // char_width)
            except:
                # Fallback if widget not yet rendered
                widget_width = max(100, (history_window.winfo_width() - 80) // 8)
            
            # Find the longest command to determine if we need to use horizontal scrolling
            max_command_length = 0
            for command in self.history:
                for line in str(command).split('\n'):
                    max_command_length = max(max_command_length, len(line))
            
            # Number column width (always fixed)
            num_width = max(5, len(str(len(self.history))))
            
            # Command column gets remaining width, but ensure minimum readability
            cmd_width = max(50, widget_width - num_width - 3)  # 3 for separators
            
            return num_width, cmd_width, max_command_length, widget_width
        
        # Update layout when window resizes
        def on_window_configure(event=None):
            if event and event.widget == history_window:
                update_display()
        
        def update_display():
            history_txt.config(state="normal")
            history_txt.delete("1.0", "end")
            
            num_width, cmd_width, max_cmd_length, total_width = calculate_layout()
            
            # Update header to match current layout
            header_text = f"{'№':<{num_width}}│ Command"
            header_label.config(text=header_text)
            
            # Add commands (most recent first)
            for i, command in enumerate(reversed(self.history)):
                item_number = len(self.history) - i
                command_text = str(command).strip()
                
                # Split command into lines
                command_lines = command_text.split('\n')
                
                # First line with number
                first_line = command_lines[0] if command_lines else ""
                
                history_txt.insert("end", f"{item_number:<{num_width}}", "number")
                history_txt.insert("end", " │ ", "separator")
                history_txt.insert("end", f"{first_line}\n", "command")
                
                # Additional lines (if multiline command)
                for line in command_lines[1:]:
                    history_txt.insert("end", f"{'':<{num_width}}", "")
                    history_txt.insert("end", " │ ", "separator")
                    history_txt.insert("end", f"{line}\n", "command")
                
                # Add horizontal line separator between commands (except for the last one)
                if i < len(self.history) - 1:
                    # More efficient: insert a single line character repeated
                    history_txt.insert("end", "─" * total_width, "divider")
                    history_txt.insert("end", "\n")
        
        # Copy functionality
        def copy_selected_command():
            try:
                # Get selected text
                selected_text = history_txt.selection_get()
                if selected_text:
                    history_window.clipboard_clear()
                    history_window.clipboard_append(selected_text)
            except tk.TclError:
                # No selection, try to get the line under cursor
                current_line = history_txt.index(tk.INSERT).split('.')[0]
                line_content = history_txt.get(f"{current_line}.0", f"{current_line}.end")
                
                # Extract command part (after the │ separator)
                if " │ " in line_content:
                    command_part = line_content.split(" │ ", 1)[1]
                    history_window.clipboard_clear()
                    history_window.clipboard_append(command_part)
        
        # Context menu
        context_menu = tk.Menu(history_window, tearoff=0)
        context_menu.add_command(label="Copy Selected", command=copy_selected_command)
        context_menu.add_command(label="Select All", command=lambda: history_txt.tag_add("sel", "1.0", "end"))
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        # Bind events
        history_txt.bind("<Button-3>", show_context_menu)  # Right-click
        history_txt.bind("<Control-c>", lambda e: copy_selected_command())
        history_txt.bind("<Double-Button-1>", lambda e: copy_selected_command())
        
        # Bind window resize
        history_window.bind("<Configure>", on_window_configure)
        
        # Initial display with proper timing
        def delayed_setup():
            update_display()
            # Set focus to the text widget for keyboard navigation
            history_txt.focus_set()
            history_txt.see("1.0")  # Scroll to top (most recent command)
        
        history_window.after(200, delayed_setup)  # Increased delay to ensure widget is fully rendered
        
        # Make text read-only
        history_txt.config(state="disabled")
        
        # Status bar
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(5, 0))
        
        status_label = tk.Label(
            status_frame, 
            text=f"Total commands: {len(self.history)}. Right-click or Ctrl+C to copy. Double-click to copy line",
            relief="sunken",
            anchor="w"
        )
        status_label.pack(fill="x")
        
        # Focus on the most recent command (scroll to top)
        history_txt.see("1.0")


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

        # Check if input is blank (no user command present)
        current_input = self.get('input', 'end-1c')
        if not current_input.strip():
            self.insert("insert", txt, "input")
            self.insert_cmd(self.get("input", "end"))
        else:
            if '\n' not in current_input:
                self.insert("insert", txt, "input")
            else:
                # Multiline: insert at cursor, preserving line breaks and adding prompt
                cursor_index = self.index("insert")
                line_idx, col_idx = map(int, cursor_index.split('.'))
                prompt = self._prompt2 if hasattr(self, '_prompt2') else '... '
                lines = txt.splitlines()

                # Insert the first line at the cursor position
                self.insert("insert", lines[0])

                # For subsequent lines, insert a newline, prompt, and the line
                for line in lines[1:]:
                    self.insert("insert", "\n")
                    self.insert("insert", prompt, "prompt")
                    self.insert("insert", line)

                if len(lines) > 1:
                    # Move cursor to the end of the input multiline text
                    self.mark_set("insert", "end-1c")
                    self.see("insert")

        return 'break'

    def prompt(self, result=False):
        """Insert a prompt"""
        if result:
            self.insert('end', self._prompt2, 'prompt')
        else:
            self.insert('end', self._prompt1, 'prompt')
        self.mark_set('input', 'end-1c')
        self.edit_reset()

    def insert_prompt(self, prompt_type="primary", index="insert"):
        """
        Insert the prompt at the given index with the correct tag.
        prompt_type: "primary" for >>>, "secondary" for ...
        """
        if prompt_type == "primary":
            self.insert(index, self._prompt1, "prompt")
            self.edit_reset()
        elif prompt_type == "secondary":
            self.insert(index, self._prompt2, "prompt")

    def is_command_edited(self):
        """
        Returns True if the current input (with prompts removed) is different from the current history entry.
        """
        # Get the raw input text
        current_input = self.get('input', 'end-1c')
        # Remove all prompts (">>> " and "... ") from the beginning of each line
        lines = current_input.splitlines()
        cleaned_lines = []
        for line in lines:
            if line.startswith(self._prompt1):
                cleaned_lines.append(line[len(self._prompt1):])
            elif line.startswith(self._prompt2):
                cleaned_lines.append(line[len(self._prompt2):])
            else:
                cleaned_lines.append(line)
        cleaned_input = '\n'.join(cleaned_lines)

        # If _hist_item is None or out of range, treat as blank/new input
        if getattr(self, '_hist_item', None) is not None and 0 <= self._hist_item < len(self.history):
            history_entry = self.history[self._hist_item]
        else:
            history_entry = ''
        return cleaned_input.strip() != history_entry.strip()

    def flash_prompt_warning(self, duration=200):
        """
        Temporarily reverse the foreground and background colors of the prompt tag as a warning.
        """
        # Get current colors
        self.tag_configure("prompt", background="red")
        # Restore after duration
        self.after(duration, lambda: self.tag_configure("prompt", background="white"))

    def on_escape(self, event=None):
        """
        When pressing Esc, jump to the last blank command (empty input) in history.
        """
        """
        if self.is_command_edited():
            self.flash_prompt_warning()
            return "break"
        """
        self.edit_separator()
        line = self._hist_match
        self._hist_item = len(self.history)

        self._hist_item = len(self.history)
        self.delete('input', 'end')
        self.insert('insert', line)
        self.edit_reset()

        return 'break'

    def on_up(self, event):
        """Handle up arrow key press: navigate history only from first line"""
        try:
            self.index("sel.first")
            # There is a selection, do nothing
        except tk.TclError:
            # No selection
            if self.tag_names("insert"):
                self.edit_reset()
                return "break"
        self.edit_separator()
        if self.compare('insert linestart', '==', 'input linestart'):
            if self.is_command_edited():
                self.flash_prompt_warning()
                return "break"
            # Get current input line for matching
            first_line_input = self.get('input', 'insert')
            
            # If we're starting a new search (first up arrow press), initialize
            if self._hist_item == len(self.history):
                self._hist_match = first_line_input
                # Start from the last (most recent) history item
                self._hist_item = len(self.history) - 1
            else:
                # Continue navigating backward from current position
                self._hist_item -= 1
            
            # Find the next matching history item going backward
            found_match = False
            while self._hist_item >= 0:
                item = self.history[self._hist_item]
                # Check if this history item starts with our match string
                if item.startswith(self._hist_match):
                    found_match = True
                    break
                self._hist_item -= 1
            
            if found_match:
                # Found a matching item, insert it
                self.insert_cmd(self.history[self._hist_item])
            else:
                # No more matches found, wrap around to find the last matching item
                self._hist_item = len(self.history) - 1
                while self._hist_item >= 0:
                    item = self.history[self._hist_item]
                    if item.startswith(self._hist_match):
                        self.insert_cmd(self.history[self._hist_item])
                        break
                    self._hist_item -= 1
                
                if self._hist_item < 0:
                    # No matches at all, restore to end position
                    self._hist_item = len(self.history)
            
            self.edit_reset()
            return 'break'
        
        # Allow normal movement within multiline input
        return None

    def on_down(self, event):
        """Handle down arrow key press: navigate history only from last line"""
        try:
            self.index("sel.first")
            # There is a selection, do nothing
        except tk.TclError:
            # No selection
            if self.tag_names("insert"):
                self.edit_reset()
                return "break"
        self.edit_separator()
        if self.compare('insert lineend', '==', 'end-1c'):
            if self.is_command_edited():
                self.flash_prompt_warning()
                return "break"
            line = self._hist_match
            self._hist_item += 1

            while self._hist_item < len(self.history):
                item = self.history[self._hist_item]
                if item.startswith(line):
                    break
                self._hist_item += 1

            if self._hist_item < len(self.history):
                self.insert_cmd(self.history[self._hist_item])
                self.mark_set('insert', 'end-1c')
            else:
                self._hist_item = len(self.history)
                self.delete('input', 'end')
                self.insert('insert', line)

            self.edit_reset()
            return 'break'
        # Else: allow normal movement within multiline
        return

    def on_shift_tab(self, event):
        """
        Move the cursor back by up to 4 spaces if possible (like un-indenting),
        but do not move back if at the beginning of a line after the prompt.
        """
        cursor_index = self.index("insert")
        line_start = self.index(f"{cursor_index} linestart")
        line_text = self.get(line_start, f"{line_start} lineend")

        # Determine prompt length for this line
        if line_text.startswith(self._prompt1):
            prompt_len = len(self._prompt1)
        elif line_text.startswith(self._prompt2):
            prompt_len = len(self._prompt2)
        else:
            prompt_len = 0

        prompt_end = f"{line_start}+{prompt_len}c"
        # If at the beginning of input (just after prompt), do nothing
        if self.compare(cursor_index, "==", prompt_end):
            return "break"

        before_cursor = self.get(line_start, cursor_index)
        # Count spaces before cursor (up to 4)
        spaces = 0
        for c in reversed(before_cursor):
            if c == " " and spaces < 4:
                spaces += 1
            else:
                break
        if spaces > 0:
            self.delete(f"{cursor_index} -{spaces}c", cursor_index)
        return "break"

    def on_tab(self, event):
        """Handle tab key press"""
        self.edit_separator()
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

    def go_to_end(self, event):
        """Move the cursor to the end of the last line of input."""
        self.edit_separator()
        self.mark_set('insert', 'end-1c')
        return 'break'

    def _move_to_line_start(self, event):
        index = self.index("insert linestart")
        self.mark_set("insert", index)
        self.see(index)
        return "break"

    def _move_to_line_end(self, event):
        index = self.index("insert lineend")
        self.mark_set("insert", index)
        self.see(index)
        return "break"

    def on_return(self, event=None):
        """Handle Return key press with modal for mid-line or multiline editing."""
        self.edit_separator()
        input_start = self.index('input')
        input_end = self.index('end-1c')
        insert_pos = self.index('insert')
        full_text = self.get('input', 'end-1c')

        # Avoid popup if the command is blank (only whitespace or empty)
        if not full_text.strip():
            self.mark_set('insert', 'end-1c')
            self.eval_current(True)
            self.see('end')
            self._hist_item = len(self.history) 
            self.history.save()
            return 'break'

        lines = full_text.splitlines()
        is_multiline = len(lines) > 1

        # Always show modal for multiline, or for single line if not at end
        if is_multiline or not self.compare('insert', '==', 'end-1c'):
            # Gather cursor info
            cursor_index = self.index('insert')
            cursor_line, cursor_col = map(int, cursor_index.split('.'))
            input_line_start = int(input_start.split('.')[0])
            rel_line = cursor_line - input_line_start

            # Prepare display lines (no marker, just dual color)
            display_lines = []
            for i, line in enumerate(lines):
                if i == 0:
                    # Add the prompt to the first line
                    display_lines.append(self._prompt1 + line)
                else:
                    display_lines.append(line)
            display_text = '\n'.join(display_lines)

            def show_modal():
                modal = tk.Toplevel(self)
                modal.title("Edit Command")
                modal.transient(self)
                modal.grab_set()

                frame = tk.Frame(modal)
                frame.pack(fill="both", expand=True)

                # Create the Text widget with no wrapping for horizontal scrolling
                text_widget = tk.Text(frame, wrap="none")
                text_widget.grid(row=0, column=0, sticky="nsew")

                # Create vertical and horizontal scrollbars
                yscroll = tk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
                xscroll = tk.Scrollbar(frame, orient="horizontal", command=text_widget.xview)
                yscroll.grid(row=0, column=1, sticky="ns")
                xscroll.grid(row=1, column=0, sticky="ew")

                # Configure the Text widget to use the scrollbars
                text_widget.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

                # Make the frame expandable
                frame.rowconfigure(0, weight=1)
                frame.columnconfigure(0, weight=1)

                text_widget.insert("1.0", display_text)
                text_widget.focus_set()

                # Dual color for the edited line
                # Determine if editing the first line of the input
                if rel_line == 0:
                    prompt_length = len(self._prompt1)
                    cursor_col_in_input = max(0, cursor_col - prompt_length)
                    # Add prompt length back for tag indices in the modal
                    before_cursor_idx = f"{rel_line+1}.0"
                    cursor_idx = f"{rel_line+1}.{cursor_col_in_input + prompt_length}"
                else:
                    before_cursor_idx = f"{rel_line+1}.0"
                    cursor_idx = f"{rel_line+1}.{cursor_col}"
                end_idx = f"{rel_line+1}.end"

                # Center the edited line in the text widget
                def center_line_in_text_widget(text_widget, rel_line1):
                    def do_scroll():
                        if not text_widget.winfo_exists():
                            return  # Widget destroyed
                        dline = text_widget.dlineinfo("1.0")
                        if not dline:
                            text_widget.after(20, do_scroll)
                            return
                        line_height = dline[3]
                        visible_lines = int(text_widget.winfo_height() // line_height)
                        total_lines = int(text_widget.index("end-1c").split('.')[0])
                        # Clamp rel_line to valid range
                        rel_line = max(1, min(rel_line1, total_lines))
                        first_visible = max(rel_line - visible_lines // 2, 1)
                        yview_value = (first_visible - 1) / max(total_lines - visible_lines + 1, 1)
                        text_widget.yview_moveto(yview_value)
                    text_widget.after(0, do_scroll)
                center_line_in_text_widget(text_widget, rel_line)

                text_widget.tag_add("before_cursor", before_cursor_idx, cursor_idx)
                text_widget.tag_configure("before_cursor", background="yellow")
                text_widget.tag_add("after_cursor", cursor_idx, end_idx)
                text_widget.tag_configure("after_cursor", background="lightgreen")
                text_widget.config(state="disabled")

                # Escape closes modal
                modal.bind("<Escape>", lambda e: modal.destroy())

                # Button actions
                def confirm_and_execute():
                    modal.destroy()
                    self.mark_set('insert', 'end-1c')
                    self.eval_current(True)
                    self.see('end')
                    self.history.save()

                def add_newline_here():
                    modal.destroy()
                    self.insert('insert', '\n')
                    self.insert('insert', self._prompt2, 'prompt')
                    self.see('insert')
                    total_lines = int(self.index('end-1c').split('.')[0])
                    current_line = int(self.index('insert').split('.')[0])
                    center_frac = max(0, (current_line - int(self['height']) // 2) / max(1, total_lines))
                    self.yview_moveto(center_frac)

                def remove_current_line():
                    modal.destroy()
                    line_start = f"{cursor_line}.0"
                    line_end = f"{cursor_line}.end+1c"
                    self.delete(line_start, line_end)

                def do_nothing():
                    modal.destroy()

                btn_frame = tk.Frame(modal)
                btn_frame.pack(pady=(0, 10))

                confirm_btn = tk.Button(btn_frame, text="Confirm & Execute", command=confirm_and_execute)
                confirm_btn.pack(side="left", padx=5)
                confirm_btn.focus_set()  # Set initial focus
                confirm_btn.bind("<Return>", lambda e: confirm_and_execute())

                add_btn = tk.Button(btn_frame, text="Add New Line Here", command=add_newline_here)
                add_btn.pack(side="left", padx=5)
                add_btn.bind("<Return>", lambda e: add_newline_here())

                remove_btn = tk.Button(btn_frame, text="Remove This Line", command=remove_current_line)
                remove_btn.pack(side="left", padx=5)
                remove_btn.bind("<Return>", lambda e: remove_current_line())

                def discard_everything():
                    modal.destroy()
                    self.on_escape()  # Or your logic to clear input and reset state

                discard_btn = tk.Button(btn_frame, text="Discard Everything", command=discard_everything)
                discard_btn.pack(side="left", padx=5)

                nothing_btn = tk.Button(btn_frame, text="Do Nothing", command=do_nothing)
                nothing_btn.pack(side="left", padx=5)
                nothing_btn.bind("<Return>", lambda e: do_nothing())

                # After creating and packing the buttons:
                buttons = [confirm_btn, add_btn, remove_btn, discard_btn, nothing_btn]

                def focus_next(event):
                    idx = buttons.index(event.widget)
                    buttons[(idx + 1) % len(buttons)].focus_set()
                    return "break"

                def focus_prev(event):
                    idx = buttons.index(event.widget)
                    buttons[(idx - 1) % len(buttons)].focus_set()
                    return "break"

                for btn in buttons:
                    btn.bind("<Right>", focus_next)
                    btn.bind("<Left>", focus_prev)

                modal.wait_window()

            self.after(10, show_modal)
            return 'break'

        # Default: execute the command
        self.eval_current(True)
        self.see('end')
        self.history.save()
        return 'break'

    def insert_line(self, event=None):
        """Handle Ctrl+Return key press"""
        self.edit_separator()
        self.insert('insert', '\n' + self._prompt2, "prompt" )
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
        self.delete('input', 'end')
        lines = cmd.splitlines()
        if not lines:
            return

        # Determine base indentation
        indent = len(re.search(r'^( )*', lines[0]).group())

        # Record current insert position as new input mark
        input_index = self.index('insert')
        self.insert('insert', lines[0][indent:])

        for line in lines[1:]:
            line = line[indent:]
            self.insert('insert', '\n')
            self.prompt(True)
            self.insert('insert', line)

        # Set the 'input' mark at the correct place (start of inserted block)
        self.mark_set('input', input_index)
        self.see('end')

    def eval_current(self, auto_indent=False):
        """Evaluate code"""
        index = self.index('input')
        lines = self.get('input', 'insert lineend').splitlines() # commands to execute
        self.mark_set('insert', 'insert lineend')
        self._hist_item = len(self.history)  # set history item to the end
        
        if lines:  # there is code to execute
            # remove prompts
            lines = [lines[0].rstrip()] + [line[len(self._prompt2):].rstrip() for line in lines[1:]]
            for i, l in enumerate(lines):
                if l.endswith('?'):
                    lines[i] = 'help(%s)' % l[:-1]
            cmds = '\n'.join(lines)
            self.insert('insert', '\n', "output")
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
                
                # Save error commands to history if option is enabled
                if self._save_errors_in_history.get() and lines:
                    cmd_text = '\n'.join(lines)
                    if not self.history or self.history[-1] != cmd_text:
                        self.history.append(cmd_text)
                        self._hist_item = len(self.history)
            else:
                output = out.getvalue()  # get output
                if output:
                    self.insert('end', output, 'output')
                
                # Check if there's a result from expression evaluation
                if not res:  # Command was complete
                    last_result = self._console.get_last_result()
                    if last_result is not None:
                        # Display the result of the expression
                        result_str = repr(last_result) + '\n'
                        self.insert('end', result_str, 'output')
                
                self.mark_set('input', 'end')
                self.see('end')
                if not res and self.compare('insert linestart', '>', 'insert'):
                    self.insert('insert', '\n', "output")
                self.prompt(res)
                
                # Handle auto-indentation logic
                if auto_indent and lines and res:  # Only auto-indent for incomplete commands
                    # insert indentation similar to previous lines
                    indent = re.search(r'^( )*', lines[-1]).group()
                    line = lines[-1].strip()
                    if line and line[-1] == ':':
                        indent = indent + '    '
                    self.insert('insert', indent, "output")
                # For complete commands (res is False), don't auto-indent - start fresh
                
                self.see('end')
                if res:
                    self.mark_set('input', index)
                    self._console.resetbuffer()  # clear buffer since the whole command will be retrieved from the text widget
                elif lines:
                    # join back into one multiline string, so history stores real newlines
                    cmd_text = '\n'.join(lines)
                    # avoid duplicate consecutive entries
                    if not self.history or self.history[-1] != cmd_text:
                        self.history.append(cmd_text)
                        self._hist_item = len(self.history)
            out.close()
            err.close()
        else:
            self.insert('insert', '\n', "output")
            self.prompt()

    def on_key_press(self, event):
        """
        Prevent character insertion if the cursor is over a character with any tag (e.g., prompt).
        """
        # Only block printable characters (not navigation, etc.)
        if event.char and event.char.isprintable():
            cursor_index = self.index("insert")
            tags = self.tag_names(cursor_index)
            if tags:
                return "break"

    def _process_arrows(self, direction):
        """
        Handles Left and Right arrow navigation.
        Does nothing if there is an active selection.
        """
        self.edit_separator()
        try:
            sel_start = self.index("sel.first")
            sel_end = self.index("sel.last")
            # If selection is active, do not process arrow keys
            return
        except tk.TclError:
            pass  # No selection, proceed as normal

        cursor_index = self.index("insert")
        line_start = self.index(f"{cursor_index} linestart")
        line_end = self.index(f"{line_start} lineend")

        if direction == "Left":
            idx = cursor_index
            while self.compare(idx, ">", line_start):
                tags = self.tag_names(idx)
                if not tags:
                    self.mark_set("insert", idx)
                    return
                idx = self.index(f"{idx} -1c")
            # If we reach the start of the line, check the last character of the previous line
            if self.compare(idx, "==", line_start):
                prev_line_num = int(line_start.split('.')[0]) - 1
                if prev_line_num >= 1:
                    prev_line_start = f"{prev_line_num}.0"
                    prev_line_end = self.index(f"{prev_line_start} lineend")
                    # Check if the last character of the previous line is not tagged
                    last_char_idx = self.index(f"{prev_line_end} -1c")
                    tags = self.tag_names(last_char_idx)
                    if not tags:
                        self.mark_set("insert", prev_line_end)
                        return
                # Otherwise, scan forward to find the first non-tagged character (existing behaviour)
                scan_idx = line_start
                line_end = self.index(f"{line_start} lineend")
                while self.compare(scan_idx, "<", line_end):
                    tags = self.tag_names(scan_idx)
                    if not tags:
                        self.mark_set("insert", scan_idx)
                        return
                    scan_idx = self.index(f"{scan_idx} +1c")
                self.mark_set("insert", line_end)

        elif direction == "Right":
            idx = cursor_index
            while self.compare(idx, "<", line_end):
                tags = self.tag_names(idx)
                if not tags:
                    self.mark_set("insert", idx)
                    return
                idx = self.index(f"{idx} +1c")
            # If we reach the end of the line, set cursor there
            self.mark_set("insert", line_end)


class TextConsole(BaseTextConsole):
    """Default implementation of the console"""
    pass
