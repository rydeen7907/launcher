import tkinter as tk
import json
import copy
import os
import shutil
import subprocess, shlex
import sys
from tkinter import ttk, messagebox, simpledialog

try:
    from PIL import Image, ImageTk
    import win32api
    import win32gui
    import win32con
    # Windowsの管理者権限でアプリを起動するためのライブラリ
    import win32com.shell.shell as shell  # type: ignore
except ImportError:
    messagebox.showerror("ライブラリ不足", "この機能には Pillow と pywin32 が必要です。\n'pip install Pillow pywin32' を実行してください。")
    exit()

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    messagebox.showerror("ライブラリ不足", "この機能には tkinterdnd2 が必要です。\n'pip install tkinterdnd2' を実行してください。")
    exit()

class AppLauncher(TkinterDnD.Tk):
    """
    設定ファイルに基づいてアプリケーションをカテゴリ別に表示するランチャー
    """
    def __init__(self):
        super().__init__()
        self.title("アプリランチャー")

        # 永続的な設定ファイルのパスを取得し、設定を読み込む
        self.config_path = self._get_persistent_config_path("config.json")
        self.config = self._load_or_create_config()

        # 設定の読み込みに失敗した場合は終了
        if not self.config:
            # エラーメッセージは _load_or_create_config 内で表示される
            self.destroy()
            return

        # ウィンドウサイズをコンパクトに変更
        self.geometry("420x400")

        # アイコンをキャッシュするための辞書
        self.icon_cache = {}

        self.settings_win = None
        # モダンなウィジェットスタイルを適用
        self.style = ttk.Style(self)
        self.style.theme_use("vista")

        self._create_widgets()

        # 最初のカテゴリのアプリを表示
        if self.config:
            first_category = next(iter(self.config))
            self.show_apps_for_category(first_category)

    def _get_persistent_config_path(self, filename: str) -> str:
        """
        永続的な設定ファイルのパスを取得する。
        .exeの場合は実行ファイルと同じディレクトリ、開発環境ではスクリプトと同じディレクトリ。
        """
        # PyInstallerによって作成された実行可能ファイルから実行されているかチェック
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # .exeのパスを取得
            app_path = os.path.dirname(sys.executable)
        else:
            # スクリプトとして実行されている場合は、スクリプトのディレクトリ
            app_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(app_path, filename)

    def _load_or_create_config(self) -> dict:
        """
        永続的な設定ファイルを読み込む。
        存在しない場合は、バンドル内のデフォルト設定をコピーして作成する。
        """
        # 永続的なパスにconfig.jsonが存在するかチェック
        if not os.path.exists(self.config_path):
            try:
                # バンドル内のデフォルトconfig.jsonのパスを取得
                default_config_path = resource_path("config.json")
                # デフォルト設定を永続的なパスにコピー
                shutil.copy2(default_config_path, self.config_path)
                messagebox.showinfo("設定ファイル", f"設定ファイルを作成しました:\n{self.config_path}")
            except Exception as e:
                messagebox.showerror("エラー", f"デフォルト設定ファイルの作成に失敗しました:\n{e}")
                return {}

        # 永続的な設定ファイルを読み込む
        return self._load_config(self.config_path)

    def _get_icon(self, path: str, size=(32, 32)):
        """
        指定されたパスからアイコンを取得し、Tkinterで使える形式に変換
        取得したアイコンはキャッシュされ、リソースは適切に解放
        """
        try:
            full_path = win32api.SearchPath(None, path, ".exe")[0]
        except Exception:
            full_path = path

        if full_path in self.icon_cache:
            return self.icon_cache[full_path]

        large, small = [], []
        hdc, hdc_mem, hbmp = 0, 0, 0
        try:
            large, small = win32gui.ExtractIconEx(full_path, 0)
            icon_handle = large[0] if large else (small[0] if small else 0)
            if icon_handle == 0:
                return None

            hdc = win32gui.GetDC(0)
            hdc_mem = win32gui.CreateCompatibleDC(hdc)
            hbmp = win32gui.CreateCompatibleBitmap(hdc, size[0], size[1])
            win32gui.SelectObject(hdc_mem, hbmp)
            
            win32gui.DrawIconEx(hdc_mem, 0, 0, icon_handle, size[0], size[1], 0, 0, win32con.DI_NORMAL)
            
            bmp_str = win32gui.GetBitmapBits(hbmp, True)
            img = Image.frombuffer('RGBA', size, bmp_str, 'raw', 'BGRA', 0, 1)

            photo_image = ImageTk.PhotoImage(img.resize(size, Image.Resampling.LANCZOS))
            self.icon_cache[full_path] = photo_image
            return photo_image
        except Exception:
            return None
        finally:
            for i in large + small:
                if i: win32gui.DestroyIcon(i)
            if hbmp: win32gui.DeleteObject(hbmp)
            if hdc_mem: win32gui.DeleteDC(hdc_mem)
            if hdc: win32gui.ReleaseDC(0, hdc)

    def _load_config(self, config_path: str) -> dict:
        """
        設定ファイルを読み込み
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("エラー", f"設定ファイルが見つかりません:\n{config_path}")
        except json.JSONDecodeError:
            messagebox.showerror("エラー", f"設定ファイル '{config_path}' の形式が正しくありません。")
        return {}

    def _create_widgets(self):
        """
        GUIウィジェットを作成して配置
        """
        # メインフレーム
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左側のカテゴリフレーム
        category_frame = ttk.Frame(main_frame)
        category_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # 右側のアプリケーション表示フレーム
        self.app_frame = ttk.Frame(main_frame)
        self.app_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # カテゴリボタンの作成
        for category in self.config.keys():
            button = ttk.Button(
                category_frame,
                text=category,
                command=lambda c=category: self.show_apps_for_category(c)
            )
            button.pack(fill=tk.X, pady=4, ipady=4)

        # --- 設定ボタンを左下に追加 ---
        # ttk.Frameをスペーサーとして使い、ボタンを左下に配置
        spacer = ttk.Frame(category_frame)
        spacer.pack(side=tk.BOTTOM, fill=tk.Y, expand=True)
        
        settings_button = ttk.Button(
            category_frame, text="設定の編集", command=self.open_settings_window
        )
        settings_button.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

    def show_apps_for_category(self, category: str):
        """
        指定されたカテゴリのアプリケーションを右側のフレームに表示
        """
        # 既存のウィジェットをクリア
        for widget in self.app_frame.winfo_children():
            widget.destroy()

        # カテゴリタイトル
        title_label = ttk.Label(
            self.app_frame,
            text=category,
            font=("Yu Gothic UI", 16, "bold")
        )
        title_label.pack(anchor=tk.W, pady=(0, 15))

        # アプリケーションボタンの作成
        apps = self.config.get(category, [])
        for app_info in apps:
            app_name = app_info.get("name", "名称未設定")
            app_path = app_info.get("path")

            if app_path:
                # アイコンを取得
                icon = self._get_icon(app_path)

                app_button = ttk.Button(
                    self.app_frame,
                    text=app_name,
                    image=icon,
                    compound=tk.LEFT, # テキストの左側に画像を表示
                    command=lambda p=app_path: self.launch_app(p)
                )
                app_button.pack(anchor=tk.W, pady=3, ipady=2, fill=tk.X)

                # 画像がガベージコレクションで消えないように参照を保持
                if icon:
                    app_button.image = icon

    def launch_app(self, path: str):
        """
        アプリケーションを起動。
        指定されたパスが存在しない場合は警告を表示し、
        管理者権限が必要な場合は昇格を試みる。
        """
        executable = ""
        params = ""
        try:
            if not path or not path.strip():
                messagebox.showwarning("起動エラー", "アプリケーションのパスが設定されていません。", parent=self)
                return

            # shlex.splitでパスと引数を安全に分割する
            # 例: '"C:\\...\\Rgui.exe" --arg' -> ['C:\\...\\Rgui.exe', '--arg']
            args = shlex.split(path)
            if not args:
                raise FileNotFoundError(f"無効なパスです: {path}")
            executable = args[0]
            params = ' '.join(args[1:])

            # subprocess.Popenで非同期にプロセスを起動する
            # shell=Trueにすることで、Windowsのシェルがパスの解釈を行うため、
            # スペースを含むパスや引用符の有無などを柔軟に扱えるようになる。
            subprocess.Popen(path, shell=True)
        except FileNotFoundError:
            # executableが設定されていればそれを使う、なければ元のパスを使う
            exe_path_to_show = executable if executable else path
            messagebox.showwarning("起動エラー", f"指定されたパスが見つかりません:\n{exe_path_to_show}", parent=self)
        except OSError as e:
            # エラーコード 5 は「アクセスが拒否されました」
            # エラーコード 740 は「要求された操作には管理者特権が必要です」
            # これらは管理者権限が必要な場合に発生するため、昇格を試みる
            if hasattr(e, 'winerror') and e.winerror in (5, 740):
                if messagebox.askyesno(
                    "管理者権限の確認",
                    f"'{os.path.basename(executable)}' の起動には管理者権限が必要な可能性があります。\n\n管理者として実行しますか？", # executableはここで定義されているはず
                    parent=self
                ):
                    try:
                        shell.ShellExecuteEx(
                            lpVerb='runas',
                            lpFile=executable,
                            lpParameters=params,
                            nShow=win32con.SW_SHOWNORMAL
                        )
                    except Exception as shell_e:
                        # UACダイアログで「いいえ」を選択した場合(エラーコード1223)はユーザーによるキャンセルなので無視
                        if not (hasattr(shell_e, 'winerror') and shell_e.winerror == 1223):
                            messagebox.showerror(
                                "起動エラー (管理者)",
                                f"管理者権限での起動に失敗しました:\n{executable}\n\nエラー: {shell_e}",
                                parent=self
                            )
            else:
                # その他のOSError
                messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\n{path}\n\nエラー: {e}", parent=self)
        except Exception as e:
            messagebox.showerror("起動エラー", f"予期せぬエラーが発生しました:\n{path}\n\nエラー: {e}", parent=self)

    def open_settings_window(self):
        """
        設定編集ウィンドウを開く
        """
        # 既にウィンドウが開いている場合は、最前面に表示
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            self.settings_win.focus_force()
            return

        # 新しい設定ウィンドウを作成
        self.settings_win = SettingsWindow(self, self.config_path, self.reload_ui)

    def reload_ui(self):
        """
        UIを再読み込みして、設定の変更を反映
        """
        # すべてのウィジェットを破棄
        for widget in self.winfo_children():
            widget.destroy()

        # 設定を再読み込み
        self.config = self._load_config(self.config_path)
        if not self.config:
            self.destroy()
            return

        # ウィジェットを再作成
        self._create_widgets()

        # 最初のカテゴリを表示
        if self.config:
            first_category = next(iter(self.config))
            self.show_apps_for_category(first_category)

# --- 設定編集ウィンドウ ---
class SettingsWindow(tk.Toplevel):
    """
    設定ファイルを編集するためのGUIウィンドウ
    """

    def __init__(self, parent, config_path, reload_callback):
        super().__init__(parent)
        self.title("設定の編集")
        self.geometry("800x500")

        self.transient(parent)  # 親ウィンドウの上に表示
        self.grab_set()         # このウィンドウにフォーカスを固定

        self.config_path = config_path
        self.reload_callback = reload_callback
        # 元の設定を直接変更しないよう、ディープコピーを作成
        self.edited_config = copy.deepcopy(parent.config)

        self.app_drag_start_index = None
        self.category_drag_start_index = None

        self._create_widgets()
        self.populate_category_list()

    def _create_widgets(self):
        """
        設定ウィンドウのウィジェットを作成・配置
        """
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 左ペイン：カテゴリ ---
        category_pane = ttk.Frame(main_frame)
        category_pane.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        ttk.Label(category_pane, text="カテゴリ", font=("Yu Gothic UI", 10, "bold")).pack(anchor=tk.W)
        self.category_listbox = tk.Listbox(category_pane, exportselection=False)
        self.category_listbox.pack(fill=tk.BOTH, expand=True)
        self.category_listbox.bind("<<ListboxSelect>>", self.on_category_select)

        # カテゴリのドラッグ&ドロップ設定
        self.category_listbox.bind("<ButtonPress-1>", self.on_category_drag_start)
        self.category_listbox.bind("<B1-Motion>", self.on_category_drag)
        self.category_listbox.bind("<ButtonRelease-1>", self.on_category_drop)

        cat_btn_frame = ttk.Frame(category_pane)
        cat_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(cat_btn_frame, text="追加", command=self.add_category).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(cat_btn_frame, text="編集", command=self.edit_category).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(cat_btn_frame, text="削除", command=self.delete_category).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # --- 右ペイン：アプリケーション ---
        app_pane = ttk.Frame(main_frame)
        app_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(app_pane, text="アプリケーション", font=("Yu Gothic UI", 10, "bold")).pack(anchor=tk.W)
        self.app_listbox = tk.Listbox(app_pane)
        self.app_listbox.pack(fill=tk.BOTH, expand=True)

        # アプリケーションのドラッグ&ドロップ設定
        self.app_listbox.bind("<ButtonPress-1>", self.on_app_drag_start)
        self.app_listbox.bind("<B1-Motion>", self.on_app_drag)
        self.app_listbox.bind("<ButtonRelease-1>", self.on_app_drop)

        app_btn_frame = ttk.Frame(app_pane)
        app_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(app_btn_frame, text="追加", command=self.add_app).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(app_btn_frame, text="編集", command=self.edit_app).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(app_btn_frame, text="削除", command=self.delete_app).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # --- 下部ボタン ---
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        ttk.Button(bottom_frame, text="キャンセル", command=self.destroy).pack(side=tk.RIGHT, padx=(5,0))
        ttk.Button(bottom_frame, text="保存して閉じる", command=self.save_and_close).pack(side=tk.RIGHT)

    def on_category_select(self, event=None):
        """カテゴリが選択された際にアプリリストを更新する。"""
        self.update_app_list()

    # --- カテゴリのドラッグ＆ドロップ処理 ---

    def on_category_drag_start(self, event):
        """カテゴリのドラッグ開始位置を記録する。"""
        self.category_drag_start_index = self.category_listbox.nearest(event.y)

    def on_category_drag(self, event):
        """ドラッグ中の処理（現在は何もしない）。"""
        pass

    def on_category_drop(self, event):
        """カテゴリのドロップ時にリストの並べ替えを行う。"""
        drop_index = self.category_listbox.nearest(event.y)
        start_index = self.category_drag_start_index

        # 開始位置がない、または同じ場所へのドロップは無視
        if start_index is None or start_index == drop_index:
            self.category_drag_start_index = None
            return

        # config辞書のキーを並べ替える
        keys = list(self.edited_config.keys())
        moved_key = keys.pop(start_index)
        keys.insert(drop_index, moved_key)

        # 新しい順序で辞書を再構築
        self.edited_config = {key: self.edited_config[key] for key in keys}

        # UIを更新
        self.populate_category_list()
        # 移動後の項目を選択状態にする
        self.category_listbox.selection_clear(0, tk.END)
        self.category_listbox.selection_set(drop_index)
        self.category_listbox.activate(drop_index)
        self.on_category_select() # アプリリストも更新

        self.category_drag_start_index = None

    # --- アプリケーションのドラッグ＆ドロップ処理 ---

    def on_app_drag_start(self, event):
        """アプリケーションのドラッグ開始位置を記録する。"""
        self.app_drag_start_index = self.app_listbox.nearest(event.y)

    def on_app_drag(self, event):
        """ドラッグ中の処理（現在は何もしない）。"""
        pass

    def on_app_drop(self, event):
        """アプリケーションのドロップ時にリストの並べ替えを行う。"""
        drop_index = self.app_listbox.nearest(event.y)
        start_index = self.app_drag_start_index

        # 開始位置がない、または同じ場所へのドロップは無視
        if start_index is None or start_index == drop_index:
            self.app_drag_start_index = None
            return

        # 選択中のカテゴリを取得
        cat_indices = self.category_listbox.curselection()
        if not cat_indices:
            self.app_drag_start_index = None # カテゴリが選択されていなければ何もしない
            return

        category = self.category_listbox.get(cat_indices[0])

        # アプリケーションリストを更新
        app_list = self.edited_config[category]
        moved_app = app_list.pop(start_index)
        app_list.insert(drop_index, moved_app)

        # UIを更新
        self.update_app_list()
        # 移動後の項目を選択状態にする
        self.app_listbox.selection_clear(0, tk.END)
        self.app_listbox.selection_set(drop_index)
        self.app_listbox.activate(drop_index)

        self.app_drag_start_index = None

    def populate_category_list(self):
        """
        カテゴリリストを更新
        """
        self.category_listbox.delete(0, tk.END)
        for category in self.edited_config.keys():
            self.category_listbox.insert(tk.END, category)
        self.update_app_list()

    def update_app_list(self, event=None):
        """
        選択されたカテゴリに応じてアプリリストを更新
        """
        self.app_listbox.delete(0, tk.END)
        selected_indices = self.category_listbox.curselection()
        if not selected_indices:
            return
        
        category = self.category_listbox.get(selected_indices[0])
        for app in self.edited_config.get(category, []):
            self.app_listbox.insert(tk.END, app.get("name", "名称未設定"))

    def add_category(self):
        """
        新しいカテゴリを追加するダイアログを表示
        """
        name = simpledialog.askstring("カテゴリの追加", "新しいカテゴリ名を入力してください:", parent=self)
        if name and name not in self.edited_config:
            self.edited_config[name] = []
            self.populate_category_list()
            self.category_listbox.selection_set(tk.END)

    def edit_category(self):
        """ 
        編集するカテゴリを選択し、名前を変更するダイアログを表示
        """
        selected_indices = self.category_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("選択エラー", "編集するカテゴリを選択してください。", parent=self)
            return
        
        old_name = self.category_listbox.get(selected_indices[0])
        new_name = simpledialog.askstring("カテゴリの編集", "新しいカテゴリ名を入力してください:", initialvalue=old_name, parent=self)

        if new_name and new_name != old_name and new_name not in self.edited_config:
            # 辞書のキーを変更するために、新しいキーで項目を作成し、古いキーを削除
            self.edited_config[new_name] = self.edited_config.pop(old_name)
            self.populate_category_list()

    def delete_category(self):
        """
        選択されたカテゴリを削除する
        """
        selected_indices = self.category_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("選択エラー", "削除するカテゴリを選択してください。", parent=self)
            return

        category = self.category_listbox.get(selected_indices[0])
        if messagebox.askyesno("削除の確認", f"カテゴリ '{category}' を削除しますか？", parent=self):
            del self.edited_config[category]
            self.populate_category_list()

    def add_app(self):
        """
        選択されたカテゴリに新しいアプリケーションを追加するダイアログを表示
        """
        cat_indices = self.category_listbox.curselection()
        if not cat_indices:
            messagebox.showwarning("選択エラー", "アプリケーションを追加するカテゴリを選択してください。", parent=self)
            return
        
        category = self.category_listbox.get(cat_indices[0])
        dialog = AppDetailDialog(self, title="アプリケーションの追加")
        if dialog.result:
            self.edited_config[category].append(dialog.result)
            self.update_app_list()

    def edit_app(self):
        """
        選択されたアプリケーションを編集するダイアログを表示
        """
        cat_indices = self.category_listbox.curselection()
        app_indices = self.app_listbox.curselection()
        if not cat_indices or not app_indices:
            messagebox.showwarning("選択エラー", "編集するアプリケーションを選択してください。", parent=self)
            return

        category = self.category_listbox.get(cat_indices[0])
        app_index = app_indices[0]
        app_data = self.edited_config[category][app_index]

        dialog = AppDetailDialog(self, title="アプリケーションの編集", initial_data=app_data)
        if dialog.result:
            self.edited_config[category][app_index] = dialog.result
            self.update_app_list()

    def delete_app(self):
        """
        選択されたアプリケーションを削除する
        """
        cat_indices = self.category_listbox.curselection()
        app_indices = self.app_listbox.curselection()
        if not cat_indices or not app_indices:
            messagebox.showwarning("選択エラー", "削除するアプリケーションを選択してください。", parent=self)
            return

        category = self.category_listbox.get(cat_indices[0])
        app_index = app_indices[0]
        app_name = self.app_listbox.get(app_index)

        if messagebox.askyesno("削除の確認", f"アプリケーション '{app_name}' を削除しますか？", parent=self):
            del self.edited_config[category][app_index]
            self.update_app_list()

    def save_and_close(self):
        """
        変更をJSONファイルに保存し、ウィンドウを閉じる
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.edited_config, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("保存完了", "設定を保存しました。", parent=self)
            self.reload_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("保存エラー", f"設定の保存に失敗しました:\n{e}", parent=self)

# --- アプリ情報入力ダイアログ ---
class AppDetailDialog(simpledialog.Dialog):
    """
    アプリケーションの名前とパスを入力するためのダイアログ
    """

    def __init__(self, parent, title=None, initial_data=None):
        self.initial_data = initial_data if initial_data else {}
        super().__init__(parent, title)

    def body(self, master):
        """
        ダイアログの本体を作成
        """
        ttk.Label(master, text="名前:").grid(row=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(master, text="パス:").grid(row=1, sticky=tk.W, padx=5, pady=2)

        self.name_entry = ttk.Entry(master, width=50)
        self.path_entry = ttk.Entry(master, width=50)

        self.name_entry.grid(row=0, column=1, padx=5, pady=2)
        self.path_entry.grid(row=1, column=1, padx=5, pady=2)

        # 編集モードの場合、初期値を設定
        self.name_entry.insert(0, self.initial_data.get("name", ""))
        self.path_entry.insert(0, self.initial_data.get("path", ""))

        # ファイル選択ボタンを追加
        browse_button = ttk.Button(master, text="参照...", command=self.browse_file)
        browse_button.grid(row=1, column=2, padx=5)

        return self.name_entry # 初期フォーカス

    def browse_file(self):
        """
        ファイル選択ダイアログを開き、パスをEntryに設定
        """
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            parent=self,
            title="実行ファイルを選択",
            filetypes=[("実行ファイル", "*.exe"), ("ショートカット", "*.lnk"), ("すべてのファイル", "*.*")]
        )
        if filepath:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, filepath)

    def validate(self):
        """
        入力値のバリデーション
        """
        name = self.name_entry.get().strip()
        path = self.path_entry.get().strip()
        if not name:
            messagebox.showwarning("入力エラー", "名前を入力してください。", parent=self)
            return 0
        if not path:
            messagebox.showwarning("入力エラー", "パスを入力してください。", parent=self)
            return 0
        return 1

    def apply(self):
        """
        OKボタンが押されたときに呼ばれる
        """
        self.result = {
            "name": self.name_entry.get().strip(),
            "path": self.path_entry.get().strip()
        }

def resource_path(relative_path: str) -> str:
    """
    実行ファイル(.exe)と開発環境の両方でリソースへのパスを解決する
    """
    try:
        # PyInstallerが作成する一時フォルダのパスを取得
        base_path = sys._MEIPASS
    except Exception:
        # 開発環境ではスクリプトのディレクトリを基準にする
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = AppLauncher()
    app.mainloop()
