import tkinter as tk
import os
import sys
import platform
import subprocess
import re
import google.generativeai as genai
from dotenv import load_dotenv
from main import text_to_speech  # Your TTS function
import threading
import time
from PIL import Image, ImageTk
import cv2
from level import LevelFrame

bot_active = False
current_video = None
video_label = None  # Will hold the video display label

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
def update_video(video_path):
    global current_video
    current_video = video_path
    play_video(video_path)

def play_video(video_file_path):
    global current_video
    cap = cv2.VideoCapture(video_file_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    def update_frame():
        if current_video == video_file_path:
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

def clean_text_for_speech(text):
    # Remove emojis and special characters using regex
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002700-\U000027BF"  # Dingbats
        u"\U000024C2-\U0001F251"  # Enclosed characters
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)


class FullscreenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Study Mode App")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='#F5F7FA')

        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        
        # App bar and sidebar etc (keep as you had it)
        self.app_bar = tk.Frame(self.root, bg='#2E7D32', height=50)
        self.app_bar.pack(side=tk.TOP, fill=tk.X)
        self.button_frame = tk.Frame(self.app_bar, bg='#2E7D32')
        self.button_frame.pack(side=tk.RIGHT, padx=10)
        self.close_button = tk.Button(self.button_frame, text="✕", font=("Roboto", 14, "bold"),
                                      bg='#D32F2F', fg='white', bd=0, width=3,
                                      command=self.root.quit, cursor="hand2")
        self.close_button.pack(side=tk.RIGHT)
        self.close_button.bind('<Enter>', lambda e: self.close_button.config(bg='#B71C1C'))
        self.close_button.bind('<Leave>', lambda e: self.close_button.config(bg='#D32F2F'))
        self.minimize_button = tk.Button(self.button_frame, text="–", font=("Roboto", 14, "bold"),
                                         bg='#0288D1', fg='white', bd=0, width=3,
                                         command=self.minimize_window, cursor="hand2")
        self.minimize_button.pack(side=tk.RIGHT, padx=5)
        self.minimize_button.bind('<Enter>', lambda e: self.minimize_button.config(bg='#0277BD'))
        self.minimize_button.bind('<Leave>', lambda e: self.minimize_button.config(bg='#0288D1'))
        self.top_frame = tk.Frame(self.root, bg='#F5F7FA')
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=10)
        self.guest_label = tk.Label(self.top_frame, text="👋 Welcome, Student!", font=("Roboto", 16, "bold"),
                                    bg='#E8F5E9', fg='#1B5E20', padx=15, pady=8,
                                    relief='flat', bd=0, highlightthickness=1, highlightbackground='#A5D6A7')
        self.guest_label.pack(side=tk.RIGHT)
        self.streak_label = tk.Label(self.top_frame, text="📘 Streak: 5", font=("Roboto", 16, "bold"),
                                     bg='#E3F2FD', fg='#0D47A1', padx=15, pady=8,
                                     relief='flat', bd=0, highlightthickness=1, highlightbackground='#90CAF9')
        self.streak_label.pack(side=tk.RIGHT, padx=10)
        self.left_frame = tk.Frame(self.root, bg='#263238', width=200)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.left_frame.pack_propagate(False)
        self.menu_data = [
            ("🏠 Dashboard", "#1B5E20"),
            ("📘 My Learning", "#1B5E20"),
            ("⚙ Settings", "#1B5E20"),
            ("🧠 Tips & Tricks", "#1B5E20"),
            ("🚪 Log Out", "#D32F2F")
        ]
        for label, color in self.menu_data:
            btn = tk.Button(self.left_frame, text=label, font=("Roboto", 16, "bold"),
                            bg='#263238', fg=color,
                            activebackground='#37474F', activeforeground=color,
                            bd=0, anchor='w', padx=20, pady=10,
                            cursor="hand2", relief='flat')
            btn.pack(fill=tk.X, pady=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg='#37474F'))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg='#263238'))
            btn.config(command=lambda x=label: self.option_selected(x))
        self.center_frame = tk.Frame(self.root, bg='#F5F7FA')
        self.center_frame.pack(expand=True, fill=tk.BOTH)
        self.default_content()

    def default_content(self):
        for widget in self.center_frame.winfo_children():
            widget.destroy()

        # Container frame to hold response + input and keep them at bottom
        self.bottom_container = tk.Frame(self.center_frame, bg='#F5F7FA')
        self.bottom_container.pack(side=tk.BOTTOM, fill=tk.X, padx=60, pady=20)

        global video_label
        video_frame = tk.Frame(self.bottom_container, bg='#F5F7FA', height=300)
        video_frame.pack(fill=tk.X, pady=(0, 10))
        video_label = tk.Label(video_frame, bg="#F5F7FA")
        video_label.pack()

        update_video(r"C:\Users\MSI\Desktop\Projects\Yesr\prev\Creating-a-chatbot\captures\merobot.mp4")

        # Response frame (2 lines height)
        self.response_frame = tk.Frame(self.bottom_container, bg='#F5F7FA', height=50)
        self.response_frame.pack(fill=tk.X)
        self.response_frame.pack_propagate(False)

        self.response_label = tk.Label(
            self.response_frame,
            text="",  # empty at start
            font=("Roboto", 14, "italic"),
            bg='#F5F7FA',
            fg='#1A237E',
            wraplength=700,
            justify='left'
        )
        self.response_label.pack(fill=tk.BOTH, expand=True)

        # Text input frame just below response frame
        self.text_input_frame = tk.Frame(self.bottom_container, bg='#FFFFFF', bd=1, relief='flat')
        self.text_input_frame.pack(fill=tk.X, pady=(10,0))

        self.text_input = tk.Text(
            self.text_input_frame, height=3, font=("Roboto", 16),
            bg='#FFFFFF', fg='#212121', insertbackground='#212121',
            bd=0, relief='flat', wrap=tk.WORD
        )
        self.text_input.pack(padx=10, pady=10, fill=tk.BOTH)
        self.text_input.insert(tk.END, "💬 Type your question here...")
        self.text_input_frame.configure(highlightbackground='#B0BEC5', highlightthickness=1)

        self.text_input.bind("<Return>", self.handle_input)



    
    def type_out_response(self, full_text):
        self.response_label.config(text="")  # clear first
        for i in range(len(full_text)):
            current_text = full_text[:i+1]
            self.response_label.config(text=current_text)
            self.response_label.update_idletasks()
            time.sleep(0.02)  # delay between chars

    def handle_input(self, event=None):
        user_message = self.text_input.get("1.0", tk.END).strip()
        if not user_message or user_message == "💬 Type your question here...":
            return "break"  # ignore empty or placeholder

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

                # Start typing and speaking together
                self.response_label.config(text="")  # Clear
                words = clean_reply.split()
                

                def type_and_speak():
                    display_text = ""
                    for word in words:
                        display_text += word + " "
                        self.response_label.config(text=display_text)
                        self.response_label.update_idletasks()
                        time.sleep(0.3)  # Faster type effect
                        threading.Thread(target=text_to_speech, args=(clean_reply,), daemon=True).start()
                    # Speak the full cleaned text after typing is done
                    


                    # After response done, revert to idle video
                    update_video(r"C:\Users\MSI\Desktop\Projects\Yesr\prev\Creating-a-chatbot\captures\merobot.mp4")
                    bot_active = False


                threading.Thread(target=type_and_speak, daemon=True).start()

            except Exception as e:
                self.response_label.config(text=f"❌ Error: {e}")
                update_video(r"C:\Users\LEGION\Desktop\Creating-a-chatbot\captures\merobot.mp4")
                bot_active = False


        threading.Thread(target=fetch_and_display, daemon=True).start()

        return "break"



    def show_grade_selection(self):
        for widget in self.center_frame.winfo_children():
            widget.destroy()

        header = tk.Label(
            self.center_frame,
            text="📚 Choose Your Grade",
            font=("Roboto", 22, "bold"),
            fg="#1B5E20",
            bg="#F5F7FA",
            pady=25
        )
        header.pack()

        grade_frame = tk.Frame(self.center_frame, bg="#F5F7FA")
        grade_frame.pack()

        for i in range(1, 11):
            btn = tk.Button(
                grade_frame,
                text=f"Grade {i}",
                font=("Roboto", 16, "bold"),
                bg="#4CAF50",
                fg="white",
                activebackground="#388E3C",
                activeforeground="white",
                relief='flat',
                bd=0,
                padx=25,
                pady=12,
                cursor="hand2",
                command=lambda g=i: self.show_pdfs_for_grade(g)
            )
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
            btn = tk.Button(
                btn_frame,
                text=pdf_file.replace(".pdf", ""),
                font=("Roboto", 14, "bold"),
                bg="#81C784", fg="white",
                activebackground="#66BB6A",
                cursor="hand2",
                relief='flat',
                padx=15, pady=10,
                command=lambda file=pdf_file: self.display_pdf(os.path.join(pdf_folder, file))
            )
            btn.grid(row=i//2, column=i%2, padx=15, pady=10)

    def display_pdf(self, file_path):
        for widget in self.center_frame.winfo_children():
            widget.destroy()

        try:
            # Show info in UI
            tk.Label(
                self.center_frame,
                text=f"📄 Opening: {os.path.basename(file_path)}",
                bg="#F5F7FA",
                fg="#1B5E20",
                font=("Roboto", 14)
            ).pack(pady=10)

            # Open PDF with system viewer
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', file_path])

        except Exception as e:
            tk.Label(
                self.center_frame,
                text=f"❌ Failed to open PDF: {e}",
                bg="#F5F7FA",
                fg="red",
                font=("Roboto", 14)
            ).pack(pady=20)

    def _on_mousewheel(self, event):
        # Note: This method references a non-existent scroll_canvas
        pass  # Temporarily disabled to avoid errors

    def show_level_page(self):
        for widget in self.center_frame.winfo_children():
            widget.destroy()
        level_page = LevelFrame(self.center_frame, controller=self)
        level_page.pack(expand=True, fill=tk.BOTH)


    def option_selected(self, option_name):
        if "My Learning" in option_name:
            self.show_grade_selection()
        elif "Dashboard" in option_name:
            self.default_content()
        elif "Tips & Tricks" in option_name:
            self.show_level_page()
        else:
            print(f"Selected: {option_name}")

    def minimize_window(self):
        self.root.iconify()

def main():
    root = tk.Tk()
    app = FullscreenApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()