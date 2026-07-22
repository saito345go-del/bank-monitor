import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
import pandas as pd
import yfinance as yf

# GitHubの暗号化設定（Secrets）から自動で読み込む
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS")
TO_ADDRESS = GMAIL_USER  # 自分宛てに送信

TARGET_STOCKS = {
    "8411.T": "みずほFG",
    "8316.T": "三井住友FG",
    "8306.T": "三菱UFJ",
}


def send_email(subject, body):
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
        print("【成功】メールを送信しました！")
    except Exception as e:
        print(f"【エラー】メール送信失敗: {e}")


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def check_dip_buying():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"--- 監視実行: {now_str} ---")
    signals = []

    for code, name in TARGET_STOCKS.items():
        df = yf.download(code, period="6mo", interval="1d", progress=False)
        if df.empty:
            continue

        close = (
            df["Close"].iloc[:, 0]
            if isinstance(df["Close"], pd.DataFrame)
            else df["Close"]
        )

        ma5 = close.rolling(window=5).mean()
        ma25 = close.rolling(window=25).mean()
        rsi14 = calculate_rsi(close, 14)

        latest_price = float(close.iloc[-1])
        latest_ma5 = float(ma5.iloc[-1])
        latest_ma25 = float(ma25.iloc[-1])
        latest_rsi = float(rsi14.iloc[-1])

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
                f"■ 25日移動平均: {latest_ma25:.1f}円（上昇トレンド）\n"
                f"■ RSI(14): {latest_rsi:.1f}（調整位置）\n"
                f"👉 SBI証券アプリで注文をご検討ください！\n"
                f"----------------------------------------"
            )
            signals.append(detail)

if signals:
        subject = f"【売買指示】銀行株の押し目通知 ({now_str})"
        body = (
            f"監視中の銀行株で押し目買い条件を満たした銘柄があります。\n\n"
            + "\n\n".join(signals)
        )
        send_email(subject, body)
    else:
        print("条件を満たす押し目銘柄はありませんでした。")
        # ▼ここを追加！条件を満たしてなくても確認メールを飛ばす
        send_email("【テスト】監視プログラム動作確認", "ちゃんと動いてるで！今日は押し目買いのチャンスは無かったわ！")


if __name__ == "__main__":
    check_dip_buying()
