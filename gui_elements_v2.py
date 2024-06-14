import customtkinter as ctk
from PIL import ImageFont
from db_interactions import Organizer
from psycopg2 import OperationalError as OError

# theme stuff
ctk.set_appearance_mode("dark")
red = "#d62c20"
green = "#32a852"
hover_red = "#781610"


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


def stackable_frame(master, title, desc, button_text, command):
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
    ctk.CTkButton(frame_house, text=button_text, fg_color=red, hover_color=hover_red, command=command).grid(column=1, row=0, rowspan=2, padx=8)


class MainWindow:
    """The whole window that does all of everything"""
    def __init__(self):
        # initial setup
        self.window = ctk.CTk()
        self.window.geometry("1000x700")
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        self.window.resizable(False, False)
        self.window.title("Blur Part Organizer")

        # for interactions with the database
        self.controller = None
        self.postgres_exists = False
        self.connection = False
        try:
            with Organizer("postgres") as postgres:
                # we were able to access postgres
                self.postgres_exists = True

                # see if the customer role does not exist
                if not postgres.customer_exists():
                    # create a customer role
                    postgres.new_user()
                    postgres.conn.commit()

            # now we should be able to connect as a customer with no problem
            self.controller = Organizer("customer")

            self.connection = True
        except OError as errormsg:
            print(errormsg)
            self.connection = False

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

        danger_zone_button = ctk.CTkButton(l_col, fg_color=red, hover_color=hover_red, text="Danger Zone", command=lambda: self.danger_zone.tkraise())
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

        data = [  # Title, Description, Button text, command
            ("Format Database", "resets the database with all default tables", "Format", self.format_database),
            ("Populate Database", "fills the database up with random data. Useful for testing", "Populate", self.populate_database)
        ]

        for args in data:
            stackable_frame(self.danger_zone, *args)

        ###################
        # Edit parts
        ###################
        self.edit_parts = ctk.CTkFrame(self.workspace, fg_color="green")
        self.edit_parts.grid(row=0, column=0, sticky="news")

        #######################
        # error message popup
        #######################
        padx = 7
        pady = 7
        self.popup_pos = {"x": padx, "y": pady}

        # make the popup
        self.popup = ctk.CTkFrame(self.workspace, width=self.workspace.winfo_width() - 2*padx, height=70, fg_color=red)
        self.popup.grid_propagate(False)  # prevent the frame from shrinking to fit the text
        self.popup.grid_columnconfigure(0, weight=9)
        self.popup.grid_columnconfigure(1, weight=1)
        self.popup.grid_rowconfigure(0, weight=1)
        self.popup.grid_rowconfigure(1, weight=1)

        # title and body text
        self.popup_title = ctk.CTkLabel(self.popup, text="Something went wrong!", font=("Arial", 19, "bold"), anchor="sw")
        self.popup_text = ctk.CTkLabel(self.popup, text="error text", font=("Arial", 17), anchor="nw", justify="left")
        self.popup_title.grid(column=0, row=0, sticky="news", padx=40)
        self.popup_text.grid(column=0, row=1, sticky="news", padx=40)

        # x button
        x_button = ctk.CTkButton(self.popup, text="✕", font=("Arial", 20), width=30, height=30, fg_color="transparent", hover=False, anchor="ne", command=self.popup.place_forget)
        x_button.grid(column=1, row=0)

        ###################
        # home
        ###################
        self.home_frame = ctk.CTkFrame(self.workspace)
        self.home_frame.grid(row=0, column=0, sticky="news")

        margin(self.home_frame)

        # include the readme (still part of home)
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

    def popup_msg(self, error_text, popup_type="error"):
        # draw
        error_text = width_splice(error_text, 17)
        new_width = self.workspace.winfo_width() - 2*self.popup_pos["x"]
        stretch_height = 70 + 18*error_text.count("\n")
        title_text, color = {"error": ("Something went wrong!", red), "success": ("Success!", green)}[popup_type]

        self.popup_title.configure(text=title_text)
        self.popup.configure(width=new_width, height=stretch_height, fg_color=color)
        self.popup_text.configure(text=error_text)
        self.popup.place(**self.popup_pos)
        self.popup.tkraise()

        if popup_type == "success":
            self.window.after(2000, self.popup.place_forget)

    def check_db_connection(self, accept_postgres=False):
        if self.connection:
            return True
        elif self.postgres_exists:
            if accept_postgres:
                return True
            else:
                self.popup_msg("We were able to connect to postgres, but not the parts database. Try reformatting under 'Danger Zone'.")
                return False
        else:
            # can't connect to a database
            self.popup_msg("We couldn't find a database to connect to. Make sure that postgreSQL is installed.")
            return False

    def format_database(self):
        # make sure that we are able to connect to the database
        if not self.check_db_connection(accept_postgres=True): return

        # try to format the database as postgres
        try:
            with Organizer("postgres") as postgres:
                postgres.format_database()
            self.popup_msg("Database formatted successfully", "success")
        except Exception as error:
            self.popup_msg(error)

    def populate_database(self):
        # make sure that we are able to connect to the database
        if not self.check_db_connection(accept_postgres=True): return

        # try to format the database as postgres
        try:
            with Organizer("postgres") as postgres:
                postgres.populate_db()
            self.popup_msg("Database populated successfully", "success")
        except Exception as error:
            self.popup_msg(error)

    def checkin_continue(self, *_):
        # check for database connection
        if not self.check_db_connection(): return

        print(self.checkin_barcode.get())
