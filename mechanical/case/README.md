# sage60 ケース生成スクリプト（左右）

Fusion の `sage60_left_bottom` / `sage60_right_bottom`（下ケース＋上ケース MOCK_A。A案で確定）をKiCadから作り直す。
設計の前提とルールは `.claude/skills/sage60-case/SKILL.md`。

## 手順
```sh
python3 -m venv venv && ./venv/bin/pip install shapely numpy matplotlib   # 初回のみ
# trackballcase.stl を取得（初回のみ。下記）
./venv/bin/python make_left.py      # left_spec.json  (+ left_geo.png で確認)
./venv/bin/python make_right.py     # right_spec.json, tb_placed.stl (+ right_geo.png)
./venv/bin/python make_checkpts.py  # 干渉チェック用の点
./venv/bin/python pcb_step.py       # models/{left,right}{,_lp}_pcb.step（PCB＋部品＋スイッチ＋キーキャップ。KiCadが変わったら）
```
Fusion（fusion-mcp の script 実行）で、左右それぞれ順に:
```python
def run(c):
    for st in ['stage0', 'stage1', 'stage2', 'stage3', 'stage5']:   # 右は 'stage4' も（stage5 の前）
        g = {'SIDE': 'left'}                                        # 'right'
        exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/%s.py' % st).read(), g)
        g['run'](c)
```
- stage0: ドキュメントのタイムラインとユーザーパラメータを全部消して作り直す（保存済みの版は履歴に残る）
- stage1: 平面とスケッチ / stage2: 下ケース（右はトラックボールのポケット・ネジ・参照メッシュも）/ stage3: 上ケース MOCK_A（A案） / stage4: 右だけ、トラックボール手前の床と上ケースの切り欠き / stage5: PCB_REF（PCB＋部品のSTEP。PCB上面を −(plate_t+pcb_gap) に置く。モックの画像は必ずこれを入れて撮る）
- 最後に `fusion/check.py` で干渉チェック（PCB・プレート・トラックボールケース・USBプラグの通り道・上下の重なり。全部0になること）

## ロープロファイル版（Choc、2026-10-03〜）
同じPCB（フットプリントが MX/Choc 両対応）に Choc を載せる薄型ケース。Fusion のドキュメントは `sage60_lp_left` / `sage60_lp_right`（stage0 が無ければ Admin Project に作る）。
```sh
SAGE60_LP=1 ./venv/bin/python make_left.py    # left_lp_spec.json, left_lp_geo.png
SAGE60_LP=1 ./venv/bin/python make_right.py   # right_lp_spec.json, tb_placed_lp.stl
```
Fusion では exec の globals に `'LP': True` を足す（`{'SIDE': 'left', 'LP': True}`）。check.py も `{'LP': True}`（片側だけなら `'SIDES': ('left',)`）。
ギャラリー用の画像は `fusion/shots.py`（globals に `SIDE` / `LP` / `OUT`、1ドキュメントずつ実行）。
平面の差分は `casegeo.py` の `LP` 分岐（CASE_OFF 3.5 / clr 0.2 / wall 1.5 / open_clr 0.5 / Zスタック）、高さ方向は `fusion/stage0.py` の `LP_PARAMS`。

## プレートの3MF（試作プリント用）
```sh
./venv/bin/python plate_3mf.py      # case/sage60_shared{,_lp}_plate.3mf（左右共通プレート。MX 1.5mm / Choc v2 1.2mm、kicad-cli で Edge.Cuts を1.5mm厚に）
```

## 形を決めている数値
`casegeo.py` の先頭（外形オフセット、角R、壁、磁石、ゴム足、USB、スライドスイッチ）と `make_right.py` の先頭（トラックボール）。
Fusion のユーザーパラメータで動くのは高さ方向と穴径など。平面形状はPythonで計算してスケッチに焼き込むので、外形を変えたらスクリプトから作り直す。

## trackballcase.stl
roBa のトラックボールケース（Keyball Trackball Case by kepeo, CC BY 4.0 を roBa が改変）。git LFS なので取ってくる:
```sh
href=$(curl -s -X POST -H 'Accept: application/vnd.git-lfs+json' -H 'Content-Type: application/vnd.git-lfs+json' \
  https://github.com/kumamuk-git/roBa.git/info/lfs/objects/batch \
  -d '{"operation":"download","transfers":["basic"],"objects":[{"oid":"cdaa94d5c244317f9dec7bfc47de96845a091c61c89673050497cd625df796c9","size":1226884}]}' \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["objects"][0]["actions"]["download"]["href"])')
curl -sL "$href" -o trackballcase.stl
```

## pcb_step.py
KiCad のフットプリントは他人の環境のモデルパス（`D:/…`、`/Users/foostan/…`、`${AMZPATH}`）を指しているので、一時コピーでパスを `models/` と KiCad 標準ライブラリに書き換えて `kicad-cli pcb export step` する。KiCad のファイルは変えない。
- `models/XIAO-nRF52840 v15.step`（Seeed 公式）と `models/Kailh-CherryMX-Socket.step`（foostan/kbd）はコピーして置いてある。
- 左の XIAO はフットプリントの offset z が 6 で5.6mm 浮くので 0.381（右と同じ）にする。右は XIAO 5種のモデルが重なっていて nRF52840 が非表示なので、それだけ表示する。
- 実物の XIAO は基板1.2mm＋はんだで0.17mm 浮くので `xiao_t` は 1.4（1.0 だと MX でレセプタクルが穴の上端に0.05mm 当たっていた。2026-10-03）。
- スイッチ（`models/cherry_mx.step`、`models/kailh_choc.step`。どちらも foostan/kbd、原点はPCB上面）とキーキャップ（`models/keycap_{mx,lp}.step`、`fusion/keycap.py` で作る簡易形状）を各スイッチのフットプリントに足す。キーキャップの下端はプレート上面＋6.0（MX）／＋3.3（ロープロ）。
- 干渉チェックは `fusion/check_parts.py`（globals に `SIDE` / `LP`。キーキャップは押し込んだ状態も見る）。

## mag_notch.py / breakaway.py / tongue_edge.py
一回限りのスクリプト（2026-10-03〜04 に適用済み。再実行すると二重に入る／tongue_edge は assert で止まる）。
- `mag_notch.py`：左 PCB・左プレート・右プレート（鏡像）の右下の縁に、φ6 磁石の柱用の半円の切り欠きを入れる（中心は `casegeo.MAG_NOTCH`）。左 PCB の ROW4 は先に手で引き直してある。
- `breakaway.py`：左プレートを左右共通にするため、右で使わない部分（トラックボールまわり・手前のタブ）にスロット＋ブリッジ／ミシン目を入れる。発注するプレートは `mx_plate` だけ。
- `tongue_edge.py`：右 PCB の J1 の舌の左の辺を x 158.0→158.9 にして、トラックボールケースの脚の腕を避ける（0.49mm 重なり→0.36mm の隙間）。舌に沿う SDIO / MOTION の配線も0.32右へ。

## shorten_tabs.py
プレートのタブを5→2.5mmにした一回限りのスクリプト（2026-10-02に適用済み。再実行するとさらに短くなる）。
