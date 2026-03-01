import os
import sys
import time
import threading
import subprocess
import webbrowser
from tkinter import *
from tkinter import ttk, filedialog, messagebox, scrolledtext

# ====================== 全局配置 ======================
GITHUB_URL = "https://github.com/FantasmRealm/ADB-Auto-Tool"
SELECTED_DEVICE = None  # 选中的设备ID
ADB_WORKING = False     # ADB操作锁（避免并发）
KEY_MAPPING_MODE = False# 键盘映射模式开关
LAST_DEVICE_LIST = []   # 上一次检测到的设备列表（用于变化判断）

# 屏幕滑动参数（适配大部分手机，可自行调整）
SCREEN_WIDTH = 1080     # 手机屏幕宽度（默认）
SCREEN_HEIGHT = 2400    # 手机屏幕高度（默认）
SWIPE_DURATION = 300    # 滑动时长（ms）

# ====================== ADB 核心功能 ======================
def run_adb_cmd(cmd_list, timeout=10):
    """执行ADB命令，返回输出结果"""
    global ADB_WORKING
    if ADB_WORKING:
        log("⚠️ 有操作正在执行，请等待")
        return ""
    ADB_WORKING = True
    try:
        # 拼接设备指定参数
        if SELECTED_DEVICE:
            cmd_list = ["adb", "-s", SELECTED_DEVICE] + cmd_list
        else:
            cmd_list = ["adb"] + cmd_list
        
        log(f"执行指令: {' '.join(cmd_list)}")
        
        # --- 关键修改：隐藏 subprocess 窗口 ---
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':  # 如果是 Windows 系统
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout, encoding="utf-8", errors="ignore",
            startupinfo=startupinfo, creationflags=creationflags
        )
        # --- 修改结束 ---
        
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        log(f"执行结果: {output}" if output else "执行完成")
        return output
    except Exception as e:
        log(f"❌ 指令执行失败: {str(e)}")
        return ""
    finally:
        ADB_WORKING = False

def get_connected_devices():
    """获取当前已连接的所有ADB设备（用于实时检测）"""
    try:
        # --- 关键修改：隐藏 subprocess 窗口 ---
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':  # 如果是 Windows 系统
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            ["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=3, encoding="utf-8", errors="ignore",
            startupinfo=startupinfo, creationflags=creationflags
        )
        # --- 修改结束 ---
        
        device_list = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and "device" in line and not line.startswith("List"):
                dev_id = line.split("\t")[0]
                device_list.append(dev_id)
        return device_list
    except:
        return []

def update_device_list_ui():
    """更新设备列表UI（线程安全）"""
    global SELECTED_DEVICE, LAST_DEVICE_LIST
    current_devices = get_connected_devices()
    
    # 只有当设备列表变化时才更新UI，避免频繁刷新
    if current_devices != LAST_DEVICE_LIST:
        LAST_DEVICE_LIST = current_devices.copy()
        
        # 更新设备列表
        listbox_dev.delete(0, END)
        for dev in current_devices:
            listbox_dev.insert(END, dev)
        
        # 更新选中状态
        if SELECTED_DEVICE not in current_devices:
            SELECTED_DEVICE = None
        elif current_devices:
            # 如果之前选中的设备还在，保持选中；否则选中第一个
            if SELECTED_DEVICE in current_devices:
                idx = current_devices.index(SELECTED_DEVICE)
                listbox_dev.selection_set(idx)
            else:
                SELECTED_DEVICE = current_devices[0]
                listbox_dev.selection_set(0)
        
        # 更新状态栏
        if current_devices:
            if SELECTED_DEVICE:
                label_status.config(text=f"✅ 已连接 {len(current_devices)} 台设备 | 当前选中: {SELECTED_DEVICE}")
            else:
                label_status.config(text=f"✅ 已连接 {len(current_devices)} 台设备 | 当前选中: 无")
        else:
            label_status.config(text="❌ 未检测到设备，请检查USB调试是否开启")

def live_device_monitor():
    """后台实时设备检测线程"""
    while True:
        update_device_list_ui()
        time.sleep(1)  # 每秒检测一次

def simulate_swipe(direction):
    """模拟屏幕滑动"""
    if not SELECTED_DEVICE:
        messagebox.showwarning("提示", "请先选择设备！")
        return
    
    # 滑动坐标计算（基于屏幕中心）
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2
    swipe_dist = SCREEN_HEIGHT // 3  # 滑动距离
    
    if direction == "up":    # 上滑（W键）
        start_x, start_y = center_x, center_y + swipe_dist
        end_x, end_y = center_x, center_y - swipe_dist
    elif direction == "down":  # 下滑（S键）
        start_x, start_y = center_x, center_y - swipe_dist
        end_x, end_y = center_x, center_y + swipe_dist
    elif direction == "left":  # 左滑（A键）
        start_x, start_y = center_x + swipe_dist, center_y
        end_x, end_y = center_x - swipe_dist, center_y
    elif direction == "right": # 右滑（D键）
        start_x, start_y = center_x - swipe_dist, center_y
        end_x, end_y = center_x + swipe_dist, center_y
    else:
        return
    
    # 执行滑动指令
    cmd = [
        "shell", "input", "swipe",
        str(start_x), str(start_y),
        str(end_x), str(end_y),
        str(SWIPE_DURATION)
    ]
    threading.Thread(target=run_adb_cmd, args=(cmd,), daemon=True).start()

def simulate_key(key):
    """模拟按键操作"""
    if not SELECTED_DEVICE:
        messagebox.showwarning("提示", "请先选择设备！")
        return
    
    key_map = {
        "h": "shell input keyevent 3",      # 主页键
        "b": "shell input keyevent 4",      # 返回键
        "m": "shell input keyevent 187",    # 多任务键
        "v+": "shell input keyevent 24",    # 音量+
        "v-": "shell input keyevent 25",    # 音量-
        "p": "shell input keyevent 26",     # 电源键（锁屏/解锁）
    }
    
    if key in key_map:
        cmd = key_map[key].split()
        threading.Thread(target=run_adb_cmd, args=(cmd,), daemon=True).start()

def toggle_key_mapping(event=None):
    """切换键盘映射模式"""
    global KEY_MAPPING_MODE
    KEY_MAPPING_MODE = not KEY_MAPPING_MODE
    if KEY_MAPPING_MODE:
        btn_key_map.config(text="🔒 关闭按键映射", bg="#ff4444", fg="white")
        log("🎮 按键映射模式已开启（WASD滑屏/H主页/B返回/M多任务/V+/V-音量）")
        # 聚焦输入框，确保按键捕获
        entry_key_focus.focus_set()
    else:
        btn_key_map.config(text="🔓 开启按键映射", bg="#4CAF50", fg="white")
        log("🛑 按键映射模式已关闭")

def capture_key_event(event):
    """捕获按键事件（仅映射模式开启时生效）"""
    if not KEY_MAPPING_MODE:
        return
    
    key = event.keysym.lower()
    # 滑屏映射
    if key == "w":
        simulate_swipe("up")
    elif key == "s":
        simulate_swipe("down")
    elif key == "a":
        simulate_swipe("left")
    elif key == "d":
        simulate_swipe("right")
    # 功能键映射
    elif key == "h":
        simulate_key("h")
    elif key == "b":
        simulate_key("b")
    elif key == "m":
        simulate_key("m")
    elif key == "plus" or key == "equal":  # 音量+（=键）
        simulate_key("v+")
    elif key == "minus":  # 音量-（-键）
        simulate_key("v-")
    elif key == "p":
        simulate_key("p")

# ====================== UI 辅助功能 ======================
def log(msg):
    """打印日志到UI"""
    text_log.config(state=NORMAL)
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    text_log.insert(END, f"{timestamp} {msg}\n")
    text_log.see(END)  # 自动滚动到底部
    text_log.config(state=DISABLED)

def on_device_select(event):
    """选择设备事件"""
    global SELECTED_DEVICE
    sel = listbox_dev.curselection()
    if sel:
        SELECTED_DEVICE = listbox_dev.get(sel[0])
        log(f"📱 已选择设备: {SELECTED_DEVICE}")
        # 立即更新状态栏
        label_status.config(text=f"✅ 已连接 {len(LAST_DEVICE_LIST)} 台设备 | 当前选中: {SELECTED_DEVICE}")

def open_github():
    """打开GitHub仓库"""
    webbrowser.open(GITHUB_URL)
    log(f"🌐 打开GitHub仓库: {GITHUB_URL}")

# ====================== 主界面构建 ======================
if __name__ == "__main__":
    # 主窗口初始化
    root = Tk()
    root.title("ADB Auto Tool | FantasmRealm")
    root.geometry("1100x700")
    root.minsize(900, 600)
    root.config(bg="#f5f5f5")
    
    # 全局样式配置
    style = ttk.Style()
    style.configure(".", font=("Microsoft YaHei", 9))
    style.configure("TButton", padding=8, font=("Microsoft YaHei", 9))
    style.configure("TLabelframe.Label", font=("Microsoft YaHei", 10, "bold"), bg="#f5f5f5")
    
    # ====================== 顶部功能栏 ======================
    frame_top = Frame(root, bg="#f5f5f5", padx=15, pady=10)
    frame_top.pack(fill=X)
    
    # 基础功能按钮
    btn_scan = ttk.Button(frame_top, text="🔍 手动扫描", command=lambda: update_device_list_ui())
    btn_scan.pack(side=LEFT, padx=5)
    
    btn_reboot = ttk.Button(frame_top, text="🔄 重启设备", command=lambda: threading.Thread(target=run_adb_cmd, args=(["shell", "reboot"],), daemon=True).start())
    btn_reboot.pack(side=LEFT, padx=5)
    
    # 锁屏按钮移到顶部导航栏
    btn_lock = ttk.Button(frame_top, text="🔒 锁屏(P)", command=lambda: threading.Thread(target=simulate_key, args=("p",), daemon=True).start())
    btn_lock.pack(side=LEFT, padx=5)
    
    # GitHub链接
    btn_github = ttk.Button(frame_top, text="🌐 GitHub", command=open_github)
    btn_github.pack(side=RIGHT, padx=5)
    
    # 按键映射开关
    btn_key_map = Button(frame_top, text="🔓 开启按键映射", bg="#4CAF50", fg="white", bd=0, padx=10, command=toggle_key_mapping)
    btn_key_map.pack(side=RIGHT, padx=5)
    
    # ====================== 红色连接提示区 ======================
    frame_tip = Frame(root, bg="#f5f5f5", padx=15, pady=5)
    frame_tip.pack(fill=X)
    
    label_tip = Label(
        frame_tip,
        text="⚠️ 连接异常提示：若设备已连接但工具未检测到，请检查数据线是否正常，并确保手机已开启「USB调试」功能。",
        bg="#f5f5f5", fg="#ff0000", font=("Microsoft YaHei", 9, "bold"), justify="left"
    )
    label_tip.pack(fill=X)
    
    # ====================== 中间核心区 ======================
    frame_mid = Frame(root, bg="#f5f5f5", padx=15, pady=5)
    frame_mid.pack(fill=BOTH, expand=True)
    
    # 左侧：设备列表 + 常用指令区
    frame_left = Frame(frame_mid, bg="#f5f5f5")
    frame_left.pack(side=LEFT, fill=Y, padx=(0, 10))
    
    # 1. 设备列表
    frame_dev = LabelFrame(frame_left, text="📱 已连接设备", bg="#f5f5f5", padx=10, pady=5)
    frame_dev.pack(fill=X, pady=(0, 10))
    
    listbox_dev = Listbox(frame_dev, width=30, height=8, font=("Consolas", 10), bd=1, relief=SOLID)
    listbox_dev.pack(fill=X)
    listbox_dev.bind("<<ListboxSelect>>", on_device_select)
    
    # 2. 常用ADB指令区
    frame_cmd = LabelFrame(frame_left, text="⚡ 常用指令", bg="#f5f5f5", padx=10, pady=10)
    frame_cmd.pack(fill=BOTH, expand=True)
    
    # 指令按钮网格布局（移除了锁屏按钮）
    cmd_buttons = [
        ("主页 (H)", lambda: threading.Thread(target=simulate_key, args=("h",), daemon=True).start()),
        ("返回 (B)", lambda: threading.Thread(target=simulate_key, args=("b",), daemon=True).start()),
        ("多任务 (M)", lambda: threading.Thread(target=simulate_key, args=("m",), daemon=True).start()),
        ("音量+ (＝)", lambda: threading.Thread(target=simulate_key, args=("v+",), daemon=True).start()),
        ("音量- (-)", lambda: threading.Thread(target=simulate_key, args=("v-",), daemon=True).start()),
        ("上滑 (W)", lambda: threading.Thread(target=simulate_swipe, args=("up",), daemon=True).start()),
        ("下滑 (S)", lambda: threading.Thread(target=simulate_swipe, args=("down",), daemon=True).start()),
        ("左滑 (A)", lambda: threading.Thread(target=simulate_swipe, args=("left",), daemon=True).start()),
        ("右滑 (D)", lambda: threading.Thread(target=simulate_swipe, args=("right",), daemon=True).start()),
    ]
    
    # 生成指令按钮（3列布局）
    for idx, (text, cmd) in enumerate(cmd_buttons):
        btn = ttk.Button(frame_cmd, text=text, command=cmd, width=12)
        btn.grid(row=idx//3, column=idx%3, padx=5, pady=5)
    
    # 右侧：按键映射区 + 日志区
    frame_right = Frame(frame_mid, bg="#f5f5f5")
    frame_right.pack(side=RIGHT, fill=BOTH, expand=True)
    
    # 1. 按键映射聚焦区
    frame_key = LabelFrame(frame_right, text="🎮 按键映射（聚焦此区域）", bg="#f5f5f5", padx=10, pady=10)
    frame_key.pack(fill=X, pady=(0, 10))
    
    entry_key_focus = Entry(frame_key, font=("Microsoft YaHei", 12), bd=1, relief=SOLID)
    entry_key_focus.pack(fill=X, padx=5, pady=5)
    entry_key_focus.insert(0, "开启映射后在此区域按WASD/H/B/M等按键操作手机...")
    # 绑定按键事件
    entry_key_focus.bind("<KeyPress>", capture_key_event)
    
    # 按键说明
    label_key_tips = Label(frame_key, text="W上滑 | S下滑 | A左滑 | D右滑 | H主页 | B返回 | M多任务 | ＝音量+ | -音量- | P锁屏", bg="#f5f5f5", fg="#666")
    label_key_tips.pack(pady=5)
    
    # 2. 日志区
    frame_log = LabelFrame(frame_right, text="📝 操作日志", bg="#f5f5f5", padx=10, pady=5)
    frame_log.pack(fill=BOTH, expand=True)
    
    text_log = scrolledtext.ScrolledText(frame_log, font=("Consolas", 9), bg="white", bd=1, relief=SOLID)
    text_log.pack(fill=BOTH, expand=True)
    text_log.config(state=DISABLED)
    
    # ====================== 底部状态栏 ======================
    frame_bottom = Frame(root, bg="#e0e0e0", padx=15, pady=5)
    frame_bottom.pack(fill=X, side=BOTTOM)
    
    label_status = Label(frame_bottom, text="ADB Auto Tool - 启动中...", bg="#e0e0e0", anchor=W)
    label_status.pack(fill=X)
    
    # 初始日志
    log("🎉 ADB Auto Tool 已启动")
    log(f"🔗 开源地址: {GITHUB_URL}")
    log("💡 提示：设备连接状态将自动实时更新，无需手动扫描")
    
    # 启动后台实时检测线程
    threading.Thread(target=live_device_monitor, daemon=True).start()
    
    # 启动主循环
    root.mainloop()