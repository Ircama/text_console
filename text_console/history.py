import os

class History(list):
    def __init__(self, history_file=".console_history"):
        super().__init__()
        self.history_file = history_file

        # Load history from the file
        if os.path.exists(self.history_file):
            with open(self.history_file, "r", encoding="utf-8") as file:
                self.extend(line.strip() for line in file if line.strip())

    def __getitem__(self, index):
        try:
            return super().__getitem__(index)
        except IndexError:
            return None

    def append(self, item):
        # Ensure only strings are added
        if isinstance(item, list):
            item = " ".join(item)  # Convert list to string
        super().append(item)

    def save(self):
        # Save history back to the file
        with open(self.history_file, "w", encoding="utf-8") as file:
            file.writelines(item + "\n" for item in self)
