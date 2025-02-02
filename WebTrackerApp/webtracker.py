import tkinter as tk
from ttkbootstrap import Style, ScrolledText
from ttkbootstrap.widgets import Button, Combobox, Entry, Frame, Label, Meter
from ttkbootstrap.constants import *
from tkinter import messagebox
import threading
import time
import json
from datetime import datetime
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import win32gui
import win32process
import psutil
from collections import defaultdict
from PIL import Image, ImageGrab
Image.CUBIC = Image.BICUBIC
import keyboard
import mouse
import os
from pathlib import Path


# Patch the _Stack issue
import matplotlib.cbook as cbook
if not hasattr(cbook, '_Stack'):        
    cbook._Stack = cbook.Stack

class ActivityLogger:
    def __init__(self):
        self.mouse_clicks = 0
        self.key_strokes = 0
        self.idle_time = 0
        self.last_active = "N/A"
        self.is_logging = False
        self.pressed_keys = []
        self.start_time = None
        self.last_activity = time.time()
        self.idle_threshold = 60  # 1 minute
        self.window_usage = defaultdict(int)
        self.current_window = None
        self.window_check_interval = 5
        self.mouse_listener = None
        self.keyboard_listener = None
        # Screenshot configuration
        self.screenshot_interval = 300  # 5 minutes
        self.is_screenshot_enabled = False
        self.screenshot_thread = None
        self.screenshot_folder = Path("screenshots")
        
    def reset(self):
        self.mouse_clicks = 0
        self.key_strokes = 0
        self.idle_time = 0
        self.pressed_keys = []
        self.start_time = None
        self.window_usage.clear()

    def take_screenshot(self):
        """Capture and save screenshot"""
        try:
            # Create screenshots directory if it doesn't exist
            self.screenshot_folder.mkdir(exist_ok=True)
            
            # Capture the screen
            screenshot = ImageGrab.grab()
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.screenshot_folder / f"screenshot_{timestamp}.png"
            
            # Save the screenshot
            screenshot.save(filename)
            print(f"Screenshot saved: {filename}")
            
        except Exception as e:
            print(f"Error taking screenshot: {e}")
    
    def get_active_window_info(self):
        try:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            
            _, pid = win32process.GetWindowThreadProcessId(window)
            process = psutil.Process(pid)
            process_name = process.name()
            
            return {
                'title': title,
                'process': process_name,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"Error getting window info: {e}")
            return None
        
def screenshot_thread():
    """Thread function to take periodic screenshots"""
    while True:
        if logger.is_logging and logger.is_screenshot_enabled:
            logger.take_screenshot()
        time.sleep(logger.screenshot_interval)


def window_tracking_thread():
    """Thread function to track active windows"""
    while True:
        if logger.is_logging:
            window_info = logger.get_active_window_info()
            if window_info:
                key = f"{window_info['process']} - {window_info['title']}"
                logger.window_usage[key] += logger.window_check_interval
                logger.current_window = key
                
                # Update the UI with current window info
                update_window_label()
        time.sleep(logger.window_check_interval)


def update_window_label():
    """Update the UI with current window information"""
    if hasattr(root, 'current_window_label'):
        current_window = logger.current_window or "N/A"
        root.current_window_label.config(text=f"Current Window: {current_window}")

def save_session_end(hours, minutes):
    """Enhanced session end saving with window usage data"""
    session_data = {
        'end_time': time.strftime("%Y-%m-%d %H:%M:%S"),
        'duration': f"{hours}h {minutes}m",
        'mouse_clicks': logger.mouse_clicks,
        'key_strokes': logger.key_strokes,
        'idle_time': logger.idle_time,
        'pressed_keys': logger.pressed_keys,
        'window_usage': {
            window: {
                'total_seconds': seconds,
                'percentage': (seconds / (hours * 3600 + minutes * 60)) * 100 if hours or minutes else 0
            }
            for window, seconds in logger.window_usage.items()
        }
    }
    try:
        with open('activity_log.json', 'a+') as f:
            json.dump(session_data, f)
            f.write('\n')
    except Exception as e:
        print(f"Error saving session end: {e}")

def show_window_usage_summary():
    """Display window usage summary in a new window"""
    summary_window = tk.Toplevel(root)
    summary_window.title("Window Usage Summary")
    summary_window.geometry("600x400")
    
    # Create text widget for summary
    summary_text = ScrolledText(summary_window, wrap=tk.WORD, width=70, height=20)
    summary_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    
    # Calculate total time
    total_seconds = sum(logger.window_usage.values())
    
    # Sort windows by usage time
    sorted_usage = sorted(logger.window_usage.items(), key=lambda x: x[1], reverse=True)
    
    # Format summary text
    summary = "Window Usage Summary:\n\n"
    for window, seconds in sorted_usage:
        minutes = seconds / 60
        percentage = (seconds / total_seconds * 100) if total_seconds > 0 else 0
        summary += f"Window: {window}\n"
        summary += f"Time spent: {minutes:.2f} minutes ({percentage:.1f}%)\n\n"
    
    summary_text.insert(tk.END, summary)
    summary_text.config(state=tk.DISABLED)


logger = ActivityLogger()

def on_mouse_click():
    if logger.is_logging:
        logger.mouse_clicks += 1
        logger.last_active = time.strftime("%I:%M:%S %p")
        logger.last_activity = time.time()
        update_labels()

def on_key_press(event):
    if logger.is_logging:
        logger.key_strokes += 1
        logger.pressed_keys.append(event.name)
        logger.last_active = time.strftime("%I:%M:%S %p")
        logger.last_activity = time.time()
        update_labels()

def calculate_idle_time():
    last_check_time = None
    while True:
        if logger.is_logging:
            current_time = time.time()
            
            # Calculate idle time only if there's a last check time
            if last_check_time is not None:
                time_gap = current_time - logger.last_activity
                
                # Reset idle time if activity detected
                if time_gap > logger.idle_threshold:
                    logger.idle_time = int(time_gap // 60)
                    update_labels()
            
            last_check_time = current_time
        else:
            last_check_time = None
        
        time.sleep(1)

def start_logging():
    if not logger.is_logging:
        logger.is_logging = True
        logger.reset()
        logger.start_time = time.time()
        logger.last_active = time.strftime("%I:%M:%S %p")
        
        try:
            # Set up mouse hook
            mouse.on_click(on_mouse_click)
            
            # Set up keyboard hook
            keyboard.on_press(on_key_press)
            
            # Start screenshot thread if enabled
            if logger.is_screenshot_enabled and logger.screenshot_thread is None:
                logger.screenshot_thread = threading.Thread(target=screenshot_thread, daemon=True)
                logger.screenshot_thread.start()
            
        except Exception as e:
            print(f"Error starting input listeners: {e}")
            messagebox.showerror("Error", 
                "Failed to start input tracking. The application will continue without input tracking.")
        
        # Update UI
        start_button.config(state='disabled')
        stop_button.config(state='normal')
        update_labels()
        
        # Save initial session info
        save_session_start()

def stop_logging():
    if logger.is_logging:
        logger.is_logging = False
        
        # Remove hooks
        try:
            mouse.unhook_all()
            keyboard.unhook_all()
        except Exception as e:
            print(f"Error stopping input listeners: {e}")
        
        # Calculate session duration
        duration = time.time() - logger.start_time
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        
        # Save session data
        save_session_end(hours, minutes)
        
        # Update UI
        start_button.config(state='normal')
        stop_button.config(state='disabled')
        
        # Show summary
        summary = f"""
        Session Summary:
        Duration: {hours}h {minutes}m
        Mouse Clicks: {logger.mouse_clicks}
        Keystrokes: {logger.key_strokes}
        Idle Time: {logger.idle_time} minutes
        """
        messagebox.showinfo("Activity Logger", summary)
        
        # Show window usage summary
        show_window_usage_summary()

def save_session_start():
    session_data = {
        'project': project_dropdown.get(),
        'task': task_dropdown.get(),
        'description': task_description.get('1.0', 'end-1c'),  # Fixed the text retrieval
        'start_time': time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open('activity_log.json', 'a+') as f:
            json.dump(session_data, f)
            f.write('\n')
    except Exception as e:
        print(f"Error saving session start: {e}")

def save_session_end(hours, minutes):
    session_data = {
        'end_time': time.strftime("%Y-%m-%d %H:%M:%S"),
        'duration': f"{hours}h {minutes}m",
        'mouse_clicks': logger.mouse_clicks,
        'key_strokes': logger.key_strokes,
        'idle_time': logger.idle_time,
        'pressed_keys': logger.pressed_keys
    }
    try:
        with open('activity_log.json', 'a+') as f:
            json.dump(session_data, f)
            f.write('\n')
    except Exception as e:
        print(f"Error saving session end: {e}")

def load_past_activities():
    activities = []
    try:
        with open('activity_log.json', 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    activities.append(data)
                    
        # Clear existing items
        past_activities_list.delete(0, tk.END)
        
        # Add activities in reverse order (newest first)
        for data in reversed(activities):
            if 'start_time' in data:  # This is a session start record
                display_text = f"{data['start_time']} - {data['project']} - {data['task']}"
                if 'description' in data and data['description'].strip():
                    display_text += f"\nDescription: {data['description']}"
                past_activities_list.insert(tk.END, display_text)
                past_activities_list.insert(tk.END, "-" * 50)  # Separator
                
        # Update analytics
        update_analytics(activities)
    except FileNotFoundError:
        past_activities_list.insert(tk.END, "No activity history found")
    except Exception as e:
        past_activities_list.insert(tk.END, f"Error loading history: {str(e)}")

def update_analytics(activities):
    # Clear previous plots
    ax1.clear()
    ax2.clear()
    
    # Extract data for analytics
    dates = []
    clicks = []
    keystrokes = []
    idle_times = []
    
    for i in range(0, len(activities), 2):  # Process in pairs (start and end records)
        if i + 1 < len(activities) and 'end_time' in activities[i + 1]:
            start_data = activities[i]
            end_data = activities[i + 1]
            
            # Convert string time to datetime
            date = datetime.strptime(start_data['start_time'], "%Y-%m-%d %H:%M:%S")
            dates.append(date)
            
            # Collect metrics
            clicks.append(end_data.get('mouse_clicks', 0))
            keystrokes.append(end_data.get('key_strokes', 0))
            idle_times.append(end_data.get('idle_time', 0))
    
    if dates:  # Only create plots if we have data
        # Plot 1: Activity over time
        ax1.plot(dates, clicks, label='Mouse Clicks', marker='o')
        ax1.plot(dates, keystrokes, label='Keystrokes', marker='s')
        ax1.set_title('Activity Trends', color='white')
        ax1.set_xlabel('Date', color='white')
        ax1.set_ylabel('Count', color='white')
        ax1.tick_params(colors='white')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Idle Time Analysis
        ax2.bar(dates, idle_times, label='Idle Time (minutes)', alpha=0.7)
        ax2.set_title('Idle Time Analysis', color='white')
        ax2.set_xlabel('Date', color='white')
        ax2.set_ylabel('Minutes', color='white')
        ax2.tick_params(colors='white')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Rotate date labels for better readability
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # Adjust layout to prevent label cutoff
        fig.tight_layout()
        
        # Update canvas
        canvas.draw()
    else:
        # If no data, display message on plots
        ax1.text(0.5, 0.5, 'No activity data available', 
                horizontalalignment='center', verticalalignment='center',
                color='white')
        ax2.text(0.5, 0.5, 'No activity data available',
                horizontalalignment='center', verticalalignment='center',
                color='white')
        canvas.draw()

def update_labels():
    if not logger.is_logging:
        return
    # Update meters
    clicks_meter.configure(amountused=min(logger.mouse_clicks, 1000))
    keystrokes_meter.configure(amountused=min(logger.key_strokes, 1000))
    idle_meter.configure(amountused=min(logger.idle_time, 60))
    
    # Update labels
    last_active_label.config(text=f"Last Active: {logger.last_active}")
    
    # Calculate session duration
    if logger.start_time:
        duration = time.time() - logger.start_time
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        session_time_label.config(text=f"Session Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")

def create_screenshot_controls(main_frame):
    screenshot_frame = Frame(main_frame, bootstyle="dark")
    screenshot_frame.pack(fill=X, pady=10)
    
    # Screenshot interval input
    Label(screenshot_frame, text="Screenshot Interval (minutes):", font=("Helvetica", 12)).pack(side=LEFT, padx=5)
    interval_entry = Entry(screenshot_frame, width=5)
    interval_entry.insert(0, str(logger.screenshot_interval // 60))
    interval_entry.pack(side=LEFT, padx=5)
    
    def update_interval():
        try:
            minutes = int(interval_entry.get())
            if minutes < 1:
                raise ValueError("Interval must be at least 1 minute")
            logger.screenshot_interval = minutes * 60
            messagebox.showinfo("Success", f"Screenshot interval updated to {minutes} minutes")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
    Button(
        screenshot_frame,
        text="Update Interval",
        bootstyle="info-outline",
        command=update_interval
    ).pack(side=LEFT, padx=5)
    
    # Screenshot toggle
    def toggle_screenshots():
        logger.is_screenshot_enabled = not logger.is_screenshot_enabled
        toggle_btn.config(
            text="🔴 Disable Screenshots" if logger.is_screenshot_enabled else "📸 Enable Screenshots",
            bootstyle="danger-outline" if logger.is_screenshot_enabled else "success-outline"
        )
    
    toggle_btn = Button(
        screenshot_frame,
        text="📸 Enable Screenshots",
        bootstyle="success-outline",
        command=toggle_screenshots
    )
    toggle_btn.pack(side=LEFT, padx=20)

# Setup the main window with a dark theme
style = Style(theme="darkly")
root = style.master
root.title("🎯 WebTracker")
root.geometry("1200x800")

# Create a modern header
header_frame = Frame(root, bootstyle="dark")
header_frame.pack(fill=X, padx=10, pady=5)

title_label = Label(
    header_frame, 
    text="WebTracker", 
    font=("Helvetica", 24, "bold"),
    bootstyle="inverse-dark"
)
title_label.pack(side=LEFT, padx=10)

# Create tabs with a modern look
tabs = tk.ttk.Notebook(root)
active_tab = Frame(tabs, bootstyle="dark")
past_tab = Frame(tabs, bootstyle="dark")
analytics_tab = Frame(tabs, bootstyle="dark")
tabs.add(active_tab, text=" 📊 Current Session ")
tabs.add(past_tab, text=" 📅 History ")
tabs.add(analytics_tab, text=" 📈 Analytics ")
tabs.pack(fill="both", expand=True, padx=10, pady=5)

# Active Tab Content with improved layout
main_frame = Frame(active_tab, bootstyle="dark")
main_frame.pack(fill="both", expand=True, padx=20, pady=10)

create_screenshot_controls(main_frame)

# Project and Task section with modern dropdowns
project_frame = Frame(main_frame, bootstyle="dark")
project_frame.pack(fill=X, pady=10)

Label(project_frame, text="Project:", font=("Helvetica", 12)).pack(side=LEFT, padx=5)
project_dropdown = Combobox(
    project_frame, 
    values=["Project A", "Project B", "Project C"],
    width=30,
    bootstyle="success"
)
project_dropdown.pack(side=LEFT, padx=10)

Label(project_frame, text="Task:", font=("Helvetica", 12)).pack(side=LEFT, padx=5)
task_dropdown = Combobox(
    project_frame, 
    values=["Task 1", "Task 2", "Task 3"],
    width=30,
    bootstyle="success"
)
task_dropdown.pack(side=LEFT, padx=10)

# Task Description with modern text input
desc_frame = Frame(main_frame, bootstyle="dark")
desc_frame.pack(fill=X, pady=10)

Label(desc_frame, text="Task Description:", font=("Helvetica", 12)).pack(anchor=W, padx=5)
task_description = ScrolledText(desc_frame, height=3, width=50)
task_description.pack(fill=X, padx=5, pady=5)

# Stats display with meters
stats_frame = Frame(main_frame, bootstyle="dark")
stats_frame.pack(fill=X, pady=20)

# Mouse clicks meter
clicks_meter = Meter(
    stats_frame,
    bootstyle="success",
    subtext="Mouse Clicks",
    interactive=False,
    metersize=150,
    textright="clicks",
    stripethickness=10
)
clicks_meter.pack(side=LEFT, padx=20)

# Keystrokes meter
keystrokes_meter = Meter(
    stats_frame,
    bootstyle="info",
    subtext="Keystrokes",
    interactive=False,
    metersize=150,
    textright="keys",
    stripethickness=10
)
keystrokes_meter.pack(side=LEFT, padx=20)

# Idle time meter
idle_meter = Meter(
    stats_frame,
    bootstyle="warning",
    subtext="Idle Time",
    interactive=False,
    metersize=150,
    textright="min",
    stripethickness=10
)
idle_meter.pack(side=LEFT, padx=20)

# Activity status with modern labels
status_frame = Frame(main_frame, bootstyle="dark")
status_frame.pack(fill=X, pady=10)

# Add window tracking label to the status frame
status_frame = Frame(main_frame, bootstyle="dark")
status_frame.pack(fill=X, pady=10)

root.current_window_label = Label(
    status_frame,
    text="Current Window: N/A",
    font=("Helvetica", 12),
    bootstyle="inverse-dark"
)
root.current_window_label.pack(side=LEFT, padx=10)

# Start window tracking thread
window_thread = threading.Thread(target=window_tracking_thread, daemon=True)
window_thread.start()

last_active_label = Label(
    status_frame,
    text="Last Active: N/A",
    font=("Helvetica", 12),
    bootstyle="inverse-dark"
)
last_active_label.pack(side=LEFT, padx=10)

session_time_label = Label(
    status_frame,
    text="Session Duration: 00:00:00",
    font=("Helvetica", 12),
    bootstyle="inverse-dark"
)
session_time_label.pack(side=RIGHT, padx=10)

# Control buttons with modern styling
button_frame = Frame(main_frame, bootstyle="dark")
button_frame.pack(pady=20)

start_button = Button(
    button_frame,
    text="▶ Start Logging",
    bootstyle="success-outline",
    width=20,
    command=start_logging
)
start_button.pack(side=LEFT, padx=10)

stop_button = Button(
    button_frame,
    text="⏹ Stop Logging",
    bootstyle="danger-outline",
    width=20,
    command=stop_logging
)
stop_button.pack(side=LEFT, padx=10)

# Past Activities Tab with improved history view
history_frame = Frame(past_tab, bootstyle="dark")
history_frame.pack(fill="both", expand=True, padx=20, pady=10)

Label(
    history_frame,
    text="Session History",
    font=("Helvetica", 16, "bold"),
    bootstyle="inverse-dark"
).pack(pady=10)

# Enhanced history list with details
past_activities_frame = Frame(history_frame, bootstyle="dark")
past_activities_frame.pack(fill="both", expand=True)

past_activities_list = tk.Listbox(
    past_activities_frame,
    font=("Helvetica", 11),
    bg="#2c3e50",
    fg="white",
    selectmode="browse",
    height=20
)
past_activities_list.pack(side=LEFT, fill="both", expand=True, padx=5)

scrollbar = tk.Scrollbar(past_activities_frame)
scrollbar.pack(side=RIGHT, fill=Y)

past_activities_list.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=past_activities_list.yview)

# Analytics Tab
analytics_frame = Frame(analytics_tab, bootstyle="dark")
analytics_frame.pack(fill="both", expand=True, padx=20, pady=10)

Label(
    analytics_frame,
    text="Activity Analytics",
    font=("Helvetica", 16, "bold"),
    bootstyle="inverse-dark"
).pack(pady=10)

# Create figure for analytics with dark theme
plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
fig.patch.set_facecolor('#2c3e50')

# Configure analytics plots
canvas = FigureCanvasTkAgg(fig, analytics_frame)
canvas.draw()
canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)

# Add refresh button for analytics
refresh_button = Button(
    analytics_frame,
    text="🔄 Refresh Analytics",
    bootstyle="info-outline",
    command=lambda: load_past_activities()
)
refresh_button.pack(pady=10)

# Initialize buttons state
stop_button.config(state='disabled')

# Load past activities
load_past_activities()

# Start idle time monitoring thread
idle_thread = threading.Thread(target=calculate_idle_time, daemon=True)
idle_thread.start()

# Run the application
root.mainloop()

