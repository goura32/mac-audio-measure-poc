# POC仕様

## ターゲット

- 2021年 14-inch MacBook Pro (M1 Pro), macOS
- Python + tkinter + sounddevice (PortAudio) + numpy/scipy + matplotlib
- 1つのウィンドウ。デバイス選択、出力振幅、測定、音量探索、グラフ、基準登録、JSON保存
- 初期は内蔵マイクと内蔵スピーカー。USB/HDMIのデバイス選択と比較は拡張の入口に留め、実機検証後に仕様確定。

## 測定と比較

- 48kHz、モノラル、80Hz〜16kHz、ログスイープ
- 1kHzを0dBとしてグラフを描き、周波数ごとの凸凹を表示
- 「基準との差分」は2つの**1kHz正規化済み**グラフの差。全体音量差は表示されない
- グラフの0dB線は「フラット/差分ゼロ」であり、スピーカーやマイクが実際にフラットであることは意味しない
- 測定位置、向き、設置、部屋、システム音量、入力ゲインなどを揃える。機器位置が違えば相対差にも部屋の影響が含まれる

## 音量探索

- 現POCはOS音量やマイクの入力ゲインを変更せず、**生成する波形のデジタル振幅**のみ0.02〜0.40の範囲で順に調整する
- 入力ピーク -6dBFS 以下、RMS -46dBFS超を目安に、その範囲で最も高いデジタル振幅を提案する
- 高い音量ほど高品質という意味ではない。歪率、コンプレッサー、音響保護の非線形挙動は別途検証が必要
- マイク感度のOS制御はMacおよび機器に依存するため、次段階でCore Audio対応可否を実機確認してから追加。非対応機器では変更しない

## Core Audio実機調査（2026-10-18）

対象Macのデフォルト内蔵スピーカーでは出力スコープの `kAudioDevicePropertyVolumeScalar` / `kAudioDevicePropertyVolumeDecibels`、内蔵マイクでは入力スコープの同プロパティが存在し、`AudioObjectGetPropertyData` による値の読み取りと `AudioObjectIsPropertySettable` の `true` を確認した。したがって、この実機・現在のデバイスではCore Audioから値を取得でき、書き込み可能として公開されている。

既存の音量・入力設定を変更しない制約から、`AudioObjectSetPropertyData` による書き込みや変更後の音響効果は試していない。対応状況はデバイス/ドライバ依存であり、この確認だけでは他機器やアナログ入力ゲインの実効性を保証しない。アプリにはCore Audio制御を実装しておらず、音量スライダーと探索機能が変更するのは波形のデジタル振幅のみ。

参照: [Apple Core Audio Functions](https://developer.apple.com/documentation/coreaudio/core-audio-functions)、[AudioObjectIsPropertySettable](https://developer.apple.com/documentation/coreaudio/audioobjectispropertysettable%28_%3A_%3A_%3A%29?language=_9)、[kAudioDevicePropertyVolumeScalar](https://developer.apple.com/documentation/coreaudio/kaudiodevicepropertyvolumescalar)

## 非目標（今回）

- キャリブレーションなしの絶対周波数特性、dB SPL測定
- 本格的な高調波歪率 / IMD / マルチトーンの測定
- スピーカーの保護回路を意図的に限界まで駆動すること
- リモート操作、常駐サービス、GitHub Actions
