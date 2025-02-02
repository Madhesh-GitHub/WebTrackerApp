import win32gui
import win32process
import psutil
import time
import json
from datetime import datetime
import os
from collections import defaultdict

class WindowTracker:
    def __init__(self, interval=5):
        """
        Initialize the window tracker
        interval: Time in seconds between checks (default 5 seconds)
        """
        self.interval = interval
        self.usage_data = defaultdict(int)
        self.current_window = None
        self.start_time = None
        
    def get_active_window_info(self):
        """Get the active window title and process name"""
        try:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            
            # Get process name
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
            
    def save_data(self):
        """Save usage data to a JSON file"""
        filename = f"window_usage_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Convert defaultdict to regular dict for JSON serialization
        data_to_save = dict(self.usage_data)
        
        with open(filename, 'w') as f:
            json.dump(data_to_save, f, indent=4)
            
    def track_windows(self, duration_minutes=None):
        """
        Start tracking window usage
        duration_minutes: Optional duration to track (in minutes)
        """
        print("Starting window tracking...")
        end_time = time.time() + (duration_minutes * 60) if duration_minutes else None
        
        try:
            while True:
                if end_time and time.time() > end_time:
                    break
                    
                window_info = self.get_active_window_info()
                
                if window_info:
                    key = f"{window_info['process']} - {window_info['title']}"
                    self.usage_data[key] += self.interval
                    
                    # Print current window if it changed
                    if key != self.current_window:
                        self.current_window = key
                        print(f"\nCurrently tracking: {key}")
                        
                    # Print a dot to show tracking is active
                    print(".", end="", flush=True)
                    
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\nTracking stopped by user")
        finally:
            self.save_data()
            self.display_summary()
            
    def display_summary(self):
        """Display summary of window usage"""
        print("\n\n=== Window Usage Summary ===")
        
        # Sort by usage time (descending)
        sorted_usage = sorted(self.usage_data.items(), key=lambda x: x[1], reverse=True)
        
        for window, seconds in sorted_usage:
            minutes = seconds / 60
            print(f"\n{window}")
            print(f"Time spent: {minutes:.2f} minutes")

if __name__ == "__main__":
    tracker = WindowTracker(interval=5)  # Check every 5 seconds
    tracker.track_windows()