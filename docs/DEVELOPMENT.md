# 開発・実機検証

## 方針

ChatGPT側でソース・GUI・設計資料・信号処理テストを用意。Hermes AgentはmacOS実機に依存する検証・最小修正・commit/pushを担当。GitHub Actions不使用。公開リポジトリは https://github.com/goura32/mac-audio-measure-poc 。

## Hermes Agent用指示（Macで実行する人に渡す）

以下を実施してください。対象は2021年14インチMacBook Pro（M1 Pro）。

1. リポジトリをcloneし、`python3 --version` と `which python3` を確認。GitHub Actionsは作成・実行しない。
2. Python環境を準備し `python -m pip install -r requirements.txt pytest`、`python -m pytest -q` を実行。
3. `python app.py` でGUI起動、内部スピーカーと内部マイクが選択できるか確認。初回はシステム出力音量を低くし、macOSのマイクアクセスを許可。GUIから短い測定が完了するか確認。
4. 安全な音量探索、1kHz正規化グラフ、基準登録、差分表示、JSON保存を一通り検証。必要なら診断情報を保存。Mac上のシステム音量・マイク入力音量は**意図せず変更しない**。
5. Core Audioで内蔵マイクの入力ゲイン制御可否および値の取得を検査する。変更が必要なら変更前の値を記録し、変更後の復元を保証。未対応の場合はUIに「非対応」と表示する方針を提案する。
6. PortAudioによる入出力の48kHz動作、デバイス切替、クリップ検出の正常性を報告。致命的な問題のみ最小修正してテスト追加。結果を `docs/DEVICE_TEST.md` に記録。
7. 実機確認で修正が必要になった場合だけ差分をcommit/pushする。READMEと検証記録に未検証事項を明記し、リポジトリURLと検証結果を報告する。

## POC完了基準

- GUIで内蔵スピーカー→内蔵マイクの測定が1回成功
- 自動振幅探索後に再測定できる
- 周波数特性の凸凹、相対0dB線、基準差分が表示できる
- JSON保存とユニットテストが成功
- 録音のクリップ時に警告またはエラーが出る
- 内蔵機器の相対測定と絶対校正との違いが明記されている
