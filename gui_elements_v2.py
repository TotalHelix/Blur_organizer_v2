import customtkinter as ctk
from PIL import ImageFont
from db_interactions import Organizer
import psycopg2.errors as p2er
import re

# theme stuff
ctk.set_appearance_mode("dark")
red = "#d62c20"
green = "#32a852"
hover_red = "#781610"

# TODO at some point: make the results screen have nice buttons that let you jump to references


# Validation function to allow only digits
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
    ctk.CTkButton(frame_house, text=button_text, fg_color=red, hover_color=hover_red, command=command).grid(column=1, row=0, rowspan=2, padx=8)


def max_length_validate(text, length):
    """max length for input validation"""
    print(f"length {length} is a {type(length)}")
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
            "Search Parts": lambda: self.raise_search("part"),
            "Search Users": lambda: self.raise_search("user")
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
        ctk.CTkButton(**button_form, text="+ Add", command=self.add_part_form).pack(**button_pack)
        ctk.CTkButton(**button_form, text="️🗑 Delete", command=self.remove_part).pack(**button_pack)
        ctk.CTkButton(**button_form, text="🖉 Edit", command=self.edit_part_form).pack(**button_pack)

        # right side (display part info)
        part_info_display_frame = ctk.CTkFrame(self.find_part, fg_color="transparent", width=350)
        part_info_display_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")

        self.part_generic_info = ctk.CTkLabel(part_info_display_frame, fg_color="transparent", text="", justify="left", font=("Ariel", 16), width=300, anchor="w")
        self.part_generic_info.pack(padx=0, pady=20, anchor="w", expand=False)

        #######################
        # add new part form
        #######################
        self.new_part_form = ctk.CTkFrame(self.workspace)
        self.new_part_form.grid(row=0, column=0, sticky="news")

        # back button
        ctk.CTkButton(self.new_part_form, fg_color="transparent", hover_color=None, text="⇽ Back", anchor="w", hover=False, command=lambda: self.raise_search("user")).pack(fill="x", padx=40, pady=20)

        # main question fields
        questions = {
            "Manufacturer": 255,
            "Manufacturer's Part Number": 255,
            "Placement location": 10,
            "Description": 0,
            "Quantity": "int"
        }
        self.add_part_entries = {}
        for question, length in questions.items():
            # make a description text
            ctk.CTkLabel(self.new_part_form, text="\n"+question, font=("Ariel", 16)).pack()

            # make a new entry box with the key
            validate_cmd = self.new_part_form.register(lambda e, l=length: max_length_validate(e, l))
            question_entry = ctk.CTkEntry(self.new_part_form, width=300, validate="key", validatecommand=(validate_cmd, "%P"))
            question_entry.bind("<FocusIn>", lambda *_, q=question_entry: q.configure(border_color="#565b5e"))
            question_entry.pack()
            self.add_part_entries[question] = question_entry

        # submit button
        ctk.CTkButton(self.new_part_form, text="Submit", command=self.submit_controller).pack(pady=20)

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
            print(document)

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
    def add_part_form(self):
        """add a new part to the database"""
        self.form_mode_add = True  # set the form to add mode and not edit mode
        self.new_part_form.tkraise()

        for name, entry in self.add_part_entries.items():
            entry.delete(0, "end")

    @handle_exceptions
    def edit_part_form(self):
        """edit the information on the selected part"""
        if not self.selected_part:
            self.popup_msg("Please select a part to edit.")
            return

        self.form_mode_add = False  # set the form to edit mode and not add mode
        self.new_part_form.tkraise()

        current_upc = self.selected_part.cget("text")
        data = self.controller.part_data(current_upc)
        print(data)

        for name, entry in self.add_part_entries.items():
            entry.delete(0, "end")
            entry.insert(0, data[name])

    @handle_exceptions
    def remove_part(self):
        """delete the selected part"""
        part_upc = self.selected_part.cget("text")
        self.controller.delete_generic(part_upc, "part")
        self.update_search()

        self.popup_msg("Deleted part "+part_upc, popup_type="success")

    @handle_exceptions
    def submit_controller(self):
        """either updates or adds a new part depending on the submit mode"""
        # get the fields
        fields = []

        for item in self.add_part_entries.values():
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
                self.controller.add_part(fields[3], *fields[:3], fields[4])
            except p2er.UniqueViolation:
                self.popup_msg("this placement already exists! to change the quantity of a part, select edit from the \"find a part\" tab.")
        else:
            selected_part_upc = self.selected_part.cget("text")
            print(fields)
            self.controller.update_part(selected_part_upc, mfr=fields[0], mfr_pn=fields[1], placement=fields[2], desc=fields[3], qty=fields[4])

        # go back to the select screen
        index_list = [(self.selected_part.cget("text") == part_widget.cget("text")) for part_widget in self.part_widgets]
        part_index = index_list.index(True)
        self.list_button_select(part_index)

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
    def popup_msg(self, error_text, popup_type="error"):
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

        if popup_type == "success":
            self.window.after(2000, self.forget_popup, popup_id)

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

        print(self.checkin_barcode.get())

    @handle_exceptions
    def clear_part_results(self):
        # clear the scrolling frame that contains all the parts
        for pwidget in self.part_widgets:
            pwidget.pack_forget()
        self.part_widgets = []

    @handle_exceptions
    def raise_search(self, search_type):
        """clear the search box and raise 'find a part'"""
        if search_type not in ["user", "part"]: raise Exception("Invalid search type. Must be either 'user' or 'part'. This is a program issue, not a user issue.")
        self.search_mode = search_type
        self.find_part.tkraise()
        self.search_box.delete("0", "end")
        self.search_box.focus()
        self.update_search()

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
    def list_button_select(self, button_index, key):
        # select the targeted part and update the results accordingly
        button = self.part_widgets[button_index]

        #  button.cget("text").lower()
        if key.lower() == "no matching items":
            return

        # un-highlight the old selection
        if self.selected_part:
            self.selected_part.configure(fg_color="transparent")

        # highlight the selected item
        button.configure(fg_color="#1f6ba5")
        self.selected_part = button

        # get the info for the selected part
        if self.search_mode == "part":
            part_info = self.controller.part_data(key)
        else:
            part_info = self.controller.user_data(key)
            if len(part_info["Parts checked out"]) < 1:
                part_info["Parts checked out"] = "None"
            else:
                part_info["Parts checked out"] = "\n" + "\n".join([f"{part} on {date}" for part, date in part_info["Parts checked out"]])

        # display the part info
        self.part_generic_info.configure(text="")
        new_text = ""
        for key, value in part_info.items():
            # if key.lower() == "description":
            #     textbox_write(self.part_description, value)
            # else:

            new_text += f"{key}: {value}\n\n"

        new_text = width_splice(new_text, 16, 400)
        self.part_generic_info.configure(text=new_text)
