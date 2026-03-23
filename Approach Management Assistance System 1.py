import tkinter as tk
from tkinter import ttk, messagebox
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import time

# 全局定义matplotlib样式，适配tkinter
plt.rcParams['font.sans-serif'] = ['SimHei']  # 解决中文显示
plt.rcParams['axes.unicode_minus'] = False

class AirTrafficControlAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("空管飞机进近辅助系统")
        self.root.geometry("800x600")  # 窗口大小

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

        # 航班号输入（大写，OpenSky返回的航班号是大写）
        ttk.Label(input_frame, text="航班号(大写):").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.flight_number = ttk.Entry(input_frame, width=15)
        self.flight_number.grid(row=0, column=3, padx=5, pady=5)
        self.flight_number.insert(0, "CA1521")  # 默认测试航班

        # 按钮区域
        self.query_btn = ttk.Button(input_frame, text="查询实时数据", command=self.query_flight_data)
        self.query_btn.grid(row=0, column=4, padx=5, pady=5)

        self.refresh_btn = ttk.Button(input_frame, text="开启实时刷新(5s)", command=self.toggle_refresh)
        self.refresh_btn.grid(row=0, column=5, padx=5, pady=5)

        # ========== 2. 数据显示区域 ==========
        data_frame = ttk.LabelFrame(root, text="飞机实时参数")
        data_frame.pack(padx=10, pady=5, fill=tk.X)

        # 高度
        ttk.Label(data_frame, text="实时高度:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.altitude_label = ttk.Label(data_frame, text="-- 米")
        self.altitude_label.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 速度（转换为节，空管常用单位）
        ttk.Label(data_frame, text="实时速度:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.speed_label = ttk.Label(data_frame, text="-- 节")
        self.speed_label.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # 航向
        ttk.Label(data_frame, text="实时航向:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.heading_label = ttk.Label(data_frame, text="-- 度")
        self.heading_label.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)

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

    def query_opensky_api(self):
        """调用OpenSky API获取航班数据"""
        try:
            # OpenSky实时航班状态接口（无API Key，免费）
            url = "https://opensky-network.org/api/states/all"
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # 抛出HTTP错误
            data = response.json()

            # 过滤指定航班号的数据（忽略空格，匹配核心航班号）
            flight_num = self.flight_number.get().strip().upper()
            airport_code = self.airport_code.get().strip().upper()

            for state in data.get("states", []):
                callsign = state[1].strip() if state[1] else ""  # 航班号（callsign）
                # 匹配航班号（兼容带航空公司前缀的情况，比如CA1521 vs 1521）
                if flight_num in callsign:
                    # 提取关键数据
                    altitude = state[13]  # 气压高度（米），None表示无数据
                    velocity = state[9]   # 地速（米/秒）
                    heading = state[10]   # 真航向（度）
                    lon = state[5]        # 经度
                    lat = state[6]        # 纬度

                    # 封装数据
                    return {
                        "altitude": altitude if altitude is not None else "无数据",
                        "speed": round(velocity * 1.94384, 1) if velocity is not None else "无数据",  # 米/秒转节
                        "heading": round(heading, 1) if heading is not None else "无数据",
                        "lon": lon,
                        "lat": lat,
                        "callsign": callsign
                    }
            # 未找到航班
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
        flight_data = self.query_opensky_api()

        if flight_data:
            # 更新文本标签
            self.altitude_label.config(text=f"{flight_data['altitude']} 米")
            self.speed_label.config(text=f"{flight_data['speed']} 节")
            self.heading_label.config(text=f"{flight_data['heading']} 度")

            # 绘制飞机位置和航向
            if flight_data["lon"] is not None and flight_data["lat"] is not None:
                # 简化为相对坐标（以机场为中心，这里用航班位置作为参考点）
                center_lon = flight_data["lon"]
                center_lat = flight_data["lat"]
                # 绘制飞机位置（红点）
                self.ax.scatter(0, 0, color="red", s=100, label=f"航班 {flight_data['callsign']}")
                # 绘制航向箭头（基于航向角度）
                angle = np.radians(flight_data["heading"]) if flight_data["heading"] != "无数据" else 0
                dx = np.cos(angle) * 0.5
                dy = np.sin(angle) * 0.5
                self.ax.arrow(0, 0, dx, dy, head_width=0.1, head_length=0.1, fc='blue', ec='blue', label="航向")
                self.ax.legend(loc="upper right")
        else:
            # 无数据时清空标签
            self.altitude_label.config(text="无数据 米")
            self.speed_label.config(text="无数据 节")
            self.heading_label.config(text="无数据 度")
            messagebox.showinfo("提示", f"未找到航班 {self.flight_number.get()} 的实时数据")

        self.canvas.draw()

    def toggle_refresh(self):
        """开启/关闭实时刷新"""
        self.refresh_flag = not self.refresh_flag
        if self.refresh_flag:
            self.refresh_btn.config(text="关闭实时刷新")
            self.auto_refresh()
        else:
            self.refresh_btn.config(text="开启实时刷新(5s)")

    def auto_refresh(self):
        """自动刷新数据（5秒一次）"""
        if self.refresh_flag:
            self.query_flight_data()
            # 5秒后再次调用
            self.root.after(5000, self.auto_refresh)

if __name__ == "__main__":
    root = tk.Tk()
    app = AirTrafficControlAssistant(root)
    root.mainloop()