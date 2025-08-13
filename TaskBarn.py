import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
import json
import os
from datetime import datetime
try:
    from tkcalendar import Calendar
except ImportError:
    Calendar = None

SAVE_FILE = "tasks.brn"
CONFIG_FILE = "taskbarn_config.json"
#COLUMNS = 3

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
        self.emoji_label = tk.Label(self.top_frame, text="", font=("Segoe UI Emoji", 36), bg=self.color)
        self.emoji_label.pack(side="left", anchor="w")
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
        
        self.color_btn = tk.Button(self.top_frame, text="🎨", width=2, command=self.pick_color, bg=self.color)
        self.color_btn.pack(side="right", padx=5)

        self.due_btn = tk.Button(self.top_frame, text="📅", width=2, command=self.set_due_date, bg=self.color)
        self.due_btn.pack(side="right", padx=5)
        self.due_label = tk.Label(self.top_frame, font=("Segoe UI", 9), bg=self.color)
        self.due_label.pack(side="right", padx=5)
        self.due_label.config(text=self.get_due_text())
        
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
            for cb_data in checkboxes:
                if len(cb_data) == 2:
                    label, checked = cb_data
                    deadline = ""
                elif len(cb_data) > 2:
                    label, checked, deadline = cb_data[:3] # Take the first 3 elements if more exist
                else:
                    print(f"Skipping invalid checkbox data during init: {cb_data}")
                    continue # Skip to the next item
                self.add_checkbox(label, checked, deadline)
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

    def add_checkbox(self, label="", checked=False, deadline=None):
        var = tk.BooleanVar(value=checked)
        container = tk.Frame(self.frame, bg=self.color)
        container.pack(fill="x", pady=2)

        checkbox_frame = tk.Frame(container, bg=self.color)
        checkbox_frame.pack(fill="x")
        
        cb = tk.Checkbutton(checkbox_frame, variable=var, command=lambda e=None, v=var: self.toggle_entry_color(text_widget, v), bg=self.color, fg=self.get_text_color(), selectcolor=self.color, activebackground=self.color, activeforeground=self.get_text_color())
        cb.pack(side="left")
        
        text_frame = tk.Frame(checkbox_frame, bg=self.color)
        text_frame.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        text_widget = tk.Text(text_frame, height=1, width=30, wrap=tk.WORD, bg=self.color, fg=self.get_text_color())
        text_widget.insert("1.0", label)
        text_widget.pack(side="left", fill="x", expand=True)
        
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack_forget()
        
        def adjust_height(event=None):
            text_widget.update_idletasks()
            num_lines = int(text_widget.index('end-1c').split('.')[0])
            text_widget.configure(height=min(num_lines, 3))
            
            if num_lines > 3:
                scrollbar.pack(side="right", fill="y")
            else:
                scrollbar.pack_forget()
        
        text_widget.bind("<Tab>", lambda e, text=text_widget: self.focus_next_entry(text))
        text_widget.bind("<Shift-Tab>", lambda e, text=text_widget: self.focus_prev_entry(text))
        text_widget.bind("<KeyRelease>", lambda e: (self._on_checkbox_edit(e), adjust_height()))
        text_widget.bind("<Configure>", adjust_height)
        
        text_widget.tag_configure("strikethrough", overstrike=1)
        text_widget.tag_configure("normal", overstrike=0)

        bottom_frame = tk.Frame(container, bg=self.color)
        bottom_frame.pack(fill="x", padx=(25, 0))  # Indent to align with text

        deadline_btn = tk.Button(bottom_frame, text="📅", width=2, command=lambda: self.set_checkbox_deadline(container, deadline_label), bg=self.color, fg=self.get_text_color())
        deadline_btn.pack(side="left", padx=2)
        
        deadline_label = tk.Label(bottom_frame, text="", font=("Segoe UI", 8), bg=self.color, fg=self.get_text_color())
        deadline_label.pack(side="left", padx=2)
        
        deadline_label._flashing = False
        deadline_label._flash_id = None

        if deadline:
            self.get_checkbox_due_text(deadline_label, deadline)

        close = tk.Button(checkbox_frame, text="✖", width=3, command=lambda: self.remove_checkbox(container, text_widget, var), bg=self.color, fg=self.get_text_color())
        close.pack(side="right")

        self.checkboxes.append((container, text_widget, var, cb, deadline_label, deadline or ""))

        self.toggle_entry_color(text_widget, var)
        if checked:
            text_widget.after(1, lambda: text_widget.configure(foreground="#808080"))
        
        adjust_height()

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

    def remove_checkbox(self, container, text_widget, var):
        for cb_data in self.checkboxes:
            if cb_data[0] == container:
                deadline_label = cb_data[4]
                self.stop_checkbox_due_flash(deadline_label)
                break

        container.destroy()
        self.checkboxes = [cb for cb in self.checkboxes if cb[0] != container]
        self.update_emoji()
        if self.dirty_callback:
            self.dirty_callback()

    def _on_checkbox_edit(self, event=None):
        if self.dirty_callback:
            self.dirty_callback()

    def toggle_entry_color(self, text_widget, var):
        if var.get():
            text_widget.configure(foreground="#808080")  # Use explicit gray color
            text_widget.tag_remove("normal", "1.0", "end-1c")
            text_widget.tag_add("strikethrough", "1.0", "end-1c")
        else:
            text_widget.configure(foreground=self.get_text_color())
            text_widget.tag_remove("strikethrough", "1.0", "end-1c")
            text_widget.tag_add("normal", "1.0", "end-1c")
        if self.dirty_callback:
            self.dirty_callback()

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
        for _, _, _, _, deadline_label, _ in self.checkboxes:
             self.stop_checkbox_due_flash(deadline_label)

        self.container.destroy()
        if self.remove_callback:
            self.remove_callback(self)

    def get_data(self):
        return {
            "title": self.title,
            "checkboxes": [(text_widget.get("1.0", "end-1c"), var.get(), deadline) for _, text_widget, var, _, _, deadline in self.checkboxes],
            "due_date": self.due_date,
            "color": self.color,
            "created": self.created
        }

    def focus_next_entry(self, current_text):
        entries = [text for _, text, _ in self.checkboxes]
        try:
            idx = entries.index(current_text)
            if idx + 1 < len(entries):
                entries[idx + 1].focus_set()
                return "break"
        except ValueError:
            pass

    def focus_prev_entry(self, current_text):
        entries = [text for _, text, _ in self.checkboxes]
        try:
            idx = entries.index(current_text)
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
        for container, text_widget, var, cb, deadline_label, deadline in self.checkboxes:
            try:
                container.configure(bg=self.color)
                text_widget.configure(bg=self.color, fg=text_color)
                cb.configure(bg=self.color, fg=text_color, selectcolor=self.color, activebackground=self.color, activeforeground=text_color)
                current_text = deadline_label.cget('text')
                is_overdue_text = "days overdue" in current_text

                if not getattr(deadline_label, '_flashing', False) or not is_overdue_text:
                     deadline_label.configure(bg=self.color, fg=text_color)

                for child in container.winfo_children():
                    if isinstance(child, tk.Button):
                        child.configure(bg=self.color, fg=text_color)
            except Exception:
                pass
        try:
            self.remove_task_label.configure(fg="#000000") # Always black
        except Exception:
            pass
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
            
        def remove_date():
            self.due_date = ""
            self.due_label.config(text="")
            if self.dirty_callback:
                self.dirty_callback()
            top.destroy()
            
        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Set", command=set_date).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Remove", command=remove_date).pack(side="left", padx=5)
        
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
            self.remove_task_label.configure(bg="#ff4444")
        else:
            self.remove_task()

    def reset_trash(self, event=None):
        if self.trash_armed:
            self.trash_armed = False
            self.remove_task_label.configure(bg="#ffcccc")

    def set_checkbox_deadline(self, container, deadline_label):
        if Calendar is None:
            messagebox.showerror("Calendar Not Installed", "Please install tkcalendar: pip install tkcalendar")
            return
        
        checkbox_data = None
        for cb_data in self.checkboxes:
            if cb_data[0] == container:
                checkbox_data = cb_data
                break
        
        if not checkbox_data:
            return
            
        top = tk.Toplevel()
        top.title("Select Deadline")
        cal = Calendar(top, selectmode='day')
        cal.pack(padx=10, pady=10)
        
        def set_date():
            date = cal.get_date()
            idx = self.checkboxes.index(checkbox_data)
            self.checkboxes[idx] = (container, checkbox_data[1], checkbox_data[2], checkbox_data[3], deadline_label, date)
            self.get_checkbox_due_text(deadline_label, date)
            if self.dirty_callback:
                self.dirty_callback()
            top.destroy()
            
        def remove_date():
            idx = self.checkboxes.index(checkbox_data)
            self.checkboxes[idx] = (container, checkbox_data[1], checkbox_data[2], checkbox_data[3], deadline_label, "")
            self.get_checkbox_due_text(deadline_label, "")
            if self.dirty_callback:
                self.dirty_callback()
            top.destroy()
            
        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Set", command=set_date).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Remove", command=remove_date).pack(side="left", padx=5)
        
        top.grab_set()
        top.wait_window()

    def get_checkbox_due_text(self, deadline_label, due_date):
        text_to_display = ""
        should_flash = False
        is_overdue = False

        if not due_date:
            self.stop_checkbox_due_flash(deadline_label)
            text_to_display = ""
        else:
            try:
                due = datetime.strptime(due_date, "%m/%d/%y").date()
                today = datetime.now().date()
                days_left = (due - today).days

                if days_left == 0:
                    text_to_display = f"{due_date} (Today!)"
                    should_flash = True
                elif days_left == 1:
                    text_to_display = f"{due_date} (Tomorrow!)"
                    should_flash = True
                elif days_left < 0:
                    text_to_display = f"{due_date} ({-days_left} days overdue)"
                    is_overdue = True # Stop flashing and set black background
                else:
                    text_to_display = f"{due_date} ({days_left} days left)"

            except Exception:
                text_to_display = due_date # Display raw date on error

        deadline_label.config(text=text_to_display)

        if should_flash:
            self.start_checkbox_due_flash(deadline_label)
        elif is_overdue:
            self.stop_checkbox_due_flash(deadline_label, overdue=True)
        else:
            self.stop_checkbox_due_flash(deadline_label)

        return text_to_display

    def start_checkbox_due_flash(self, deadline_label):
        if getattr(deadline_label, '_flashing', False):
            return
        deadline_label._flashing = True
        deadline_label._flash_state = False
        self._flash_single_checkbox_due_label(deadline_label)

    def stop_checkbox_due_flash(self, deadline_label, overdue=False):
        if getattr(deadline_label, '_flashing', False):
            deadline_label._flashing = False
            if hasattr(deadline_label, '_flash_id') and deadline_label._flash_id:
                 try:
                    deadline_label.after_cancel(deadline_label._flash_id)
                 except tk.TclError: # Handle case where widget is already destroyed
                    pass
                 deadline_label._flash_id = None

        if overdue:
            deadline_label.configure(bg="#000000", fg="#ffffff")
        else:
            deadline_label.configure(bg=self.color, fg=self.get_text_color())

    def _flash_single_checkbox_due_label(self, deadline_label):
        if not getattr(deadline_label, '_flashing', False) or not deadline_label.winfo_exists():
            if hasattr(deadline_label, '_flash_id') and deadline_label._flash_id:
                 try:
                    deadline_label.after_cancel(deadline_label._flash_id)
                 except tk.TclError:
                    pass
                 deadline_label._flash_id = None
            return
        flash_state = getattr(deadline_label, '_flash_state', False)

        if flash_state:
            deadline_label.configure(bg="#ff4444", fg="#ffffff")
        else:
            deadline_label.configure(bg="#ffffff", fg="#ff4444")

        deadline_label._flash_state = not flash_state
        deadline_label._flash_id = deadline_label.after(400, lambda: self._flash_single_checkbox_due_label(deadline_label))

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🐮 TaskBarn")
        self.tasks = []
        self.dirty = False
        self.sort_method = tk.StringVar(value="created")
        self.bg_color = "#f0f0f0"
        self.fg_color = "#000000"
        self._loading = True
        self._resize_after_id = None
        self._last_canvas_width = 0
        
        config = self.load_config()
        self.current_file = config.get('last_file', SAVE_FILE)
        win_size = config.get('window_size')
        was_maximized = config.get('maximized', False)
        if win_size:
            self.root.geometry(win_size)
        if was_maximized:
            self.root.state('zoomed')

        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)
        
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
        self.sort_method.set(sort_labels[0])
        sort_menu.config(bg=self.bg_color, fg=self.fg_color, highlightthickness=0, activebackground=self.bg_color, activeforeground=self.fg_color)
        sort_menu.pack(side="left", padx=5)

        entry_frame = tk.Frame(root, bg=self.bg_color)
        entry_frame.pack(padx=10, pady=(4, 0), fill="x")

        self.entry = tk.Entry(entry_frame, bg=self.bg_color, fg=self.fg_color, font=("Segoe UI", 20), width=30, justify="center")
        self.entry.pack(side="left", pady=0, padx=(0, 8), expand=True, fill="x")
        self.entry.bind("<Return>", lambda e: self.add_task())

        self.add_task_btn = tk.Button(entry_frame, text="➕ Add Group", command=self.add_task, bg=self.bg_color, fg=self.fg_color)
        self.add_task_btn.pack(side="left", pady=0)

        self.canvas = tk.Canvas(root, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview, bg=self.bg_color, troughcolor=self.bg_color, activebackground=self.bg_color)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        self.task_frame = tk.Frame(self.canvas, bg=self.bg_color)
        self.canvas.create_window((0, 0), window=self.task_frame, anchor="nw", width=self.canvas.winfo_width())

        self.task_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.load_tasks()
        self._loading = False # Loading complete

    def _on_mousewheel(self, event):
        first, last = self.canvas.yview()
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            if first > 0.0:
                self.canvas.yview_scroll(-1, "units")

    def on_canvas_resize(self, event):
        if self._resize_after_id:
            self.root.after_cancel(self._resize_after_id)
        
        new_width = event.width
        if new_width == self._last_canvas_width:
            return
            
        self._last_canvas_width = new_width
        
        self._resize_after_id = self.root.after(100, lambda: self._do_canvas_resize(new_width))
    
    def _do_canvas_resize(self, new_width):
        self._resize_after_id = None
        self.canvas.itemconfig("all", width=new_width)
        task_width_estimate = 300
        tasks_per_row = max(1, new_width // task_width_estimate)
        self.place_tasks(tasks_per_row)

    def mark_dirty(self, *args, **kwargs):
        if not self._loading:
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

    def place_tasks(self, tasks_per_row):
        if not self.tasks:
            return
            
        for task in self.tasks:
            task.container.grid_forget()
            
        for i in range(20):  # Assuming max 20 columns is sufficient
            self.task_frame.grid_columnconfigure(i, weight=0)

        num_tasks = len(self.tasks)
        
        for row in range((num_tasks + tasks_per_row - 1) // tasks_per_row):
            start = row * tasks_per_row
            end = min(start + tasks_per_row, num_tasks)
            num_in_row = end - start
            pad = (tasks_per_row - num_in_row) // 2
            
            for col in range(tasks_per_row):
                self.task_frame.grid_columnconfigure(col + 1 + pad, weight=1)

            self.task_frame.grid_columnconfigure(0, weight=1)  # Left spacer
            self.task_frame.grid_columnconfigure(tasks_per_row + 1 + pad, weight=1)  # Right spacer

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
        if answer is None:
            return
        elif answer:
            self.save_tasks()
            self.save_last_file()
            self.root.destroy()
        else:
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
                        loaded_checkboxes_data = item.get("checkboxes", [])
                        checkboxes_to_add = []
                        for cb_data in loaded_checkboxes_data:
                            # Ensure cb_data is a list/tuple and has at least 2 elements
                            if isinstance(cb_data, (list, tuple)) and len(cb_data) >= 2:
                                label = cb_data[0]
                                checked = cb_data[1]
                                deadline = cb_data[2] if len(cb_data) > 2 else ""
                                checkboxes_to_add.append((label, checked, deadline))
                            else:
                                print(f"Skipping invalid checkbox data: {cb_data}") # Or use a more robust error handling

                        task = Task(
                            self.task_frame,
                            item["title"],
                            remove_callback=self.remove_task,
                            checkboxes=checkboxes_to_add,
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
        self.place_tasks(3)  # Default to 3 columns

    def new_file(self):
        if self.dirty:
            answer = messagebox.askyesnocancel(
                "Save Changes?",
                "Do you want to save your changes before creating a new file?",
                icon="question"
            )
            if answer is None:
                return
            elif answer:
                self.save_tasks()

        for task in self.tasks:
            task.container.destroy()
        self.tasks.clear()
        self.current_file = SAVE_FILE
        self.root.title("🐮 TaskBarn")
        self.dirty = False

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()
