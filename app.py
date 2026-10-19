"""Small macOS acoustic measurement POC. Run: python app.py"""
from __future__ import annotations

import json
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from audio import SAMPLE_RATE, response_db, summarize_recording, make_sweep

mpl.rcParams['font.family'] = ['Hiragino Sans', 'sans-serif']

try:
    import sounddevice as sd
except ImportError as exc:
    raise SystemExit('Install dependencies with: python -m pip install -r requirements.txt') from exc


class Application:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('Mac Audio Measure — POC')
        self.root.geometry('1000x680')
        self.events = queue.Queue()
        self.busy = False
        self.measurement = None
        self.reference = None
        self.devices = []

        panel = ttk.Frame(root, padding=12)
        panel.pack(fill=tk.X)
        ttk.Label(panel, text='出力（スピーカー）').grid(row=0, column=0, sticky='w')
        ttk.Label(panel, text='入力（マイク）').grid(row=1, column=0, sticky='w')
        self.output_device = ttk.Combobox(panel, state='readonly', width=70)
        self.input_device = ttk.Combobox(panel, state='readonly', width=70)
        self.output_device.grid(row=0, column=1, columnspan=4, sticky='ew', padx=6, pady=2)
        self.input_device.grid(row=1, column=1, columnspan=4, sticky='ew', padx=6, pady=2)
        ttk.Button(panel, text='デバイス更新', command=self.refresh_devices).grid(row=0, column=5, padx=5)
        ttk.Label(panel, text='出力デジタル振幅').grid(row=2, column=0, sticky='w')
        self.level = tk.DoubleVar(value=0.02)
        ttk.Scale(panel, from_=0.01, to=0.40, variable=self.level, orient=tk.HORIZONTAL).grid(
            row=2, column=1, columnspan=3, sticky='ew', padx=6)
        self.level_label = ttk.Label(panel)
        self.level_label.grid(row=2, column=4)
        self.level.trace_add('write', lambda *_: self.level_label.configure(text=f'{self.level.get():.2f}'))
        self.level_label.configure(text=f'{self.level.get():.2f}')
        self.measure_btn = ttk.Button(panel, text='測定', command=self.measure)
        self.measure_btn.grid(row=3, column=0, pady=8)
        self.auto_btn = ttk.Button(panel, text='安全な音量を探索', command=self.auto_level)
        self.auto_btn.grid(row=3, column=1, pady=8, sticky='w')
        self.ref_btn = ttk.Button(panel, text='現在値を基準に登録', command=self.set_reference)
        self.ref_btn.grid(row=3, column=2, pady=8, sticky='w')
        ttk.Button(panel, text='JSON保存', command=self.save_json).grid(row=3, column=3, pady=8, sticky='w')
        self.mode = tk.StringVar(value='shape')
        ttk.Radiobutton(panel, text='1kHzを0dBに正規化', variable=self.mode, value='shape',
                        command=self.plot).grid(row=4, column=0, columnspan=2, sticky='w')
        ttk.Radiobutton(panel, text='基準との差分（0dBが一致）', variable=self.mode, value='difference',
                        command=self.plot).grid(row=4, column=2, columnspan=3, sticky='w')
        panel.columnconfigure(1, weight=1)

        self.fig = Figure(figsize=(9, 4.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12)
        self.status = tk.StringVar(value='準備中')
        ttk.Label(root, textvariable=self.status, padding=(12, 6), wraplength=950).pack(fill=tk.X)
        ttk.Label(root, text='相対測定のみ。室内反射・マイク・OS音声処理を含み、校正済み周波数特性やdB SPLは得られません。',
                  padding=(12, 6), foreground='#555').pack(fill=tk.X)
        self.refresh_devices()
        self.plot()
        root.after(100, self.poll)

    def refresh_devices(self):
        try:
            all_devices = sd.query_devices()
            outputs = [(idx, d) for idx, d in enumerate(all_devices) if d['max_output_channels'] >= 1]
            inputs = [(idx, d) for idx, d in enumerate(all_devices) if d['max_input_channels'] >= 1]
            self.outputs = outputs
            self.inputs = inputs
            self.output_device['values'] = [f'{idx}: {d["name"]}' for idx, d in outputs]
            self.input_device['values'] = [f'{idx}: {d["name"]}' for idx, d in inputs]
            default_input, default_output = sd.default.device
            for combo, items, default in ((self.output_device, outputs, default_output),
                                          (self.input_device, inputs, default_input)):
                pos = next((i for i, (idx, _) in enumerate(items) if idx == default), 0)
                if items:
                    combo.current(pos)
            self.status.set('48kHz / モノラル。測定中はMacを動かさず静かにしてください。')
        except Exception as exc:
            self.status.set(f'デバイス一覧を取得できません: {exc}')

    def selected(self):
        if self.input_device.current() < 0 or self.output_device.current() < 0:
            raise RuntimeError('入力・出力デバイスを選択してください')
        i, i_data = self.inputs[self.input_device.current()]
        o, o_data = self.outputs[self.output_device.current()]
        return i, o, i_data['name'], o_data['name']

    def run_async(self, work, label):
        if self.busy:
            return
        try:
            info = self.selected()
        except Exception as exc:
            messagebox.showerror('デバイス選択', str(exc))
            return
        self.busy = True
        self.measure_btn.configure(state='disabled')
        self.auto_btn.configure(state='disabled')
        self.status.set(label)

        def wrapped():
            try:
                result = work(info)
                self.events.put(('done', result))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=wrapped, daemon=True).start()

    @staticmethod
    def record(device_info, level, duration=2.5):
        input_id, output_id, input_name, output_name = device_info
        stimulus = make_sweep(level, duration)
        # sounddevice device tuple order is (input, output).
        capture = sd.playrec(stimulus.reshape(-1, 1), samplerate=SAMPLE_RATE,
                             channels=1, dtype='float32', device=(input_id, output_id), blocking=True)
        capture = capture.reshape(-1).copy()
        metrics = summarize_recording(capture)
        return stimulus, capture, metrics

    def measure(self):
        level = self.level.get()
        def task(devices):
            emitted, recorded, stats = self.record(devices, level)
            if stats['near_clip']:
                raise ValueError('録音がクリップしています。音量を下げて再測定してください。')
            frequencies, curve = response_db(emitted, recorded)
            return {'type': 'measure', 'level': level, 'frequencies_hz': frequencies.tolist(),
                    'response_db': curve.tolist(), 'peak_dbfs': stats['peak_dbfs'],
                    'rms_dbfs': stats['rms_dbfs'], 'input_name': devices[2],
                    'output_name': devices[3], 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                    'sample_rate': SAMPLE_RATE}
        self.run_async(task, 'スイープ再生・録音・解析中…（開始音量に注意）')

    def auto_level(self):
        def task(devices):
            # Fixed system speaker volume and microphone gain: search digital drive level only.
            candidates = (0.02, 0.04, 0.06, 0.08, 0.12, 0.16, 0.22, 0.30, 0.40)
            viable = []
            details = []
            for level in candidates:
                _, capture, stats = self.record(devices, level, duration=0.65)
                details.append({'level': level, **stats})
                # Leave 6dB headroom in input, avoid clipping. Require meaningful signal.
                if stats['peak_dbfs'] > -6 or stats['near_clip']:
                    break
                if stats['rms_dbfs'] > -46:
                    viable.append(level)
            if not viable:
                raise RuntimeError('安全な入力レベルを見つけられません。システム音量またはマイク入力設定を確認してください。')
            return {'type': 'level', 'level': max(viable), 'readings': details}
        self.run_async(task, '出力デジタル振幅を低レベルから探索中…')

    def set_reference(self):
        if self.measurement is None:
            messagebox.showinfo('基準未設定', 'まず測定してください。')
            return
        self.reference = dict(self.measurement)
        self.status.set('現在の測定値を基準に登録しました。別の機器を測定して「基準との差分」を選べます。')
        self.plot()

    def save_json(self):
        if self.measurement is None:
            messagebox.showinfo('未測定', 'まず測定してください。')
            return
        name = f'measurement-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        path = filedialog.asksaveasfilename(defaultextension='.json', initialfile=name,
                                            filetypes=[('JSON', '*.json')])
        if not path:
            return
        payload = {'measurement': self.measurement, 'reference': self.reference,
                   'note': 'Uncalibrated relative response including room, mic, and OS DSP'}
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        self.status.set(f'保存しました: {path}')

    def poll(self):
        try:
            while True:
                kind, content = self.events.get_nowait()
                self.busy = False
                self.measure_btn.configure(state='normal')
                self.auto_btn.configure(state='normal')
                if kind == 'error':
                    self.status.set('エラー: ' + content)
                    continue
                if content['type'] == 'level':
                    self.level.set(content['level'])
                    self.status.set(f'推奨デジタル振幅: {content["level"]:.2f}。これは歪み最小の保証ではなく、録音ヘッドルームに基づく暫定値です。')
                else:
                    self.measurement = content
                    self.status.set(f'測定完了: peak {content["peak_dbfs"]:.1f} dBFS, '
                                    f'RMS {content["rms_dbfs"]:.1f} dBFS / '
                                    f'{content["output_name"]} → {content["input_name"]}')
                    self.plot()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def plot(self):
        self.ax.clear()
        self.ax.axhline(0, color='gray', linestyle='--', linewidth=1, label='0 dB')
        if self.measurement is not None:
            f = np.asarray(self.measurement['frequencies_hz'])
            db = np.asarray(self.measurement['response_db'])
            if self.mode.get() == 'difference' and self.reference is not None:
                rf = np.asarray(self.reference['frequencies_hz'])
                ref = np.interp(f, rf, np.asarray(self.reference['response_db']))
                db = db - ref
                title = '基準に対する差分（1kHz基準）'
            else:
                title = '相対周波数特性（1kHz = 0dB）'
            self.ax.semilogx(f, db, linewidth=1.8)
            self.ax.set_title(title)
        else:
            self.ax.set_title('測定後に周波数特性が表示されます')
        self.ax.set_xlim(80, 16000)
        self.ax.set_xlabel('周波数 (Hz)')
        self.ax.set_ylabel('相対レベル (dB)')
        self.ax.grid(True, which='both', alpha=0.25)
        self.fig.tight_layout()
        self.canvas.draw_idle()


def main():
    root = tk.Tk()
    Application(root)
    root.mainloop()


if __name__ == '__main__':
    main()
