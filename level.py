import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os

class LevelFrame(tk.Frame):
    def __init__(self, parent, controller, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.controller = controller
        self.configure(bg='#B3E5FC')

        self.total_levels = 10
        self.unlocked_level = 1  # Start with only level 1 unlocked
        self.questions = self.load_questions()

        # Load lock icon
        lock_img_path = r"C:\path\to\lock.png"  # Change to your lock icon path
        if os.path.exists(lock_img_path):
            self.lock_icon = ImageTk.PhotoImage(Image.open(lock_img_path).resize((60, 60)))
        else:
            self.lock_icon = None  # Fallback to text if no image

        self.show_levels()

    def load_questions(self):
        return [
            {"question": f"Level {i+1}: What is {i+1} + {i+2}?", "answer": str((i+1)+(i+2))}
            for i in range(self.total_levels)
        ]

    def show_levels(self):
        for widget in self.winfo_children():
            widget.destroy()

        tk.Label(self, text="🌟 Choose Your Level", font=("Roboto", 22, "bold"),
                 bg="#B3E5FC", fg="#01579B").pack(pady=20)

        grid_frame = tk.Frame(self, bg="#B3E5FC")
        grid_frame.pack()

        for i in range(self.total_levels):
            if (i + 1) <= self.unlocked_level:
                btn = tk.Button(grid_frame, text=str(i+1), font=("Roboto", 16, "bold"),
                                width=6, height=3, bg="#4CAF50", fg="white",
                                command=lambda lvl=i: self.play_level(lvl))
            else:
                if self.lock_icon:
                    btn = tk.Button(grid_frame, image=self.lock_icon,
                                    width=60, height=60, state="disabled", bg="#B3E5FC", bd=0)
                else:
                    btn = tk.Button(grid_frame, text="🔒", font=("Roboto", 16),
                                    width=6, height=3, state="disabled", bg="#B3E5FC")
            btn.grid(row=i//5, column=i%5, padx=10, pady=10)

    def play_level(self, level_index):
        self.current_level = level_index
        self.show_question()

    def show_question(self):
        for widget in self.winfo_children():
            widget.destroy()

        q = self.questions[self.current_level]

        tk.Label(self, text=f"🌟 Level {self.current_level + 1}", font=("Roboto", 22, "bold"),
                 bg="#B3E5FC", fg="#01579B").pack(pady=10)

        tk.Label(self, text=q["question"], font=("Roboto", 16), bg="#B3E5FC").pack(pady=10)

        self.answer_entry = tk.Entry(self, font=("Roboto", 16))
        self.answer_entry.pack(pady=10)

        submit_btn = tk.Button(self, text="Submit Answer", font=("Roboto", 14, "bold"),
                               bg="#4CAF50", fg="white", padx=15, pady=8,
                               command=self.check_answer)
        submit_btn.pack(pady=10)

    def check_answer(self):
        user_ans = self.answer_entry.get().strip()
        correct_ans = self.questions[self.current_level]["answer"]

        if user_ans.lower() == correct_ans.lower():
            messagebox.showinfo("✅ Correct!", "Level completed!")
            if self.current_level + 1 > self.unlocked_level - 1:
                self.unlocked_level = self.current_level + 2  # Unlock next
            self.show_levels()
        else:
            messagebox.showerror("❌ Incorrect", "Try again!")
