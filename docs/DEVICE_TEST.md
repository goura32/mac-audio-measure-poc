# 実機検証記録

実施日: 2026-10-18（GUI・基本確認）
追記日: 2026-10-19（PortAudio短時間I/O切り分け）
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
| デジタル振幅スライダー | 未完了 | GUI上の表示と初期値0.08は前回確認済み。0.02へ変更するクリック後も表示は0.08のまま。続けて行うドラッグ操作はComputer Useの承認タイムアウトとなり、再試行していない。 |
| 48kHz対応 | 合格 | PortAudio一覧の既定レートが48kHzで、48kHz/モノラルの入力ストリームも開けた。 |
| 0.2秒入力ストリーム | 合格 | 独立子プロセスで9600フレームを録音し、15秒以内に正常終了。overflowなし。サンプルはメモリ内でピーク/RMSを計算後に破棄し、音声ファイルは作成していない。 |
| 0.2秒無音出力 | 合格 | 9600フレームのゼロ波形を出力ストリームに書き込み、underflowなし。音量設定は変更していない。 |
| 0.2秒全二重（callback） | 合格 | callbackで入力を取り込みつつ出力をゼロに保ち、9600フレームを15秒以内に取得。callback statusなし。 |
| `sounddevice.playrec()` 無音経路 | 合格 | アプリと同じAPIにゼロ波形を渡し、入力9600フレームを15秒以内に取得。録音データはメモリ内で破棄。 |
| ブロッキング全二重の逐次read/write | プローブ方式に注意 | 出力を書いた後に入力を読む試験ではinput overflowが立った。callback同時処理およびアプリと同じ`playrec()`では再現せず、逐次read/writeによる試験手順の影響と判断。 |
| グラフ表示 | 一部確認 | 空のグラフ領域と日本語軸ラベルを表示。実測データを使った曲線は未確認。初回起動時に日本語グリフが欠落したため、macOSのHiragino SansをMatplotlibに指定して修正し、再起動後に表示を確認。 |
| 周波数特性計算・1kHz正規化 | 合成信号で確認 | 自動テストのフラットなループバックと振幅スケーリングのテストは合格。実機録音に対する計算は未確認。 |
| 基準との差分 | 未検証 | 実機の2測定を用いた表示は未確認。 |
| JSON保存 | 未検証 | GUIからの実測結果保存は未確認。測定データは作成・保存していない。 |
| 自動音量探索 | 未検証 | 実機で段階測定を実施していない。録音ピーク/RMS、実録音クリップ検出、推奨値の妥当性も未確認。 |
| macOS音量・入力設定の保全 | 合格 | Core Audio調査では読み取りだけを実施。システム音量、マイク入力設定を変更していない。 |

## PortAudio切り分けと実音響測定の残り

デバイス情報取得、入力、無音出力、全二重、`playrec()` の各確認は別々の子プロセスで実行し、各15秒で打ち切る制限を付けた。マイク入力・`playrec()` が成功し、権限ダイアログも出なかったため、少なくとも今回のプロセスではマイク権限や実ストリームの開始が停止原因ではない。

前回240秒で停止した `sounddevice.check_input_settings(device=1, samplerate=48000, channels=1)` は再実行していない。インストール済みsounddevice 0.5.6のソース確認では、この関数はストリームパラメーターを作った後にPortAudioの `Pa_IsFormatSupported()` を呼ぶ。今回同じ48kHz入力パラメーターの実ストリーム開始・録音は成功したため、停止箇所は実際の入力I/Oではなく形式検査APIの経路に絞られる。ただし240秒停止時のネイティブスタックは採取しておらず、Core Audio内部のどの呼び出しで止まったかは未確定。PortAudioの公開API上、`Pa_IsFormatSupported()` は指定したデバイス・形式・レートでストリームを開けるかを検査する関数である。

実スイープはまだ実施していない。macOSシステム出力音量を人が低く設定したことは確認済みだが、GUIのデジタル振幅を0.02へ設定する操作が完了しなかった。クリック後の画面でも値は初期値0.08のままで、続けて要求したドラッグは承認タイムアウトとなったため、それ以上のGUI操作は行わず停止した。測定ボタンは押しておらず、可聴スイープや測定データの保存は行っていない。

参照: [python-sounddevice 0.5.6 source](https://github.com/spatialaudio/python-sounddevice/blob/0.5.6/src/sounddevice.py)、[PortAudio API Overview](https://portaudio.com/docs/v19-doxydocs-dev/api_overview.html)

## Core Audio調査

Core Audioのデフォルト出力デバイス（内蔵スピーカー）とデフォルト入力デバイス（内蔵マイク）に対して、`AudioObjectHasProperty`、`AudioObjectIsPropertySettable`、`AudioObjectGetPropertyData` を読み取り専用で実行した。

| 対象 | スコープ | プロパティ | 存在 | 現在値の取得 | settable |
|---|---|---|---|---|---|
| 内蔵スピーカー | 出力 | `kAudioDevicePropertyVolumeScalar` / `kAudioDevicePropertyVolumeDecibels` | はい | 成功 | true |
| 内蔵マイク | 入力 | `kAudioDevicePropertyVolumeScalar` / `kAudioDevicePropertyVolumeDecibels` | はい | 成功 | true |

このMacの現在のデバイスはCore Audio上で該当値を読み取り可能で、書き込み可能として公開されている。ただし、既存設定を変更しないため書き込みAPIは実行しておらず、設定変更後の実効音量・実効入力ゲインも検証していない。プロパティの有無と意味は機器・ドライバに依存する。アプリ自体はこの制御APIを使用せず、波形のデジタル振幅だけを調整する。

参照: [Apple Core Audio Functions](https://developer.apple.com/documentation/coreaudio/core-audio-functions)、[AudioObjectIsPropertySettable](https://developer.apple.com/documentation/coreaudio/audioobjectispropertysettable%28_%3A_%3A_%3A%29?language=_9)、[kAudioDevicePropertyVolumeScalar](https://developer.apple.com/documentation/coreaudio/kaudiodevicepropertyvolumescalar)

## 安全・データ

- 可聴スイープは再生していない。無音出力テストだけを実施し、音量を上げる操作や急な音量変化はない。
- macOSのシステム音量・マイク入力設定は変更していない。
- 実スイープ測定データや認証情報は作成・保存・コミットしていない。短時間入力試験の生音声も保存していない。
- この検証はPOCの実機測定成功を示さない。校正のない結果を絶対周波数特性やdB SPLとして扱わないこと。
