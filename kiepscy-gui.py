import os
import re
import random
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import vlc
import tkinter.font as tkfont

def load_links(file_path):
    if not os.path.exists(file_path):
        messagebox.showerror("Error", f"File '{file_path}' not found.")
        return None
    seasons = {}
    current_season = None
    current_name = None
    url_pattern = re.compile(r"^https?://")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                if re.match(r"SEZON\s+\d+", line, re.IGNORECASE):
                    current_season = line
                    seasons[current_season] = []
                    current_name = None
                elif url_pattern.match(line):
                    if current_season and current_name:
                        seasons[current_season].append((current_name, line))
                        current_name = None
                else:
                    current_name = line
    except Exception as e:
        messagebox.showerror("Error Reading File", f"An error occurred: {e}")
        return None
    if not seasons:
        messagebox.showinfo("Info", "No seasons or episodes found.")
        return None
    return seasons

class EpisodePlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kiepskie GUI")
        self.root.geometry("800x600")
        self.root.configure(bg="black")

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            script_dir = os.getcwd()

        self.font_path = os.path.join(script_dir, "BoinkLETPlain.ttf")

        # Register custom font
        try:
            self.custom_font = tkfont.Font(family="BoinkLETPlain", size=14)
            tkfont.Font(root=root, font=self.custom_font)
            root.tk.call('font', 'create', 'BoinkLETPlain', '-family', 'BoinkLETPlain', '-size', 14)
        except:
            pass
        try:
            root.tk.call('font', 'create', 'boinklet', '-family', 'BoinkLETPlain', '-size', 14)
        except tk.TclError:
            try:
                root.tk.call('font', 'create', 'boinklet', '-family', 'BoinkLETPlain', '-size', 14)
            except:
                pass
        self.font_name = "boinklet"

        self.txt_file = "links.txt"
        self.seasons_data = None

        self.bg_image_path = os.path.join(script_dir, "kiepskie_background.png")

        self.text_color = "#32CD32"
        self.hover_color = "#90EE90"

        self.ui_elements = {}

        self.canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.load_background()

        self.root.bind("<Configure>", self.on_resize)
        self.root.after(100, self.setup_tv_area)

        self.canvas.tag_bind("clickable_text", "<Enter>", self.on_text_enter)
        self.canvas.tag_bind("clickable_text", "<Leave>", self.on_text_leave)
        self.canvas.tag_bind("clickable_text", "<Button-1>", self.on_text_click)

        self.vlc_instance = vlc.Instance()
        self.vlc_player = None
        self.video_playing = False
        self.fullscreen_mode = False

        # Controls frame (hidden initially)
        self.controls_frame = tk.Frame(self.root, bg="#4e4e4e")
        self.controls_frame.pack(side="bottom", fill="x")
        self.controls_frame.pack_forget()

        self.play_pause_btn = tk.Button(self.controls_frame, text="⏯", command=self.toggle_play_pause)
        self.play_pause_btn.pack(side="left", padx=5, pady=5)

        self.stop_btn = tk.Button(self.controls_frame, text="⏹", command=self.stop_video)
        self.stop_btn.pack(side="left", padx=5, pady=5)

        self.vol_down_btn = tk.Button(self.controls_frame, text="🔉", command=self.volume_down)
        self.vol_down_btn.pack(side="left", padx=5, pady=5)

        self.vol_up_btn = tk.Button(self.controls_frame, text="🔊", command=self.volume_up)
        self.vol_up_btn.pack(side="left", padx=5, pady=5)

        self.fullscreen_btn = tk.Button(self.controls_frame, text="⛶", command=self.toggle_fullscreen)
        self.fullscreen_btn.pack(side="left", padx=5, pady=5)

        self.seek_var = tk.DoubleVar()
        self.seekbar = tk.Scale(
            self.controls_frame,
            variable=self.seek_var,
            from_=0, to=1000,
            orient="horizontal",
            showvalue=0,
            length=300,
            command=self.on_seek
        )
        self.seekbar.pack(side="left", padx=5, pady=5)

        # Overlay controls for fullscreen
        self.overlay_controls = tk.Frame(self.root, bg="#4e4e4e")
        self.overlay_controls.place_forget()

        self.play_pause_btn2 = tk.Button(self.overlay_controls, text="⏯", command=self.toggle_play_pause)
        self.play_pause_btn2.pack(side="left", padx=5, pady=5)

        self.stop_btn2 = tk.Button(self.overlay_controls, text="⏹", command=self.stop_video)
        self.stop_btn2.pack(side="left", padx=5, pady=5)

        self.vol_down_btn2 = tk.Button(self.overlay_controls, text="🔉", command=self.volume_down)
        self.vol_down_btn2.pack(side="left", padx=5, pady=5)

        self.vol_up_btn2 = tk.Button(self.overlay_controls, text="🔊", command=self.volume_up)
        self.vol_up_btn2.pack(side="left", padx=5, pady=5)

        self.fullscreen_btn2 = tk.Button(self.overlay_controls, text="⛶", command=self.toggle_fullscreen)
        self.fullscreen_btn2.pack(side="left", padx=5, pady=5)

        # Keybinds
        root.bind("<Left>", lambda e: self.seek_relative(-10))
        root.bind("<Right>", lambda e: self.seek_relative(10))
        root.bind("<space>", lambda e: self.toggle_play_pause())
        root.bind("<Up>", lambda e: self.volume_up())
        root.bind("<Down>", lambda e: self.volume_down())
        root.bind("f", lambda e: self.toggle_fullscreen())

        root.bind("<Motion>", self.show_overlay_controls)

    def load_background(self):
        try:
            if not os.path.exists(self.bg_image_path):
                print(f"Image not found: {self.bg_image_path}")
                return
            self.original_image = Image.open(self.bg_image_path)
            self.update_background_display()
        except Exception as e:
            print(f"Error loading background: {e}")

    def update_background_display(self):
        if not hasattr(self, 'original_image') or not self.original_image:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 1 or h < 1:
            return
        try:
            img_resized = self.original_image.resize((w, h), Image.Resampling.LANCZOS)
        except:
            return
        self.bg_photo = ImageTk.PhotoImage(img_resized)
        self.canvas.delete("background")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.bg_photo, tags="background")
        self.canvas.tag_raise("tv_area")
        self.canvas.tag_raise("ui_element")

    def on_resize(self, event):
        if event.widget == self.root:
            if hasattr(self, '_resize_job'):
                self.root.after_cancel(self._resize_job)
            self._resize_job = self.root.after(150, self.redraw_all)

    def redraw_all(self):
        self.update_background_display()
        if self.fullscreen_mode:
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            self.canvas.coords(self.tv_canvas_window, 0, 0)
            self.tv_canvas.config(width=w, height=h)
            return
        self.update_tv_area()
        self.show_current_screen()

    def setup_tv_area(self):
        self.tv_relx = 0.048
        self.tv_rely = 0.41
        self.tv_relwidth = 0.3
        self.tv_relheight = 0.35

        self.tv_canvas = tk.Canvas(self.canvas, bg="#4e4e4e", highlightthickness=0)
        self.tv_canvas_window = self.canvas.create_window(0, 0, anchor=tk.NW, window=self.tv_canvas, tags="tv_area")

        self.tv_scrollable_canvas = tk.Canvas(self.tv_canvas, bg="#4e4e4e", highlightthickness=0)
        self.tv_scrollable_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.tv_scrollbar = ttk.Scrollbar(
            self.tv_canvas, orient="vertical", command=self.tv_scrollable_canvas.yview, style="Vertical.TScrollbar"
        )
        self.tv_scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor='ne')

        self.tv_scrollable_canvas.configure(yscrollcommand=self.tv_scrollbar.set)

        self.tv_inner_frame = tk.Frame(self.tv_scrollable_canvas, bg="#4e4e4e")
        self.tv_inner_frame_id = self.tv_scrollable_canvas.create_window((0, 0), window=self.tv_inner_frame, anchor=tk.NW)

        def on_frame_configure(event):
            self.tv_scrollable_canvas.configure(scrollregion=self.tv_scrollable_canvas.bbox("all"))

        self.tv_inner_frame.bind("<Configure>", on_frame_configure)

        self.tv_scrollable_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.tv_scrollable_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.tv_scrollable_canvas.bind_all("<Button-5>", self._on_mousewheel)

        self.search_frame = tk.Frame(self.tv_inner_frame, bg="#4e4e4e")
        self.search_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(self.search_frame, text="Szukaj:", fg="white", bg="#4e4e4e", font=(self.font_name, 12)).pack(side="left")

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(self.search_frame, textvariable=self.search_var, width=15, font=(self.font_name, 12))
        search_entry.pack(side="left", padx=5)

        def on_search_change(*args):
            self.search_episode_by_number()

        self.search_var.trace_add("write", on_search_change)

        self.tv_list_frame = tk.Frame(self.tv_inner_frame, bg="#4e4e4e")
        self.tv_list_frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Vertical.TScrollbar",
            background="#4e4e4e",
            troughcolor="#4e4e4e",
            arrowcolor="#CCCCCC"
        )

        self.update_tv_area()
        self.show_main_menu()

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.tv_scrollable_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.tv_scrollable_canvas.yview_scroll(1, "units")
        else:
            delta = int(-1 * (event.delta / 120))
            self.tv_scrollable_canvas.yview_scroll(delta, "units")

    def update_tv_area(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        tv_x = int(w * self.tv_relx)
        tv_y = int(h * self.tv_rely)
        tv_width = int(w * self.tv_relwidth)
        tv_height = int(h * self.tv_relheight)
        self.tv_canvas.config(width=tv_width, height=tv_height)
        self.canvas.coords(self.tv_canvas_window, tv_x, tv_y)

    def show_main_menu(self):
        if not self.fullscreen_mode:
            self.stop_video()
            self.tv_scrollable_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.current_screen = 'main'
        self.canvas.delete("ui_element")
        self.ui_elements.clear()

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        font_title = (self.font_name, 36, "bold")
        font_button = (self.font_name, 24, "bold")

        self.canvas.create_text(
            w * 0.75, h * 0.15, text="KIEPSKIE GUI", font=font_title,
            fill=self.text_color, anchor=tk.CENTER, tags=("ui_element",)
        )

        labels = ["WYBÓR ODCINKA", "WYBÓR SEZONU", "LOSOWY ODCINEK"]
        tags = ["button_odcinka", "button_sezonu", "button_losowy"]
        for i, (label, tag) in enumerate(zip(labels, tags)):
            y = h * 0.4 + i * h * 0.12
            self.canvas.create_text(
                w * 0.75, y, text=label, font=font_button,
                fill=self.text_color, anchor=tk.CENTER,
                tags=("ui_element", "clickable_text", tag)
            )

    def on_text_enter(self, event):
        item_id = self.canvas.find_withtag(tk.CURRENT)
        if item_id:
            self.canvas.itemconfig(item_id[0], fill=self.hover_color)

    def on_text_leave(self, event):
        item_id = self.canvas.find_withtag(tk.CURRENT)
        if item_id:
            self.canvas.itemconfig(item_id[0], fill=self.text_color)

    def on_text_click(self, event):
        item_id = self.canvas.find_withtag(tk.CURRENT)
        if not item_id:
            return
        tags = self.canvas.gettags(item_id[0])
        if "button_sezonu" in tags:
            self.show_season_list()
        elif "button_odcinka" in tags:
            self.show_all_episodes()
        elif "button_losowy" in tags:
            self.play_random_episode()

    def show_season_list(self):
        if not self.fullscreen_mode:
            self.stop_video()
            self.tv_scrollable_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.current_screen = 'season_list'
        self.clear_tv_list()
        if not self.load_data_if_needed():
            return
        font = (self.font_name, 14, "bold")
        for idx, season in enumerate(self.seasons_data.keys()):
            lbl = tk.Label(
                self.tv_list_frame, text=season, font=font,
                fg=self.text_color, bg="#4e4e4e", anchor="w", justify="left", cursor="hand2"
            )
            lbl.pack(fill="x", padx=5, pady=2)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=self.hover_color))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=self.text_color))
            lbl.bind("<Button-1>", lambda e, s=season: self.show_episode_list(s))

    def show_episode_list(self, season_name):
        if not self.fullscreen_mode:
            self.stop_video()
            self.tv_scrollable_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.current_screen = 'episode_list'
        self.current_season_name = season_name
        self.clear_tv_list()
        episodes = self.seasons_data.get(season_name, [])
        font = (self.font_name, 12, "bold")
        for idx, (ep_name, ep_url) in enumerate(episodes):
            lbl = tk.Label(
                self.tv_list_frame, text=ep_name, font=font,
                fg=self.text_color, bg="#4e4e4e", anchor="w", justify="left", cursor="hand2"
            )
            lbl.pack(fill="x", padx=5, pady=2)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=self.hover_color))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=self.text_color))
            lbl.bind("<Button-1>", lambda e, url=ep_url, name=ep_name: self.play_link(url, name))

    def show_all_episodes(self):
        if not self.fullscreen_mode:
            self.stop_video()
            self.tv_scrollable_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.current_screen = 'all_episodes'
        self.clear_tv_list()
        if not self.load_data_if_needed():
            return
        all_episodes = []
        for eps in self.seasons_data.values():
            all_episodes.extend(eps)
        font = (self.font_name, 12, "bold")
        for idx, (ep_name, ep_url) in enumerate(all_episodes):
            lbl = tk.Label(
                self.tv_list_frame, text=ep_name, font=font,
                fg=self.text_color, bg="#4e4e4e", anchor="w", justify="left", cursor="hand2"
            )
            lbl.pack(fill="x", padx=5, pady=2)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=self.hover_color))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=self.text_color))
            lbl.bind("<Button-1>", lambda e, url=ep_url, name=ep_name: self.play_link(url, name))

    def clear_tv_list(self):
        for widget in self.tv_list_frame.winfo_children():
            widget.destroy()

    def search_episode_by_number(self):
        query = self.search_var.get().strip().lower()
        if not self.load_data_if_needed():
            return
        all_episodes = []
        for eps in self.seasons_data.values():
            all_episodes.extend(eps)
        filtered = []
        for idx, (name, url) in enumerate(all_episodes, 1):
            idx_str = str(idx)
            name_lower = name.lower()
            if query in idx_str or query in name_lower:
                filtered.append((name, url))
        self.current_screen = 'search_results'
        self.clear_tv_list()
        if not filtered:
            lbl = tk.Label(
                self.tv_list_frame, text="Brak wyników", font=(self.font_name, 12, "bold"),
                fg="white", bg="#4e4e4e"
            )
            lbl.pack(pady=10)
            return
        font = (self.font_name, 12, "bold")
        for idx, (ep_name, ep_url) in enumerate(filtered):
            lbl = tk.Label(
                self.tv_list_frame, text=ep_name, font=font,
                fg=self.text_color, bg="#4e4e4e", anchor="w", justify="left", cursor="hand2"
            )
            lbl.pack(fill="x", padx=5, pady=2)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=self.hover_color))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=self.text_color))
            lbl.bind("<Button-1>", lambda e, url=ep_url, name=ep_name: self.play_link(url, name))

    def load_data_if_needed(self):
        if self.seasons_data is None:
            self.seasons_data = load_links(self.txt_file)
        return self.seasons_data is not None

    def play_link(self, link, window_title="Playing Episode"):
        self.clear_tv_list()
        if self.vlc_player:
            self.vlc_player.stop()
        self.vlc_player = self.vlc_instance.media_player_new()
        media = self.vlc_instance.media_new(link)
        self.vlc_player.set_media(media)
        wid = self.tv_canvas.winfo_id()
        if os.name == "nt":
            self.vlc_player.set_hwnd(wid)
        else:
            self.vlc_player.set_xwindow(wid)
        self.vlc_player.play()
        self.video_playing = True
        self.tv_scrollable_canvas.place_forget()
        self.tv_scrollbar.place_forget()
        self.controls_frame.pack(side="bottom", fill="x")
        self.update_seekbar()

    def toggle_play_pause(self):
        if self.vlc_player:
            if self.vlc_player.is_playing():
                self.vlc_player.pause()
            else:
                self.vlc_player.play()

    def stop_video(self):
        if self.vlc_player:
            self.vlc_player.stop()
        self.video_playing = False
        self.controls_frame.pack_forget()
        self.seek_var.set(0)
        if not self.fullscreen_mode:
            self.tv_scrollable_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.tv_scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor='ne')

    def volume_up(self):
        if self.vlc_player:
            vol = self.vlc_player.audio_get_volume()
            self.vlc_player.audio_set_volume(min(vol + 10, 150))

    def volume_down(self):
        if self.vlc_player:
            vol = self.vlc_player.audio_get_volume()
            self.vlc_player.audio_set_volume(max(vol - 10, 0))

    def toggle_fullscreen(self):
        is_full = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not is_full)
        self.fullscreen_mode = not is_full

        if self.fullscreen_mode:
            self.controls_frame.pack_forget()
            self.tv_scrollable_canvas.place_forget()
            self.tv_scrollbar.place_forget()
            self.canvas.pack(fill="both", expand=True)
            self.canvas.tag_raise("tv_area")
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            self.canvas.coords(self.tv_canvas_window, 0, 0)
            self.tv_canvas.config(width=w, height=h)
            self.overlay_controls.place(relx=0.5, rely=1.0, anchor="s")
            self.overlay_controls.lift()
            self.overlay_controls.after(3000, self.hide_overlay_controls)
        else:
            self.overlay_controls.place_forget()
            self.canvas.pack(fill="both", expand=True)
            self.update_tv_area()
            self.canvas.tag_raise("tv_area")
            if self.video_playing:
                self.tv_scrollable_canvas.place_forget()
                self.tv_scrollbar.place_forget()
                self.controls_frame.pack(side="bottom", fill="x")
            else:
                self.tv_scrollable_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
                self.tv_scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor='ne')
                self.controls_frame.pack_forget()

    def hide_overlay_controls(self):
        if self.fullscreen_mode:
            self.overlay_controls.place_forget()

    def show_overlay_controls(self, event=None):
        if self.fullscreen_mode:
            self.overlay_controls.place(relx=0.5, rely=1.0, anchor="s")
            self.overlay_controls.lift()
            self.overlay_controls.after(3000, self.hide_overlay_controls)

    def on_seek(self, value):
        if self.vlc_player and self.vlc_player.get_length() > 0:
            pos = float(value) / 1000
            self.vlc_player.set_position(pos)

    def update_seekbar(self):
        if self.vlc_player and self.vlc_player.is_playing():
            try:
                pos = self.vlc_player.get_position()
                self.seek_var.set(pos * 1000)
            except:
                pass
        self.root.after(500, self.update_seekbar)

    def seek_relative(self, seconds):
        if self.vlc_player:
            length = self.vlc_player.get_length() / 1000
            current = self.vlc_player.get_time() / 1000
            new_time = max(0, min(length, current + seconds))
            self.vlc_player.set_time(int(new_time * 1000))

    def play_random_episode(self):
        if not self.load_data_if_needed():
            return
        all_episodes = [(n, l) for eps in self.seasons_data.values() for n, l in eps]
        if not all_episodes:
            messagebox.showinfo("Info", "Brak odcinków do losowania.")
            return
        selected_name, selected_link = random.choice(all_episodes)
        self.play_link(selected_link, window_title=f"(Losowy) {selected_name}")

if __name__ == "__main__":
    if not os.path.exists("links.txt"):
        root_check = tk.Tk()
        root_check.withdraw()
        messagebox.showerror("Fatal Error", "links.txt not found!")
        root_check.destroy()
    else:
        root = tk.Tk()
        app = EpisodePlayerApp(root)
        root.mainloop()
