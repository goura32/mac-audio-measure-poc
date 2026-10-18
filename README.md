# Mac Audio Measure — POC

2021年14インチ MacBook Pro (M1 Pro) を最初のターゲットにした、GUI付き音響測定ツールの試作です。REWには依存しません。

## 現在できること

- macOSの入力・出力音声デバイスを一覧から選択（将来のUSB/HDMIにも対応する入口）
- ログスイープ 80 Hz–16 kHz を48 kHzで再生して同時録音
- 相対周波数特性のグラフ表示（1 kHz を0 dBに正規化）
- 一度取得した測定を基準に、別測定との差分を0 dB基準線で表示
- 低振幅から試して録音のヘッドルームを確保する「安全な音量を探索」
- 結果をJSON保存（入力・出力名、振幅、測定日時、グラフのデータ、録音レベル）

## 起動（Mac上）

macOS上でPython 3.11以上とTk対応Pythonを用意し、以下を実行:

```bash
git clone https://github.com/goura32/mac-audio-measure-poc.git
cd mac-audio-measure-poc
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

macOSがマイクへのアクセス許可を尋ねたら許可します。スピーカー音量を十分小さくしてから最初の測定を実施してください。**必ず静かな場所で、音量を上げすぎず**使用してください。

テスト（音声機器なしで実行可）:

```bash
python -m pip install pytest
python -m pytest -q
```

**制約:** MacBook内蔵スピーカーとマイクの両方の周波数特性、室内反射、macOS側の信号処理が合成された値を測ります。フラットな校正基準でも、dB SPL（音圧）の測定でもありません。これを差し引いて外部機器の絶対的特性を復元することもできません。同一環境・配置での相対比較に限定してください。

**未実装・未検証:** macOSシステム音量とマイク入力ゲインの自動操作、歪み率/IMDの測定、macOS実機による測定の成功確認。音量探索は現時点ではデジタル出力振幅と録音ピーク/RMSに基づく暫定処理です。

詳細は `docs/SPEC.md`、`docs/MEASUREMENT.md`、`docs/DEVELOPMENT.md`。
