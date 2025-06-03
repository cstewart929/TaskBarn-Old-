import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
import json
import os
from datetime import datetime
try:
    from tkcalendar import Calendar
except ImportError:
    Calendar = None  # Will show a message if not installed

SAVE_FILE = "tasks.brn"  # Default save file
CONFIG_FILE = "taskbarn_config.json"  # Configuration file
COLUMNS = 2  # Number of task columns

SORT_OPTIONS = [
    ("Time Left", "time_left"),
    ("Size", "size"),
    ("Name", "name"),
    ("Date Created", "created")
]

class Task:
    def __init__(self, root, title, remove_callback=None, checkboxes=None, dirty_callback=None, due_date=None, color=None, created=None):
        self.title = title
        self.remove_callback = remove_callback
        self.dirty_callback = dirty_callback
        self.checkboxes = []
        self.due_date = due_date or ""
        self.color = color or "#ffffff"
        self.created = created or datetime.now().isoformat()

        self.container = tk.Frame(root, bg=self.color, highlightbackground="#bbb", highlightthickness=1)
        self.container.grid_propagate(False)

        self.top_frame = tk.Frame(self.container, height=50, bg=self.color)
        self.top_frame.pack(fill="x")

        # Place the emoji on the left
        self.emoji_label = tk.Label(self.top_frame, text="", font=("Segoe UI Emoji", 36), bg=self.color)
        self.emoji_label.pack(side="left", anchor="w")

        # Place the trash icon as a label styled as a button
        self.trash_armed = False
        self.remove_task_label = tk.Label(
            self.top_frame,
            text="🗑️",
            font=("Segoe UI Emoji", 12),
            width=4,
            height=1,
            relief="solid",
            borderwidth=1,
            bg="#ffcccc",
            cursor="hand2"
        )
        self.remove_task_label.pack(side="right", padx=10, pady=(5, 10))
        self.remove_task_label.bind("<Button-1>", self.trash_click)
        self.remove_task_label.bind("<Leave>", self.reset_trash)
        self.remove_task_label.bind("<FocusOut>", self.reset_trash)
        self.remove_task_label.bind("<Double-Button-1>", self.trash_click)

        # Color picker button
        self.color_btn = tk.Button(self.top_frame, text="🎨", width=2, command=self.pick_color, bg=self.color)
        self.color_btn.pack(side="right", padx=5)

        # Due date button and label
        self.due_btn = tk.Button(self.top_frame, text="📅", width=2, command=self.set_due_date, bg=self.color)
        self.due_btn.pack(side="right", padx=5)
        self.due_label = tk.Label(self.top_frame, font=("Segoe UI", 9), bg=self.color)
        self.due_label.pack(side="right", padx=5)
        self.due_label.config(text=self.get_due_text())

        # Create title frame with edit capability
        self.title_frame = tk.Frame(self.container, bg=self.color)
        self.title_frame.pack(fill="x", pady=(0, 5))
        
        self.title_label = tk.Label(self.title_frame, text=title, font=("Segoe UI", 10, "bold"), bg=self.color)
        self.title_label.pack(side="left", fill="x", expand=True)
        self.title_label.bind("<Double-Button-1>", self.start_title_edit)
        
        self.title_entry = tk.Entry(self.title_frame, font=("Segoe UI", 10), bg=self.color)
        self.title_entry.bind("<Return>", self.finish_title_edit)
        self.title_entry.bind("<Escape>", self.cancel_title_edit)
        self.title_entry.bind("<FocusOut>", self.finish_title_edit)
        self.title_entry.bind("<KeyRelease>", self._on_title_edit)

        self.frame = tk.LabelFrame(self.container, text="", bg=self.color, padx=10, pady=10)
        self.frame.pack(fill="x", pady=(5, 0))

        self.add_button = tk.Button(self.frame, text="+ Add Task", command=self.add_checkbox, bg=self.color)
        self.add_button.pack(anchor="w", pady=5)

        if checkboxes:
            for label, checked in checkboxes:
                self.add_checkbox(label, checked)
        else:
            self.add_checkbox()

        self.update_emoji()
        self.apply_color()

    def start_title_edit(self, event=None):
        self.title_label.pack_forget()
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, self.title)
        self.title_entry.pack(side="left", fill="x", expand=True)
        self.title_entry.focus_set()
        self.title_entry.select_range(0, tk.END)

    def finish_title_edit(self, event=None):
        new_title = self.title_entry.get().strip()
        if new_title and new_title != self.title:
            self.title = new_title
            self.title_label.config(text=new_title)
            if self.dirty_callback:
                self.dirty_callback()
        self.title_entry.pack_forget()
        self.title_label.pack(side="left", fill="x", expand=True)

    def cancel_title_edit(self, event=None):
        self.title_entry.pack_forget()
        self.title_label.pack(side="left", fill="x", expand=True)

    def _on_title_edit(self, event=None):
        if self.dirty_callback:
            self.dirty_callback()

    def add_checkbox(self, label="", checked=False):
        var = tk.BooleanVar(value=checked)
        container = tk.Frame(self.frame, bg=self.color)
        container.pack(fill="x", pady=2)

        # Use tk.Checkbutton for color control
        cb = tk.Checkbutton(container, variable=var, command=lambda e=None, v=var: self.toggle_entry_color(entry, v), bg=self.color, fg=self.get_text_color(), selectcolor=self.color, activebackground=self.color, activeforeground=self.get_text_color())
        cb.pack(side="left")

        entry = tk.Entry(container, bg=self.color, fg=self.get_text_color())
        entry.insert(0, label)
        entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        entry.bind("<Tab>", lambda e, entry=entry: self.focus_next_entry(entry))
        entry.bind("<Shift-Tab>", lambda e, entry=entry: self.focus_prev_entry(entry))
        entry.bind("<KeyRelease>", self._on_checkbox_edit)

        close = tk.Button(container, text="✖", width=3, command=lambda: self.remove_checkbox(container, entry, var), bg=self.color, fg=self.get_text_color())
        close.pack(side="right")

        self.checkboxes.append((container, entry, var, cb))

        # Set initial state using toggle_entry_color, potentially delayed for color
        self.toggle_entry_color(entry, var) # Apply font immediately
        if checked:
            # Schedule color change after a short delay
            entry.after(1, lambda: entry.configure(foreground="#808080"))

        self.update_emoji()
        if self.dirty_callback:
            self.dirty_callback()

    def get_text_color(self):
        bg = self.color.lstrip('#')
        if len(bg) == 3:
            bg = ''.join([c*2 for c in bg])
        r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
        luminance = 0.299*r + 0.587*g + 0.114*b
        return '#ffffff' if luminance < 128 else '#000000'

    def remove_checkbox(self, container, entry, var):
        container.destroy()
        self.checkboxes = [cb for cb in self.checkboxes if cb[0] != container]
        self.update_emoji()
        if self.dirty_callback:
            self.dirty_callback()

    def _on_checkbox_edit(self, event=None):
        if self.dirty_callback:
            self.dirty_callback()

    def toggle_entry_color(self, entry, var):
        if var.get():
            entry.configure(foreground="#808080")  # Use explicit gray color
            entry.configure(font=("Segoe UI", 10, "overstrike"))
        else:
            entry.configure(foreground=self.get_text_color())
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
            "checkboxes": [(entry.get(), var.get()) for _, entry, var, _ in self.checkboxes],
            "due_date": self.due_date,
            "color": self.color,
            "created": self.created
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

    def pick_color(self):
        color_code = colorchooser.askcolor(title="Choose task color", initialcolor=self.color)[1]
        if color_code:
            self.color = color_code
            self.apply_color()
            if self.dirty_callback:
                self.dirty_callback()

    def apply_color(self):
        text_color = self.get_text_color()
        widgets = [self.container, self.top_frame, self.title_frame, self.frame, self.emoji_label, self.due_label, self.title_label, self.title_entry, self.add_button, self.color_btn, self.due_btn]
        for w in widgets:
            try:
                w.configure(bg=self.color)
            except Exception:
                pass
            try:
                w.configure(fg=text_color)
            except Exception:
                pass
        # Also update all checkbox containers, entries, and buttons
        for container, entry, var, cb in self.checkboxes:
            try:
                container.configure(bg=self.color)
                entry.configure(bg=self.color, fg=text_color)
                cb.configure(bg=self.color, fg=text_color, selectcolor=self.color, activebackground=self.color, activeforeground=text_color)
                for child in container.winfo_children():
                    if isinstance(child, tk.Button) and child['text'] == '✖':
                        child.configure(bg=self.color, fg=text_color)
            except Exception:
                pass
        # Trash can label
        try:
            # Don't set trash can background here, it's handled by trash_click/reset_trash
            self.remove_task_label.configure(fg="#000000") # Always black
        except Exception:
            pass
        
        # Re-evaluate and apply due date styling based on new color
        self.due_label.config(text=self.get_due_text())

    def set_due_date(self):
        if Calendar is None:
            messagebox.showerror("Calendar Not Installed", "Please install tkcalendar: pip install tkcalendar")
            return
        top = tk.Toplevel()
        top.title("Select Due Date")
        cal = Calendar(top, selectmode='day')
        cal.pack(padx=10, pady=10)
        def set_date():
            self.due_date = cal.get_date()
            self.due_label.config(text=self.get_due_text())
            if self.dirty_callback:
                self.dirty_callback()
            top.destroy()
        btn = tk.Button(top, text="Set", command=set_date)
        btn.pack(pady=5)
        top.grab_set()
        top.wait_window()

    def get_due_text(self):
        if not self.due_date:
            self.stop_due_flash()
            return ""
        try:
            due = datetime.strptime(self.due_date, "%m/%d/%y").date()
            today = datetime.now().date()
            days_left = (due - today).days
            if days_left == 0:
                self.start_due_flash()
                return f"{self.due_date} (Due today!)"
            elif days_left == 1:
                self.start_due_flash()
                return f"{self.due_date} (Due tomorrow!)"
            elif days_left < 0:
                self.stop_due_flash(overdue=True)
                return f"{self.due_date} ({-days_left} days overdue)"
            else:
                self.stop_due_flash()
                return f"{self.due_date} ({days_left} days left)"
        except Exception:
            self.stop_due_flash()
            return self.due_date

    def start_due_flash(self):
        if hasattr(self, '_flashing') and self._flashing:
            return
        self._flashing = True
        self._flash_state = False
        self._flash_due_label()

    def stop_due_flash(self, overdue=False):
        if hasattr(self, '_flashing') and self._flashing:
            self._flashing = False
        if overdue:
            self.due_label.configure(bg="#000000", fg="#ffffff")
        else:
            self.due_label.configure(bg=self.color, fg=self.get_text_color())

    def _flash_due_label(self):
        if not getattr(self, '_flashing', False):
            return
        if self._flash_state:
            self.due_label.configure(bg="#ff4444", fg="#ffffff")
        else:
            self.due_label.configure(bg="#ffffff", fg="#ff4444")
        self._flash_state = not self._flash_state
        self.due_label.after(400, self._flash_due_label)

    def trash_click(self, event=None):
        if not self.trash_armed:
            self.trash_armed = True
            # Change background to distinct red on first click
            self.remove_task_label.configure(bg="#ff4444")
        else:
            self.remove_task()

    def reset_trash(self, event=None):
        if self.trash_armed:
            self.trash_armed = False
            # Reset background to default light red only if it was armed
            self.remove_task_label.configure(bg="#ffcccc")

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🐮 TaskBarn")
        self.tasks = []
        self.dirty = False  # Track unsaved changes
        self.sort_method = tk.StringVar(value="created")
        self.bg_color = "#f0f0f0"
        self.fg_color = "#000000"
        
        # Load last used file and window size from config
        config = self.load_config()
        self.current_file = config.get('last_file', SAVE_FILE)
        win_size = config.get('window_size')
        was_maximized = config.get('maximized', False)
        if win_size:
            self.root.geometry(win_size)
        if was_maximized:
            self.root.state('zoomed')

        # Create menu bar
        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)
        
        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New", command=self.new_file)
        self.file_menu.add_command(label="Save", command=self.save_tasks, accelerator="Ctrl+S")
        self.file_menu.add_command(label="Save As...", command=self.save_as)
        self.file_menu.add_command(label="Open...", command=self.load_from)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_close)

        self.root.bind("<Control-s>", self.save_tasks)

        sort_frame = tk.Frame(root, bg=self.bg_color)
        sort_frame.pack(padx=10, pady=(0, 5), fill="x", before=None)
        tk.Label(sort_frame, text="Sort by:", bg=self.bg_color, fg=self.fg_color).pack(side="left")
        sort_labels = [label for label, _ in SORT_OPTIONS]
        sort_menu = tk.OptionMenu(sort_frame, self.sort_method, *sort_labels, command=self.sort_and_place_tasks)
        self.sort_method.set(sort_labels[0])  # Set the default value
        sort_menu.config(bg=self.bg_color, fg=self.fg_color, highlightthickness=0, activebackground=self.bg_color, activeforeground=self.fg_color)
        sort_menu.pack(side="left", padx=5)

        entry_frame = tk.Frame(root, bg=self.bg_color)
        entry_frame.pack(padx=10, pady=(4, 0), fill="x")

        self.entry = tk.Entry(entry_frame, bg=self.bg_color, fg=self.fg_color, font=("Segoe UI", 20), width=30, justify="center")
        self.entry.pack(side="left", pady=0, padx=(0, 8), expand=True, fill="x")
        self.entry.bind("<Return>", lambda e: self.add_task())

        self.add_task_btn = tk.Button(entry_frame, text="➕ Add Group", command=self.add_task, bg=self.bg_color, fg=self.fg_color)
        self.add_task_btn.pack(side="left", pady=0)

        # Scrollable canvas
        self.canvas = tk.Canvas(root, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview, bg=self.bg_color, troughcolor=self.bg_color, activebackground=self.bg_color)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        # Bind mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        self.task_frame = tk.Frame(self.canvas, bg=self.bg_color)
        self.canvas.create_window((0, 0), window=self.task_frame, anchor="nw", width=self.canvas.winfo_width())

        self.task_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.load_tasks()

    def _on_mousewheel(self, event):
        # Get current scroll position
        first, last = self.canvas.yview()
        if event.num == 5 or event.delta < 0:  # scroll down
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:  # scroll up
            if first > 0.0:
                self.canvas.yview_scroll(-1, "units")

    def on_canvas_resize(self, event):
        canvas_width = event.width
        self.canvas.itemconfig("all", width=canvas_width)
        self.place_tasks()  # Reflow tasks when window is resized

    def mark_dirty(self, *args, **kwargs):
        self.dirty = True

    def add_task(self):
        title = self.entry.get().strip()
        if title:
            task = Task(self.task_frame, title, remove_callback=self.remove_task, dirty_callback=self.mark_dirty)
            self.tasks.append(task)
            self.sort_and_place_tasks()
            self.entry.delete(0, tk.END)
            self.mark_dirty()

    def remove_task(self, task):
        if task in self.tasks:
            self.tasks.remove(task)
            self.sort_and_place_tasks()
            self.mark_dirty()

    def place_tasks(self):
        # Clear existing grid
        for task in self.tasks:
            task.container.grid_forget()
        for i in range(20):  # Clear previous grid weights (arbitrary max columns)
            self.task_frame.grid_columnconfigure(i, weight=0)

        # Calculate available width
        available_width = self.canvas.winfo_width() - 20  # 20px padding
        task_width = 300  # Approximate width of a task
        tasks_per_row = max(1, available_width // task_width)
        num_tasks = len(self.tasks)
        if num_tasks == 0:
            return
        
        # Centering logic
        for row in range((num_tasks + tasks_per_row - 1) // tasks_per_row):
            start = row * tasks_per_row
            end = min(start + tasks_per_row, num_tasks)
            num_in_row = end - start
            pad = (tasks_per_row - num_in_row) // 2
            for col in range(tasks_per_row):
                self.task_frame.grid_columnconfigure(col, weight=0)
            self.task_frame.grid_columnconfigure(0, weight=1)  # Left spacer
            self.task_frame.grid_columnconfigure(tasks_per_row + 1, weight=1)  # Right spacer
            for i, task in enumerate(self.tasks[start:end]):
                task.container.grid(row=row, column=i + 1 + pad, padx=5, pady=5, sticky="nsew")

    def on_close(self):
        if not self.dirty:
            self.save_last_file()
            self.root.destroy()
            return
        answer = messagebox.askyesnocancel(
            "Save Changes?",
            "Do you want to save your changes before exiting?",
            icon="question"
        )
        if answer is None:  # Cancel
            return
        elif answer:  # Yes (Save)
            self.save_tasks()
            self.save_last_file()
            self.root.destroy()
        else:  # No (Discard)
            self.save_last_file()
            self.root.destroy()

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_last_file(self):
        try:
            config = self.load_config()
            config['last_file'] = self.current_file
            config['window_size'] = self.root.geometry()
            config['maximized'] = (self.root.state() == 'zoomed')
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception:
            pass

    def save_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".brn",
            filetypes=[("TaskBarn Files", "*.brn"), ("All Files", "*.*")],
            initialfile=self.current_file
        )
        if file_path:
            self.current_file = file_path
            self.save_tasks()
            self.save_last_file()
            self.root.title(f"🐮 TaskBarn - {os.path.basename(file_path)}")

    def load_from(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("TaskBarn Files", "*.brn"), ("All Files", "*.*")]
        )
        if file_path:
            self.current_file = file_path
            self.save_last_file()
            # Clear existing tasks
            for task in self.tasks:
                task.container.destroy()
            self.tasks.clear()
            # Load new tasks
            self.load_tasks()
            self.root.title(f"🐮 TaskBarn - {os.path.basename(file_path)}")

    def save_tasks(self, event=None):
        try:
            data = [task.get_data() for task in self.tasks]
            with open(self.current_file, "w") as f:
                json.dump(data, f, indent=2)
            self.root.title(f"🐮 TaskBarn - {os.path.basename(self.current_file)}")
            self.dirty = False
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def load_tasks(self):
        if os.path.exists(self.current_file):
            try:
                with open(self.current_file, "r") as f:
                    data = json.load(f)
                    for item in data:
                        task = Task(
                            self.task_frame,
                            item["title"],
                            remove_callback=self.remove_task,
                            checkboxes=item.get("checkboxes", []),
                            dirty_callback=self.mark_dirty,
                            due_date=item.get("due_date", ""),
                            color=item.get("color", "#ffffff"),
                            created=item.get("created")
                        )
                        self.tasks.append(task)
                    self.sort_and_place_tasks()
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid file format")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")

    def sort_and_place_tasks(self, *args):
        method = self.sort_method.get()
        if method == "Time Left" or method == "time_left":
            def days_left(task):
                try:
                    due = datetime.strptime(task.due_date, "%m/%d/%y").date()
                    today = datetime.now().date()
                    return (due - today).days
                except Exception:
                    return float('inf')
            self.tasks.sort(key=lambda t: (days_left(t) if t.due_date else float('inf'), t.title.lower()))
        elif method == "Size" or method == "size":
            self.tasks.sort(key=lambda t: (-len(t.checkboxes), t.title.lower()))
        elif method == "Name" or method == "name":
            self.tasks.sort(key=lambda t: t.title.lower())
        else:  # Date Created
            self.tasks.sort(key=lambda t: t.created)
        self.place_tasks()

    def new_file(self):
        if self.dirty:
            answer = messagebox.askyesnocancel(
                "Save Changes?",
                "Do you want to save your changes before creating a new file?",
                icon="question"
            )
            if answer is None:  # Cancel
                return
            elif answer:  # Yes (Save)
                self.save_tasks()

        # Clear existing tasks
        for task in self.tasks:
            task.container.destroy()
        self.tasks.clear()
        self.current_file = SAVE_FILE
        self.root.title("🐮 TaskBarn")
        self.dirty = False

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()
