import tkinter as tk
from tkinter import ttk
import json
import os

SAVE_FILE = "tasks.brn"
COLUMNS = 2

class Task:
    def __init__(self, root, title, remove_callback=None, checkboxes=None):
        self.title = title
        self.remove_callback = remove_callback
        self.checkboxes = []

        self.container = ttk.Frame(root, padding=10, relief="raised")
        self.container.grid_propagate(False)

        self.top_frame = ttk.Frame(self.container)
        self.top_frame.pack(fill="x")

        self.emoji_label = ttk.Label(self.top_frame, text="", font=("Segoe UI Emoji", 36))
        self.emoji_label.pack(side="left")

        self.remove_task_button = ttk.Button(self.top_frame, text="🗑️", command=self.remove_task)
        self.remove_task_button.pack(side="right")

        self.frame = ttk.LabelFrame(self.container, text=title, padding=10)
        self.frame.pack(fill="x", pady=(5, 0))

        self.add_button = ttk.Button(self.frame, text="+ Add checkbox", command=self.add_checkbox)
        self.add_button.pack(anchor="w", pady=5)

        if checkboxes:
            for label, checked in checkboxes:
                self.add_checkbox(label, checked)
        else:
            self.add_checkbox()

        self.update_emoji()

    def add_checkbox(self, label="", checked=False):
        var = tk.BooleanVar(value=checked)
        container = ttk.Frame(self.frame)
        container.pack(fill="x", pady=2)

        cb = ttk.Checkbutton(container, variable=var, command=lambda e=None, v=var: self.toggle_entry_color(entry, v))
        cb.pack(side="left")

        entry = ttk.Entry(container)
        entry.insert(0, label)
        entry.pack(side="left", fill="x", expand=True, padx=(5, 5))

        entry.bind("<Tab>", lambda e, entry=entry: self.focus_next_entry(entry))
        entry.bind("<Shift-Tab>", lambda e, entry=entry: self.focus_prev_entry(entry))

        close = ttk.Button(container, text="✖", width=3, command=lambda: self.remove_checkbox(container, entry, var))
        close.pack(side="right")

        self.checkboxes.append((container, entry, var))
        self.toggle_entry_color(entry, var)
        self.update_emoji()

    def remove_checkbox(self, container, entry, var):
        container.destroy()
        self.checkboxes = [cb for cb in self.checkboxes if cb != (container, entry, var)]
        self.update_emoji()

    def toggle_entry_color(self, entry, var):
        if var.get():
            entry.configure(foreground="gray")
            entry.configure(font=("Segoe UI", 10, "overstrike"))
        else:
            entry.configure(foreground="black")
            entry.configure(font=("Segoe UI", 10))

    def update_emoji(self):
        count = len(self.checkboxes)
        if count == 0:
            emoji = "🥚"
        elif count <= 3:
            emoji = "🐔"
        elif count <= 5:
            emoji = "🐖"
        elif count <= 10:
            emoji = "🐄"
        elif count <= 20:
            emoji = "🐉"
        else:
            emoji = "🌎"
        self.emoji_label.config(text=emoji)

    def remove_task(self):
        self.container.destroy()
        if self.remove_callback:
            self.remove_callback(self)

    def get_data(self):
        return {
            "title": self.title,
            "checkboxes": [(entry.get(), var.get()) for _, entry, var in self.checkboxes]
        }

    def focus_next_entry(self, current_entry):
        entries = [entry for _, entry, _ in self.checkboxes]
        try:
            idx = entries.index(current_entry)
            if idx + 1 < len(entries):
                entries[idx + 1].focus_set()
                return "break"
        except ValueError:
            pass

    def focus_prev_entry(self, current_entry):
        entries = [entry for _, entry, _ in self.checkboxes]
        try:
            idx = entries.index(current_entry)
            if idx > 0:
                entries[idx - 1].focus_set()
                return "break"
        except ValueError:
            pass


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TaskBarn - By Blanc 🦬")
        self.tasks = []

        style = ttk.Style()
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 10))
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

        self.entry = ttk.Entry(root)
        self.entry.pack(padx=10, pady=(10, 0), fill="x")

        self.add_task_btn = ttk.Button(root, text="➕ Add Task", command=self.add_task)
        self.add_task_btn.pack(padx=10, pady=(5, 10))

        # Scrollable canvas
        self.canvas = tk.Canvas(root)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        self.task_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.task_frame, anchor="nw")

        self.task_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.load_tasks()

    def on_canvas_resize(self, event):
        canvas_width = event.width
        self.canvas.itemconfig("all", width=canvas_width)

    def add_task(self):
        title = self.entry.get().strip()
        if title:
            task = Task(self.task_frame, title, remove_callback=self.remove_task)
            self.tasks.append(task)
            self.place_tasks()
            self.entry.delete(0, tk.END)

    def remove_task(self, task):
        if task in self.tasks:
            self.tasks.remove(task)
            self.place_tasks()

    def place_tasks(self):
        for i, task in enumerate(self.tasks):
            row = i // COLUMNS
            col = i % COLUMNS
            task.container.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

    def on_close(self):
        self.save_tasks()
        self.root.destroy()

    def save_tasks(self):
        data = [task.get_data() for task in self.tasks]
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def load_tasks(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                for item in data:
                    task = Task(self.task_frame, item["title"], remove_callback=self.remove_task, checkboxes=item.get("checkboxes", []))
                    self.tasks.append(task)
                self.place_tasks()


root = tk.Tk()
app = TaskManagerApp(root)
root.mainloop()
