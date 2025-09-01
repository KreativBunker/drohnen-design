import tkinter as tk


def start():
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)


def stop():
    stop_button.config(state=tk.DISABLED)
    start_button.config(state=tk.NORMAL)


root = tk.Tk()
root.title('Drohnen Design')

start_button = tk.Button(root, text='Start', command=start)
start_button.pack(padx=10, pady=5)

stop_button = tk.Button(root, text='Stop', state=tk.DISABLED, command=stop)
stop_button.pack(padx=10, pady=5)

root.mainloop()
