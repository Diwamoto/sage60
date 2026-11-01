# pcb

KiCad の元データ（`.kicad_pro` / `.kicad_pcb` / `.kicad_sch`）だけをコミットする。バックアップ・`.kicad_prl`・プラグイン設定・ガーバーなどの出力はローカルのみ（`.gitignore`）。発注に使うファイルは `production/`。JLCPCB 用ガーバーは `.kicad_pcb` を push すると Actions（`.github/workflows/gerber.yml`）が基板ごとの artifact `gerber-*` に出す。ダウンロードした zip をそのまま JLCPCB に上げられる。

| フォルダ | 中身 |
| --- | --- |
| `mx/left/` | MX 左のメイン基板（`mx.kicad_*`、XIAO nRF52840） |
| `mx/right/` | MX 右（トラックボール、PMW3610 センサー基板へ J1） |
| `ec/main/` | 東プレ（静電容量）左メイン |
| `ec/scan_module/` | 静電容量の読み取りモジュール |
| `modules/footprint/sage60.pretty/`、`modules/symbol/sage60.kicad_sym` | 自作部品（XIAO nRF52840 Plus）。`mx/right` と `ec/main` の `fp-lib-table` / `sym-lib-table` が読む |

PMW3610 センサー基板は GPL-3.0 なのでここには置かない。元データは [Diwamoto/roBa](https://github.com/Diwamoto/roBa/tree/sage60/pcb/pmw3610_breakout_for_roBa)（roBa のまま無改変）で、ガーバーは同じ Actions の `gerber-pmw3610_breakout` に出る。
