import tkinter as tk
from tkinter import messagebox
import threading
import time
from pynput import mouse, keyboard
import sqlite3

# Initialize global variables
mouse_clicks = 0
key_strokes = 0
keys_pressed = []

# SQLite database setup
def setup_database():
    conn = sqlite3.connect("activity_logger.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            start_time TEXT,
            end_time TEXT,
            total_minutes REAL,
            mouse_clicks INTEGER,
            key_strokes INTEGER,
            keys_pressed TEXT
        )
    """)
    conn.commit()
    conn.close()

# Track mouse clicks
def on_click(x, y, button, pressed):
    global mouse_clicks
    if pressed:
        mouse_clicks += 1
        mouse_clicks_var.set(f"Mouse Clicks: {mouse_clicks}")

# Track keystrokes
def on_press(key):
    global key_strokes, keys_pressed
    key_strokes += 1
    keys_pressed.append(str(key))
    key_strokes_var.set(f"Keystrokes: {key_strokes}")
    keys_pressed_var.set(f"Keys Pressed: {', '.join(keys_pressed[-5:])}")  # Display last 5 keys

# Start activity logger
def start_logger():
    global start_time
    start_time = time.time()
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)

    # Start mouse and keyboard listeners
    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener.start()
    keyboard_listener.start()

    # Keep the listeners alive in a separate thread
    def keep_listeners_alive():
        mouse_listener.join()
        keyboard_listener.join()

    threading.Thread(target=keep_listeners_alive, daemon=True).start()

# Stop activity logger
def stop_logger():
    global start_time, mouse_clicks, key_strokes, keys_pressed
    end_time = time.time()
    total_minutes = (end_time - start_time) / 60
    user = user_entry.get()

    # Save data to database
    conn = sqlite3.connect("activity_logger.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (user, start_time, end_time, total_minutes, mouse_clicks, key_strokes, keys_pressed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user, time.ctime(start_time), time.ctime(end_time), total_minutes, mouse_clicks, key_strokes, ', '.join(keys_pressed)))
    conn.commit()
    conn.close()

    # Reset variables and GUI elements
    messagebox.showinfo("Activity Logger", "Activity logged successfully!")
    mouse_clicks = 0
    key_strokes = 0
    keys_pressed = []
    mouse_clicks_var.set("Mouse Clicks: 0")
    key_strokes_var.set("Keystrokes: 0")
    keys_pressed_var.set("Keys Pressed: None")
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)

# GUI Setup
app = tk.Tk()
app.title("Activity Logger")

# User entry
tk.Label(app, text="Enter User Name:").pack(pady=5)
user_entry = tk.Entry(app)
user_entry.pack(pady=5)

# Display real-time statistics
mouse_clicks_var = tk.StringVar(value="Mouse Clicks: 0")
key_strokes_var = tk.StringVar(value="Keystrokes: 0")
keys_pressed_var = tk.StringVar(value="Keys Pressed: None")

tk.Label(app, textvariable=mouse_clicks_var, font=("Arial", 12)).pack(pady=5)
tk.Label(app, textvariable=key_strokes_var, font=("Arial", 12)).pack(pady=5)
tk.Label(app, textvariable=keys_pressed_var, font=("Arial", 12)).pack(pady=5)

# Start and Stop buttons
start_button = tk.Button(app, text="Start Logger", command=start_logger, bg="green", fg="white")
start_button.pack(pady=10)

stop_button = tk.Button(app, text="Stop Logger", command=stop_logger, bg="red", fg="white", state=tk.DISABLED)
stop_button.pack(pady=10)

# Initialize database
setup_database()

# Run the GUI
app.mainloop()
