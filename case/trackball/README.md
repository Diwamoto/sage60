# トラックボールケース

ケース本体は GPL-3.0 なのでこのリポジトリには置かず、[Diwamoto/roBa の `sage60` ブランチ](https://github.com/Diwamoto/roBa/tree/sage60/sage60)に分けている（変更点とライセンスもそちら）。`.gitignore` 済みのファイルとして手元に取得して使う。`tb.py` / `make_right.py` は `trackballcase_low.stl` がないと動かない。

```sh
R=https://raw.githubusercontent.com/Diwamoto/roBa/8c4270c27fa89b2665fa79c7284dcb1bcf0a1e8f/sage60
curl -fsSL $R/trackballcase_low.stl -o case/trackball/trackballcase_low.stl
curl -fsSL $R/trackballcase_low.3mf -o production/case_print/trackballcase_low.3mf
```

| ファイル | 中身 |
| --- | --- |
| `trackballcase_low.stl`（取得） | `trackballcase_low.3mf` を z+2 して STL にしたもの。`tb.py` / `make_right.py` が読む |
| `production/case_print/trackballcase_low.3mf`（取得） | プリント用 |
| `tb_socket_cut.py` | `production/case_print/trackballcase_low.3mf` を加工する：J1 ソケット用の切り欠き（2026-10-28）、ネジの耳を磁石 φ6×3 の保持部にする（2026-10-29）。`trackballcase_low.stl` も書き直す。結果を変えたら fork にも入れて、上の URL のコミットを更新し、`site/build_models.py` を流し直す（サイトはこの URL から読む） |
