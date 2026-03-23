import tkinter as tk
from tkinter import ttk, messagebox
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import time
from datetime import datetime

# 全局定义matplotlib样式，适配tkinter
plt.rcParams['font.sans-serif'] = ['SimHei']  # 解决中文显示
plt.rcParams['axes.unicode_minus'] = False

class AirTrafficControlAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("空管飞机进近辅助系统（国内API版）")
        self.root.geometry("800x600")  # 窗口大小
        
        # 聚合数据API Key（请替换为你自己的Key）
        self.API_KEY = "你的聚合数据API Key"  # 关键替换点
        
        # 初始化变量
        self.flight_data = None  # 存储航班数据
        self.refresh_flag = False  # 实时刷新标记

        # ========== 1. 输入区域 ==========
        input_frame = ttk.LabelFrame(root, text="查询参数")
        input_frame.pack(padx=10, pady=5, fill=tk.X)

        # 机场ICAO码输入
        ttk.Label(input_frame, text="机场ICAO码:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.airport_code = ttk.Entry(input_frame, width=10)
        self.airport_code.grid(row=0, column=1, padx=5, pady=5)
        self.airport_code.insert(0, "ZBAA")  # 默认北京首都机场

        # 航班号输入
        ttk.Label(input_frame, text="航班号:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.flight_number = ttk.Entry(input_frame, width=15)
        self.flight_number.grid(row=0, column=3, padx=5, pady=5)
        self.flight_number.insert(0, "CA1521")  # 默认测试航班

        # 查询日期（默认当天）
        ttk.Label(input_frame, text="查询日期:").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
        self.query_date = ttk.Entry(input_frame, width=12)
        self.query_date.grid(row=0, column=7, padx=5, pady=5)
        self.query_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # 按钮区域
        self.query_btn = ttk.Button(input_frame, text="查询实时数据", command=self.query_flight_data)
        self.query_btn.grid(row=0, column=4, padx=5, pady=5)

        self.refresh_btn = ttk.Button(input_frame, text="开启实时刷新(10s)", command=self.toggle_refresh)
        self.refresh_btn.grid(row=0, column=5, padx=5, pady=5)

        # ========== 2. 数据显示区域 ==========
        data_frame = ttk.LabelFrame(root, text="飞机实时参数")
        data_frame.pack(padx=10, pady=5, fill=tk.X)

        # 高度
        ttk.Label(data_frame, text="实时高度:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.altitude_label = ttk.Label(data_frame, text="-- 米")
        self.altitude_label.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 速度（节，空管常用单位）
        ttk.Label(data_frame, text="实时速度:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.speed_label = ttk.Label(data_frame, text="-- 节")
        self.speed_label.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # 航向
        ttk.Label(data_frame, text="实时航向:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.heading_label = ttk.Label(data_frame, text="-- 度")
        self.heading_label.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)

        # 航班状态
        ttk.Label(data_frame, text="航班状态:").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
        self.status_label = ttk.Label(data_frame, text="--")
        self.status_label.grid(row=0, column=7, padx=5, pady=5, sticky=tk.W)

        # ========== 3. 图形显示区域 ==========
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # 初始化图形
        self.init_plot()

    def init_plot(self):
        """初始化绘图区域"""
        self.ax.clear()
        self.ax.set_title("飞机实时位置与航向（空管进近辅助）")
        self.ax.set_xlabel("相对经度")
        self.ax.set_ylabel("相对纬度")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(-1, 1)
        self.ax.set_ylim(-1, 1)
        self.canvas.draw()

    def query_juhe_api(self):
        """调用聚合数据API获取航班数据"""
        try:
            api_url = "http://v.juhe.cn/flight_dynamic/query"
            params = {
                "key": self.API_KEY,
                "fnum": self.flight_number.get().strip(),
                "date": self.query_date.get().strip()
            }

            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()  # 抛出HTTP错误
            data = response.json()

            if data.get("error_code") == 0:  # 成功返回
                flight_info = data.get("result", {}).get("flight", {})
                real_time_data = data.get("result", {}).get("realtime", {})

                # 提取关键数据（处理空值）
                altitude = real_time_data.get("altitude", 0) or "无数据"
                speed = real_time_data.get("speed", 0) or "无数据"
                heading = real_time_data.get("direction", 0) or "无数据"
                lon = real_time_data.get("lon", 0) or 0
                lat = real_time_data.get("lat", 0) or 0
                status = flight_info.get("status", "未知状态")

                # 单位转换：米/秒 → 节（1米/秒 = 1.94384节）
                if speed != "无数据" and speed > 0:
                    speed = round(speed * 1.94384, 1)

                return {
                    "altitude": altitude,
                    "speed": speed,
                    "heading": heading,
                    "lon": lon,
                    "lat": lat,
                    "status": status,
                    "callsign": self.flight_number.get().strip()
                }
            else:
                messagebox.showwarning("API错误", f"错误码: {data.get('error_code')}, 信息: {data.get('reason')}")
                return None
        except requests.exceptions.RequestException as e:
            messagebox.showerror("网络错误", f"API调用失败：{str(e)}")
            return None
        except Exception as e:
            messagebox.showerror("解析错误", f"数据解析失败：{str(e)}")
            return None

    def query_flight_data(self):
        """查询航班数据并更新UI"""
        self.init_plot()  # 清空之前的绘图
        flight_data = self.query_juhe_api()

        if flight_data:
            # 更新文本标签
            self.altitude_label.config(text=f"{flight_data['altitude']} 米")
            self.speed_label.config(text=f"{flight_data['speed']} 节")
            self.heading_label.config(text=f"{flight_data['heading']} 度")
            self.status_label.config(text=flight_data['status'])

            # 绘制飞机位置和航向
            if flight_data["lon"] != 0 and flight_data["lat"] != 0:
                # 简化为相对坐标（以当前位置为中心）
                self.ax.scatter(0, 0, color="red", s=100, label=f"航班 {flight_data['callsign']}")
                # 绘制航向箭头
                if flight_data["heading"] != "无数据" and flight_data["heading"] > 0:
                    angle = np.radians(flight_data["heading"])
                    dx = np.cos(angle) * 0.5
                    dy = np.sin(angle) * 0.5
                    self.ax.arrow(0, 0, dx, dy, head_width=0.1, head_length=0.1, fc='blue', ec='blue', label="航向")
                self.ax.legend(loc="upper right")
        else:
            # 无数据时清空标签
            self.altitude_label.config(text="无数据 米")
            self.speed_label.config(text="无数据 节")
            self.heading_label.config(text="无数据 度")
            self.status_label.config(text="无数据")

        self.canvas.draw()

    def toggle_refresh(self):
        """开启/关闭实时刷新"""
        self.refresh_flag = not self.refresh_flag
        if self.refresh_flag:
            self.refresh_btn.config(text="关闭实时刷新")
            self.auto_refresh()
        else:
            self.refresh_btn.config(text="开启实时刷新(10s)")

    def auto_refresh(self):
        """自动刷新数据（10秒一次，适配国内API频率限制）"""
        if self.refresh_flag:
            self.query_flight_data()
            # 10秒后再次调用（国内API不建议过快刷新）
            self.root.after(10000, self.auto_refresh)

if __name__ == "__main__":
    root = tk.Tk()
    app = AirTrafficControlAssistant(root)
    root.mainloop()