=====

### シンプルに作ったつもりのデスクトップランチャー  

[ .exe化 ]  
pip install pyinstaller (pip listでインストールが確認できない場合にインストール)  

1. desktop_launcher.py と config.json が保存されているフォルダに移動  
    (config.jsonがなくても .exeの初回起動で自動で作成される)  
2. PyInstallerを実行して .exe ファイルをビルド  
3. アプリケーションにはいくつか考慮すべき点があるため  
    オプションを指定して実行するのがおすすめ  

1. GUIアプリであること: 実行時に黒いコンソール画面が表示されないように   
    --windowed (または -w) オプションを追加  
2. 設定ファイル (config.json) が必要: .exe ファイルに   
    config.json を含める必要があり --add-data オプションで指定  
3. 配布のしやすさ: 関連ファイルをすべて1つの .exe ファイルにまとめる   
    --onefile オプションを使うと便利  

[ .exe化コマンド (例)]
pyinstaller --onefile --windowed --add-data "config.json;." --icon="app.ico" --name "AppLauncher" --hidden-import="win32timezone" desktop_launcher.py  

※ --icon="app.ico"は iconのファイル名を記入するように…  

[ コマンドオプション ]  
--onefile: すべての依存ライブラリやファイルを1つの .exe ファイルにまとめる  
--windowed: GUIアプリケーションであることを示し、実行時にコンソールウィンドウを表示させない  
--add-data "config.json;.": config.json ファイルを、ビルド成果物（.exe）と  
    同じディレクトリ（.）に含めます。Windowsでは区切り文字に ; を使用  
--icon="app.ico": アプリケーションのアイコンファイルを指定  
    ".ico"形式のファイルを事前に用意  

    **補足: Windows標準のアイコンを使いたい場合**  
    ・Windowsに内蔵されているアイコン
    （例：フォルダや設定のアイコン）を使いたい場合、それらはDLLファイル内に格納されている  
    ・PyInstallerでこれらを利用するには、一度 `.ico` ファイルとして抽出する必要がある  
    1. アイコン抽出ツール（例: Resource Hacker）を使って、  
        "C:\Windows\System32\shell32.dll" や "C:\Windows\System32\imageres.dll" を開く  
        (C:\Windows\SystemResourcesに格納されていることも…)  
        詳細はWebで検索  

    2. 好みのアイコンを探し、".ico" ファイルとしてプロジェクトフォルダに保存  

    3. 保存した ".ico" ファイルをこのオプションで指定  
--name "AppLauncher": 生成される .exe ファイルの名前を AppLauncher.exe に指定  
    desktop_launcher.py: 変換対象のPythonスクリプト  

[ 生成されたファイル確認 ]  
コマンドが正常に完了すると、  
プロジェクトフォルダ内にいくつかの新しいフォルダとファイルが作成される  

dist フォルダ: この中に完成した AppLauncher.exe が格納  
    この .exe ファイルをダブルクリックすれば、アプリケーションが起動  
build フォルダ: ビルドプロセス中に使用された一時ファイルが格納  
    不要であれば削除しても問題ない  
AppLauncher.spec: ビルド設定が記述されたファイル  
    より高度なカスタマイズを行う際に編集できる  
これで、dist フォルダにある AppLauncher.exe を他のPCにコピーするだけで、  
    アプリケーションを実行できるように…  

##### [ 用語・説明 ]  
バリデーションとは？  
一言で言うと、**「入力されたデータが正しいかどうかを検証する処理」**  

プログラムがユーザーからの入力を受け取ったり、  
データを保存したりする際に、そのデータが意図した形式やルールに従っているかを確認する  
もしルールに反するデータがあれば、エラーメッセージを表示して入力を促したり、処理を中断したりする  

###### [ バリデーションのメリット ]  
1. 不正確なデータを防ぐ: アプリケーションが予期せぬデータによって誤作動したり、  
    停止したりするのを防ぐ  
2. ユーザー体験の向上: ユーザーが間違った情報を入力した際に、  
    その場で何が問題なのかを伝えることで、スムーズな操作を助ける  
3. セキュリティの強化: 不正な形式のデータ（悪意のあるコードなど）が  
    システムに送り込まれるのを防ぐ  

##### [ AppLauncher.spec の役割と内容]  
このファイルはPythonスクリプト形式で書かれており、  
主に2つの重要なセクションから構成されている  

[ Analysisセクション ]  
1. どのPythonスクリプトをビルドの中心にするか (['desktop_launcher.py'])  
2. どのデータファイル（例: config.json、画像ファイル）を.exeに含めるか (datas=)  
3. どのライブラリをバンドルに含めるか、または除外するか  
4. PyInstallerが自動で見つけられない「隠れた」インポートモジュールは何か (hiddenimports=) などを定義  

[ EXEセクション ]  
1. 生成される.exeファイルの名前 (name=)  
2. コンソールウィンドウを表示しないようにするか（GUIアプリの場合） (console=False)  
3. アプリケーションのアイコン (icon=) などを定義  

[ readme.mdのコマンドとの対応 ]  
readme.mdに記載されているpyinstallerコマンドのオプションは、  
AppLauncher.specファイル内の設定に直接対応  

readme.mdのコマンドオプション	    AppLauncher.spec内の設定	                  説明  
-----------------------------------------------------------------------------------------------------  
・desktop_launcher.py	          a = Analysis(['desktop_launcher.py'], ...)	ビルド対象のスクリプト  
・--name "AppLauncher"	          name='AppLauncher'	                        生成される.exeファイル名  
・--windowed	                  console=False	                                コンソールウィンドウを非表示  
・--add-data "config.json;."	  datas=[('config.json', '.')]	                config.jsonを.exeと同じ階層に含める  
・--icon="app.ico"	              icon=['app.ico']	                            アプリケーションのアイコンを指定  

[ etc. ]  
2025.08.20  
1. 一部のアプリを起動させると  
    「要求された動作には管理者権限が必要です」(エラーコード: 740) が表示される現象を解消  
2. "config.json"に登録されたアプリのパスにスペースが含まれる場合  
    パスがスペースで分割・認識するために発生する"c:/programが見つかりません…"というエラーを解消  
3. 設定の編集画面にて  
    カテゴリとアプリケーションの順番をドラッグ＆ドロップで操作可能  


思い出したら追記予定😅  

=====