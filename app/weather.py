import math
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from typing import NamedTuple, List
import time


#クラスの定義
class WeatherPoint(NamedTuple):
    time: datetime
    value: float

class WeatherForecast(NamedTuple):
    location_name: str
    weather: List[str]
    pops: List[WeatherPoint]
    temps: List[WeatherPoint]

class Amedas_data(NamedTuple):
    time: datetime
    temp: float
    humidity: float
    wind_direction: int
    wind: float


def get_weather_forcast():
    load_dotenv()
    location = os.getenv("LOCATION_NAME")
    meso_area_code = os.getenv("MESO_AREA_CODE")
    local_area_code = os.getenv("LOCAL_AREA_CODE")
    city_code = os.getenv("CITY_CODE")
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{meso_area_code}.json"
    
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    #今日、明日、明後日のデータは最初のカラムに入っている
    raw_data = data[0]
    weather_list = []
    pop_list = []
    temp_list = []

    for ts in raw_data['timeSeries']:
        times = [datetime.fromisoformat(t) for t in ts['timeDefines']]
    
        for area in ts['areas']:
            code = area['area']['code']

            if code in [local_area_code, city_code]:
                if 'weathers' in area:
                    weather_list = area['weathers']

                # 降水確率の抽出
                if code == local_area_code and 'pops' in area:
                    for t, v in zip(times, area['pops']):
                        pop_list.append(WeatherPoint(time=t, value=float(v)))

                # 気温の抽出
                if code == city_code and 'temps' in area:
                    for t, v in zip(times, area['temps']):
                        temp_list.append(WeatherPoint(time=t, value=float(v)))
    # 最後にクラスにまとめて返す
    return WeatherForecast(
        location_name= location,
        weather= weather_list,
        pops=pop_list,
        temps=temp_list
    )

#アメダスデータ取得用欠損地ヘルパー関数    
# キー（tempなど）が不在、もしくはその中身がNoneならNoneを返す
def get_safe_value(data_dict, key, default=None):

    values = data_dict.get(key)
    if values and values[0] is not None:
        return values[0]

    return default


#最新のアメダスデータの時刻取得(datetime.datetime型で出力)
def amedas_now_time():
    url = "https://www.jma.go.jp/bosai/amedas/data/latest_time.txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
        raw_str = response.text.strip()
        #datetime型に変換
        dt = datetime.strptime(raw_str, '%Y-%m-%dT%H:%M:%S%z')
        return dt

    except Exception as e:
        print(f"最新時刻の取得に失敗: {e}")
        return None


#アメダスのデータ取得
def get_amedas_data(found_time:datetime):
    load_dotenv()
    amedas_number = os.getenv("AMEDAS_NUMBER")
    url_time = found_time.strftime("%Y%m%d%H%M00")
    url = f"https://www.jma.go.jp/bosai/amedas/data/map/{url_time}.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        select_data = data.get(amedas_number)
        temp = get_safe_value(select_data, "temp")
        humidity = get_safe_value(select_data, "humidity")
        wind_direction = get_safe_value(select_data, "windDirection")
        wind = get_safe_value(select_data, "wind")

        if None in [temp, humidity, wind_direction, wind]:
            return None

        return Amedas_data(
            time = found_time,
            temp = temp,
            humidity = humidity,
            wind_direction = wind_direction,
            wind = wind
        )
    
    except Exception as e:
        print(f"({url_time})に対応するURLが存在しません: {e}")
        return None

#アメダスの過去12時間分のデータ取得
def collect_12th_amedas():
    base_time = amedas_now_time()
    if not base_time:
        print("最新情報の時刻データを取得できません")
        return []

    amedas_list = []

    for i in range(12):
        target_time = base_time - timedelta(hours=i)
        data = get_amedas_data(target_time)
        #Noneでなければデータに追加
        if data:
            amedas_list.append(data)
        #0.5秒処理を止める、apiのお作法
        time.sleep(0.5)

    return amedas_list


#アメダスの過去12時間分のデータ取得
#現在の10分刻みの最新データ＋正時のデータ
def collect_12th_amedas00():
    base_time = amedas_now_time()
    if not base_time:
        print("最新情報の時刻データを取得できません")
        return []

    amedas_list = []

    latest_data = get_amedas_data(base_time)
    if latest_data:
        amedas_list.append(latest_data)

    base_hour = base_time.replace(minute=0, second=0, microsecond=0)

    for i in range(13):
        target_time = base_hour - timedelta(hours=i)
        data = get_amedas_data(target_time)
        #現在時刻が正時のデータなら重複して取得しない
        if target_time == base_time:
            continue

        #Noneでなければデータに追加
        if data:
            amedas_list.append(data)
        #0.5秒処理を止める、apiのお作法
        time.sleep(0.5)

    return amedas_list

    

def apparent_temp(temp:float, humidity:float, wind_speed:float):
    #Steadmanの式による体感温度を計算する
    # 飽和水蒸気圧 E (hPa) を計算（テッテンスの式）
    e_sat = 6.1078 * math.pow(10, (7.5 * temp) / (temp + 237.3))
    # 現在の水蒸気圧 e (hPa) を計算
    e_abs = e_sat * (humidity / 100)
    # 体感温度 AT を計算
    # AT = T + 0.33 * e - 0.70 * v - 4.00
    at = temp + (0.33 * e_abs) - (0.70 * wind_speed) - 4.00

    return round(at, 1)




# --- 動作確認 ---
if __name__ == "__main__":
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/420000.json"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    raw_data = data[0]
    
    #print(get_amedas_data(amedas_now_time()))
    
    #print(get_weather_forcast())

    #amd = get_amedas_data(20260212141000)
    #print(apparent_temp(amd.temp, amd.humidity, amd.wind))

    #print(collect_12th_amedas())

    #Sprint(collect_12th_amedas00())

    #print(amedas_now_time())

