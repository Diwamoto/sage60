# トラックボールケース

| ファイル | 中身 |
| --- | --- |
| `trackballcase.stl` | 元データ。roBa（[kumamuk-git/roBa](https://github.com/kumamuk-git/roBa)）の `trackballcase.stl`（git LFS、oid cdaa94d5…）。roBa が Keyball Trackball Case（kepeo）を改変したもの |
| `trackballcase_low.stl` | 2026-10-20 から使っている版（`production/case_print/trackballcase_low.3mf` を z+2 して STL にしたもの。+x 側が 2.7mm 短い）。`tb.py` / `make_right.py` が読む |
| `tb_socket_cut.py` | `production/case_print/trackballcase_low.3mf`（プリント用）を加工する：J1 ソケット用の切り欠き（2026-10-28）、ネジの耳を磁石 φ6×3 の保持部にする（2026-10-29）。`trackballcase_low.stl` も書き直す |

ライセンス: Keyball Trackball Case by kepeo, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)（roBa が改変、それをさらに sage60 用に改変）。

元データを取り直すとき（git LFS）:
```sh
href=$(curl -s -X POST -H 'Accept: application/vnd.git-lfs+json' -H 'Content-Type: application/vnd.git-lfs+json' \
  https://github.com/kumamuk-git/roBa.git/info/lfs/objects/batch \
  -d '{"operation":"download","transfers":["basic"],"objects":[{"oid":"cdaa94d5c244317f9dec7bfc47de96845a091c61c89673050497cd625df796c9","size":1226884}]}' \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["objects"][0]["actions"]["download"]["href"])')
curl -sL "$href" -o trackballcase.stl
```
