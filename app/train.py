import csv
import os
from datetime import datetime, timedelta
import jpholiday
from dotenv import load_dotenv


def get_time():
   #日付と時刻を返す
   nowtime = datetime.now()
   #日付のみを返す
   today = nowtime.date()
   day = today.strftime("%Y/%m/%d")
   #時刻のみを返す
   time = nowtime.time().strftime("%H:%M:%S")
   #曜日を返す(0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日)
   week = nowtime.weekday()
   
   #休日ならTrue、平日ならFalseを返す
   weekend = week >= 5
   #祝日ならTrue、平日ならFalseを返す
   japanese_holiday = jpholiday.is_holiday(today)
   #休日または祝日ならTrue、平日かつ祝日でないならFalseを返す
   weekend_holiday = weekend or japanese_holiday
   
   if weekend_holiday:
       today_csv = "data/train_data/scedule_weekend.csv"
   else:
       today_csv = "data/train_data/schedule_weekday.csv"

   return nowtime, day, time,  weekend_holiday, today_csv

