import tkinter as tk

class CommandHistoryPanel(tk.Toplevel):
    def __init__(self, master, history, insert_cmd_callback, hist_item_ref, close_callback=None):
        super().__init__(master)
        self.history = history
        self.insert_cmd_callback = insert_cmd_callback
        self.hist_item_ref = hist_item_ref
        self.close_callback = close_callback
        self.title("Command History")
        self.geometry("600x600")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_ui()
        self.history_txt.see("1.0")
        self.after(200, self.delayed_setup)

    def _build_ui(self):
        main_frame = tk.Frame(self)
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
        self.after(300, self.focus_search_entry_delayed)
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
            text=f"Total commands: {len(self.history)}. Right-click or Ctrl+C to copy. Double-click to edit the command.",
            relief="sunken",
            anchor="w"
        )
        self.status_label.pack(fill="x")
        self.history_txt.see("1.0")
        # Context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy Selected", command=self.copy_selected_command)
        self.context_menu.add_command(label="Close", command=self.destroy)
        self.bind("<Button-3>", lambda e: self.context_menu.post(e.x_root, e.y_root))
        self.bind("<Control-w>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())
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
        self.bind('<Control-s>', self.load_selected_to_main)
        self.bind('<Control-n>', lambda e: self.on_search_down())
        self.bind('<Control-b>', lambda e: self.on_search_up())
        self.bind('<Escape>', self.close_history_panel)
        self.history_txt.bind("<ButtonRelease-1>", self.on_selection)
        self.history_txt.bind("<B1-Motion>", self.on_selection)
        self.history_txt.bind("<Double-Button-1>", self.on_number_double_click)
        self.history_txt.bind("<Enter>", self.on_number_enter)
        self.history_txt.bind("<Leave>", self.on_number_leave)
        self.bind('<Configure>', self.on_window_configure)

    def delayed_setup(self):
        self.update_display()
        self.history_txt.focus_set()
        self.history_txt.see("1.0")

    def focus_search_entry_delayed(self):
        self.search_entry.focus_set()

    def on_close(self):
        if self.close_callback:
            self.close_callback()
        self.destroy()

    def calculate_layout(self):
        try:
            text_width_pixels = self.history_txt.winfo_width()
            char_width = 8
            widget_width = max(80, text_width_pixels // char_width)
        except:
            widget_width = max(100, (self.winfo_width() - 80) // 8)
        max_command_length = 0
        for command in self.history:
            for line in str(command).split('\n'):
                max_command_length = max(max_command_length, len(line))
        num_width = max(5, len(str(len(self.history))))
        cmd_width = max(50, widget_width - num_width - 3)
        return num_width, cmd_width, max_command_length, widget_width

    def on_window_configure(self, event=None):
        if event and event.widget == self:
            self.update_display()

    def on_number_double_click(self, event):
        index = self.history_txt.index(f"@{event.x},{event.y}")
        line = int(index.split('.')[0])
        while line > 0:
            num_text = self.history_txt.get(f"{line}.0", f"{line}.end").split('│')[0].strip()
            if num_text.isdigit():
                hist_index = int(num_text) - 1  # assuming history is 1-based in the panel
                break
            line -= 1
        else:
            hist_index = None  # Not found

        if hist_index is not None:
            command = self.history[hist_index]
            self.hist_item_ref[0] = hist_index
            self.insert_cmd_callback(command)
            self.master.focus_set()
            self.close()

    def on_number_enter(self, event):
        index = self.history_txt.index(f"@{event.x},{event.y}")
        line = index.split('.')[0]
        col = index.split('.')[1]
        sep_index = self.history_txt.get(f"{line}.0", f"{line}.end").find("│")
        if int(col) < 7 and sep_index > 0:
            self.history_txt.config(cursor="hand2")
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
                self.clipboard_clear()
                self.clipboard_append(command_text)
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
                    self.lift()
            except Exception as e:
                print(f"[DEBUG] Error in load_selected_to_main: {e}")
                pass

    def close_history_panel(self, event=None):
        if hasattr(self.master, '_history_window') and self.master._history_window is not None:
            self.master._history_window.destroy()
            self.master._history_window = None

    def close(self):
        self.after(300, self.destroy)