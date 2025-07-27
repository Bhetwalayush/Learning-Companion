# level.py
import tkinter as tk
from tkinter import messagebox

class LevelFrame(tk.Frame):
    def __init__(self, parent, controller, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.controller = controller
        self.configure(bg='#F5F7FA')
        self.total_questions = 150
        self.current_level = 0  # Start at level 0
        self.questions = self.load_questions()
        self.show_question()

    def load_questions(self):
        # Dummy questions with increasing difficulty for now
        return [
            {"question": f"Level {i+1}: What is {i+1} + {i+2}?", "answer": str((i+1)+(i+2))}
            for i in range(self.total_questions)
        ]

    def show_question(self):
        for widget in self.winfo_children():
            widget.destroy()

        q = self.questions[self.current_level]

        tk.Label(self, text=f"🌟 Level {self.current_level + 1}", font=("Roboto", 22, "bold"),
                 bg="#F5F7FA", fg="#1B5E20").pack(pady=10)

        tk.Label(self, text=q["question"], font=("Roboto", 16), bg="#F5F7FA").pack(pady=10)

        self.answer_entry = tk.Entry(self, font=("Roboto", 16))
        self.answer_entry.pack(pady=10)

        submit_btn = tk.Button(
            self, text="Submit Answer", font=("Roboto", 14, "bold"),
            bg="#4CAF50", fg="white", padx=15, pady=8, command=self.check_answer
        )
        submit_btn.pack(pady=10)

    def check_answer(self):
        user_ans = self.answer_entry.get().strip()
        correct_ans = self.questions[self.current_level]["answer"]

        if user_ans.lower() == correct_ans.lower():
            self.current_level += 1
            if self.current_level >= self.total_questions:
                messagebox.showinfo("🎉 Finished!", "You've completed all levels!")
            else:
                messagebox.showinfo("✅ Correct!", "On to the next level!")
                self.show_question()
        else:
            messagebox.showerror("❌ Incorrect", "Try again!")

