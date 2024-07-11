import tkinter as tk
import customtkinter as ctk
from PIL import ImageFont
from db_interactions import Organizer
import psycopg2.errors as p2er
import re

# theme stuff
ctk.set_appearance_mode("dark")
red = "#d62c20"
green = "#32a852"
color_red = {"fg_color": red, "hover_color": "#781610"}
color_green = {"fg_color": green, "hover_color": "#0f4f22"}


def _int(string):
    """turns a string into an int if the string can become an int"""
    if string.isnumeric():
        return int(string)
    else:
        return string


def make_box(itf, v, tall=False):
    """generates a box frame for displaying output text when a list button is selected"""
    textbox_height = 60 if tall else 20
    value_box = ctk.CTkTextbox(itf, height=textbox_height)
    value_box.insert("0.0", v)
    value_box.configure(state="disabled")
    value_box.pack(side="right", padx=10, pady=7)


def validate_upc(new_value):
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


def width_splice(text, font_size, max_width=650):
    """break text after a certain number of pixels in a font"""

    # just skip if there's not any text
    if text.isspace():
        return " "

    font = ImageFont.truetype("arial.ttf", font_size)
    words = text.split(" ")
    lines = []
    current_line = ""
    current_width = 0

    for word in words:
        if "\n" in word:
            current_width = 0

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


def textbox_write(textbox, text):
    textbox.configure(state="normal")
    textbox.delete("0.0", "end")
    textbox.insert("0.0", text)
    textbox.configure(state="disabled")


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
    ctk.CTkButton(frame_house, text=button_text, **color_red, command=command).grid(column=1, row=0, rowspan=2, padx=8)


def max_length_validate(text, length):
    """max length for input validation"""
    if text == "": return True
    if length == "int": return text.isdigit()
    if length == 0: return True
    return len(text) <= length


def handle_exceptions(func):
    """wrapper for error handling, relies on self.popup_msg so only use in MainWindow."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as er:

            args[0].popup_msg(str(er))
            raise er
    return wrapper


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
        self.popup_counter = 0
        self.form_mode_add = True
        self.search_mode = "part"
        self.selected_part_key = ""
        self.checkout_upc = ""
        self.output_frames = []
        self.prompt_response = None

        # for interactions with the database
        self.controller = None
        self.postgres_exists = False
        self.connection = False
        try:
            with Organizer("postgres") as _:
                # we were able to access postgres
                self.postgres_exists = True

            # now we should be able to connect as a customer with no problem
            self.controller = Organizer("customer")

            self.connection = True
        except p2er.OperationalError as error_msg:
            print(error_msg)
            self.connection = False

        # left column
        l_col = ctk.CTkFrame(self.window, fg_color="transparent")
        l_col.grid(row=0, column=0, padx=10, pady=10, sticky="ns")
        side_buttons = {
            # these have to be lambda again because the frames haven't been defined yet.
            "Home": lambda: self.home_frame.tkraise(),
            "Check Out": lambda: self.checkout_frame.tkraise(),
            "Check In": lambda: self.checkin_frame.tkraise(),
            "Part Search": lambda: self.raise_search("part"),
            "User Search": lambda: self.raise_search("user")
        }
        for button_name, cmd in side_buttons.items():
            button = ctk.CTkButton(l_col, text=button_name, command=cmd)
            button.pack(padx=10, pady=11)

        danger_zone_button = ctk.CTkButton(l_col, **color_red, text="Danger Zone", command=lambda: self.danger_zone.tkraise())
        danger_zone_button.pack(side=ctk.BOTTOM, padx=10, pady=11)

        # workspace
        self.workspace = ctk.CTkFrame(self.window)
        self.workspace.grid(row=0, column=1, padx=10, pady=10, sticky="news")
        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(0, weight=1)

        ##########################################
        # different frames
        ##########################################

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
        validate_command = self.checkin_frame.register(validate_upc)

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
        checkin_finalize = ctk.CTkButton(input_frame, text="Go", command=self.checkin_continue)
        checkin_finalize.pack(side="left")

        ###################
        # checkout
        ###################
        self.checkout_frame = ctk.CTkFrame(self.workspace)
        self.checkout_frame.grid(row=0, column=0, sticky="news")

        margin(self.checkout_frame)

        # Title Label
        title_label = ctk.CTkLabel(self.checkout_frame, text="Check out a part", font=ctk.CTkFont(size=30, weight="bold"))
        title_label.pack(pady=10)

        # Explanation Text
        explanation_text = ctk.CTkLabel(self.checkout_frame, text="Please scan a barcode or manually enter UPC of the part you would like to check out:", font=("Ariel", 18))
        explanation_text.pack(pady=10)

        # Register the validation function
        validate_command = self.checkout_frame.register(validate_upc)

        # Frame for Entry Field and Button
        input_frame = ctk.CTkFrame(self.checkout_frame)
        input_frame.pack(pady=10, padx=40, fill="x")

        # Entry Field for Barcode Scanning or Manual Input
        self.checkout_barcode = ctk.CTkEntry(
            input_frame,
            placeholder_text="Scan barcode or enter digits here",
            validate="key",
            validatecommand=(validate_command, '%P')
        )
        self.checkout_barcode.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.checkout_barcode.bind("<Return>", self.checkout_continue)

        # Go Button
        checkout_continue = ctk.CTkButton(input_frame, text="Continue", command=self.checkout_continue)
        checkout_continue.pack(side="left")

        #################
        # checkout continue (user select)
        #################
        self.checkout_user_frame = ctk.CTkFrame(self.workspace)
        self.checkout_user_frame.grid(row=0, column=0, sticky="news")

        margin(self.checkout_user_frame)

        # explainer text
        ctk.CTkLabel(self.checkout_user_frame, text="Please select your account", font=("Ariel", 16)).pack(pady=10)

        # frame for the search box and dropdown
        long_frame = ctk.CTkFrame(self.checkout_user_frame, fg_color="transparent")
        long_frame.pack(pady=15)

        # search box in the user select frame
        self.reverse_users = {}
        self.checkout_user_search = ctk.CTkEntry(long_frame, placeholder_text="Search", width=200)
        self.checkout_user_search.pack(side="left")
        self.checkout_user_search.bind("<Key>", self.update_user_select_options)

        # dropdown of users to pick from
        self.checkout_selected_user = tk.StringVar(value=" ")
        self.checkout_user_dropdown = ctk.CTkOptionMenu(long_frame, values=[" "], variable=self.checkout_selected_user)
        self.checkout_user_dropdown.pack(side="left")

        # check out button (not a trick like the 'go' button)
        self.checkout_finalize_button = ctk.CTkButton(self.checkout_user_frame, text="Check Out", command=self.checkout_finalize)
        self.checkout_finalize_button.pack()

        # prompt for force checkout
        self.force_prompt = ctk.CTkFrame(self.checkout_user_frame)
        self.prompt_text = ctk.CTkLabel(self.force_prompt, text="This part is already checked out by None. checkout anyways?")
        self.prompt_text.pack(pady=5, padx=7)
        buttons_frame = ctk.CTkFrame(self.force_prompt, fg_color="transparent")
        buttons_frame.pack(pady=10)
        ctk.CTkButton(buttons_frame, text="Yes", **color_green, command=lambda: self.checkout_finalize(force=True)).pack(side="left", padx=8)
        ctk.CTkButton(buttons_frame, text="Cancel", **color_red, command=self.checkout_frame.tkraise).pack(side="left", padx=8)

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
        # search gui
        ###################
        self.find_part = ctk.CTkFrame(self.workspace)
        self.find_part.grid(row=0, column=0, sticky="news")
        self.find_part.columnconfigure(0, weight=1, minsize=300)
        self.find_part.columnconfigure(1, weight=2, minsize=400)
        self.find_part.rowconfigure(0, weight=0)
        self.find_part.rowconfigure(1, weight=1)
        self.find_part.rowconfigure(2, weight=0)

        # left side (search, results, add button)
        self.search_box = ctk.CTkEntry(self.find_part, placeholder_text="Search for a part", width=200)
        self.search_box.grid(row=0, column=0, sticky="nsew", padx=40, pady=20)
        self.search_box.bind("<KeyRelease>", self.update_search)

        self.result_parts = ctk.CTkScrollableFrame(self.find_part, width=200)
        self.result_parts.grid(row=1, column=0, sticky="nsew", padx=40, pady=0)
        self.part_widgets = []
        self.selected_part = None

        # buttons that run along the bottom
        thin_frame = ctk.CTkFrame(self.find_part, fg_color="transparent")
        thin_frame.grid(column=0, row=2, columnspan=2, padx=40, pady=10, sticky="ew")

        button_form = {"master": thin_frame, "width": 100, "height": 32}
        button_pack = {"side": "left", "padx": 10}
        #                                                                       has to ba lambda bc the new part form doesn't exist yet
        ctk.CTkButton(**button_form, text="+ Add", command=self.add_part).pack(**button_pack)
        ctk.CTkButton(**button_form, text="️🗑 Delete", command=self.remove_part).pack(**button_pack)
        ctk.CTkButton(**button_form, text="🖉 Edit", command=self.edit_part_form).pack(**button_pack)
        # ctk.CTkButton(**button_form, text="🖨 Print", command=lambda: self.controller.upc_create(self.selected_part_key)).pack(**button_pack)

        # right side (display part info)
        part_info_display_frame = ctk.CTkFrame(self.find_part, fg_color="transparent", width=350)
        part_info_display_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")

        self.part_generic_info = ctk.CTkFrame(part_info_display_frame, fg_color="transparent")
        self.part_generic_info.pack(padx=0, pady=20, anchor="n", expand=True, fill="x")

        #######################
        # add new part form
        #######################
        part_questions = {
            "Manufacturer": 255,
            "Manufacturer's part number": 255,
            "Placement location": 4,
            "Description": 0,
            "Quantity": "int"
        }

        user_questions = {
            "First name": 50,
            "Last name": 50,
            "Email": 255
        }

        self.add_part_entries = {}
        self.add_user_entries = {}
        self.new_part_form = self.make_new_form(part_questions, self.add_part_entries)
        self.new_user_form = self.make_new_form(user_questions, self.add_user_entries)

        #######################
        # error message popup
        #######################
        padx = 7
        pady = 7
        self.popup_pos = {"x": padx, "y": pady}

        # make the popup
        self.popup_window = ctk.CTkFrame(self.workspace, width=self.workspace.winfo_width() - 2 * padx, height=70, fg_color=red)
        self.popup_window.grid_propagate(False)  # prevent the frame from shrinking to fit the text
        self.popup_window.grid_columnconfigure(0, weight=9)
        self.popup_window.grid_columnconfigure(1, weight=1)
        self.popup_window.grid_rowconfigure(0, weight=1)
        self.popup_window.grid_rowconfigure(1, weight=1)

        # title and body text
        self.popup_title = ctk.CTkLabel(self.popup_window, text="Something went wrong!", font=("Arial", 19, "bold"), anchor="sw")
        self.popup_text = ctk.CTkLabel(self.popup_window, text="error text", font=("Arial", 17), anchor="nw", justify="left")
        self.popup_title.grid(column=0, row=0, sticky="news", padx=40)
        self.popup_text.grid(column=0, row=1, sticky="news", padx=40)

        # x button
        x_button = ctk.CTkButton(self.popup_window, text="✕", font=("Arial", 20), width=30, height=30, fg_color="transparent", hover=False, anchor="ne", command=self.popup_window.place_forget)
        x_button.grid(column=1, row=0)

        ###################
        # home
        ###################
        self.home_frame = ctk.CTkFrame(self.workspace)
        self.home_frame.grid(row=0, column=0, sticky="news")

        margin(self.home_frame)

        # include the readme (still part of home)
        with open("README.md", "r") as readme:
            document = "\n".join([s.rstrip() for s in readme.readlines()]).split("\n"*2)

            for line in document:
                line = line.replace("\n", " ")

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
                label_text = line[info[0]:]  # .strip()

                paragraph_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
                paragraph_frame.pack(pady=10, anchor="w")

                for label_line in width_splice(label_text, info[1]).split("\n"):
                    # inline/quotebox formatting
                    # Split the line based on backticks
                    segments = re.split(r'(`[^`]+`)', label_line)
                    line_frame = ctk.CTkFrame(paragraph_frame, fg_color="transparent")
                    line_frame.pack(padx=40, anchor="w")

                    for segment in segments:
                        if segment.startswith('`') and segment.endswith('`'):
                            # Remove backticks and format as a quote box
                            formatted_text = segment[1:-1]
                            label = ctk.CTkLabel(line_frame, text=width_splice(formatted_text, info[1]),
                                                 fg_color="#414243", corner_radius=5, font=("cascadia mono", info[1]))
                        else:
                            # Normal text
                            label = ctk.CTkLabel(line_frame, text=width_splice(segment, info[1]),
                                                 font=("Arial", info[1]))

                        label.pack(side="left", padx=2)

    @handle_exceptions
    def set_response(self, popup, response):
        """sets self.prompt_response to response and deletes the popup window"""
        self.prompt_response = response
        popup.destroy()

    @handle_exceptions
    def popup_prompt(self, message="Are you sure?", options=None):
        """
        Creates a prompt for the user to click one of the provided options.
        Get the user response by reading self.prompt_response ofter calling.
        """
        if not options:
            options = ["Yes", "Cancel"]

        popup = ctk.CTkToplevel()
        popup.title(message)

        # center the popup to the middle of the window
        root_x = self.window.winfo_x()
        root_y = self.window.winfo_y()
        root_width = self.window.winfo_width()
        root_height = self.window.winfo_height()
        popup_width = 350
        popup_height = 120

        popup_x = root_x + (root_width // 2) - (popup_width // 2)
        popup_y = root_y + (root_height // 2) - (popup_height // 2)
        popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")

        # remove the title bar
        popup.overrideredirect(True)

        ctk.CTkLabel(popup, text=message, fg_color="transparent", font=("Arial", 16)).pack(pady=10)
        buttons_frame = ctk.CTkFrame(popup, fg_color="transparent")
        buttons_frame.pack()

        for option in options:
            option_button = ctk.CTkButton(buttons_frame, text=option, command=lambda response=option: self.set_response(popup, response))

            # make yes/confirm green and no/cancel red
            if option.lower() == "yes" or option.lower() == "confirm":
                option_button.configure(**color_green)
            elif option.lower() == "no" or option.lower() == "cancel":
                option_button.configure(**color_red)

            option_button.pack(side="left", padx=10, pady=10)

        popup.transient(self.window)
        popup.grab_set()
        self.window.wait_window(popup)

    @handle_exceptions
    def make_link_button(self, itf, ref):
        """
        make a button that links a checked out part to its holder or
        a user with a checkout to the part checked out
        """
        ctk.CTkButton(itf, width=20, height=30, text="↗", command=lambda reference=ref: self.open_reference(ref)).pack(side="right")

    @handle_exceptions
    def open_reference(self, ref):
        if ref.isnumeric():
            self.raise_search("part")
        else:
            self.raise_search("user")

        print("sent", ref)
        self.list_button_select(database_key=ref)

    @handle_exceptions
    def update_user_select_options(self, key_event):
        """
        in the checkout frame, get the info from the entry box
        and use it to search for users, and then add them to the dropdown
        """
        # get the text from the entry box
        search_term = self.checkout_user_search.get()

        # the last character hasn't registered yet, so add that from the key event
        key = key_event.keysym
        print(key)
        if len(key) == 1: search_term += key
        if key == "BackSpace": search_term = search_term[:-1]

        # search for the matching users
        users = self.controller.user_search(search_term, use_full_names=True)
        self.reverse_users = {data: uid for uid, data in users.items()}
        names_list = list(self.reverse_users.keys())

        # update the search accordingly
        self.checkout_user_dropdown.configure(values=names_list)
        self.checkout_selected_user.set(names_list[0])

    @handle_exceptions
    def checkout_finalize(self, force=False):
        """take the upc and user id and check out the part."""
        user = self.checkout_selected_user.get()

        if user not in self.reverse_users.keys() or user.lower() == "no matching items":
            self.popup_msg("please select a valid user.")
            return

        uid = self.reverse_users[user]
        upc = self.checkout_upc

        result = self.controller.part_checkout(upc, uid, force)

        if result == "-CHECKOUT_SUCCESS-":
            self.popup_msg("Part checked out successfully", "success")
            self.checkout_frame.tkraise()
        else:
            # if the part is already checked out by someone else

            # split into error message and part holder
            split_result = result.split(";;")

            # if the formatting doesn't make sense (if everything is working, this should never fire)
            if (not len(split_result) >= 2) or (not split_result[0] == "-PART_HOLDER-"):
                raise Exception("Something went wrong on our end. Try returning the part and returning to checkout.")

            # tell the user that the part is already checked out, and ask if he/she wants to force checkout
            self.prompt_text.configure(text=f"This part is already checked out by {split_result[1]}. Check out anyways?")
            self.force_prompt.pack(pady=20)

    @handle_exceptions
    def make_new_form(self, questions_dict, entries_storing_variable):
        """makes a new form from a question dictionary"""
        new_form = ctk.CTkFrame(self.workspace)
        new_form.grid(row=0, column=0, sticky="news")

        # back button
        ctk.CTkButton(new_form, fg_color="transparent", hover_color=None, text="⇽ Back", anchor="w", hover=False, command=lambda: self.raise_search("user")).pack(fill="x", padx=40, pady=20)

        # main question fields
        for question, length in questions_dict.items():
            # make a description text
            ctk.CTkLabel(new_form, text="\n"+question, font=("Ariel", 16)).pack()

            # make a new entry box with the key
            validate_cmd = new_form.register(lambda e, l=length: max_length_validate(e, l))
            question_entry = ctk.CTkEntry(new_form, width=300, validate="key", validatecommand=(validate_cmd, "%P"))

            command = lambda *_, q=question_entry: q.configure(border_color="#565b5e")
            question_entry.bind("<FocusIn>", command)
            question_entry.bind("<Key>", command)
            question_entry.pack()
            entries_storing_variable[question] = question_entry

        # submit button
        ctk.CTkButton(new_form, text="Submit", command=self.submit_controller).pack(pady=20)

        return new_form

    @handle_exceptions
    def add_part(self):
        """add a new part to the database"""
        self.form_mode_add = True  # set the form to add mode and not edit mode
        if self.search_mode == "part":
            self.new_part_form.tkraise()
        else:
            self.new_user_form.tkraise()

        for name, entry in (self.add_part_entries | self.add_user_entries).items():

            entry.delete(0, "end")
            entry.configure(border_color="#565b5e")

    @handle_exceptions
    def edit_part_form(self):
        """edit the information on the selected part"""
        if not self.selected_part:
            self.popup_msg("Please select a part to edit.")
            return

        self.form_mode_add = False  # set the form to edit mode and not add mode

        if self.search_mode == "part":
            data = self.controller.part_data(self.selected_part_key)
            self.new_part_form.tkraise()
            print(data.keys())
            for name, entry in self.add_part_entries.items():
                print(name)
                entry.delete(0, "end")
                entry.insert(0, data[name])

        else:
            data = self.controller.user_data(self.selected_part_key)
            self.new_user_form.tkraise()
            for name, entry in self.add_user_entries.items():
                entry.delete(0, "end")
                entry.insert(0, data[name])

    @handle_exceptions
    def remove_part(self):
        """delete the selected part"""
        self.popup_prompt(message=f"Delete {self.search_mode} {self.selected_part_key}?")
        if self.prompt_response == "No" or self.prompt_response == "Cancel":
            return

        result = self.controller.delete_generic(self.selected_part_key, self.search_mode)

        if result == "-PARTS_STILL_CHECKED_OUT-":

            warning_msg = "This user still has parts checked out." if self.search_mode == "user" else "This part is still checked out."

            self.popup_prompt(message=f"Warning!\n{warning_msg}\nWould you like to return checked out part(s)?")
            if self.prompt_response.lower() == "yes" or self.prompt_response.lower() == "confirm":
                self.controller.clear_checkout(self.selected_part_key)
                self.controller.delete_generic(self.selected_part_key, self.search_mode)
            else:
                return

        self.update_search()

        self.popup_msg(f"Deleted {self.search_mode} {self.selected_part.cget('text')}", popup_type="success")

    @handle_exceptions
    def submit_controller(self):
        """either updates or adds a new part depending on the submit mode"""
        # get the fields
        fields = []

        if self.search_mode == "part":
            entries = self.add_part_entries
        else:
            entries = self.add_user_entries

        for item in entries.values():
            field_text = item.get()

            fields.append(field_text)
            if item.get() == "":
                item.configure(border_color=red)

        if "" in fields:
            self.popup_msg("You have empty fields!")
            return

        # new part mode
        if self.form_mode_add:
            try:
                if self.search_mode == "part":
                    new_key = self.controller.add_part(fields[3], *fields[:3], fields[4])
                else:
                    new_key = self.controller.add_user(*fields)

                    if new_key == "-EMAIL_ALREADY_TAKEN-":
                        self.popup_msg("This email is already in use!")
                        self.add_user_entries["Email"].configure(border_color=red)
                        return
                    elif new_key == "-NAME_ALREADY_TAKEN-":
                        self.popup_msg("This name is already in use")
                        self.add_user_entries["First name"].configure(border_color=red)
                        self.add_user_entries["Last name"].configure(border_color=red)
                        return
            except p2er.UniqueViolation:
                self.popup_msg("this placement already exists! to change the quantity of a part, select edit from the \"find a part\" tab.")
                return
        else:
            if self.search_mode == "part":
                selected_part_upc = self.selected_part.cget("text")
                result = self.controller.update_part(selected_part_upc, mfr=fields[0], mfr_pn=fields[1], placement=fields[2], desc=fields[3], qty=fields[4])

                if result == "-PLACEMENT_ALREADY_TAKEN-":
                    self.popup_msg("This placement location is already in use.")
                    return
                else:
                    self.list_button_select(database_key=result)
            elif self.search_mode == "user":
                result = self.controller.update_user(self.selected_part_key, *fields[0:3])

                # if the database says that you can't do that
                if result == "-NAME_ALREADY_TAKEN-":
                    self.popup_msg("This name is already in use.")
                    return
                elif result == "-EMAIL_ALREADY_TAKEN-":
                    self.popup_msg("This email is already in use.")
                    return
                else:
                    self.list_button_select(button_index=0, database_key=result)

        # go back to the select screen  TO-DO    this reselect old part thing doesn't work
        #                               TO-DO    it's just aesthetic though, so it doesn't really matter
        # print(self.selected_part)
        # if self.selected_part:
        #     index_list = [(self.selected_part.cget("text") == part_widget.cget("text")) for part_widget in self.part_widgets]
        #     if True in index_list:
        #         part_index = index_list.index(True)
        #         self.list_button_select(part_index, new_key)

        self.raise_search(self.search_mode)

    @handle_exceptions
    def reconnect_db(self):
        # make a connection to the database
        try:
            self.controller = Organizer()
            print("we have a new connection")
        except Exception as er:
            # raise er
            self.popup_msg(er)

    @handle_exceptions
    def forget_popup(self, popup_id):
        print(popup_id)
        print(self.popup_counter)
        if popup_id == self.popup_counter:
            self.popup_window.place_forget()
            print("forgot")

    @handle_exceptions
    def popup_msg(self, error_text, popup_type="error", display_time_sec=2):
        self.popup_counter += 1
        popup_id = self.popup_counter

        # draw
        error_text = width_splice(str(error_text), 17)
        new_width = self.workspace.winfo_width() - 2*self.popup_pos["x"]
        stretch_height = 70 + 18*error_text.count("\n")
        title_text, color = {"error": ("Something went wrong!", red), "success": ("Success!", green)}[popup_type]

        self.popup_title.configure(text=title_text)
        self.popup_window.configure(width=new_width, height=stretch_height, fg_color=color)
        self.popup_text.configure(text=error_text)
        self.popup_window.place(**self.popup_pos)
        self.popup_window.tkraise()

        # bring the window to the top after other movement of gui from whatever caused the error
        self.window.after(5, self.popup_window.tkraise)

        # success messages hide themselves after 2 seconds
        if popup_type == "success":
            self.window.after(display_time_sec*1000, self.forget_popup, popup_id)

    @handle_exceptions
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

    @handle_exceptions
    def format_database(self):
        """delete the database and remake everything"""

        # confirm if the user wants to nuke everything
        # said "response is not yes" here instead of "response is no" because force
        # closing will count as a no, so one less way to accidentally nuke
        self.popup_prompt("Are you sure?\nThis will delete everything in the database.")
        if not (self.prompt_response.lower() == "yes" or self.prompt_response.lower() == "confirm"):
            return

        # make sure that we are able to connect to the database
        if not self.check_db_connection(accept_postgres=True): return

        # try to format the database as postgres
        try:
            with Organizer("postgres") as postgres:
                postgres.format_database()
                print("ok")
            self.popup_msg("Database formatted successfully", "success")
        except Exception as error:
            self.popup_msg(str(error))
            # raise error
        finally:
            self.reconnect_db()

    @handle_exceptions
    def populate_database(self):
        """fill the database with sample data"""

        # confirmation
        self.popup_prompt("Populate the database?")
        if not (self.prompt_response.lower() == "yes" or self.prompt_response.lower() == "confirm"):
            return

        # make sure that we are able to connect to the database
        if not self.check_db_connection(accept_postgres=True): return

        # try to format the database as postgres
        try:
            with Organizer() as postgres:
                postgres.populate_db()
                self.popup_msg("Database populated successfully", "success")
        except Exception as error:
            self.popup_msg(str(error))

    @handle_exceptions
    def checkin_continue(self, *_):
        # check for database connection
        if not self.check_db_connection(): return

        # database checkin
        upc = self.checkin_barcode.get()
        result = self.controller.part_checkin(upc)

        # clear the entry box
        self.checkin_barcode.delete("0", "end")

        # relay the database message
        if "success" in result.lower():
            self.popup_msg(result, "success", 5)
        else:
            self.popup_msg(result)

    @handle_exceptions
    def checkout_continue(self, *_):
        # check for database connection
        if not self.check_db_connection(): return

        upc = self.checkout_barcode.get()

        if not self.controller.upc_exists(upc):
            self.popup_msg("UPC code not found in database")
            return

        # clear out whatever old stuff might be in this or the next panel
        self.force_prompt.pack_forget()
        self.checkout_user_search.delete("0", "end")
        self.checkout_upc = self.checkout_barcode.get()
        self.checkout_barcode.delete("0", "end")
        self.checkout_selected_user.set(" ")

        # move on to the user selection page
        self.checkout_user_frame.tkraise()

    @handle_exceptions
    def clear_part_results(self):
        # clear the scrolling frame that contains all the parts
        for pwidget in self.part_widgets:
            pwidget.pack_forget()
        self.part_widgets = []

    @handle_exceptions
    def raise_search(self, search_type):
        """clear the search box and raise either 'part search' or 'user search' depending on the search_type"""

        # this should never be fired
        if search_type not in ["user", "part"]: raise Exception("Invalid search type. Must be either 'user' or 'part'. This is a program issue, not a user issue.")

        # configure app to new search type
        self.search_mode = search_type

        # clear leftover data
        self.search_box.delete("0", "end")
        self.clear_output_box()
        self.update_search()

        # raise the search window
        self.find_part.tkraise()
        self.search_box.focus()

    @handle_exceptions
    def update_search(self, *_):
        """update the search scrollable frame to show new results"""
        active = self.check_db_connection()
        self.clear_part_results()

        if active:
            search = self.search_box.get()
            if self.search_mode == "part":
                parts = self.controller.part_search(search)
                names_dict = {part: part for part in parts}
            elif self.search_mode == "user":
                names_dict = self.controller.user_search(search, use_full_names=True)
                parts = names_dict.keys()
            else:
                raise Exception("the search mode is not set to either part or user.")

            # add the parts into the scrolling frame
            for index, part in enumerate(parts):
                name_text = str(names_dict[part])

                part_widget = ctk.CTkButton(
                    self.result_parts, text=name_text, anchor="w", fg_color="transparent",
                    hover=not part.lower() == "no matching items",
                    command=lambda i=index, p=str(part): self.list_button_select(i, p)
                )
                part_widget.pack(fill="x", expand=True)
                self.part_widgets.append(part_widget)

    @handle_exceptions
    def clear_output_box(self):
        for item in self.output_frames:
            item.pack_forget()
        self.output_frames.clear()

    @handle_exceptions
    def list_button_select(self, button_index=None, database_key=None):
        print(database_key)
        """select the targeted part and update the results accordingly"""
        if not database_key:
            database_key = self.selected_part_key

        if not button_index:
            for i, button in enumerate(self.part_widgets):
                if _int(button.cget("text")) == _int(database_key):
                    print("got one!")
                    button_index = i

        print(self.part_widgets)
        print(button_index)

        button = self.part_widgets[button_index]

        if database_key.lower() == "no matching items":
            return

        # un-highlight the old selection
        if self.selected_part:
            self.selected_part.configure(fg_color="transparent")

        # get the info for the selected part
        if self.search_mode == "part":
            part_info = self.controller.part_data(database_key)
        else:

            # if the database key given is a name, convert it to a user id
            if " " in database_key:
                database_key = self.controller.user_id_from_name(database_key)

            part_info = self.controller.user_data(database_key)
            if len(part_info["Parts checked out"]) < 1:
                part_info["Parts checked out"] = "None"

        # display the part info
        self.clear_output_box()
        for key, value in part_info.items():
            # generate a frame to put the item and text side by side
            item_frame = ctk.CTkFrame(self.part_generic_info, fg_color="transparent")

            # object description
            ctk.CTkLabel(item_frame, fg_color="transparent", text=key).pack(side="left")

            # object value
            if key == "Parts checked out" and value != "None":
                # special rules for parts checked out
                stack_boxes_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
                stack_boxes_frame.pack(side="right")

                # make a box for each checkout
                for part in value:
                    yet_another_frame = ctk.CTkFrame(stack_boxes_frame, fg_color="transparent")
                    yet_another_frame.pack()
                    make_box(yet_another_frame, part, tall=True)
                    pn = part.split("\n")[0]
                    self.make_link_button(yet_another_frame, pn)
            else:
                # normal value boxes
                make_box(item_frame, value, key.lower() == "description")

            # jump to reference button
            if key.lower() == "currently checked out by" and value.lower() != "not checked out":
                self.make_link_button(item_frame, value.split("(")[0][:-1])

            # save the item frame to a list so that we can draw everything at the same time
            self.output_frames.append(item_frame)

        for frame in self.output_frames:
            frame.pack(fill="x", expand=True)

        # new_text = width_splice(new_text, 16, 400)

        # finally, highlight the selected item in the scrolling frame
        button.configure(fg_color="#1f6ba5")
        self.selected_part = button
        print(database_key)
        self.selected_part_key = database_key
