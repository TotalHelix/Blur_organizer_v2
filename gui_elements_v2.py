import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont


def width_splice(text, font_size):
    """break text after a certain number of pixels in a font"""
    font = ImageFont.truetype("arial.ttf", font_size)
    words = text.split()
    lines = []
    current_line = ""
    current_width = 0
    max_width = 650

    for word in words:
        word_width = font.getlength(word + " ")
        if current_width + word_width <= max_width:
            current_line += word + " "
            current_width += word_width
        else:
            lines.append(current_line.strip())
            current_line = word + " "
            current_width = word_width

    if current_line:
        lines.append(current_line.strip())

    return "\n".join(lines)


class MainWindow:
    # initial setup
    def __init__(self):
        self.window = ctk.CTk()
        self.window.geometry("1000x700")
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        self.window.resizable(False, False)
        self.window.title("Blur Part Organizer")

        # left column
        l_col = ctk.CTkFrame(self.window, fg_color="transparent")
        l_col.grid(row=0, column=0, padx=10, pady=10, sticky="ns")
        side_buttons = {
            "Home": lambda: self.home_frame.tkraise(),
            "Check out": lambda: self.checkout_frame.tkraise(),
            "Check in": lambda: self.checkin_frame.tkraise(),
            "Edit parts": lambda: self.edit_parts.tkraise()
        }
        for button_name, cmd in side_buttons.items():
            button = ctk.CTkButton(l_col, text=button_name, command=cmd)
            button.pack(padx=10, pady=11)

        danger_zone_button = ctk.CTkButton(l_col, fg_color="#d62c20", hover_color="#bd1515", text="Danger Zone", command=lambda: self.danger_zone.tkraise())
        danger_zone_button.place(relx=0.5, rely=.985, anchor="s")

        # workspace
        self.workspace = ctk.CTkFrame(self.window)
        self.workspace.grid(row=0, column=1, padx=10, pady=10, sticky="news")
        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(0, weight=1)

        #####################
        # different frames
        #####################

        ###################
        # checkin
        ###################
        self.checkin_frame = ctk.CTkFrame(self.workspace)
        self.checkin_frame.grid(row=0, column=0, sticky="news")

        # margin
        ctk.CTkLabel(self.checkin_frame, text=" ", font=("Ariel", 1)).pack()

        # Title Label
        title_label = ctk.CTkLabel(self.checkin_frame, text="Scan barcode", font=ctk.CTkFont(size=30, weight="bold"))
        title_label.pack(pady=10)

        # Explanation Text
        explanation_text = ctk.CTkLabel(self.checkin_frame, text="Please scan a barcode or manually enter the digits below:", font=("Ariel", 18))
        explanation_text.pack(pady=10)

        # Validation function to allow only digits
        def validate_input(new_value):
            # Check if the new value contains only digits and is not longer than 12 characters
            if new_value.isdigit() and len(new_value) <= 12:
                return True
            elif new_value == "":
                # Allow empty entry (optional, if you want to allow clearing the entry box)
                return True
            else:
                return False
        
        # Register the validation function
        validate_command = self.checkin_frame.register(validate_input)

        # Frame for Entry Field and Button
        input_frame = ctk.CTkFrame(self.checkin_frame)
        input_frame.pack(pady=10, padx=40, fill="x")

        # Entry Field for Barcode Scanning or Manual Input
        barcode_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Scan barcode or enter digits here",
            validate="key",
            validatecommand=(validate_command, '%P')
        )
        barcode_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Go Button
        go_button = ctk.CTkButton(input_frame, text="Go", command=lambda: print("Input:", barcode_entry.get()))
        go_button.pack(side="left")

        ###################
        # checkout
        ###################
        self.checkout_frame = ctk.CTkFrame(self.workspace, fg_color="blue")
        self.checkout_frame.grid(row=0, column=0, sticky="news")

        ###################
        # danger zone
        ###################
        self.danger_zone = ctk.CTkFrame(self.workspace, fg_color="red")
        self.danger_zone.grid(row=0, column=0, sticky="news")

        ###################
        # Edit parts
        ###################
        self.edit_parts = ctk.CTkFrame(self.workspace, fg_color="green")
        self.edit_parts.grid(row=0, column=0, sticky="news")

        ###################
        # home
        ###################
        self.home_frame = ctk.CTkFrame(self.workspace)
        self.home_frame.grid(row=0, column=0, sticky="news")

        # margin
        ctk.CTkLabel(self.home_frame, text=" ", font=("Ariel", 1)).pack()

        # include the readme
        with open("README.md", "r") as readme:
            for line in readme.readlines():

                # skip blank lines
                if not line or line.isspace():
                    continue

                # format titles [start pos, font size]
                info = [0, 14]
                if line.startswith('# '):
                    info = [2, 30]
                elif line.startswith('## '):
                    info = [3, 24]
                elif line.startswith('### '):
                    info = [4, 18]

                # remove junk
                label_text = width_splice(line[info[0]:].strip(), info[1])

                label = ctk.CTkLabel(self.home_frame, text=label_text, font=("Arial", info[1], "bold"), justify="left")
                label.pack(pady=10, padx=40, anchor="w")

        self.home_frame.tkraise()  # put the home on the top by default
