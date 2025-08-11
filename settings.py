import tkinter as tk
from tkinter import messagebox, PhotoImage
import json
import os

DATA_FILE = "user_data.json"

# Load user data
def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Save user data
def save_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def settings_window():
    user_data = load_user_data()
    username = user_data.get("username", "")
    level = user_data.get("level", 0)

    root = tk.Toplevel()
    root.title("Settings")
    root.geometry("600x500")
    root.config(bg="#1a1a1a")

    title = tk.Label(root, text="Settings", font=("Arial", 20, "bold"), fg="white", bg="#1a1a1a")
    title.pack(pady=10)

    # ===== Change Password Section =====
    pw_frame = tk.LabelFrame(root, text="Change Password", font=("Arial", 12, "bold"),
                             fg="white", bg="#1a1a1a", bd=2, relief="groove", padx=10, pady=10)
    pw_frame.pack(pady=10, fill="x", padx=20)

    tk.Label(pw_frame, text="Old Password:", fg="white", bg="#1a1a1a").grid(row=0, column=0, sticky="w")
    old_pw = tk.Entry(pw_frame, show="*")
    old_pw.grid(row=0, column=1, pady=5)

    tk.Label(pw_frame, text="New Password:", fg="white", bg="#1a1a1a").grid(row=1, column=0, sticky="w")
    new_pw = tk.Entry(pw_frame, show="*")
    new_pw.grid(row=1, column=1, pady=5)

    tk.Label(pw_frame, text="Confirm Password:", fg="white", bg="#1a1a1a").grid(row=2, column=0, sticky="w")
    confirm_pw = tk.Entry(pw_frame, show="*")
    confirm_pw.grid(row=2, column=1, pady=5)

    def change_password():
        if old_pw.get() != user_data.get("password", ""):
            messagebox.showerror("Error", "Old password is incorrect!")
            return
        if new_pw.get() != confirm_pw.get():
            messagebox.showerror("Error", "New passwords do not match!")
            return
        user_data["password"] = new_pw.get()
        save_user_data(user_data)
        messagebox.showinfo("Success", "Password changed successfully!")

    tk.Button(pw_frame, text="Change Password", command=change_password,
              bg="#ffcc00", fg="black", font=("Arial", 10, "bold")).grid(row=3, columnspan=2, pady=10)

    # ===== Rewards Section =====
    reward_frame = tk.LabelFrame(root, text="Rewards", font=("Arial", 12, "bold"),
                                 fg="white", bg="#1a1a1a", bd=2, relief="groove", padx=10, pady=10)
    reward_frame.pack(pady=10, fill="both", expand=True, padx=20)

    rewards = []
    unlock_levels = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]

    for i in range(10):
        frame = tk.Frame(reward_frame, bg="#1a1a1a", bd=1, relief="solid", width=100, height=100)
        frame.grid_propagate(False)
        frame.grid(row=i // 5, column=i % 5, padx=10, pady=10)

        if level >= unlock_levels[i]:
            if i == 0:
                try:
                    img = PhotoImage(file=r"C:\Users\MSI\Desktop\Projects\Yesr\prev\Nothing Here\ChatBot\bot.png")
                    label = tk.Label(frame, image=img, bg="#1a1a1a")
                    label.image = img
                    label.pack(expand=True)
                except:
                    tk.Label(frame, text="Image Missing", fg="white", bg="#1a1a1a").pack(expand=True)
            else:
                tk.Label(frame, text=f"Reward {i+1}", fg="white", bg="#1a1a1a").pack(expand=True)
        else:
            tk.Label(frame, text="🔒", font=("Arial", 20), bg="#1a1a1a").pack()
            tk.Label(frame, text=f"Unlock at lvl {unlock_levels[i]}", fg="gray", bg="#1a1a1a").pack()

        rewards.append(frame)

    root.mainloop()

if __name__ == "__main__":
    settings_window()
