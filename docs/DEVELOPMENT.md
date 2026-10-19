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

## GUIのComputer Use承認が止まる場合の次回検証

`measure_once.py` を使用する。これはGUI操作の承認を回避するための**代替測定経路**であり、承認や安全確認を無視するものではない。

1. 人に確認してmacOSシステム出力音量を小さくしてもらい、可聴スイープ再生の許可を確認する。マイク権限が必要なら操作を依頼する。
2. 既存のPython仮想環境で `python -m pytest -q` を実行する。
3. 最初は `python measure_once.py` を実行し、明示フラグがないと音を鳴らさず失敗することを確認する。
4. その後、明示的な確認に基づき `python measure_once.py --confirm-low-volume` を**1回だけ**実行する（独立子プロセス、15秒程度の上限）。自動で再試行しない。
5. `MEASUREMENT_COMPLETE` の表示、音量・録音品質の統計、`measurements/first-sweep.json` の240点、1kHz近傍の0dB正規化を確認する。ファイルはGitへ追加しない。
6. 失敗時はエラーをそのまま記録し、原因を切り分ける。信号不足時に自動的に音量を上げない。
7. 実測が成功したら、**GUIからの測定・表示・差分・JSON保存は別途未検証**であることを維持し、残るGUI検証と安全な振幅探索の対応を検討する。
8. `docs/DEVICE_TEST.md` に事実だけ追記し、必要な最小差分をcommit/push。GitHub Actions不要。
