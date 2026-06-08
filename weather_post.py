import requests
import os
import sys
from datetime import datetime, timezone, timedelta

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
JST = timezone(timedelta(hours=9))


def get_weather_icon_and_text(code):
    if code == 0:
        return "☀️", "快晴"
    elif code == 1:
        return "☀️", "晴れ"
    elif code == 2:
        return "⛅", "晴れ時々曇り"
    elif code == 3:
        return "☁️", "曇り"
    elif code in [45, 48]:
        return "🌫️", "霧"
    elif 51 <= code <= 57:
        return "🌦️", "小雨"
    elif 61 <= code <= 67:
        return "🌧️", "雨"
    elif 80 <= code <= 82:
        return "🌧️", "にわか雨"
    elif 95 <= code <= 99:
        return "⛈️", "雷雨"
    else:
        return "🌤️", "天気変わりやすい"


def get_wave_status(height):
    if height <= 0.5:
        return "穏やか🙌"
    elif height <= 1.0:
        return "やや穏やか"
    elif height <= 1.5:
        return "やや波あり"
    elif height <= 2.5:
        return "波あり・要注意"
    else:
        return "高波・要注意⚠️"


def get_comment(weather_code, wave_height, countdown):
    if countdown <= 0:
        return "本日より運航再開！皆さんのお越しをお待ちしています🎊"
    elif countdown <= 3:
        return "いよいよカウントダウンも一桁！7月1日をお楽しみに🎉"
    elif weather_code in [61, 62, 63, 64, 65, 66, 67, 80, 81, 82]:
        return "雨の久米島もまた風情があります☔ 運航再開に向けて準備中🚢"
    elif weather_code == 2:
        return "雲間から差し込む陽光が海面をきらめかせています🌤️"
    elif weather_code == 3:
        return "曇り空でも、久米島の海の美しさは格別です🌿"
    elif weather_code in [0, 1] and wave_height <= 0.5:
        return "青い空、青い海——久米島が最高の表情を見せてくれています✨"
    else:
        return "久米島の海が、皆さんのお越しをお待ちしています🌊"


def get_weekday_ja(weekday):
    return ["月", "火", "水", "木", "金", "土", "日"][weekday]


def fetch_data():
    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=26.3397&longitude=126.7758"
        "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code"
        "&wind_speed_unit=kmh&timezone=Asia%2FTokyo"
    )
    marine_url = (
        "https://marine-api.open-meteo.com/v1/marine"
        "?latitude=26.3397&longitude=126.7758"
        "&current=wave_height&timezone=Asia%2FTokyo"
    )
    weather_data = requests.get(weather_url, timeout=10).json()
    marine_data = requests.get(marine_url, timeout=10).json()
    return weather_data, marine_data


def build_tweet(now, weather_data, marine_data):
    reopen_date = datetime(2026, 7, 1, tzinfo=JST)
    countdown = (reopen_date.date() - now.date()).days

    current = weather_data["current"]
    temp = round(current["temperature_2m"])
    feels_like = round(current["apparent_temperature"])
    humidity = current["relative_humidity_2m"]
    wind = round(current["wind_speed_10m"])
    weather_code = current["weather_code"]
    wave_height = round(marine_data["current"]["wave_height"], 1)

    icon, weather_text = get_weather_icon_and_text(weather_code)
    wave_status = get_wave_status(wave_height)
    comment = get_comment(weather_code, wave_height, countdown)

    month = now.month
    day = now.day
    weekday = get_weekday_ja(now.weekday())

    if countdown > 0:
        tweet = (
            f"【久米島 本日の海況】{month}月{day}日({weekday})\n"
            f"🚢 運航再開まであと{countdown}日！\n\n"
            f"{icon} {weather_text}\n"
            f"🌡️ 気温{temp}℃（体感{feels_like}℃）　💧湿度{humidity}%\n"
            f"💨 風速{wind}km/h　🌊 波高{wave_height}m（{wave_status}）\n\n"
            f"{comment}\n\n"
            f"那覇発のジェット船でお気軽にどうぞ🚢\n"
            f"#久米島 #沖縄 #離島観光 #久米島オーシャンジェット"
        )
    else:
        tweet = (
            f"【久米島 本日の海況】{month}月{day}日({weekday})\n"
            f"🚢 本日も運航中！\n\n"
            f"{icon} {weather_text}\n"
            f"🌡️ 気温{temp}℃（体感{feels_like}℃）　💧湿度{humidity}%\n"
            f"💨 風速{wind}km/h　🌊 波高{wave_height}m（{wave_status}）\n\n"
            f"{comment}\n\n"
            f"那覇〜久米島、ジェット船で約85分🚢\n"
            f"#久米島 #沖縄 #離島観光 #久米島オーシャンジェット"
        )
    return tweet


def post_to_discord(tweet):
    message = (
        "📋 **本日のX投稿テキスト**\n"
        "コピーして @kumejimaocean へ投稿してください👇\n\n"
        f"```\n{tweet}\n```"
    )
    resp = requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
    return resp.status_code


def main():
    if not WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL が設定されていません")
        sys.exit(1)

    now = datetime.now(JST)
    print(f"実行時刻: {now.strftime('%Y-%m-%d %H:%M JST')}")

    weather_data, marine_data = fetch_data()
    tweet = build_tweet(now, weather_data, marine_data)

    print("生成されたツイート:")
    print(tweet)

    status = post_to_discord(tweet)
    if status == 204:
        print("✅ Discordへの投稿成功")
    else:
        print(f"❌ Discord投稿エラー: status={status}")
        sys.exit(1)


if __name__ == "__main__":
    main()
