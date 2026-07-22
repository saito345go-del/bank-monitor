import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
import pandas as pd
import yfinance as yf

# ==========================================
# 1. 設定情報（GitHub Secretsまたは直接指定）
# ==========================================
GMAIL_USER = os.environ.get("GMAIL_USER", "ご自身のGmailアドレス")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS", "ご自身の16桁アプリパスワード")
TO_ADDRESS = GMAIL_USER  # 通知先アドレス

# 監視する銘柄（Yahoo Finance用に .T を付与）
TARGET_STOCKS = {
    "8411.T": "みずほFG",
    "8316.T": "三井住友FG",
    "8306.T": "三菱UFJ",
}

# ==========================================
# 2. メール送信関数
# ==========================================


def send_email(subject, body):
    """メールを送信する関数"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = TO_ADDRESS
    msg["Date"] = formatdate(localtime=True)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.send_message(msg)
        server.close()
        print("【送信完了】指示メールを送信しました！")
    except Exception as e:
        print(f"【エラー】メール送信失敗: {e}")


# ==========================================
# 3. テクニカル指標計算関数
# ==========================================


def calculate_rsi(series, period=14):
    """RSI（相対力指数）を計算"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# ==========================================
# 4. メイン判定処理
# ==========================================


def check_dip_buying():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"--- 監視実行: {now_str} ---")

    signals = []

    for code, name in TARGET_STOCKS.items():
        # 過去6ヶ月分のデータを取得
        df = yf.download(code, period="6mo", interval="1d", progress=False)

        if df.empty:
            print(f"データ取得失敗: {name}({code})")
            continue

        # 移動平均線とRSIの計算
        close = (
            df["Close"].iloc[:, 0]
            if isinstance(df["Close"], pd.DataFrame)
            else df["Close"]
        )

        ma5 = close.rolling(window=5).mean()
        ma25 = close.rolling(window=25).mean()
        rsi14 = calculate_rsi(close, 14)

        # 最新データの取得
        latest_price = float(close.iloc[-1])
        latest_ma5 = float(ma5.iloc[-1])
        latest_ma25 = float(ma25.iloc[-1])
        latest_rsi = float(rsi14.iloc[-1])

        # スクリーニング＆押し目判定
        is_uptrend = latest_price > latest_ma25
        is_dip = (latest_rsi <= 45) or (latest_price < latest_ma5)

        print(
            f"[{name}] 現在値:{latest_price:.1f}円 | MA25:{latest_ma25:.1f}円 | RSI:{latest_rsi:.1f}"
        )

        if is_uptrend and is_dip:
            detail = (
                f"【買い指示（押し目到来）】\n"
                f"■ 銘柄: {name} ({code.replace('.T', '')})\n"
                f"■ 現在値: {latest_price:.1f}円\n"
                f"■ 25日移動平均: {latest_ma25:.1f}円（上昇トレンド継続中）\n"
                f"■ RSI(14): {latest_rsi:.1f}（短期的過熱感なし・調整位置）\n"
                f"👉 SBI証券アプリでチャートを確認し、買注文をご検討ください！\n"
                f"----------------------------------------"
            )
            signals.append(detail)

    # メール送信判定
    if signals:
        subject = f"【売買指示】銀行株の押し目通知 ({now_str})"
        body = (
            f"監視中の銀行株で「押し目買い条件」を満たした銘柄があります。\n\n"
            + "\n\n".join(signals)
        )
        send_email(subject, body)
    else:
        print("本日（現在）は条件を満たす押し目銘柄はありませんでした。")
        # 動作テスト用メール通知
        send_email(
            "【テスト】監視プログラム動作確認",
            "ちゃんと動いてるで！今日は押し目買いのチャンスは無かったわ！",
        )


# 実行
if __name__ == "__main__":
    check_dip_buying()
