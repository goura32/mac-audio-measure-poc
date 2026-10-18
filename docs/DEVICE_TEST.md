# 実機検証記録

実施日: 2026-10-18
対象: 2021年14インチ MacBook Pro (MacBookPro18,3 / Apple M1 Pro / arm64)
OS: macOS 26.6.2

## 結果一覧

| 項目 | 判定 | 結果 |
|---|---|---|
| 実機識別 | 合格 | M1 ProのMacBook Proを確認。シリアル番号等は記録しない。 |
| Python環境 | 合格 | Python 3.11.15の仮想環境で依存ライブラリを読み込み。 |
| 自動テスト | 合格 | `python -m pytest -q`: 4 passed。合成信号によるテストであり、実機音響測定ではない。 |
| GUI起動 | 合格 | Tk GUIが起動し、操作画面とグラフ領域を表示。 |
| 内蔵デバイス表示 | 合格 | PortAudio一覧とGUIに「MacBook Proのスピーカー」「MacBook Proのマイク」が表示され、デフォルト選択を確認。デバイスを手動で切り替える操作は未確認。 |
| デジタル振幅スライダー | 一部確認 | GUI上の表示と初期値0.08を確認。レベルを下げるGUI操作の承認がタイムアウトしたため、変更操作は行っていない。 |
| 48kHz対応 | 一部確認 | macOSのデバイス情報とPortAudio一覧でデフォルトサンプルレート48kHzを確認。実ストリームの開始は未確認。 |
| グラフ表示 | 一部確認 | 空のグラフ領域と日本語軸ラベルを表示。実測データを使った曲線は未確認。初回起動時に日本語グリフが欠落したため、macOSのHiragino SansをMatplotlibに指定して修正し、再起動後に表示を確認。 |
| 周波数特性計算・1kHz正規化 | 合成信号で確認 | 自動テストのフラットなループバックと振幅スケーリングのテストは合格。実機録音に対する計算は未確認。 |
| 基準との差分 | 未検証 | 実機の2測定を用いた表示は未確認。 |
| JSON保存 | 未検証 | GUIからの実測結果保存は未確認。測定データは作成・保存していない。 |
| 自動音量探索 | 未検証 | 実機で段階測定を実施していない。録音ピーク/RMS、実録音クリップ検出、推奨値の妥当性も未確認。 |
| macOS音量・入力設定の保全 | 合格 | Core Audio調査では読み取りだけを実施。システム音量、マイク入力設定を変更していない。 |

## 実音響測定を完了できなかった理由

測定レベルを低く設定するGUI操作の承認が得られず、測定開始操作を実行しなかった。このため、内蔵スピーカーからのスイープ再生、内蔵マイク録音、録音ピーク/RMS取得、周波数特性の表示・差分・JSON保存は未実施。マイク権限ダイアログも発生していない。

別途、`sounddevice.check_input_settings(device=1, samplerate=48000, channels=1)` は240秒以内に応答しなかった。一方、`sounddevice.query_devices()` は内蔵デバイスを列挙した。入力形式確認が停止した原因は特定できておらず、録音ストリームが動作するとは判断できない。実機測定を再開する前に、マイク権限とPortAudio入力ストリームを確認する必要がある。

## Core Audio調査

Core Audioのデフォルト出力デバイス（内蔵スピーカー）とデフォルト入力デバイス（内蔵マイク）に対して、`AudioObjectHasProperty`、`AudioObjectIsPropertySettable`、`AudioObjectGetPropertyData` を読み取り専用で実行した。

| 対象 | スコープ | プロパティ | 存在 | 現在値の取得 | settable |
|---|---|---|---|---|---|
| 内蔵スピーカー | 出力 | `kAudioDevicePropertyVolumeScalar` / `kAudioDevicePropertyVolumeDecibels` | はい | 成功 | true |
| 内蔵マイク | 入力 | `kAudioDevicePropertyVolumeScalar` / `kAudioDevicePropertyVolumeDecibels` | はい | 成功 | true |

このMacの現在のデバイスはCore Audio上で該当値を読み取り可能で、書き込み可能として公開されている。ただし、既存設定を変更しないため書き込みAPIは実行しておらず、設定変更後の実効音量・実効入力ゲインも検証していない。プロパティの有無と意味は機器・ドライバに依存する。アプリ自体はこの制御APIを使用せず、波形のデジタル振幅だけを調整する。

参照: [Apple Core Audio Functions](https://developer.apple.com/documentation/coreaudio/core-audio-functions)、[AudioObjectIsPropertySettable](https://developer.apple.com/documentation/coreaudio/audioobjectispropertysettable%28_%3A_%3A_%3A%29?language=_9)、[kAudioDevicePropertyVolumeScalar](https://developer.apple.com/documentation/coreaudio/kaudiodevicepropertyvolumescalar)

## 安全・データ

- 測定音を再生していないため、音量を上げる操作や急な音量変化は発生していない。
- macOSのシステム音量・マイク入力設定は変更していない。
- 実測データや認証情報は作成・保存・コミットしていない。
- この検証はPOCの実機測定成功を示さない。校正のない結果を絶対周波数特性やdB SPLとして扱わないこと。
