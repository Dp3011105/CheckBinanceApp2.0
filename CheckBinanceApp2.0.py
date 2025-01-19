import os
import json
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from ta.trend import MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QMessageBox, QGroupBox, QGridLayout, QComboBox, QProgressDialog
)
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

class BinanceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phân Tích Thị Trường Binance")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        self.api_key = None
        self.api_secret = None
        self.client = None
        self.load_api_credentials()
        self.check_ip()

    def init_ui(self):
        # Chế độ tối
        self.apply_dark_theme()

        font = QFont()
        font.setPointSize(10)

        # Hiển thị IP
        self.ip_label = QLabel("Địa chỉ IP: Đang kiểm tra...")
        self.ip_label.setFont(font)

        # Nhóm thông tin API
        api_group = QGroupBox("Thông tin API")
        api_layout = QGridLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Nhập API Key")
        self.api_key_input.setFont(font)

        self.api_secret_input = QLineEdit()
        self.api_secret_input.setPlaceholderText("Nhập API Secret")
        self.api_secret_input.setEchoMode(QLineEdit.Password)
        self.api_secret_input.setFont(font)

        self.check_api_button = QPushButton("Xác minh API Key và Secret")
        self.check_api_button.setFont(font)
        self.check_api_button.setStyleSheet("background-color: #4caf50; color: white;")
        self.check_api_button.clicked.connect(self.check_api_validity)

        api_layout.addWidget(QLabel("API Key:"), 0, 0)
        api_layout.addWidget(self.api_key_input, 0, 1)
        api_layout.addWidget(QLabel("API Secret:"), 1, 0)
        api_layout.addWidget(self.api_secret_input, 1, 1)
        api_layout.addWidget(self.check_api_button, 2, 0, 1, 2)
        api_group.setLayout(api_layout)

        # Nhóm phân tích thị trường
        market_group = QGroupBox("Phân Tích Thị Trường")
        market_layout = QGridLayout()

        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Nhập mã đồng coin (ví dụ: BTCUSDT, ETHUSDT)")
        self.symbol_input.setFont(font)
        self.symbol_input.textChanged.connect(self.validate_symbols)

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["4h", "1d"])
        self.interval_combo.setFont(font)
        self.interval_combo.setCurrentIndex(0)

        self.analyze_button = QPushButton("Phân Tích Dữ Liệu")
        self.analyze_button.setFont(font)
        self.analyze_button.setStyleSheet("background-color: #2196f3; color: white;")
        self.analyze_button.clicked.connect(self.analyze_market)

        market_layout.addWidget(QLabel("Đồng Coin:"), 0, 0)
        market_layout.addWidget(self.symbol_input, 0, 1)
        market_layout.addWidget(QLabel("Khung Thời Gian:"), 1, 0)
        market_layout.addWidget(self.interval_combo, 1, 1)
        market_layout.addWidget(self.analyze_button, 2, 0, 1, 2)
        market_group.setLayout(market_layout)

        # Hiển thị kết quả
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(font)
        self.result_text.setStyleSheet("background-color: #2b2b2b; color: white;")

        # Layout chính
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.ip_label)
        main_layout.addWidget(api_group)
        main_layout.addWidget(market_group)
        main_layout.addWidget(QLabel("Kết Quả Phân Tích:"))
        main_layout.addWidget(self.result_text)

        self.setLayout(main_layout)

    def apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

    def check_ip(self):
        try:
            ip_info = requests.get("https://api64.ipify.org?format=json").json()
            ip_address = ip_info.get("ip", "Unknown")
            self.ip_label.setText(f"Địa chỉ IP: {ip_address}")
        except:
            self.ip_label.setText("Không thể kiểm tra IP. Vui lòng kiểm tra kết nối mạng.")

    def load_api_credentials(self):
        if os.path.exists("api_credentials.txt"):
            with open("api_credentials.txt", "r") as file:
                data = json.load(file)
                self.api_key = data.get("api_key")
                self.api_secret = data.get("api_secret")
                self.api_key_input.setText(self.api_key)
                self.api_secret_input.setText(self.api_secret)

    def save_api_credentials(self):
        with open("api_credentials.txt", "w") as file:
            json.dump({"api_key": self.api_key, "api_secret": self.api_secret}, file)

    def check_api_validity(self):
        self.api_key = self.api_key_input.text()
        self.api_secret = self.api_secret_input.text()
        if not self.api_key or not self.api_secret:
            QMessageBox.critical(self, "Lỗi", "API Key và Secret không được để trống.")
            return

        # Tạo kết nối đến Binance API bằng các giá trị key và secret từ người dùng nhập
        self.client = Client(self.api_key, self.api_secret)
        try:
            # Kiểm tra tính hợp lệ của API key và secret
            self.client.futures_account_balance()
            QMessageBox.information(self, "Thành Công", "API Key và Secret hợp lệ.")
            self.save_api_credentials()  # Lưu thông tin API nếu cần
        except BinanceAPIException as e:
            QMessageBox.critical(self, "Lỗi", f"API không hợp lệ: {e}")

    def validate_symbols(self):
        symbols_input = self.symbol_input.text().strip()
        symbols = [s.strip().upper() for s in symbols_input.split(",")]
        if len(symbols) > 10:
            self.symbol_input.setStyleSheet("border: 1px solid red;")
        else:
            self.symbol_input.setStyleSheet("border: 1px solid green;")

    def analyze_market(self):
        if not self.client:
            QMessageBox.critical(self, "Lỗi", "Vui lòng xác minh API trước.")
            return

        symbols_input = self.symbol_input.text().strip()
        symbols = [s.strip().upper() for s in symbols_input.split(",")]

        if not symbols or len(symbols) > 10:
            QMessageBox.critical(self, "Lỗi", "Vui lòng nhập tối đa 10 đồng coin.")
            return

        # Hiển thị hiệu ứng đang tải
        progress_dialog = QProgressDialog("Đang tải dữ liệu...", "Hủy", 0, 0, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setValue(0)
        QTimer.singleShot(1000, lambda: progress_dialog.setValue(50))

        # Tạo một luồng riêng biệt để phân tích từng đồng coin
        self.analysis_thread = MarketAnalysisThread(self.client, symbols, progress_dialog)
        self.analysis_thread.update_result.connect(self.update_result)
        self.analysis_thread.start()

    def update_result(self, result):
        self.result_text.setText(result)


class MarketAnalysisThread(QThread):
    update_result = pyqtSignal(str)

    def __init__(self, client, symbols, progress_dialog):
        super().__init__()
        self.client = client
        self.symbols = symbols
        self.progress_dialog = progress_dialog

    def run(self):
        result = ""
        for idx, symbol in enumerate(self.symbols):
            result += f"Đang phân tích {symbol}...\n"
            data = self.get_historical_data(symbol)
            if data is None or data.empty:
                result += f"Không thể lấy dữ liệu cho {symbol}.\n"
                continue

            # Kiểm tra số lượng dữ liệu
            if len(data) < 14:
                result += f"Dữ liệu cho {symbol} không đủ để phân tích ADX.\n"
                continue

            trend, signal = self.market_analysis(data)
            decision = self.trading_decision(data, trend, signal)

            result += f"Phân tích cho {symbol}:\n" + \
                      f" - Xu hướng thị trường: {trend}\n" + \
                      f" - Tín hiệu giao dịch: {signal}\n" + \
                      f" - Kết luận: {decision}\n\n"

            self.update_result.emit(result)  # Cập nhật kết quả ra giao diện
            QThread.msleep(500)  # Đợi một chút trước khi phân tích đồng tiếp theo

    def get_historical_data(self, symbol):
        try:
            klines = self.client.futures_klines(symbol=symbol, interval="1d", limit=100)
            data = pd.DataFrame(klines, columns=[
                "timestamp", "open", "high", "low", "close", "volume", 
                "close_time", "quote_asset_volume", "number_of_trades", 
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ])
            data["close"] = pd.to_numeric(data["close"], errors='coerce')
            data["high"] = pd.to_numeric(data["high"], errors='coerce')
            data["low"] = pd.to_numeric(data["low"], errors='coerce')
            data["volume"] = pd.to_numeric(data["volume"], errors='coerce')
            return data.dropna(subset=["high", "low", "close"])
        except BinanceAPIException as e:
            return None

    def market_analysis(self, data):
        macd = MACD(close=data["close"])
        adx = ADXIndicator(high=data["high"], low=data["low"], close=data["close"])
        rsi = RSIIndicator(close=data["close"])

        latest_macd = macd.macd().iloc[-1]
        latest_signal = macd.macd_signal().iloc[-1]
        adx_value = adx.adx().iloc[-1]
        rsi_value = rsi.rsi().iloc[-1]

        if adx_value > 25:
            if latest_macd > latest_signal and rsi_value < 70:
                return "Tăng", "mua"
            elif latest_macd < latest_signal and rsi_value > 30:
                return "Giảm", "bán"
        elif adx_value < 20:
            return "Đi ngang", "không"
        else:
            return "Không ổn định", "không"

    def trading_decision(self, data, trend, signal):
        close_price = data["close"].iloc[-1]
        atr = AverageTrueRange(high=data["high"], low=data["low"], close=data["close"])
        latest_atr = atr.average_true_range().iloc[-1]

        if signal == "mua":
            tp = close_price + latest_atr * 2
            sl = close_price - latest_atr * 2
            return f"Mở lệnh mua.\n - Chốt lời (TP): {tp:.8f}\n - Cắt lỗ (SL): {sl:.8f}"
        elif signal == "bán":
            tp = close_price - latest_atr * 2
            sl = close_price + latest_atr * 2
            return f"Mở lệnh bán.\n - Chốt lời (TP): {tp:.8f}\n - Cắt lỗ (SL): {sl:.8f}"
        else:
            return "Không khuyến nghị hành động."


if __name__ == "__main__":
    app = QApplication([])
    window = BinanceApp()
    window.show()
    app.exec_()
