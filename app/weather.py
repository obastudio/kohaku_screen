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

#アメダスのデータ取得
def get_amedas_data(found_time:int):
    load_dotenv()
    amedas_number = os.getenv("AMEDAS_NUMBER")
    time = str(found_time)
    dt = datetime.strptime(time, "%Y%m%d%H%M%S")
    url = f"https://www.jma.go.jp/bosai/amedas/data/map/{time}.json"
    
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    select_data = data.get(amedas_number)
    temp = get_safe_value(select_data, "temp")
    humidity = get_safe_value(select_data, "humidity")
    wind_direction = get_safe_value(select_data, "wind")
    wind = get_safe_value(select_data, "wind")

    if None in [temp, humidity, wind_direction, wind]:
        return None
    
    return Amedas_data(
        time = dt,
        temp = temp,
        humidity = humidity,
        wind_direction = wind_direction,
        wind = wind
    )

def collect_12th_amedas():
    amedas_list = []
    
    T = "20260212230000"
    base_time = datetime.strptime(T, "%Y%m%d%H%M%S")

    for i in range(12):
        target_time = base_time - timedelta(hours=i)

        time_str = target_time.strftime("%Y%m%d%H0000")

        data = get_amedas_data(time_str)

        #Noneでなければデータに追加
        if data:
            amedas_list.append(data)

        #0.5秒処理を止める、apiのお作法
        time.sleep(0.5)

    return amedas_list

    

def apparent_temp(temp:float, humidity:float, wind_speed:float):
    #Steadmanの式による体感温度を計算する
    # 1. 飽和水蒸気圧 E (hPa) を計算（テッテンスの式）
    e_sat = 6.1078 * math.pow(10, (7.5 * temp) / (temp + 237.3))
    # 2. 現在の水蒸気圧 e (hPa) を計算
    e_abs = e_sat * (humidity / 100)
    # 3. 体感温度 AT を計算
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
    
    #print(get_amedas_data(20260212141000))
    
    #print(get_weather_forcast())

    amd = get_amedas_data(20260212141000)
    #print(apparent_temp(amd.temp, amd.humidity, amd.wind))

    print(collect_12th_amedas())



