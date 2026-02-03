import csv
import os
from datetime import datetime, timedelta
import jpholiday
from dotenv import load_dotenv
from typing import NamedTuple

#クラス設計
#個人設定の定義
class PersonalConfig(NamedTuple):
    WALK_TIME_MIN: int
    DASH_TIME_MIN: int

#現在時刻の定義
class NowTime(NamedTuple):
    nowtime: datetime
    day: str
    time: str
    weekend_holiday: bool
    today_csv: str

#駅到達時刻の定義
class ArivalTime(NamedTuple):
    walk_arival: datetime
    dash_arival: datetime

#列車情報の定義
class TrainInfo(NamedTuple):
    train_time: str
    train_type: str
    train_destination: str
    train_color: str
    success_walk: bool
    success_dash: bool

#個人設定の読み込み
def load_settings():
    load_dotenv()
    return PersonalConfig(
        WALK_TIME_MIN = int(os.getenv("WALK_TIME_MIN")),
        DASH_TIME_MIN = int(os.getenv("DASH_TIME_MIN"))
    )

# 現在の時刻(datetime型)、日付(str型)、時刻(str型)、
# 休日か平日かの判定(bool型)(休日ならTrue平日ならFalse)、対応する時刻表の相対パス(str型)
def get_time():
   now = datetime.now()
   today = now.date()
   display_day = today.strftime("%m/%d")
   display_time = now.time().strftime("%H:%M:%S")
   #曜日を返す(0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日)
   week = now.weekday()
   
   #休日または祝日ならTrue、平日かつ祝日でないならFalseを返す
   weekend = week >= 5
   japanese_holiday = jpholiday.is_holiday(today)
   weekend_holiday = weekend or japanese_holiday
   
   if weekend_holiday:
       today_csv = "data/train_data/schedule_weekend.csv"
   else:
       today_csv = "data/train_data/schedule_weekday.csv"

   return NowTime(
       nowtime = now,
       day = display_day,
       time = display_time,
       weekend_holiday = weekend_holiday,
       today_csv = today_csv
   )

#駅到達時刻の計算
def arival_time():
    walk_arival = get_time().nowtime + timedelta(minutes = load_settings().WALK_TIME_MIN)
    dash_arival = get_time().nowtime + timedelta(minutes = load_settings().DASH_TIME_MIN)
    return ArivalTime(
        walk_arival = walk_arival,
        dash_arival = dash_arival
    )

#列車基本情報の取得
def train_base_info():
    master = {}
    train_master_path = "data/train_data/train_master.csv"
    with open(train_master_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            master[row['id']] = row
    return master

# 乗車可能列車情報の取得
def upcoming_train():
    nowtime = get_time()
    arivaltime = arival_time()
    master = train_base_info()
    upcoming = []
    
    with open(nowtime.today_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dep_dt = nowtime.nowtime.replace(
                hour = int(row['hour']), 
                minute = int(row['min']),
                second = 0,
                microsecond = 0
            )
            #ダッシュ到着時刻より前の列車は除外
            if dep_dt < arivaltime.dash_arival:
                continue
            
            m_info = master.get(row['master_id'])
            if not m_info:
                continue
            
            upcoming.append(
                TrainInfo(
                    train_time = dep_dt.strftime('%H:%M'),
                    train_type = m_info['type'],
                    train_destination = m_info['dest'],
                    train_color = m_info['color'],
                    success_walk = dep_dt >= arivaltime.walk_arival,
                    success_dash = dep_dt >= arivaltime.dash_arival
                )
            )
            if len(upcoming) >= 3:
                break


    return upcoming

# エントリーポイント
if __name__ == "__main__":
    # 1. 電車情報を取得
    trains = upcoming_train()
    
    # 2. 結果を表示
    print("--- 次に乗れる電車（直近3本） ---")
    if not trains:
        print("現在、乗れる電車はありません。")
    else:
        for i, train in enumerate(trains, 1):
            # success_walkなどの真偽値も確認できるように
            status = "徒歩OK" if train.success_walk else "ダッシュ推奨"
            print(f"{i}: {train.train_time}発 {train.train_type}({train.train_destination}行) [{status}]")