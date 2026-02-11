import math
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from typing import NamedTuple, List
from datetime import datetime

#クラスの定義
class WeatherPoint(NamedTuple):
    time: datetime
    value: float

class WeatherForecast(NamedTuple):
    location_name: str
    weather: List[str]
    pops: List[WeatherPoint]
    temps: List[WeatherPoint]

"""
def get_weather_json():
    load_dotenv()
    meso_area_code = os.getenv("MESO_AREA_CODE")
    local_area_code = os.getenv("LOCAL_AREA_CODE")
    city_code = os.getenv("CITY_CODE")
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{meso_area_code}.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        #今日、明日、明後日のデータは最初のカラムに入っている
        latest_forecast = data[0]
        local_data = {}
        for ts in latest_forecast['timeSeries']:
            time_labels = ts['timeDefines']
            for area_data in ts['areas']:
                # エリアコードが一致するか確認
                if area_data['area']['code'] in [local_area_code, city_code]:
                    # 辞書の中身を更新(天気、降水確率、気温などを統合)
                    local_data.update(area_data)
                    # どの値がどの時刻に対応するか分かるように名前を付けて保存
                    if 'pops' in area_data:
                        local_data['pop_times'] = time_labels
                    if 'temps' in area_data:
                        local_data['temp_times'] = time_labels
                    if 'weathers' in area_data:
                        local_data['weather_times'] = time_labels
        return local_data
    except requests.exceptions.RequestException as e:
        print(f"データの取得に失敗しました: {e}")
        return None
"""

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
    

def apparent_temp(temp:float, humidity:float, wind_speed:float) -> float:
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
    #print(data)
    select_data = data[0]

    #print(select_data)

    #choise = get_weather_json()

    local_data = {}
    for ts in select_data['timeSeries']:
        time_labels = ts['timeDefines']
        #print(time_labels)
    
    print(get_weather_forcast())

    #local_area_code = os.getenv("LOCAL_AREA_CODE")
    #city_code = os.getenv("CITY_CODE")

    #print(local_area_code, city_code)