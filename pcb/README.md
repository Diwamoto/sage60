# pcb

KiCad の元データ（`.kicad_pro` / `.kicad_pcb` / `.kicad_sch`）だけをコミットする。バックアップ・`.kicad_prl`・プラグイン設定・ガーバーなどの出力はローカルのみ（`.gitignore`）。発注に使うファイルは `production/`。

| フォルダ | 中身 |
| --- | --- |
| `mx/left/` | MX 左のメイン基板（`mx.kicad_*`、XIAO nRF52840） |
| `mx/right_tb/` | MX 右（トラックボール、PMW3610 センサー基板へ J1） |
| `mx/left_plate/` | 左プレート（MX / Choc v2 共通、1.2mm） |
| `mx/right_tb_plate/` | 右プレート（トラックボールまわりの親指キー2つと手前のタブが無い形） |
| `ec/main/` | 東プレ（静電容量）左メイン |
| `ec/right/` | 東プレ右（`ec/main` の左右ミラー） |
| `ec/plate/` | 東プレ用プレート |
| `ec/scan_module/` | 静電容量の読み取りモジュール |
