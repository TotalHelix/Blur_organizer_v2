import customtkinter as ctk
from PIL import ImageFont
import db_interactions


# Validation function to allow only digits
def validate_input(new_value):
    """Check if the new value contains only digits and is not longer than 12 characters"""
    if new_value.isdigit() and len(new_value) <= 12:
        return True
    elif new_value == "":
        # Allow empty entry
        return True
    else:
        return False

def margin(master):
    """a margin that you should add to the top of each frame"""
    ctk.CTkLabel(master, text=" ", font=("Ariel", 1)).pack()

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


def stackable_frame(master, title, desc, button_text):
    """A stackable frame that has a title and description on the left, and a button on the right"""
    frame_house = ctk.CTkFrame(master, height=80)
    frame_house.pack(fill="x", padx=40, pady=7)

    frame_house.grid_columnconfigure(0, weight=5)
    frame_house.grid_columnconfigure(1, weight=1)
    frame_house.grid_rowconfigure(0, weight=1)
    frame_house.grid_rowconfigure(1, weight=1)

    # title
    ctk.CTkLabel(frame_house, text=title, font=("Ariel", 18, "bold"), anchor="sw").grid(column=0, row=0, sticky="w", padx=15, pady=5)

    # description
    ctk.CTkLabel(frame_house, text=desc, font=("Ariel", 16), anchor="nw").grid(column=0, row=1, sticky="w", padx=15, pady=5)

    # button
    ctk.CTkButton(frame_house, text=button_text, fg_color="#d62c20", hover_color="#781610").grid(column=1, row=0, rowspan=2, padx=8)


class MainWindow:
    """The whole window that does all of everything"""
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

        danger_zone_button = ctk.CTkButton(l_col, fg_color="#d62c20", hover_color="#781610", text="Danger Zone", command=lambda: self.danger_zone.tkraise())
        danger_zone_button.pack(side=ctk.BOTTOM, padx=10, pady=11)

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

        margin(self.checkin_frame)

        # Title Label
        title_label = ctk.CTkLabel(self.checkin_frame, text="Return a part", font=ctk.CTkFont(size=30, weight="bold"))
        title_label.pack(pady=10)

        # Explanation Text
        explanation_text = ctk.CTkLabel(self.checkin_frame, text="Please scan a barcode or manually enter digits of the part you would like to return:", font=("Ariel", 18))
        explanation_text.pack(pady=10)

        # Register the validation function
        validate_command = self.checkin_frame.register(validate_input)

        # Frame for Entry Field and Button
        input_frame = ctk.CTkFrame(self.checkin_frame)
        input_frame.pack(pady=10, padx=40, fill="x")

        # Entry Field for Barcode Scanning or Manual Input
        self.checkin_barcode = ctk.CTkEntry(
            input_frame,
            placeholder_text="Scan barcode or enter digits here",
            validate="key",
            validatecommand=(validate_command, '%P')
        )
        self.checkin_barcode.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.checkin_barcode.bind("<Return>", self.checkin_continue)

        # Go Button
        go_button = ctk.CTkButton(input_frame, text="Go", command=self.checkin_continue)
        go_button.pack(side="left")

        ###################
        # checkout
        ###################
        self.checkout_frame = ctk.CTkFrame(self.workspace, fg_color="blue")
        self.checkout_frame.grid(row=0, column=0, sticky="news")

        ###################
        # danger zone
        ###################
        self.danger_zone = ctk.CTkFrame(self.workspace)
        self.danger_zone.grid(row=0, column=0, sticky="news")

        margin(self.danger_zone)

        data = [  # Title, Description, Button text
            ("Format Database", "resets the database with all default tables", "Format"),
            ("Populate Database", "fills the database up with random data. Useful for testing", "Populate")
        ]

        for title, desc, btxt in data:
            stackable_frame(self.danger_zone, title, desc, btxt)

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

        margin(self.home_frame)

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

    def checkin_continue(self, *_):
        print(self.checkin_barcode.get())
