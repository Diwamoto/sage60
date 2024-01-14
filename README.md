# Sage60

東プレスイッチを使った60%分割キーボードです。
nrf52840を使って無線接続で左右間接続、PCとの接続を行います。

# ファームウェア

zmkを使用しています。
nrf52840にzmkを焼いて、adcを用いることで静電容量を読み取りキー入力を判定しています。
詳細な判定方法は[こちら](https://nogikes.booth.pm/items/2373281)や[こちら](https://booth.pm/ja/items/2232932)を参考にしてください。

# プロジェクトロードマップ

* 👍 左右間の無線通信
* 👍 PCとのBLE接続
* 👍 キーマップ変更
* 👍 Lipoバッテリーの充電
* ❌ BOMファイル等の準備によるPCBAまでサポート
* ❌ ラピッドトリガー機能
* ❌ Remap等のダイナミックキーマップ変更
* ❌ アルミケース
* ❌ ガスケットマウント

# 参考
* zmkの設定: [tako-config](https://github.com/ssbb/tako-config)
* 基板: [tako](https://github.com/ssbb/tako)
