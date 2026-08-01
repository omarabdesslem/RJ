#!/usr/bin/env python3
import os
import shutil
import subprocess
import threading
import tkinter as tk
import tkinter.font as tkfont
from queue import Empty, Queue
from tkinter import filedialog, messagebox, ttk

import rawpy
from PIL import Image


RAW_FORMATS = (".nef", ".cr2", ".cr3", ".arw", ".dng")
WINDOW_WIDTH = 540
COLLAPSED_HEIGHT = 372
EXTRAS_HEIGHT = 116
ACTIVITY_HEIGHT = 54
BACKGROUND = "#1F2124"
PATH_BACKGROUND = "#2A2C30"
BUTTON_FILL = "#4A4C50"
BUTTON_HOVER = "#5A5C60"
DISABLED_BUTTON = "#35373A"
TEXT = "#F2F2F4"
MUTED_TEXT = "#A6A7AB"


def system_accent_color():
    accent_colors = {
        -1: "#8E8E93",
        0: "#FF453A",
        1: "#FF9F0A",
        2: "#FFD60A",
        3: "#30D158",
        4: "#0A84FF",
        5: "#BF5AF2",
        6: "#FF375F",
    }
    try:
        accent = int(subprocess.check_output(["defaults", "read", "-g", "AppleAccentColor"], text=True))
    except (OSError, ValueError, subprocess.CalledProcessError):
        accent = 4
    return accent_colors.get(accent, accent_colors[4])


SYSTEM_ACCENT = system_accent_color()


class ColorButton(tk.Canvas):
    def __init__(self, parent, text, command, font):
        super().__init__(
            parent,
            bg=BACKGROUND,
            bd=0,
            highlightthickness=0,
            cursor="pointinghand",
            takefocus=True,
        )
        self.text = text
        self.command = command
        self.font = font
        self.enabled = True
        self.primary = False
        self.hovered = False
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)
        self.bind("<Return>", self._on_key)
        self.bind("<space>", self._on_key)

    def set_text(self, text):
        self.text = text
        self._draw()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.hovered = False
        self._draw()

    def set_primary(self, primary):
        self.primary = primary
        self._draw()

    def _on_enter(self, _event):
        if self.enabled:
            self.hovered = True
            self._draw()

    def _on_leave(self, _event):
        self.hovered = False
        self._draw()

    def _on_click(self, _event):
        if self.enabled:
            self.focus_set()
            self.command()

    def _on_key(self, _event):
        if self.enabled:
            self.command()

    def _draw(self, _event=None):
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1:
            return

        if not self.enabled:
            fill = DISABLED_BUTTON
            text_color = MUTED_TEXT
        elif self.primary:
            fill = SYSTEM_ACCENT
            text_color = TEXT
        else:
            fill = BUTTON_HOVER if self.hovered else BUTTON_FILL
            text_color = TEXT

        self.delete("all")
        radius = min(8, height // 2)
        self.create_rectangle(radius, 0, width - radius, height, fill=fill, outline=fill)
        self.create_rectangle(0, radius, width, height - radius, fill=fill, outline=fill)
        self.create_arc(0, 0, radius * 2, radius * 2, start=90, extent=90, fill=fill, outline=fill)
        self.create_arc(
            width - radius * 2,
            0,
            width,
            radius * 2,
            start=0,
            extent=90,
            fill=fill,
            outline=fill,
        )
        self.create_arc(
            width - radius * 2,
            height - radius * 2,
            width,
            height,
            start=270,
            extent=90,
            fill=fill,
            outline=fill,
        )
        self.create_arc(0, height - radius * 2, radius * 2, height, start=180, extent=90, fill=fill, outline=fill)
        self.create_text(width / 2, height / 2, text=self.text, fill=text_color, font=self.font)


class ImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RJ")
        self.root.geometry(f"{WINDOW_WIDTH}x{COLLAPSED_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=BACKGROUND)
        self.root.withdraw()
        self.events = Queue()
        self.worker = None
        self.extras_visible = False
        self.activity_visible = False
        self.button_font = tkfont.nametofont("TkDefaultFont").copy()
        self.button_font.configure(size=13)
        self.path_font = tkfont.nametofont("TkDefaultFont").copy()
        self.path_font.configure(size=12)

        self.main = tk.Frame(root, bg=BACKGROUND)
        self.main.pack(fill="both", expand=True)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.input_display = tk.StringVar()
        self.output_display = tk.StringVar()
        self.status_text = tk.StringVar(value="Choose folders to begin.")

        self.input_browse_button = self._make_button(
            self.main,
            text="Browse",
            command=self.select_input_folder,
            font=self.button_font,
        )
        self.input_browse_button.place(relx=0.5, y=112, anchor="n", width=112, height=30)

        self.input_entry = self._make_path_entry(self.main, self.input_display)

        self.convert_button = self._make_button(
            self.main,
            text="Convert",
            command=self.start_conversion,
            font=self.button_font,
        )
        self.convert_button.place(relx=0.5, y=216, anchor="n", width=112, height=30)
        self._set_convert_ready(False)

        self.extras_button = self._make_button(
            self.main,
            text="Extras",
            command=self.toggle_extras,
            font=self.button_font,
        )
        self.extras_button.place(relx=0.5, y=258, anchor="n", width=112, height=30)

        self.extras = tk.Frame(self.main, bg=BACKGROUND, width=430, height=96)
        self.extras.pack_propagate(False)

        quality_frame = tk.Frame(self.extras, bg=BACKGROUND)
        quality_frame.place(x=0, y=0, width=430, height=34)
        quality_frame.columnconfigure(1, weight=1)

        tk.Label(
            quality_frame,
            text="JPEG quality",
            bg=BACKGROUND,
            fg=MUTED_TEXT,
            font=self.path_font,
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.quality_var = tk.DoubleVar(value=85)
        self.quality_display = tk.StringVar(value="85%")
        self.quality_slider = ttk.Scale(
            quality_frame,
            from_=1,
            to=100,
            orient="horizontal",
            variable=self.quality_var,
            command=self._update_quality_label,
        )
        self.quality_slider.grid(row=0, column=1, sticky="ew")
        self.quality_value = tk.Label(
            quality_frame,
            width=4,
            textvariable=self.quality_display,
            bg=BACKGROUND,
            fg=TEXT,
            font=self.path_font,
        )
        self.quality_value.grid(row=0, column=2, sticky="e", padx=(12, 0))

        tk.Label(
            self.extras,
            text="Output folder",
            bg=BACKGROUND,
            fg=MUTED_TEXT,
            font=self.path_font,
        ).place(x=0, y=48, width=82, height=26)
        self.output_entry = self._make_path_entry(self.extras, self.output_display)
        self.output_entry.place(x=88, y=48, width=246, height=26)
        self.output_browse_button = self._make_button(
            self.extras,
            text="Browse",
            command=self.select_output_folder,
            font=self.button_font,
        )
        self.output_browse_button.place(x=342, y=48, width=88, height=26)

        self.activity = tk.Frame(self.main, bg=BACKGROUND, width=360, height=ACTIVITY_HEIGHT)
        self.activity.pack_propagate(False)

        self.progress = ttk.Progressbar(self.activity, orient="horizontal", mode="determinate")
        self.progress.place(x=0, y=0, width=360, height=14)

        self.status_label = tk.Label(
            self.activity,
            textvariable=self.status_text,
            bg=BACKGROUND,
            fg=MUTED_TEXT,
            font=self.path_font,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self.status_label.place(x=0, y=22, width=360, height=32)
        self._resize_window()
        self.root.deiconify()

    def _make_button(self, parent, text, command, font):
        return ColorButton(parent, text, command, font)

    def _make_path_entry(self, parent, variable):
        return tk.Entry(
            parent,
            textvariable=variable,
            state="readonly",
            readonlybackground=PATH_BACKGROUND,
            fg=TEXT,
            font=self.path_font,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )

    @staticmethod
    def default_output_folder(input_folder):
        input_folder = os.path.abspath(input_folder)
        folder_name = os.path.basename(os.path.normpath(input_folder)) or "converted"
        return os.path.join(os.path.dirname(input_folder), f"{folder_name}_converted")

    @staticmethod
    def folder_display_name(folder_path):
        return os.path.basename(os.path.normpath(folder_path))

    @staticmethod
    def rounded_quality(value):
        return max(1, min(100, int(float(value) + 0.5)))

    def _update_quality_label(self, value):
        self.quality_display.set(f"{self.rounded_quality(value)}%")

    def toggle_extras(self):
        self.extras_visible = not self.extras_visible
        if self.extras_visible:
            self.extras.place(relx=0.5, y=322, anchor="n", width=430, height=96)
            self.extras_button.set_text("Hide extras")
        else:
            self.extras.place_forget()
            self.extras_button.set_text("Extras")
        self._resize_window()

    def _show_activity(self):
        if not self.activity_visible:
            self.activity_visible = True
            self._place_activity()
            self._resize_window()

    def _place_activity(self):
        activity_y = 318
        if self.extras_visible:
            activity_y += EXTRAS_HEIGHT
        self.activity.place(relx=0.5, y=activity_y, anchor="n", width=360, height=ACTIVITY_HEIGHT)

    def _resize_window(self):
        height = COLLAPSED_HEIGHT
        if self.extras_visible:
            height += EXTRAS_HEIGHT
        if self.activity_visible:
            height += ACTIVITY_HEIGHT
            self._place_activity()
        x = max(0, (self.root.winfo_screenwidth() - WINDOW_WIDTH) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{height}+{x}+{y}")

    def _set_convert_ready(self, ready):
        self.convert_button.set_enabled(ready)
        self.convert_button.set_primary(ready)

    def _set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.extras_button.set_enabled(enabled)
        self.input_browse_button.set_enabled(enabled)
        self.output_browse_button.set_enabled(enabled)
        self.quality_slider.configure(state=state)
        self._set_convert_ready(enabled and bool(self.input_path.get()))

    def select_input_folder(self):
        folder_selected = filedialog.askdirectory(title="Choose the folder containing your RAW files")
        if folder_selected:
            self.input_path.set(folder_selected)
            self.input_display.set(self.folder_display_name(folder_selected))
            self.input_entry.place(relx=0.5, y=154, anchor="n", width=270, height=26)
            output_folder = self.default_output_folder(folder_selected)
            self.output_path.set(output_folder)
            self.output_display.set(self.folder_display_name(output_folder))
            self.input_entry.xview_moveto(0)
            self.output_entry.xview_moveto(0)
            self._set_convert_ready(True)

    def select_output_folder(self):
        folder_selected = filedialog.askdirectory(
            title="Choose where converted JPEGs should be saved",
            mustexist=False,
        )
        if folder_selected:
            self.output_path.set(folder_selected)
            self.output_display.set(self.folder_display_name(folder_selected))
            self.output_entry.xview_moveto(0)

    def start_conversion(self):
        input_folder = self.input_path.get()
        output_folder = self.output_path.get()
        quality = self.rounded_quality(self.quality_var.get())

        if not input_folder:
            messagebox.showerror("Error", "Please select an input folder.")
            return

        if not os.path.isdir(input_folder):
            messagebox.showerror("Error", "Selected input folder does not exist.")
            return

        if not output_folder:
            messagebox.showerror("Error", "Please select an output folder.")
            return

        if os.path.abspath(input_folder) == os.path.abspath(output_folder):
            messagebox.showerror("Error", "Choose a different output folder.")
            return

        self.progress["value"] = 0
        self.status_text.set("Converting...")
        self._show_activity()
        self._set_controls_enabled(False)
        self.worker = threading.Thread(
            target=self.convert_raw_to_jpeg,
            args=(input_folder, output_folder, quality),
            daemon=True,
        )
        self.worker.start()
        self.root.after(100, self.process_events)

    def convert_raw_to_jpeg(self, input_folder, output_folder, quality):
        input_folder = os.path.abspath(input_folder)
        output_folder = os.path.abspath(output_folder)

        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as exc:
            self.events.put(("error", f"Could not create output folder: {exc}"))
            return

        files_to_process = []
        for root, dirs, files in os.walk(input_folder):
            dirs[:] = [
                directory
                for directory in dirs
                if os.path.abspath(os.path.join(root, directory)) != output_folder
            ]
            for file in files:
                files_to_process.append((root, file))

        total_files = len(files_to_process)
        processed_files = 0

        if total_files == 0:
            self.events.put(("done", "No files were found in the selected folder."))
            return

        for root, file in files_to_process:
            relative_path = os.path.relpath(root, input_folder)
            destination_subfolder = os.path.join(output_folder, relative_path)
            os.makedirs(destination_subfolder, exist_ok=True)

            file_path = os.path.join(root, file)

            if file.lower().endswith(RAW_FORMATS):
                output_path = os.path.join(destination_subfolder, f"{os.path.splitext(file)[0]}.jpg")
                if os.path.exists(output_path):
                    print(f"Skipped {file}, already exists")
                else:
                    try:
                        with rawpy.imread(file_path) as raw:
                            rgb = raw.postprocess()

                        img = Image.fromarray(rgb)
                        img.save(output_path, "JPEG", quality=quality)
                        print(f"Converted {file} to JPEG with quality {quality}")
                    except Exception as exc:
                        print(f"Failed to process {file}: {exc}")
            else:
                destination_file_path = os.path.join(destination_subfolder, file)
                if os.path.exists(destination_file_path):
                    print(f"Skipped {file}, already exists")
                else:
                    try:
                        shutil.copy(file_path, destination_file_path)
                        print(f"Copied {file} to {destination_file_path}")
                    except Exception as exc:
                        print(f"Failed to copy {file}: {exc}")

            processed_files += 1
            self.events.put(("progress", processed_files, total_files, file))

        self.events.put(("done", "All files have been processed."))

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                event_type = event[0]

                if event_type == "progress":
                    processed_files, total_files, file = event[1:]
                    self.progress["value"] = (processed_files / total_files) * 100
                    self.status_text.set(f"Processed {processed_files} of {total_files}: {file}")
                elif event_type == "error":
                    self._set_controls_enabled(True)
                    self.status_text.set("Conversion failed.")
                    messagebox.showerror("Error", event[1])
                    return
                elif event_type == "done":
                    self._set_controls_enabled(True)
                    self.status_text.set(event[1])
                    messagebox.showinfo("Conversion Complete", event[1])
                    return
        except Empty:
            pass

        if self.worker and self.worker.is_alive():
            self.root.after(100, self.process_events)
        else:
            self._set_controls_enabled(True)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageConverterApp(root)
    root.mainloop()
