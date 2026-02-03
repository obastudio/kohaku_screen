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
       today_csv = "data/train_data/scedule_weekend.csv"
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



