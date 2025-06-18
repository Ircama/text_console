import tkinter as tk

class CommandHistoryPanel:
    def __init__(self, master, history, insert_cmd_callback, hist_item_ref, close_callback=None):
        self.master = master
        self.history = history
        self.insert_cmd_callback = insert_cmd_callback
        self.hist_item_ref = hist_item_ref
        self.close_callback = close_callback
        self.window = None

    def show(self):
        """Open a separate window with the output of the history, or raise it if already open."""
        if hasattr(self.master, '_history_window') and self.master._history_window is not None:
            try:
                self.master._history_window.lift()
                self.master._history_window.focus_force()
                return
            except Exception:
                self.master._history_window = None  # Window was closed externally
        self.window = tk.Toplevel(self.master)
        self.master._history_window = self.window
        self.window.title("Command History")
        self.window.geometry("600x600")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_ui()
        self.history_txt.see("1.0")
        self.window.after(200, self.delayed_setup)

    def _build_ui(self):
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        header_frame = tk.Frame(main_frame, bg="white", relief="solid", bd=1)
        header_frame.pack(fill="x", pady=(0, 5))
        self.header_label = tk.Label(
            header_frame, 
            text="№     │ Command",
            font=("Consolas", 10, "bold"),
            fg="#000080",
            bg="white",
            anchor="w",
            padx=5,
            pady=3
        )
        self.header_label.pack(fill="x")
        # --- Search bar frame ---
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Consolas", 10))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.btn_up = tk.Button(search_frame, text="↑", width=2)
        self.btn_up.pack(side="left")
        self.btn_down = tk.Button(search_frame, text="↓", width=2)
        self.btn_down.pack(side="left")
        self.window.after(300, self.focus_search_entry_delayed)
        # --- End search bar frame ---
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        v_scrollbar = tk.Scrollbar(text_frame, orient="vertical")
        h_scrollbar = tk.Scrollbar(text_frame, orient="horizontal")
        self.history_txt = tk.Text(
            text_frame, 
            wrap="none",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            font=("Consolas", 10),
            bg="white",
            fg="black",
            selectbackground="#cce7ff"
        )
        v_scrollbar.config(command=self.history_txt.yview)
        h_scrollbar.config(command=self.history_txt.xview)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.history_txt.pack(fill="both", expand=True)
        self.history_txt.tag_configure("number", foreground="#0066cc", font=("Consolas", 10, "bold"))
        self.history_txt.tag_configure("number_hover", background="#e0f0ff")
        self.history_txt.tag_configure("separator", foreground="#888888")
        self.history_txt.tag_configure("command", foreground="#000000", font=("Consolas", 10))
        self.history_txt.tag_configure("divider", foreground="#cccccc", selectbackground="white", selectforeground="#cccccc")
        self.history_txt.tag_configure("nonselectable", foreground="#0066cc", font=("Consolas", 10, "bold"), selectbackground="white", selectforeground="#0066cc")
        self.history_txt.config(state="disabled")
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(5, 0))
        self.status_label = tk.Label(
            status_frame, 
            text=f"Total commands: {len(self.history)}. Right-click or Ctrl+C to copy. Double-click to copy line",
            relief="sunken",
            anchor="w"
        )
        self.status_label.pack(fill="x")
        self.history_txt.see("1.0")
        # Context menu
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="Copy Selected", command=self.copy_selected_command)
        self.context_menu.add_command(label="Close", command=self.window.destroy)
        self.window.bind("<Button-3>", lambda e: self.context_menu.post(e.x_root, e.y_root))
        self.window.bind("<Control-w>", lambda e: self.window.destroy())
        self.window.bind("<Escape>", lambda e: self.window.destroy())
        # Search navigation state
        self.search_matches = []
        self.search_index = [0]
        # Bindings
        self.history_txt.bind("<Control-c>", self.copy_selected_command)
        self.history_txt.bind("<Control-C>", self.copy_selected_command)
        self.search_entry.bind("<Return>", self.on_search_enter)
        self.btn_up.config(command=self.on_search_up)
        self.btn_down.config(command=self.on_search_down)
        self.search_entry.bind("<Control-Up>", lambda e: self.on_search_up())
        self.search_entry.bind("<Control-Down>", lambda e: self.on_search_down())
        self.window.bind('<Control-s>', self.load_selected_to_main)
        self.window.bind('<Control-n>', lambda e: self.on_search_down())
        self.window.bind('<Control-b>', lambda e: self.on_search_up())
        self.window.bind('<Escape>', self.close_history_panel)
        self.history_txt.bind("<ButtonRelease-1>", self.on_selection)
        self.history_txt.bind("<B1-Motion>", self.on_selection)
        self.history_txt.bind("<Double-Button-1>", self.on_number_double_click)
        self.history_txt.bind("<Enter>", self.on_number_enter)
        self.history_txt.bind("<Leave>", self.on_number_leave)
        self.window.bind('<Configure>', self.on_window_configure)

    def delayed_setup(self):
        self.update_display()
        self.history_txt.focus_set()
        self.history_txt.see("1.0")

    def focus_search_entry_delayed(self):
        self.search_entry.focus_set()

    def on_close(self):
        self.master._history_window = None
        if self.close_callback:
            self.close_callback()
        self.window.destroy()

    def calculate_layout(self):
        try:
            text_width_pixels = self.history_txt.winfo_width()
            char_width = 8
            widget_width = max(80, text_width_pixels // char_width)
        except:
            widget_width = max(100, (self.window.winfo_width() - 80) // 8)
        max_command_length = 0
        for command in self.history:
            for line in str(command).split('\n'):
                max_command_length = max(max_command_length, len(line))
        num_width = max(5, len(str(len(self.history))))
        cmd_width = max(50, widget_width - num_width - 3)
        return num_width, cmd_width, max_command_length, widget_width

    def on_window_configure(self, event=None):
        if event and event.widget == self.window:
            self.update_display()

    def on_number_double_click(self, event):
        index = self.history_txt.index(f"@{event.x},{event.y}")
        line = int(index.split('.')[0])
        num_text = self.history_txt.get(f"{line}.0", f"{line}.end").split('│')[0].strip()
        try:
            hist_index = int(num_text) - 1
            if 0 <= hist_index < len(self.history):
                self.hist_item_ref[0] = hist_index
                print(f"[DEBUG] Double-clicked history item {hist_index}: {self.history[hist_index]}")
                self.insert_cmd_callback(self.history[hist_index])
                self.master.focus_set()  # Ensure main panel gets focus
                self.window.lift()
        except Exception as e:
            print(f"[DEBUG] Error in on_number_double_click: {e}")
            pass

    def on_number_enter(self, event):
        self.history_txt.config(cursor="hand2")
        index = self.history_txt.index(f"@{event.x},{event.y}")
        line = index.split('.')[0]
        sep_index = self.history_txt.get(f"{line}.0", f"{line}.end").find("│")
        if sep_index != -1:
            self.history_txt.tag_add("number_hover", f"{line}.0", f"{line}.{sep_index}")

    def on_number_leave(self, event):
        self.history_txt.config(cursor="")
        self.history_txt.tag_remove("number_hover", "1.0", "end")

    def on_selection(self, event=None):
        try:
            sel_start = self.history_txt.index("sel.first")
            sel_end = self.history_txt.index("sel.last")
            start_line = int(sel_start.split('.')[0])
            end_line = int(sel_end.split('.')[0])
            for line in range(start_line, end_line + 1):
                line_content = self.history_txt.get(f"{line}.0", f"{line}.end")
                sep_index = line_content.find("│")
                if sep_index != -1:
                    self.history_txt.tag_remove("sel", f"{line}.0", f"{line}.{sep_index+1}")
                if set(line_content.strip()) == {"─"}:
                    self.history_txt.tag_remove("sel", f"{line}.0", f"{line}.end")
        except tk.TclError:
            pass

    def update_display(self):
        self.history_txt.config(state="normal")
        self.history_txt.delete("1.0", "end")
        num_width, cmd_width, max_cmd_length, total_width = self.calculate_layout()
        header_text = f"{'№':<{num_width}}│ Command"
        self.header_label.config(text=header_text)
        for i, command in enumerate(reversed(self.history)):
            item_number = len(self.history) - i
            command_text = str(command).strip()
            command_lines = command_text.split('\n')
            first_line = command_lines[0] if command_lines else ""
            tag_name = f"numtag_{item_number}"
            start_idx = self.history_txt.index("end-1c")
            self.history_txt.insert("end", f"{item_number:<{num_width}}", ("number", "nonselectable", tag_name))
            end_idx = self.history_txt.index("end-1c")
            self.history_txt.insert("end", " │ ", ("separator", "nonselectable"))
            self.history_txt.insert("end", f"{first_line}\n", "command")
            # Bind number column events for this tag
            self.history_txt.tag_bind(tag_name, "<Double-Button-1>", self.on_number_double_click)
            self.history_txt.tag_bind(tag_name, "<Enter>", self.on_number_enter)
            self.history_txt.tag_bind(tag_name, "<Leave>", self.on_number_leave)
            for line in command_lines[1:]:
                self.history_txt.insert("end", f"{'':<{num_width}}", "nonselectable")
                self.history_txt.insert("end", " │ ", ("separator", "nonselectable"))
                self.history_txt.insert("end", f"{line}\n", "command")
            if i < len(self.history) - 1:
                self.history_txt.insert("end", "─" * total_width, "divider")
                self.history_txt.insert("end", "\n")
        self.history_txt.config(state="disabled")

    def copy_selected_command(self, event=None):
        try:
            sel_start = self.history_txt.index("sel.first")
            sel_end = self.history_txt.index("sel.last")
            start_line = int(sel_start.split('.')[0])
            end_line = int(sel_end.split('.')[0])
            result_lines = []
            for line in range(start_line, end_line + 1):
                line_content = self.history_txt.get(f"{line}.0", f"{line}.end")
                if set(line_content.strip()) == {"─"}:
                    continue
                sep_index = line_content.find("│")
                if sep_index != -1:
                    command_part = line_content[sep_index+1:]
                    sel_line_start = max(int(sel_start.split('.')[1]), 0) if line == start_line else 0
                    sel_line_end = int(sel_end.split('.')[1]) if line == end_line else len(line_content)
                    if sel_line_end > sep_index:
                        result_lines.append(command_part.rstrip("\n"))
                else:
                    result_lines.append(line_content.rstrip("\n"))
            command_text = '\n'.join(result_lines).rstrip("\n")
            if command_text:
                self.window.clipboard_clear()
                self.window.clipboard_append(command_text)
        except tk.TclError:
            pass
        return "break"

    def search_history(self, forward=True):
        pattern = self.search_var.get().strip()
        self.history_txt.tag_remove("sel", "1.0", "end")
        if not pattern:
            return
        matches = []
        for i in range(1, int(self.history_txt.index("end-1c").split(".")[0])):
            line_content = self.history_txt.get(f"{i}.0", f"{i}.end")
            sep_index = line_content.find("│")
            if sep_index != -1:
                command_part = line_content[sep_index+1:]
                col_offset = sep_index + 1
                idx = command_part.lower().find(pattern.lower())
                if idx != -1:
                    matches.append((i, col_offset + idx, col_offset + idx + len(pattern)))
        if not matches:
            self.search_index[0] = 0
            return
        if forward:
            self.search_index[0] = (self.search_index[0] + 1) % len(matches) if self.search_index[0] < len(matches) else 0
        else:
            self.search_index[0] = (self.search_index[0] - 1) % len(matches)
        line, start_col, end_col = matches[self.search_index[0]]
        self.history_txt.see(f"{line}.0")
        self.history_txt.tag_add("sel", f"{line}.{start_col}", f"{line}.{end_col}")
        self.history_txt.mark_set("insert", f"{line}.{start_col}")
        self.history_txt.focus_set()
        self.search_matches.clear()
        self.search_matches.extend(matches)

    def on_search_enter(self, event=None):
        self.search_index[0] = -1
        self.search_history(forward=True)

    def on_search_up(self, event=None):
        if self.search_matches:
            self.search_history(forward=False)

    def on_search_down(self, event=None):
        if self.search_matches:
            self.search_history(forward=True)

    def load_selected_to_main(self, event=None):
        if self.search_matches and 0 <= self.search_index[0] < len(self.search_matches):
            line, start_col, end_col = self.search_matches[self.search_index[0]]
            num_text = self.history_txt.get(f"{line}.0", f"{line}.end").split('│')[0].strip()
            try:
                hist_index = int(num_text) - 1
                if 0 <= hist_index < len(self.history):
                    self.hist_item_ref[0] = hist_index
                    self.insert_cmd_callback(self.history[hist_index])
                    self.window.lift()
            except Exception as e:
                print(f"[DEBUG] Error in load_selected_to_main: {e}")
                pass

    def close_history_panel(self, event=None):
        if hasattr(self.master, '_history_window') and self.master._history_window is not None:
            self.master._history_window.destroy()
            self.master._history_window = None






def dump_history(self):
    """Open a separate window with the output of the history, or raise it if already open."""
    if hasattr(self, '_history_window') and self._history_window is not None:
        try:
            self._history_window.lift()
            self._history_window.focus_force()
            return
        except Exception:
            self._history_window = None  # Window was closed externally
    self._history_window = tk.Toplevel(self)
    history_window = self._history_window
    history_window.title("Command History")
    history_window.geometry("600x600")
    
    def on_close():
        self._history_window = None
        history_window.destroy()
    history_window.protocol("WM_DELETE_WINDOW", on_close)
    
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
    
    # --- Search bar frame ---
    search_frame = tk.Frame(main_frame)
    search_frame.pack(fill="x", pady=(0, 5))
    search_var = tk.StringVar()
    search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Consolas", 10))
    search_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
    btn_up = tk.Button(search_frame, text="↑", width=2)
    btn_up.pack(side="left")
    btn_down = tk.Button(search_frame, text="↓", width=2)
    btn_down.pack(side="left")
    # --- End search bar frame ---
    def focus_search_entry_delayed():
        search_entry.focus_set()
    history_window.after(300, focus_search_entry_delayed)

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
    history_txt.tag_configure("number_hover", background="#e0f0ff")
    history_txt.tag_configure("separator", foreground="#888888")
    history_txt.tag_configure("command", foreground="#000000", font=("Consolas", 10))
    history_txt.tag_configure("divider", foreground="#cccccc", selectbackground="white", selectforeground="#cccccc")
    history_txt.tag_configure("nonselectable", foreground="#0066cc", font=("Consolas", 10, "bold"), selectbackground="white", selectforeground="#0066cc")

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
    
    def on_number_double_click(event):
        index = history_txt.index(f"@{event.x},{event.y}")
        line = int(index.split('.')[0])
        num_text = history_txt.get(f"{line}.0", f"{line}.end").split('│')[0].strip()
        try:
            hist_index = int(num_text) - 1
            if 0 <= hist_index < len(self.history):
                self._hist_item = hist_index
                self.insert_cmd(self.history[hist_index])
                history_window.lift()
        except Exception:
            pass

    def on_number_enter(event):
        history_txt.config(cursor="hand2")
        index = history_txt.index(f"@{event.x},{event.y}")
        line = index.split('.')[0]
        # Only highlight the number column, not the command
        sep_index = history_txt.get(f"{line}.0", f"{line}.end").find("│")
        if sep_index != -1:
            history_txt.tag_add("number_hover", f"{line}.0", f"{line}.{sep_index}")
    def on_number_leave(event):
        history_txt.config(cursor="")
        history_txt.tag_remove("number_hover", "1.0", "end")

    def on_selection(event=None):
        try:
            sel_start = history_txt.index("sel.first")
            sel_end = history_txt.index("sel.last")
            start_line = int(sel_start.split('.')[0])
            end_line = int(sel_end.split('.')[0])
            for line in range(start_line, end_line + 1):
                line_content = history_txt.get(f"{line}.0", f"{line}.end")
                sep_index = line_content.find("│")
                if sep_index != -1:
                    # Remove selection from number column
                    history_txt.tag_remove("sel", f"{line}.0", f"{line}.{sep_index+1}")
                # Remove selection from divider lines
                if set(line_content.strip()) == {"─"}:
                    history_txt.tag_remove("sel", f"{line}.0", f"{line}.end")
        except tk.TclError:
            pass

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
            command_lines = command_text.split('\n')
            first_line = command_lines[0] if command_lines else ""
            tag_name = f"numtag_{item_number}"
            start_idx = history_txt.index("end-1c")
            history_txt.insert("end", f"{item_number:<{num_width}}", ("number", "nonselectable", tag_name))
            end_idx = history_txt.index("end-1c")
            history_txt.insert("end", " │ ", ("separator", "nonselectable"))
            history_txt.insert("end", f"{first_line}\n", "command")
            # Bind number column events for this tag
            history_txt.tag_bind(tag_name, "<Double-Button-1>", on_number_double_click)
            history_txt.tag_bind(tag_name, "<Enter>", on_number_enter)
            history_txt.tag_bind(tag_name, "<Leave>", on_number_leave)
            for line in command_lines[1:]:
                history_txt.insert("end", f"{'':<{num_width}}", "nonselectable")
                history_txt.insert("end", " │ ", ("separator", "nonselectable"))
                history_txt.insert("end", f"{line}\n", "command")
            if i < len(self.history) - 1:
                history_txt.insert("end", "─" * total_width, "divider")
                history_txt.insert("end", "\n")
        
        # Bind double-click for all number tags
        for i in range(1, len(self.history)+1):
            history_txt.tag_bind(f"numtag_{i}", "<Double-Button-1>", on_number_double_click)
            history_txt.tag_bind(f"numtag_{i}", "<Enter>", on_number_enter)
            history_txt.tag_bind(f"numtag_{i}", "<Leave>", on_number_leave)
    
        history_txt.config(state="disabled")
    
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

    def copy_selected_command(event=None):
        try:
            sel_start = history_txt.index("sel.first")
            sel_end = history_txt.index("sel.last")
            start_line = int(sel_start.split('.')[0])
            end_line = int(sel_end.split('.')[0])
            result_lines = []
            for line in range(start_line, end_line + 1):
                line_content = history_txt.get(f"{line}.0", f"{line}.end")
                # Skip divider lines
                if set(line_content.strip()) == {"─"}:
                    continue
                sep_index = line_content.find("│")
                if sep_index != -1:
                    # Preserve all whitespace after the separator
                    command_part = line_content[sep_index+1:]
                    sel_line_start = max(int(sel_start.split('.')[1]), 0) if line == start_line else 0
                    sel_line_end = int(sel_end.split('.')[1]) if line == end_line else len(line_content)
                    # Only add if selection is after separator
                    if sel_line_end > sep_index:
                        result_lines.append(command_part.rstrip("\n"))
                else:
                    result_lines.append(line_content.rstrip("\n"))
            command_text = '\n'.join(result_lines).rstrip("\n")
            if command_text:
                history_window.clipboard_clear()
                history_window.clipboard_append(command_text)
        except tk.TclError:
            pass
        return "break"
    
    history_txt.bind("<Control-c>", copy_selected_command)
    history_txt.bind("<Control-C>", copy_selected_command)
    
    context_menu = tk.Menu(history_window, tearoff=0)
    context_menu.add_command(label="Copy Selected", command=copy_selected_command)
    context_menu.add_command(label="Close", command=history_window.destroy)
    history_window.bind("<Button-3>", lambda e: context_menu.post(e.x_root, e.y_root))
    history_window.bind("<Control-w>", lambda e: history_window.destroy())
    history_window.bind("<Escape>", lambda e: history_window.destroy())

    # State for search navigation
    search_matches = []
    search_index = [0]  # Use list for mutability in closures

    def search_history(forward=True):
        pattern = search_var.get().strip()
        history_txt.tag_remove("sel", "1.0", "end")
        if not pattern:
            return
        matches = []
        for i in range(1, int(history_txt.index("end-1c").split(".")[0])):
            line_content = history_txt.get(f"{i}.0", f"{i}.end")
            sep_index = line_content.find("│")
            if sep_index != -1:
                command_part = line_content[sep_index+1:]
                col_offset = sep_index + 1
                idx = command_part.lower().find(pattern.lower())
                if idx != -1:
                    # (line, start_col, end_col)
                    matches.append((i, col_offset + idx, col_offset + idx + len(pattern)))
        if not matches:
            search_index[0] = 0
            return
        # Move to next/prev match
        if forward:
            search_index[0] = (search_index[0] + 1) % len(matches) if search_index[0] < len(matches) else 0
        else:
            search_index[0] = (search_index[0] - 1) % len(matches)
        line, start_col, end_col = matches[search_index[0]]
        history_txt.see(f"{line}.0")
        history_txt.tag_add("sel", f"{line}.{start_col}", f"{line}.{end_col}")
        history_txt.mark_set("insert", f"{line}.{start_col}")
        history_txt.focus_set()
        # Save matches for up/down navigation
        search_matches.clear()
        search_matches.extend(matches)

    def on_search_enter(event=None):
        search_index[0] = -1
        search_history(forward=True)
    def on_search_up(event=None):
        if search_matches:
            search_history(forward=False)
    def on_search_down(event=None):
        if search_matches:
            search_history(forward=True)
    search_entry.bind("<Return>", on_search_enter)
    btn_up.config(command=on_search_up)
    btn_down.config(command=on_search_down)
    # Optionally, bind Ctrl+Up/Down for keyboard navigation
    search_entry.bind("<Control-Up>", lambda e: on_search_up())
    search_entry.bind("<Control-Down>", lambda e: on_search_down())

    def load_selected_to_main(event=None):
        if search_matches and 0 <= search_index[0] < len(search_matches):
            line, start_col, end_col = search_matches[search_index[0]]
            # Get the full command for this line (including multiline)
            # Find the command index in self.history
            num_text = history_txt.get(f"{line}.0", f"{line}.end").split('│')[0].strip()
            try:
                hist_index = int(num_text) - 1
                if 0 <= hist_index < len(self.history):
                    self._hist_item = hist_index
                    self.insert_cmd(self.history[hist_index])
                    self._history_window.lift()
            except Exception:
                pass
    def close_history_panel(event=None):
        if hasattr(self, '_history_window') and self._history_window is not None:
            self._history_window.destroy()
            self._history_window = None
    # Bindings for search navigation and actions
    history_window.bind('<Control-s>', load_selected_to_main)
    history_window.bind('<Control-n>', lambda e: on_search_down())
    history_window.bind('<Control-b>', lambda e: on_search_up())
    history_window.bind('<Escape>', close_history_panel)
