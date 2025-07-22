
import gi
import threading
import subprocess
import json
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class YouTubeMusicPlayer:
    def __init__(self):
        self.window = Gtk.Window(title="YouTube Music Player")
        self.window.set_default_size(500, 400)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.connect("destroy", Gtk.main_quit)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_left(20)
        main_box.set_margin_right(20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        self.window.add(main_box)
        
        header = Gtk.Label()
        header.set_markup("<big><b>🎵 YouTube Music Player</b></big>")
        main_box.pack_start(header, False, False, 0)
        
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Enter song name...")
        self.search_entry.connect("activate", self.on_search_clicked)
        
        search_button = Gtk.Button(label="Search")
        search_button.connect("clicked", self.on_search_clicked)
        
        search_box.pack_start(self.search_entry, True, True, 0)
        search_box.pack_start(search_button, False, False, 0)
        main_box.pack_start(search_box, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        self.results_list = Gtk.ListStore(str, str, str)
        self.tree_view = Gtk.TreeView(model=self.results_list)
        
        renderer_title = Gtk.CellRendererText()
        column_title = Gtk.TreeViewColumn("Title", renderer_title, text=0)
        column_title.set_expand(True)
        self.tree_view.append_column(column_title)
        
        renderer_duration = Gtk.CellRendererText()
        column_duration = Gtk.TreeViewColumn("Duration", renderer_duration, text=2)
        self.tree_view.append_column(column_duration)
        
        self.tree_view.connect("row-activated", self.on_row_activated)
        scrolled.add(self.tree_view)
        main_box.pack_start(scrolled, True, True, 0)
        
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.play_button = Gtk.Button(label="▶ Play")
        self.play_button.connect("clicked", self.on_play_selected)
        self.play_button.set_sensitive(False)
        
        self.stop_button = Gtk.Button(label="⏹ Stop")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.stop_button.set_sensitive(False)
        
        controls_box.pack_start(self.play_button, False, False, 0)
        controls_box.pack_start(self.stop_button, False, False, 0)
        main_box.pack_start(controls_box, False, False, 0)
        
        self.status_label = Gtk.Label()
        self.status_label.set_text("Ready to search...")
        self.status_label.set_xalign(0)
        main_box.pack_start(self.status_label, False, False, 0)
        
        self.current_process = None
        self.is_playing = False
        
        self.window.show_all()

    def update_status(self, text):
        GLib.idle_add(self.status_label.set_text, text)

    def search_youtube(self, query):
        self.update_status("Searching...")
        
        try:
            cmd = [
                "yt-dlp",
                "--print-json",
                "--flat-playlist",
                f"ytsearch10:{query}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.results_list.clear()
            
            lines = result.stdout.strip().split('\n')
            found_results = 0
            
            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if 'title' in data and 'url' in 
                            title = data.get('title', 'Untitled')
                            url = data.get('url', '')
                            duration = data.get('duration_string', 'N/A')
                            
                            self.results_list.append([title, url, duration])
                            found_results += 1
                    except json.JSONDecodeError:
                        continue
            
            if found_results > 0:
                self.update_status(f"Found {found_results} results")
                self.play_button.set_sensitive(True)
            else:
                self.update_status("No results found")
                self.play_button.set_sensitive(False)
                
        except subprocess.CalledProcessError:
            self.update_status("Search error")
            self.play_button.set_sensitive(False)
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.play_button.set_sensitive(False)

    def on_search_clicked(self, widget):
        query = self.search_entry.get_text().strip()
        if query:
            thread = threading.Thread(target=self.search_youtube, args=(query,))
            thread.daemon = True
            thread.start()

    def on_row_activated(self, tree_view, path, column):
        model = tree_view.get_model()
        iter = model.get_iter(path)
        url = model.get_value(iter, 1)
        if url:
            self.play_audio(url)

    def on_play_selected(self, widget):
        selection = self.tree_view.get_selection()
        model, iter = selection.get_selected()
        if iter:
            url = model.get_value(iter, 1)
            if url:
                self.play_audio(url)

    def play_audio(self, url):
        self.stop_audio()
        
        self.update_status("Starting playback...")
        self.is_playing = True
        self.play_button.set_sensitive(False)
        self.stop_button.set_sensitive(True)
        
        def play_thread():
            try:
                cmd = [
                    "mpv",
                    "--no-video",
                    "--audio-display=no",
                    "--quiet",
                    url
                ]
                
                self.current_process = subprocess.Popen(cmd)
                self.current_process.wait()
                
                GLib.idle_add(self.on_playback_finished)
            except Exception as e:
                GLib.idle_add(self.update_status, f"Playback error: {str(e)}")
                GLib.idle_add(self.on_playback_finished)
        
        thread = threading.Thread(target=play_thread)
        thread.daemon = True
        thread.start()

    def stop_audio(self):
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
        self.current_process = None

    def on_stop_clicked(self, widget):
        self.stop_audio()
        self.on_playback_finished()

    def on_playback_finished(self):
        self.is_playing = False
        self.current_process = None
        self.play_button.set_sensitive(True)
        self.stop_button.set_sensitive(False)
        self.update_status("Playback stopped")

if __name__ == "__main__":
    app = YouTubeMusicPlayer()
    Gtk.main()
