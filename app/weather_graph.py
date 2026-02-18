import weather as wt
import matplotlib.pyplot as plt
import japanize_matplotlib 
from datetime import datetime,  timedelta
import matplotlib.dates as mdates
import numpy as np
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

def add_icon(fig, image_path, xy, zoom=0.1, colorize_white=True):
    """
    画像を配置する関数
    colorize_white=True のとき、画像（黒いアイコンなど）を強制的に白くします
    """
    try:
        # 1. 画像を読み込む
        img = plt.imread(image_path)
        
        # 2. 画像の色を加工する (NumPyを使用)
        if colorize_white:
            # データのコピーを作成
            img_processed = img.copy()
            # RGBチャンネル (0, 1, 2番目) をすべて 1.0 (白) に書き換える
            # アルファチャンネル (3番目: 透明度) はそのままにする
            img_processed[:, :, :3] = 1.0
            img = img_processed

        # 3. 加工した画像を OffsetImage に渡す
        # ここに colorize_white を入れてはいけません（エラーの原因になります）
        imagebox = OffsetImage(img, zoom=zoom)

        # 4. 配置の設定
        ab = AnnotationBbox(imagebox, xy, xycoords='figure fraction', 
                            frameon=False, box_alignment=(0, 0.5))
        
        # Figureに描画を追加
        fig.gca().add_artist(ab)
        
    except FileNotFoundError:
        print(f"Warning: Icon not found at {image_path}")
    except Exception as e:
        print(f"Error loading icon {image_path}: {e}")

def draw_weather_dashboard(past_data, intr_temps, intr_pops, forecast_info, umbrella):
    # --- 1. スタイルの設定 (ダークモード) ---
    plt.style.use('dark_background')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), sharex=True, gridspec_kw={'height_ratios': [3, 1.5, 0.3]})
    plt.subplots_adjust(top=0.82, hspace=0.15) #上下の間隔をつめて一体感を出す

    # データのタイムゾーンを取得と時間の設定
    tz = past_data[0].time.tzinfo
    now = datetime.now(tz=tz)
    start_time = now - timedelta(hours=12)
    end_time = now + timedelta(hours=12)

    # アメダスのデータを古いデータを先頭に並べ替える
    past_data = sorted(past_data[1:], key=lambda x: x.time)

    latest = past_data[-1]
    at_latest = wt.list_apparent_temp([latest])[0]["apparent_temp"]

    # --- 1段目: 日付・時刻・天気アイコン ---
    date_str = now.strftime('%m/%d')
    time_str = now.strftime('%H:%M')
    
    # テキスト配置 (座標は 0.0〜1.0 の相対位置)
    fig.text(0.21, 0.87, f"{date_str}  {time_str}", fontsize=24, color='white', fontweight='bold')
    
    # 天気アイコン ( weather_codes[0] からファイル名を判定 )
    weather_icon_path = f"icons/weather/weather_code/{forecast_info.weather_codes[0]}.png"
    add_icon(fig, weather_icon_path, xy=(0.39, 0.81), zoom=0.25, colorize_white=True) # 天気アイコン

    # --- 2段目: 各種数値・傘アイコン ---
    # 数値テキスト
    metrics_text = (
        f"気温: {latest.temp:.1f}℃   体感: {at_latest:.1f}℃   "
        f"湿度: {latest.humidity}%   降水: {latest.precipitation1h}mm"
    )
    fig.text(0.12, 0.84, metrics_text, fontsize=14, color='#cccccc')

    # 傘情報とアイコン
    fig.text(0.69, 0.85, "傘判定:", fontsize=12, color='#cccccc')
    
    # 6h傘アイコン ( umbrella.level_6h からファイル名判定 )
    umb6_path = f"icons/weather/umb_func/{umbrella.level_6h}.png"
    add_icon(fig, umb6_path, xy=(0.69, 0.78), zoom=0.25, colorize_white=True)
    fig.text(0.75, 0.89, "6時間", fontsize=12, color='#cccccc')
    
    # 12h傘アイコン
    umb12_path = f"icons/weather/umb_func/{umbrella.level_12h}.png"
    add_icon(fig, umb12_path, xy=(0.75, 0.78), zoom=0.25, colorize_white=True)
    fig.text(0.81, 0.89, "12時間", fontsize=12, color='#cccccc')



    # --- 2. 上段：気温グラフ (ax1) ---
    # 実績データ (history[1:])
    past_times = [p.time for p in past_data]
    past_temps = [p.temp for p in past_data]
    # 補間予報データ (fine_temps)
    future_times = [f.time for f in intr_temps]
    future_temps = [f.value for f in intr_temps]

    ax1.plot(past_times, past_temps, color='#ff7f0e', linewidth=3, label='観測気温')
    ax1.plot(future_times, future_temps, color='#ff7f0e', linestyle='--', linewidth=3, label='予報気温')
    ax1.plot(past_times, [p["apparent_temp"] for p in wt.list_apparent_temp(past_data)], color='#ffbb78', linewidth=2, alpha=0.7, label='体感温度')

    ax1.set_ylabel('気温 (℃)', color='#ff7f0e', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='#ff7f0e')

    # 現在時刻に垂直線を引く
    ax1.axvline(now, color='white', linestyle=':', alpha=0.5)
    #ax1.text(now, ax1.get_ylim()[1], ' 現在', color='white', va='bottom', fontweight='bold')

    ax1.set_ylim(-5, 35)
    ax1.set_ylabel('気温 (℃)')
    ax1.grid(True, alpha=0.5)
    ax1.legend(loc='upper left', frameon=False)
    #ax1.set_title(f"{forecast_info.location_name} のウェザーダッシュボード", fontsize=14, pad=20)

    #降水確率　二軸グラフ
    ax1_prec = ax1.twinx()

    # 過去：アメダス降水量 (mm)
    past_prec = [p.precipitation1h for p in past_data] # 降水量
    bars_p = ax1_prec.bar(past_times, past_prec, color='#00ffff', alpha=0.5, width=0.03, label='降水量(mm/h)')
    # 降水量の数値を棒の上に表示（0mmより大きい時のみ）
    for bar in bars_p:
        height = bar.get_height()
        if height > 0:
            ax1_prec.text(bar.get_x() + bar.get_width()/2., height + 1,
                          f'{height}mm', ha='center', va='bottom', color='#00ffff', fontsize=8, fontweight='bold')

    #降水確率
    valid_pops = [p for p in intr_pops if p.time >= now]
    pop_times = [p.time for p in valid_pops]
    pop_vals = [p.value for p in valid_pops]
    if pop_times:
        # facecolor='none' で中身を空に、edgecolor で枠線を描画
        ax1_prec.bar(pop_times, pop_vals, facecolor='none', edgecolor='#1f77b4', 
                     linewidth=1.5, width=0.03, label='降水確率(%)', alpha=0.8)
    
    ax1_prec.set_ylim(0,100) # 降水量(100mm/h)と降水確率(100%)がこの軸の最大
    ax1_prec.set_ylabel('降水量(mm/h) / 確率(%)', color='#1f77b4', fontsize=12)
    ax1_prec.tick_params(axis='y', labelcolor='#1f77b4')
    ax1_prec.grid(False) # 右軸のグリッドは非表示

    #ax1.set_title(f"【{forecast_info.location_name}】 気象情報", fontsize=16, pad=20)
    
    # --- 3. サブグラフ (ax2)：体感温度 ＆ 風速 ---
    # 実績データのみ（右半分は空く）
    apparent_temps = wt.list_apparent_temp(past_data)
    at_vals = [p["apparent_temp"] for p in apparent_temps]
    wind_vals = [p.wind for p in past_data]
    wind_dirs = [p.wind_direction for p in past_data]

    #湿度(左軸)
    hum_vals = [p.humidity for p in past_data] # アメダス湿度
    ax2.plot(past_times, hum_vals, color='#5bc0de', linewidth=2, label='湿度')
    ax2.set_ylabel('湿度 (%)', color='#5bc0de', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='#5bc0de')
    ax2.set_ylim(0, 100)

    # 風速 (右軸)
    ax2_wind = ax2.twinx()
    ax2_wind.plot(past_times, wind_vals, color='#2ca02c', linewidth=2, label='風速')
    ax2_wind.set_ylabel('風速 [絶対値] (m/s)', color='#2ca02c')
    ax2_wind.tick_params(axis='y', labelcolor='#2ca02c')
    ax2_wind.set_ylim(0, 20)
    ax2_wind.grid(False)

    # 風向矢印の描画 (quiver)
    # 風向は「吹いてくる方向」なのでベクトルを反転させる

    u = [-np.sin(d * (np.pi / 8))  for d in wind_dirs]
    v = [-np.cos(d * (np.pi / 8)) for d in wind_dirs]
 
    # ax3風向を並べる
    ax3.quiver(past_times, [0.5]*len(past_times), u, v, 
               color='#2ca02c', angles='uv', scale=45, width=0.015,
               headwidth=2, headlength=2.5, headaxislength=2, 
               pivot='middle', alpha=0.7)
    
    ax3.set_yticks([]) # Y軸の目盛りを消す
    ax3.set_ylabel('風向', color='#2ca02c', rotation=0, labelpad=20, va='center')
    ax3.patch.set_facecolor('#222222') # 背景を少し暗くして「帯」を表現
    ax3.patch.set_alpha(0.5)

    # --- 4. 共通設定と時間軸の修正 ---
    for ax in [ax1, ax2]:
        ax.set_xlim(start_time, end_time) # ここで表示範囲を固定
        ax.axvline(now, color='white', linestyle='-', linewidth=1.5, alpha=0.8) # 現在線
        ax.grid(True, alpha=0.5, linestyle='--')

    # X軸の目盛り設定
    # HourLocator(byhour=[0, 3, 6, 9, 12, 15, 18, 21]) などで正時に固定
    formatter = mdates.DateFormatter('%H:%M', tz=tz)
    ax2.xaxis.set_major_formatter(formatter)
    ax2.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 3, 6, 9, 12, 15, 18, 21], tz=tz))

    """
    # --- 5. 傘判定・天気情報の表示 ---
    emoji = wt.get_weather_emoji(forecast_info.weather_codes[0])
    status_map = {0: "傘不要", 1: "折り畳み推奨", 2: "必須"}
    info_text = (
        f"現在の天気:{emoji} {forecast_info.weather[0]}\n"
        f"傘(6h): {status_map[umbrella.level_6h]} (最高降水確率{int(umbrella.max_pop_6h)}%)\n"
        f"傘(12h): {status_map[umbrella.level_12h]} (最高降水確率{int(umbrella.max_pop_12h)}%)"
    )
    fig.text(0.76, 0.86, info_text, fontsize=11, color='white',
             bbox=dict(facecolor='#333333', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))
    """

    plt.savefig('img/weather_report.png', bbox_inches='tight', dpi=150)
    plt.close(fig)




if __name__ == "__main__":
    past_data = wt.collect_12th_amedas00()

    forecast_temps = wt.get_weather_forcast().temps
    intr_temps = wt.interpolate_forecast(forecast_temps, "temps")

    forecast_pops = wt.get_weather_forcast().pops
    intr_pops = wt.interpolate_forecast(forecast_pops, "pops")
    
    forecast_info = wt.get_weather_forcast()
    
    umbrella = wt.judge_umbrella_necessity(intr_pops)

    draw_weather_dashboard(past_data, intr_temps, intr_pops, forecast_info, umbrella)
