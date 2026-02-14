import math
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from typing import NamedTuple, List
import time
from scipy.interpolate import Akima1DInterpolator, PchipInterpolator
import numpy as np

#クラスの定義
class WeatherPoint(NamedTuple):
    time: datetime
    value: float

class WeatherForecast(NamedTuple):
    location_name: str
    weather: List[str]
    weather_codes: List[str]
    pops: List[WeatherPoint]
    temps: List[WeatherPoint]

class Amedas_data(NamedTuple):
    time: datetime
    temp: float
    humidity: float
    wind_direction: int
    wind: float

class UmbrellaResult(NamedTuple):
    level_6h: int     # 0:なし, 1:折り畳み, 2:必須
    max_pop_6h: float 
    level_12h: int    # 0:なし, 1:折り畳み, 2:必須
    max_pop_12h: float 

#予報数値の取得
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
    weather_code_list = []
    pop_list = []
    temp_list = []

    for ts in raw_data['timeSeries']:
        times = [datetime.fromisoformat(t) for t in ts['timeDefines']]
    
        for area in ts['areas']:
            code = area['area']['code']

            if code in [local_area_code, city_code]:
                if 'weathers' in area:
                    weather_list = area['weathers']
                
                if 'weatherCodes' in area:
                    weather_code_list = area['weatherCodes']

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
        weather_codes=weather_code_list,
        pops=pop_list,
        temps=temp_list
    )

#予報数値を将来12時間分の内挿
def interpolate_forecast(forecasts_point, mode:str):
    #データが2つ未満なら補完せずに返す
    if len(forecasts_point) < 2:
        print("補間に十分なデータ数がありません")
        return None

    data = []
    if mode == "temps":
        amedas_data = collect_12th_amedas()
        amedas_3h_data = sorted(amedas_data[:3], key=lambda x: x.time)
        for h in amedas_3h_data:
            data.append(WeatherPoint(time=h.time, value=h.temp))

        #アメダスの3時間前データよりも未来の予報データのみdataリストにいれる
        latest_amedas_time = amedas_3h_data[2].time
        for p in forecasts_point:
            if p.time > latest_amedas_time:
                data.append(p)

    elif mode == "pops":
        data = forecasts_point

    else:
        print("選択したmodeが不正です。tempsかpopsと入力してください") 
        return None
    
    #datetime型からfloot型に一時的に変換
    x = [d.time.timestamp() for d in data]
    y = [d.value for d in data]

    #補間方法
    #気温なら秋間補間、降水確率はPCHIP補間、それ以外は補間せずに返す
    if mode == "temps":
        interp_func = Akima1DInterpolator(x, y)

    elif mode == "pops":
        interp_func = PchipInterpolator(x, y)
    
    else:
        print("選択したmodeが不正です") 
        return None

    #期間の設定
    start_time = x[0]
    end_time = x[-1]
    forcast_start_time = sorted(forecasts_point, key=lambda x: x.time)[0]

    x_new = np.arange(start_time, end_time + 1, 3600)
    y_new = interp_func(x_new)

    result = []
    # タイムゾーン情報を保持するために、入力データのtzinfoを使う
    tz = data[0].time.tzinfo
    
    for ts, val in zip(x_new, y_new):
        if mode == "temps":
            current_dt = datetime.fromtimestamp(ts, tz=tz)
            #補間したリストを最新のアメダスデータよりも新しいもののみをリストに残す
            if latest_amedas_time and current_dt < latest_amedas_time:
                continue

        if mode in ['pop', 'humidity']:
            val = max(0.0, min(100.0, val))
            
        result.append(WeatherPoint(
            time=datetime.fromtimestamp(ts, tz=tz), # 数値を日付に戻す
            value=round(float(val), 1)
        ))
    
    return result






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

#アメダスと予報の気温データを合体
def merge_temps(amedas_list, forecast_list):
    total_series = []
    past_events = sorted(amedas_list[1:], key=lambda x: x.time)
    
    for h in past_events:
        total_series.append(WeatherPoint(
            time=h.time,
            value=h.temp,
            # 予報フラグオフ
            #is_forecast=False 
        ))

    # 2. 最新〜未来データの追加
    for f in forecast_list:
        total_series.append(WeatherPoint(
            time=f.time,
            value=f.value,
            # 予報フラグオン
            #is_forecast=True
        ))

    return total_series

#体感温度の計算式
def apparent_temp(amedas):
    temp = amedas.temp
    humidity = amedas.humidity
    wind_speed = amedas.wind

    #Steadmanの式による体感温度を計算する
    # 飽和水蒸気圧 E (hPa) を計算（テッテンスの式）
    e_sat = 6.1078 * math.pow(10, (7.5 * temp) / (temp + 237.3))
    # 現在の水蒸気圧 e (hPa) を計算
    e_abs = e_sat * (humidity / 100)
    # 体感温度 AT を計算
    # AT = T + 0.33 * e - 0.70 * v - 4.00
    at = temp + (0.33 * e_abs) - (0.70 * wind_speed) - 4.00

    return round(at, 1)

#アメダスデータに体感温度を付与する
def list_apparent_temp(amedas_list):
    apparent_temp_list = []
    for amedas in amedas_list:
     
        at =  apparent_temp(amedas)       

        apparent_temp_list.append({
            "time" : amedas.time,
            "real_temp": amedas.temp,
            "apparent_temp": at
        }) 
    return apparent_temp_list

# 補間済みの降水確率データから、6時間・12時間以内の傘必要度を判定する
def judge_umbrella_necessity(fine_pops: List[WeatherPoint]) -> UmbrellaResult:
    if not fine_pops:
        return UmbrellaResult(0, 0.0, 0, 0.0)

    # 基準時刻（補間データの開始点 = 最新の実況時刻）
    base_time = fine_pops[0].time

    def get_max_and_level(hours: int):
        limit_time = base_time + timedelta(hours=hours)
        
        # 指定時間内の確率を抽出
        relevant_values = [
            p.value for p in fine_pops 
            if base_time <= p.time <= limit_time
        ]
        
        max_pop = max(relevant_values) if relevant_values else 0.0
        
        # 判定ロジック (0, 1, 2)
        if max_pop >= 60:
            level = 2 # 傘必須
        elif max_pop >= 30:
            level = 1 # 折り畳み推奨
        else:
            level = 0 # 傘なし
            
        return max_pop, level

    # 6時間と12時間の計算
    pop6, lvl6 = get_max_and_level(6)
    pop12, lvl12 = get_max_and_level(12)

    return UmbrellaResult(
        level_6h=lvl6,
        max_pop_6h=pop6,
        level_12h=lvl12,
        max_pop_12h=pop12
    )

# --- 動作確認 ---
if __name__ == "__main__":
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/420000.json"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    raw_data = data[0]
    
    #print(get_amedas_data(amedas_now_time()))
    
    #print(get_weather_forcast().weather_codes[1])
    #print(type(get_weather_forcast().temps[1]))
    #amd = get_amedas_data(20260212141000)
    #print(apparent_temp(amd.temp, amd.humidity, amd.wind))

    #print(collect_12th_amedas())

    #Sprint(collect_12th_amedas00())

    #print(amedas_now_time())

    #print((list_apparent_temp(collect_12th_amedas00())))

    #now_amd = get_amedas_data(amedas_now_time())

    # = now_amd.temp
   

    
    #print(apparent_temp(now_amd))
    
    #forecast_temp = get_weather_forcast().temps
    #forecast_temp_intr = interpolate_forecast(forecast_temp, "temps")
    #print(forecast_temp_intr)

    #forecast_pops = get_weather_forcast().pops
    #intr_pops = interpolate_forecast(forecast_pops, "pops")
    #print(judge_umbrella_necessity(intr_pops).level_6h)

    #amedas = collect_12th_amedas00()

    #print(merge_temps(amedas, forecast_temp_intr))



