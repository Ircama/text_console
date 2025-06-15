import os
import pickle

class History(list):
    def __init__(self, history_file=".console_history"):
        super().__init__()
        self.history_file = history_file

        if os.path.exists(self.history_file):
            try:
                # Try loading pickled history (preferred)
                with open(self.history_file, "rb") as f:
                    data = pickle.load(f)
                    # Ensure all entries are strings
                    for entry in data:
                        if not isinstance(entry, str):
                            raise ValueError
                    self.extend(data)
            except Exception:
                # Fallback: legacy line-by-line text file
                with open(self.history_file, "r", encoding="utf-8") as f:
                    for line in f:
                        txt = line.rstrip("\n")
                        if txt:
                            self.append(txt)

    def __getitem__(self, index):
        try:
            return super().__getitem__(index)
        except IndexError:
            return None

    def append(self, item):
        # Convert lists to true multiline strings
        if isinstance(item, list):
            item = "\n".join(item)
        elif not isinstance(item, str):
            item = str(item)
        super().append(item)

    def save(self):
        # Pickle the list of strings so embedded newlines survive
        with open(self.history_file, "wb") as f:
            pickle.dump(list(self), f)
