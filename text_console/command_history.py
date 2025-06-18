import tkinter as tk
from tkinter import ttk

class CommandHistoryPanel:
    def __init__(self, master, history, insert_cmd_callback, hist_item_ref, close_callback=None):
        self.master = master
        self.history = history
        self.insert_cmd_callback = insert_cmd_callback
        self.hist_item_ref = hist_item_ref  # Should be a mutable reference (e.g., [value])
        self.close_callback = close_callback
        self.window = tk.Toplevel(master)
        self.window.title("Command History")
        self.window.geometry("600x600")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_ui()
        self.window.after(100, self.focus_search_entry_delayed)

    def _build_ui(self):
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        # Search bar
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Consolas", 10))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.btn_up = tk.Button(search_frame, text="↑", width=2, command=self.on_search_up)
        self.btn_up.pack(side="left")
        self.btn_down = tk.Button(search_frame, text="↓", width=2, command=self.on_search_down)
        self.btn_down.pack(side="left")
        # History text
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        v_scrollbar = tk.Scrollbar(text_frame, orient="vertical")
        h_scrollbar = tk.Scrollbar(text_frame, orient="horizontal")
        self.history_txt = tk.Text(
            text_frame, wrap="none", yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set,
            font=("Consolas", 10), bg="white", fg="black", selectbackground="#cce7ff"
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
        self._search_matches = []
        self._search_index = [0]
        self._draw_history()
        self._bind_events()

    def _draw_history(self):
        self.history_txt.config(state="normal")
        self.history_txt.delete("1.0", "end")
        num_width = max(5, len(str(len(self.history))))
        for i, command in enumerate(reversed(self.history)):
            item_number = len(self.history) - i
            command_text = str(command).strip()
            command_lines = command_text.split('\n')
            first_line = command_lines[0] if command_lines else ""
            start_idx = self.history_txt.index("end-1c")
            self.history_txt.insert("end", f"{item_number:<{num_width}}", ("number", "nonselectable"))
            self.history_txt.insert("end", " │ ", ("separator", "nonselectable"))
            self.history_txt.insert("end", f"{first_line}\n", "command")
            self.history_txt.tag_add(f"numtag_{item_number}", start_idx, f"{start_idx.split('.')[0]}.end")
            for line in command_lines[1:]:
                self.history_txt.insert("end", f"{'':<{num_width}}", "nonselectable")
                self.history_txt.insert("end", " │ ", ("separator", "nonselectable"))
                self.history_txt.insert("end", f"{line}\n", "command")
            if i < len(self.history) - 1:
                self.history_txt.insert("end", "─" * 80, "divider")
                self.history_txt.insert("end", "\n")
        self.history_txt.config(state="disabled")

    def _bind_events(self):
        self.search_entry.bind("<Return>", lambda e: self.on_search_enter())
        self.search_entry.bind("<Control-Up>", lambda e: self.on_search_up())
        self.search_entry.bind("<Control-Down>", lambda e: self.on_search_down())
        self.history_txt.bind("<Control-s>", self.load_selected_to_main)
        self.history_txt.bind("<Control-n>", lambda e: self.on_search_down())
        self.history_txt.bind("<Control-b>", lambda e: self.on_search_up())
        self.history_txt.bind("<Escape>", self.on_close)
        self.window.bind("<Escape>", self.on_close)
        self.history_txt.bind("<Button-1>", lambda e: self.history_txt.focus_set())
        self.history_txt.bind("<<Selection>>", self.on_selection)
        for i in range(1, len(self.history)+1):
            self.history_txt.tag_bind(f"numtag_{i}", "<Double-Button-1>", self.on_number_double_click)
            self.history_txt.tag_bind(f"numtag_{i}", "<Enter>", self.on_number_enter)
            self.history_txt.tag_bind(f"numtag_{i}", "<Leave>", self.on_number_leave)

    def focus_search_entry_delayed(self):
        self.window.after(100, lambda: self.search_entry.focus_set())

    def on_search_enter(self):
        self._search_index[0] = -1
        self.search_history(forward=True)

    def on_search_up(self, event=None):
        if self._search_matches:
            self.search_history(forward=False)

    def on_search_down(self, event=None):
        if self._search_matches:
            self.search_history(forward=True)

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
            self._search_index[0] = 0
            return
        if forward:
            self._search_index[0] = (self._search_index[0] + 1) % len(matches) if self._search_index[0] < len(matches) else 0
        else:
            self._search_index[0] = (self._search_index[0] - 1) % len(matches)
        line, start_col, end_col = matches[self._search_index[0]]
        self.history_txt.see(f"{line}.0")
        self.history_txt.tag_add("sel", f"{line}.{start_col}", f"{line}.{end_col}")
        self.history_txt.mark_set("insert", f"{line}.{start_col}")
        self.history_txt.focus_set()
        self._search_matches = matches

    def load_selected_to_main(self, event=None):
        if self._search_matches and 0 <= self._search_index[0] < len(self._search_matches):
            line, start_col, end_col = self._search_matches[self._search_index[0]]
            num_text = self.history_txt.get(f"{line}.0", f"{line}.end").split('│')[0].strip()
            try:
                hist_index = int(num_text) - 1
                if 0 <= hist_index < len(self.history):
                    self.hist_item_ref[0] = hist_index
                    self.insert_cmd_callback(self.history[hist_index])
                    self.window.lift()
            except Exception:
                pass

    def on_close(self, event=None):
        if self.close_callback:
            self.close_callback()
        self.window.destroy()

    def on_number_double_click(self, event):
        index = self.history_txt.index(f"@{event.x},{event.y}")
        line = int(index.split('.')[0])
        num_text = self.history_txt.get(f"{line}.0", f"{line}.end").split('│')[0].strip()
        try:
            hist_index = int(num_text) - 1
            if 0 <= hist_index < len(self.history):
                self.hist_item_ref[0] = hist_index
                self.insert_cmd_callback(self.history[hist_index])
                self.window.lift()
        except Exception:
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
