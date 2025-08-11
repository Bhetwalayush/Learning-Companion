# app.py
import tkinter as tk
from tkinter import messagebox
import os
import json
import time
import random
import hashlib
import platform
import subprocess
import threading
import re
import google.generativeai as genai
from dotenv import load_dotenv
from main import text_to_speech  # Your TTS function (must exist)
from PIL import Image, ImageTk
import cv2
from level import LevelFrame
from settings import settings_window

# ---------------------- Configuration / Globals ----------------------
USER_DATA_FILE = "user_data.json"
QUIZ_COOLDOWN_SECONDS = 24 * 3600  # 24 hours

# Keep your Gemini config the same as before (unchanged)
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


generation_config = {
  "temperature": 0.9,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2000,
  "response_mime_type": "text/plain",
}
safety_settings = [
  {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
  {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
  model_name="gemini-2.5-flash",
  safety_settings=safety_settings,
  generation_config=generation_config,
  system_instruction = (
    "You are an AI learning companion for children aged 5 to 16, especially designed for Nepali students. "
    "Your job is to make learning fun, personalized, and easy to understand across subjects like Social Studies, "
    "Nepali Language, Mathematics, Geography, and Moral Education. "
    "Use friendly, age-appropriate language, simple analogies, stories, and interactive questions to explain concepts. "
    "Encourage curiosity and creativity. Provide emotional support when children feel confused or frustrated, and celebrate their efforts and progress. "
    "Adapt your explanations based on the child's responses, and always be patient and encouraging. "
    "If a child doesn't understand, try explaining it in different ways until they do — using real-world examples, Nepali culture, local festivals, or everyday situations. "
    "Write everything in English (Romanized Nepali) — for example, use 'K xa khabar?' instead of writing in Nepali script. "
    "Avoid using Devanagari or any Nepali script. "
    "Include relatable observations, fun facts, games, and mini challenges where possible. Use humor and a light-hearted tone to keep the conversation engaging. "
    "Your goal is to make the child feel supported, heard, and excited to learn — in both academic knowledge and behavioral growth."
  ),
)

chat_session = model.start_chat(history=[])

bot_active = False
current_video = None
video_label = None  # Will hold the video display label

# ---------------------- Utility: local user storage ----------------------
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_user_data(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# ---------------------- Video + text cleaning helpers ----------------------
def update_video(video_path):
    global current_video
    current_video = video_path
    play_video(video_path)

def play_video(video_file_path):
    global current_video, video_label
    try:
        cap = cv2.VideoCapture(video_file_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24

        def update_frame():
            if current_video == video_file_path and video_label:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (800, 450))
                    img = Image.fromarray(frame)
                    img_tk = ImageTk.PhotoImage(image=img)
                    video_label.config(image=img_tk)
                    video_label.image = img_tk
                video_label.after(int(1000 / fps), update_frame)
        update_frame()
    except Exception:
        # silently ignore video issues for now
        pass

def clean_text_for_speech(text):
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002700-\U000027BF"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

# ---------------------- Daily quiz data ----------------------
SAMPLE_QUIZ_QUESTIONS = [
    {"q": "What is 2 + 3?", "choices": ["3", "4", "5", "6"], "answer": "5"},
    {"q": "Capital of Nepal?", "choices": ["Kathmandu", "Lalitpur", "Pokhara", "Biratnagar"], "answer": "Kathmandu"},
    {"q": "Which planet is known as red planet?", "choices": ["Earth", "Mars", "Venus", "Jupiter"], "answer": "Mars"},
    {"q": "What is 7 - 2?", "choices": ["5", "6", "4", "3"], "answer": "5"},
    {"q": "Which is a primary color?", "choices": ["Green", "Purple", "Red", "Black"], "answer": "Red"},
]

# ---------------------- Main App ----------------------
class FullscreenApp:
    def __init__(self, root, user):
        self.root = root
        self.user = user  # dict with name, email, password_hash, level, streak, last_quiz_time
        self.root.title("Study Mode App")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='#F5F7FA')

        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

        self.app_bar = tk.Frame(self.root, bg='#2E7D32', height=50)
        self.app_bar.pack(side=tk.TOP, fill=tk.X)
        self.button_frame = tk.Frame(self.app_bar, bg='#2E7D32')
        self.button_frame.pack(side=tk.RIGHT, padx=10)
        self.close_button = tk.Button(self.button_frame, text="✕", font=("Roboto", 14, "bold"),
                                      bg='#D32F2F', fg='white', bd=0, width=3,
                                      command=self.root.quit, cursor="hand2")
        self.close_button.pack(side=tk.RIGHT)
        self.minimize_button = tk.Button(self.button_frame, text="–", font=("Roboto", 14, "bold"),
                                         bg='#0288D1', fg='white', bd=0, width=3,
                                         command=self.minimize_window, cursor="hand2")
        self.minimize_button.pack(side=tk.RIGHT, padx=5)

        self.top_frame = tk.Frame(self.root, bg='#F5F7FA')
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=10)
        self.guest_label = tk.Label(self.top_frame, text=f"👋 Welcome, {self.user.get('name','Student')}!", font=("Roboto", 16, "bold"),
                                    bg='#E8F5E9', fg='#1B5E20', padx=15, pady=8)
        self.guest_label.pack(side=tk.RIGHT)
        self.streak_label = tk.Label(self.top_frame, text=f"📘 Streak: {self.user.get('streak', 0)}", font=("Roboto", 16, "bold"),
                                     bg='#E3F2FD', fg='#0D47A1', padx=15, pady=8)
        self.streak_label.pack(side=tk.RIGHT, padx=10)

        self.left_frame = tk.Frame(self.root, bg='#263238', width=200)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.left_frame.pack_propagate(False)

        # Add Daily Quiz in menu
        self.menu_data = [
            ("🏠 Dashboard", "#1B5E20"),
            ("📘 My Learning", "#1B5E20"),
            ("🧪 Daily Quiz", "#1B5E20"),
            ("⚙ Settings", "#1B5E20"),
            ("🧠 Level", "#1B5E20"),
            ("🚪 Log Out", "#D32F2F")
        ]
        for label, color in self.menu_data:
            btn = tk.Button(self.left_frame, text=label, font=("Roboto", 16, "bold"),
                            bg='#263238', fg=color, activebackground='#37474F', activeforeground=color,
                            bd=0, anchor='w', padx=20, pady=10, cursor="hand2", relief='flat')
            btn.pack(fill=tk.X, pady=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg='#37474F'))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg='#263238'))
            btn.config(command=lambda x=label: self.option_selected(x))

        self.center_frame = tk.Frame(self.root, bg='#F5F7FA')
        self.center_frame.pack(expand=True, fill=tk.BOTH)
        self.default_content()
    

    # ---------------------- Default / Chat UI (kept similar) ----------------------
    def default_content(self):
        for widget in self.center_frame.winfo_children():
            widget.destroy()

        bottom = tk.Frame(self.center_frame, bg='#F5F7FA')
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=60, pady=20)

        global video_label
        video_frame = tk.Frame(bottom, bg='#F5F7FA', height=300)
        video_frame.pack(fill=tk.X, pady=(0, 10))
        video_label = tk.Label(video_frame, bg="#F5F7FA")
        video_label.pack()

        # try to update with your idle video (if exists)
        try:
            update_video(r"C:\Users\MSI\Desktop\Projects\Yesr\prev\Creating-a-chatbot\captures\merobot.mp4")
        except Exception:
            pass

        response_frame = tk.Frame(bottom, bg='#F5F7FA', height=50)
        response_frame.pack(fill=tk.X)
        response_frame.pack_propagate(False)

        self.response_label = tk.Label(response_frame, text="", font=("Roboto", 14, "italic"),
                                       bg='#F5F7FA', fg='#1A237E', wraplength=700, justify='left')
        self.response_label.pack(fill=tk.BOTH, expand=True)

        self.text_input_frame = tk.Frame(bottom, bg='#FFFFFF', bd=1, relief='flat')
        self.text_input_frame.pack(fill=tk.X, pady=(10,0))

        self.text_input = tk.Text(self.text_input_frame, height=3, font=("Roboto", 16),
                                  bg='#FFFFFF', fg='#212121', insertbackground='#212121', bd=0, relief='flat', wrap=tk.WORD)
        self.text_input.pack(padx=10, pady=10, fill=tk.BOTH)
        self.text_input.insert(tk.END, "💬 Type your question here...")
        self.text_input_frame.configure(highlightbackground='#B0BEC5', highlightthickness=1)
        self.text_input.bind("<Return>", self.handle_input)

    def type_out_response(self, full_text):
        self.response_label.config(text="")
        for i in range(len(full_text)):
            current_text = full_text[:i+1]
            self.response_label.config(text=current_text)
            self.response_label.update_idletasks()
            time.sleep(0.02)

    def handle_input(self, event=None):
        user_message = self.text_input.get("1.0", tk.END).strip()
        if not user_message or user_message == "💬 Type your question here...":
            return "break"

        self.text_input.delete("1.0", tk.END)
        self.response_label.config(text="🤔 Thinking...")
        self.root.update_idletasks()

        def fetch_and_display():
            global bot_active
            try:
                bot_active = True
                update_video(r"C:\Users\MSI\Desktop\Projects\Yesr\prev\Creating-a-chatbot\captures\Chat Bot Show Loading Data.webm")
                response = chat_session.send_message(user_message)
                reply = response.text
                clean_reply = clean_text_for_speech(reply)

                update_video(r"C:\Users\MSI\Desktop\Projects\Yesr\prev\Creating-a-chatbot\captures\Chat Bot Show Process.webm")

                self.response_label.config(text="")
                words = clean_reply.split()

                def type_and_speak():
                    display_text = ""
                    for word in words:
                        display_text += word + " "
                        self.response_label.config(text=display_text)
                        self.response_label.update_idletasks()
                        time.sleep(0.12)
                    threading.Thread(target=text_to_speech, args=(clean_reply,), daemon=True).start()
                    update_video(r"C:\Users\MSI\Desktop\Projects\Yesr\prev\Creating-a-chatbot\captures\merobot.mp4")
                    bot_active = False

                threading.Thread(target=type_and_speak, daemon=True).start()

            except Exception as e:
                self.response_label.config(text=f"❌ Error: {e}")
                bot_active = False

        threading.Thread(target=fetch_and_display, daemon=True).start()
        return "break"

    # ---------------------- Grade / PDF (unchanged) ----------------------
    def show_grade_selection(self):
        for widget in self.center_frame.winfo_children():
            widget.destroy()
        header = tk.Label(self.center_frame, text="📚 Choose Your Grade", font=("Roboto", 22, "bold"), fg="#1B5E20", bg="#F5F7FA", pady=25)
        header.pack()
        grade_frame = tk.Frame(self.center_frame, bg="#F5F7FA")
        grade_frame.pack()
        for i in range(1, 11):
            btn = tk.Button(grade_frame, text=f"Grade {i}", font=("Roboto", 16, "bold"), bg="#4CAF50", fg="white",
                            activebackground="#388E3C", activeforeground="white", relief='flat', bd=0, padx=25, pady=12,
                            cursor="hand2", command=lambda g=i: self.show_pdfs_for_grade(g))
            btn.grid(row=(i-1)//2, column=(i-1)%2, padx=25, pady=15)

    def show_pdfs_for_grade(self, grade_number):
        for widget in self.center_frame.winfo_children():
            widget.destroy()
        pdf_folder = rf"C:\Users\MSI\Desktop\Projects\B\Grade{grade_number}"
        if not os.path.exists(pdf_folder):
            tk.Label(self.center_frame, text="❌ No books found for this grade.", bg="#F5F7FA", font=("Roboto", 14)).pack(pady=20)
            return
        tk.Label(self.center_frame, text=f"📚 Books for Grade {grade_number}", font=("Roboto", 20, "bold"), bg="#F5F7FA", fg="#1B5E20").pack(pady=20)
        files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
        if not files:
            tk.Label(self.center_frame, text="No PDF books available.", bg="#F5F7FA", font=("Roboto", 14)).pack()
            return
        btn_frame = tk.Frame(self.center_frame, bg="#F5F7FA")
        btn_frame.pack()
        for i, pdf_file in enumerate(files):
            btn = tk.Button(btn_frame, text=pdf_file.replace(".pdf", ""), font=("Roboto", 14, "bold"),
                            bg="#81C784", fg="white", activebackground="#66BB6A", cursor="hand2", relief='flat',
                            padx=15, pady=10, command=lambda file=pdf_file: self.display_pdf(os.path.join(pdf_folder, file)))
            btn.grid(row=i//2, column=i%2, padx=15, pady=10)

    def display_pdf(self, file_path):
        for widget in self.center_frame.winfo_children():
            widget.destroy()
        try:
            tk.Label(self.center_frame, text=f"📄 Opening: {os.path.basename(file_path)}", bg="#F5F7FA", fg="#1B5E20", font=("Roboto", 14)).pack(pady=10)
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':
                subprocess.call(['open', file_path])
            else:
                subprocess.call(['xdg-open', file_path])
        except Exception as e:
            tk.Label(self.center_frame, text=f"❌ Failed to open PDF: {e}", bg="#F5F7FA", fg="red", font=("Roboto", 14)).pack(pady=20)

    # ---------------------- Level page (keeps using your LevelFrame) ----------------------
    def show_level_page(self):
        for widget in self.center_frame.winfo_children():
            widget.destroy()
        level_page = LevelFrame(self.center_frame, controller=self)
        level_page.pack(expand=True, fill=tk.BOTH)

    def show_settings_page(self):
    # Clear previous widgets in center_frame
        for widget in self.center_frame.winfo_children():
            widget.destroy()

        user_data = self.user  # or load from file if you want fresh data

        frame = tk.Frame(self.center_frame, bg="#1a1a1a")
        frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        title = tk.Label(frame, text="Settings", font=("Arial", 20, "bold"), fg="white", bg="#1a1a1a")
        title.pack(pady=10)

        # --- Change Password Section ---
        pw_frame = tk.LabelFrame(frame, text="Change Password", font=("Arial", 12, "bold"),
                                fg="white", bg="#1a1a1a", bd=2, relief="groove", padx=10, pady=10)
        pw_frame.pack(pady=10, fill="x")

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
            # Save updated user data (assuming you have self.user and save_user_data function)
            save_user_data(user_data)
            self.user = user_data  # update current user data
            messagebox.showinfo("Success", "Password changed successfully!")

        tk.Button(pw_frame, text="Change Password", command=change_password,
                bg="#ffcc00", fg="black", font=("Arial", 10, "bold")).grid(row=3, columnspan=2, pady=10)

        # --- Rewards Section ---
        reward_frame = tk.LabelFrame(frame, text="Rewards", font=("Arial", 12, "bold"),
                                    fg="white", bg="#1a1a1a", bd=2, relief="groove", padx=10, pady=10)
        reward_frame.pack(pady=10, fill="both", expand=True)

        level = user_data.get("level", 0)
        unlock_levels = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]

        for i in range(10):
            r_frame = tk.Frame(reward_frame, bg="#1a1a1a", bd=1, relief="solid", width=100, height=100)
            r_frame.grid_propagate(False)
            r_frame.grid(row=i // 5, column=i % 5, padx=10, pady=10)

            if level >= unlock_levels[i]:
                if i == 0:
                    try:
                        img = tk.PhotoImage(file=r"C:\Users\MSI\Desktop\Projects\Yesr\prev\Nothing Here\ChatBot\bot.png")
                        img = img.subsample(7, 7)
                        label = tk.Label(r_frame, image=img, bg="#1a1a1a")
                        label.image = img  # keep a reference!
                        label.pack(expand=True)
                    except Exception:
                        tk.Label(r_frame, text="Image Missing", fg="white", bg="#1a1a1a").pack(expand=True)
                else:
                    tk.Label(r_frame, text=f"Reward {i+1}", fg="white", bg="#1a1a1a").pack(expand=True)
            else:
                tk.Label(r_frame, text="🔒", font=("Arial", 20), bg="#1a1a1a").pack()
                tk.Label(r_frame, text=f"Unlock at lvl {unlock_levels[i]}", fg="gray", bg="#1a1a1a").pack()


    # ---------------------- Daily Quiz ----------------------
    def show_daily_quiz(self):
        for widget in self.center_frame.winfo_children():
            widget.destroy()
        frame = tk.Frame(self.center_frame, bg="#F5F7FA")
        frame.pack(expand=True, fill=tk.BOTH, padx=30, pady=20)

        tk.Label(frame, text="🧪 Daily Quiz", font=("Roboto", 22, "bold"), bg="#F5F7FA", fg="#1B5E20").pack(pady=10)

        # countdown label
        countdown_lbl = tk.Label(frame, text="", font=("Roboto", 14), bg="#F5F7FA")
        countdown_lbl.pack(pady=5)

        # quiz question area
        q_frame = tk.Frame(frame, bg="#F5F7FA")
        q_frame.pack(pady=15)

        # choose a random question
        question = random.choice(SAMPLE_QUIZ_QUESTIONS)
        question_lbl = tk.Label(q_frame, text=question["q"], font=("Roboto", 16), bg="#F5F7FA")
        question_lbl.pack(pady=8)

        selected_choice = tk.StringVar(value="")

        choices_frame = tk.Frame(q_frame, bg="#F5F7FA")
        choices_frame.pack()
        for choice in question["choices"]:
            r = tk.Radiobutton(choices_frame, text=choice, variable=selected_choice, value=choice, font=("Roboto", 14), bg="#F5F7FA", anchor="w")
            r.pack(fill="x", padx=10, pady=4)

        result_lbl = tk.Label(q_frame, text="", font=("Roboto", 14), bg="#F5F7FA")
        result_lbl.pack(pady=8)

        def refresh_countdown():
            last = self.user.get("last_quiz_time", 0)
            elapsed = int(time.time()) - int(last)
            remaining = QUIZ_COOLDOWN_SECONDS - elapsed
            if remaining <= 0:
                countdown_lbl.config(text="Next question in: 00:00:00")
                enable_quiz(True)
            else:
                hrs = remaining // 3600
                mins = (remaining % 3600) // 60
                secs = remaining % 60
                countdown_lbl.config(text=f"Next question in: {hrs:02d}:{mins:02d}:{secs:02d}")
                enable_quiz(False)
                # update every second
                self.center_frame.after(1000, refresh_countdown)

        def enable_quiz(allow):
            state = "normal" if allow else "disabled"
            for child in choices_frame.winfo_children():
                try:
                    child.config(state=state)
                except Exception:
                    pass
            submit_btn.config(state=state)
            if not allow:
                result_lbl.config(text="Quiz locked until next question.")
            else:
                result_lbl.config(text="Good luck!")

        def submit_answer():
            choice = selected_choice.get()
            if not choice:
                messagebox.showwarning("Choose", "Please pick an answer.")
                return
            if choice == question["answer"]:
                # correct
                result_lbl.config(text="✅ Correct!")
                # set streak to 1 if it was 0
                if self.user.get("streak", 0) == 0:
                    self.user["streak"] = 1
                # set last_quiz_time to now
                self.user["last_quiz_time"] = int(time.time())
                save_user_data(self.user)
                self.streak_label.config(text=f"📘 Streak: {self.user.get('streak',0)}")
                messagebox.showinfo("Great!", "Correct! Your streak updated.")
                # restart countdown
                refresh_countdown()
            else:
                result_lbl.config(text="❌ Incorrect. Try again!")

        submit_btn = tk.Button(q_frame, text="Submit Answer", font=("Roboto", 14, "bold"),
                               bg="#4CAF50", fg="white", padx=15, pady=8, command=submit_answer)
        submit_btn.pack(pady=10)

        refresh_countdown()

    # ---------------------- Menu handling ----------------------
    def option_selected(self, option_name):
        if "My Learning" in option_name:
            self.show_grade_selection()
        elif "Dashboard" in option_name:
            self.default_content()
        elif "Level" in option_name:
            self.show_level_page()
        elif "Settings" in option_name:
            self.show_settings_page()
        elif "Daily Quiz" in option_name or "🧪" in option_name:
            self.show_daily_quiz()
        elif "Log Out" in option_name or "Log out" in option_name:
            # logout: clear user variable and show login dialog
            self.logout_and_restart()
        else:
            print(f"Selected: {option_name}")

    def logout_and_restart(self):
        # For simplicity, just restart the app: destroy root and call main again.
        self.root.destroy()
        main()  # relaunch app (local restart)

    def minimize_window(self):
        self.root.iconify()

# ---------------------- Authentication UI (local) ----------------------
def show_signup_window(root):
    # returns user dict on success, None otherwise
    top = tk.Toplevel(root)
    top.title("Signup")
    top.geometry("420x420")
    top.grab_set()
    tk.Label(top, text="📝 Sign Up", font=("Roboto", 18, "bold")).pack(pady=10)

    name_var = tk.StringVar()
    email_var = tk.StringVar()
    pass_var = tk.StringVar()
    pass2_var = tk.StringVar()

    tk.Label(top, text="Name").pack(pady=4)
    name_entry = tk.Entry(top, textvariable=name_var)
    name_entry.pack(padx=20, fill="x")

    tk.Label(top, text="Email").pack(pady=4)
    email_entry = tk.Entry(top, textvariable=email_var)
    email_entry.pack(padx=20, fill="x")

    tk.Label(top, text="Password").pack(pady=4)
    pass_entry = tk.Entry(top, textvariable=pass_var, show="*")
    pass_entry.pack(padx=20, fill="x")

    tk.Label(top, text="Confirm Password").pack(pady=4)
    pass2_entry = tk.Entry(top, textvariable=pass2_var, show="*")
    pass2_entry.pack(padx=20, fill="x")

    result_label = tk.Label(top, text="", fg="red")
    result_label.pack(pady=6)

    def do_signup():
        name = name_var.get().strip()
        email = email_var.get().strip()
        p1 = pass_var.get()
        p2 = pass2_var.get()
        if not (name and email and p1 and p2):
            result_label.config(text="Please fill all fields.")
            return
        if p1 != p2:
            result_label.config(text="Passwords do not match.")
            return
        # create user object
        user = {
            "name": name,
            "email": email,
            "password_hash": hash_password(p1),
            "level": 1,
            "streak": 0,
            "last_quiz_time": 0
        }
        save_user_data(user)
        messagebox.showinfo("Signed Up", "Signup complete! You can now login.")
        top.destroy()

    tk.Button(top, text="Sign Up", bg="#4CAF50", fg="white", command=do_signup).pack(pady=12)
    top.wait_window()
    return load_user_data()

def show_login_window(root):
    # returns user dict on success, None otherwise
    top = tk.Toplevel(root)
    top.title("Login")
    top.geometry("360x300")
    top.grab_set()
    tk.Label(top, text="🔐 Login", font=("Roboto", 18, "bold")).pack(pady=10)

    email_var = tk.StringVar()
    pass_var = tk.StringVar()

    tk.Label(top, text="Email").pack(pady=4)
    email_entry = tk.Entry(top, textvariable=email_var)
    email_entry.pack(padx=20, fill="x")

    tk.Label(top, text="Password").pack(pady=4)
    pass_entry = tk.Entry(top, textvariable=pass_var, show="*")
    pass_entry.pack(padx=20, fill="x")

    result_label = tk.Label(top, text="", fg="red")
    result_label.pack(pady=6)

    def do_login():
        data = load_user_data()
        if not data:
            result_label.config(text="No user exists. Please sign up.")
            return
        email = email_var.get().strip()
        p = pass_var.get()
        if not (email and p):
            result_label.config(text="Fill both fields.")
            return
        if email != data.get("email") or hash_password(p) != data.get("password_hash"):
            result_label.config(text="Invalid credentials.")
            return
        # success
        messagebox.showinfo("Welcome", f"Welcome back, {data.get('name')}!")
        top.destroy()

    tk.Button(top, text="Login", bg="#0288D1", fg="white", command=do_login).pack(pady=10)
    tk.Button(top, text="Sign up instead", bg="#EEEEEE", command=lambda: [top.destroy(), show_signup_window(root)]).pack(pady=6)
    top.wait_window()
    return load_user_data()

# ---------------------- App entry point ----------------------
def main():
    # Create a hidden root for auth dialogs first
    root = tk.Tk()
    root.withdraw()  # hide while authenticating

    user = load_user_data()
    if not user:
        # first-run: open signup
        user = show_signup_window(root)
        if not user:
            messagebox.showerror("Signup Failed", "Signup not completed. Exiting.")
            root.destroy()
            return

    # Next show login (if user exists)
    user = show_login_window(root)
    if not user:
        messagebox.showerror("Login Failed", "Login not completed. Exiting.")
        root.destroy()
        return

    # Now start main app with the real root
    root.deiconify()
    root.geometry("1200x800")
    app = FullscreenApp(root, user=user)
    root.mainloop()

if __name__ == "__main__":
    main()
