import math
import warnings
from os import remove as os_remove
import tkinter as tk
import urllib
import customtkinter as ctk
from sys import exit
import requests
from PIL import ImageFont, Image
from db_interactions import Organizer, get_location
import psycopg2.errors as p2er
from re import compile, split as re_split
from webbrowser import open as web_open
from CTkMessagebox import CTkMessagebox

# theme stuff; colors and fonts
ctk.set_appearance_mode("dark")
red = "#d62c20"
green = "#32a852"
color_red = {"fg_color": red, "hover_color": "#781610"}
color_green = {"fg_color": green, "hover_color": "#0f4f22"}
title = ("Arial", 30, "bold")
subtitle = ("Ariel", 18)
listbutton_font = ("Roboto Mono", 12)
manage_finder_font = ("Roboto Mono", 10)
button_enable = {"state": "normal", "fg_color": "#206ca4"}
button_disable = {"state": "disabled", "fg_color": "#506474"}


def make_floating_frame(master, return_frame=False, scrolling_frame=False):
    """
    makes a frame that sits in the middle of other frames, so that it scales when the window is fullscreen.

    :param return_frame: whether the border frame is returned, default is False.
    :param master: the frame the floating frame is made in.
    :param scrolling_frame: if True, the frame will be a scrolling frame, otherwise it will be a normal frame.
    :returns: just the interior frame if return_frame is False, otherwise (border frame, interior frame)
    """

    outer = ctk.CTkFrame(master)
    outer.grid(row=0, column=0, sticky="news")

    outer.grid_rowconfigure(0, weight=1)
    outer.grid_columnconfigure(0, weight=1)
    outer.grid_columnconfigure(1, weight=4)
    outer.grid_columnconfigure(2, weight=1)

    if scrolling_frame:
        inner = ctk.CTkScrollableFrame(outer, fg_color="transparent")
    else:
        inner = ctk.CTkFrame(outer, fg_color="transparent")
    inner.grid(row=0, column=1, sticky="news")

    if return_frame:
        return outer, inner
    else:
        return inner


def list_button_format(text, search_mode):
    """
    Takes a tuple of part and turns it into a single string to print on list buttons

    :param text: tuple or list that will be formatted:
            for parts: (mfr_pn, mfr_name, upc, date_added, placement, description)
            for users: (user_id, full_name, email)
    :param search_mode: format as part or as user
    :return: string formatted text
    """
    if not isinstance(text, (tuple, list)):
        raise("list_button_format requires a tuple argument, but received", type(text))

    if search_mode == "part":
        final_string = ""
        text = [text[6], *text[:6]]
        lengths = [24, 21, 16, 14, 12, 16, 34]
    else:
        final_string = ""
        lengths = [17, 22, 30]

    for i, seg_len in enumerate(lengths):
        if len(text[i]) > seg_len:
            this_segment = text[i][:seg_len-3]+"..."
        else:
            this_segment = text[i]
        final_string += f"{this_segment: <{seg_len}} "

    return final_string


def _int(string):
    """turns a string into an int if the string can become an int"""
    if not string or (isinstance(string, str) and string.isspace()): return

    if string.isnumeric():
        return int(string)
    elif string.split()[0].isnumeric():
        return int(string.split()[0])
    else:
        return string


def make_box(itf, v, tall=False):
    """generates a box frame for displaying output text when a list button is selected"""

    textbox_height = 60 if tall else 20
    value_box = ctk.CTkTextbox(itf, height=textbox_height)
    value_box.insert("0.0", str(v))
    value_box.configure(state="disabled")
    value_box.pack(side="right", padx=10, pady=7)


def margin(master):
    """a margin that you should add to the top of each frame"""
    ctk.CTkLabel(master, text=" ", font=("Ariel", 1)).pack()


def stackable_frame(master, text, desc, button_text, command):
    """A stackable frame that has a title and description on the left, and a button on the right"""
    frame_house = ctk.CTkFrame(master, height=80)
    frame_house.pack(fill="x", pady=7)

    frame_house.grid_columnconfigure(0, weight=5)
    frame_house.grid_columnconfigure(1, weight=1)
    frame_house.grid_rowconfigure(0, weight=1)
    frame_house.grid_rowconfigure(1, weight=1)

    # title
    ctk.CTkLabel(frame_house, text=text, font=subtitle, anchor="sw").grid(column=0, row=0, sticky="w", padx=15, pady=5)

    # description
    ctk.CTkLabel(frame_house, text=desc, font=("Ariel", 16), anchor="nw").grid(column=0, row=1, sticky="w", padx=15, pady=5)

    # button
    ctk.CTkButton(frame_house, text=button_text, **color_red, command=command).grid(column=2, row=0, rowspan=2, padx=8)

    # spacer
    ctk.CTkLabel(frame_house, text="").grid(column=3, row=0, padx=17)


def max_length_validate(text, length):
    """max length for input validation"""
    if text == "": return True
    if length == "int": return text.isdigit() and int(text) < 32767
    if length == 0: return True
    return len(text) <= length


def handle_exceptions(func):
    """wrapper for error handling, relies on self.popup_msg so only use in MainWindow."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as er:

            args[0].popup_msg(str(er))
            raise er  # TODO: comment this out again when you deploy (it will crash the program (i think))
    return wrapper


class ButtonWithVar(ctk.CTkButton):
    def __init__(self, master, var_value, **kwargs):
        self.button = super().__init__(master, **kwargs)
        self.var = tk.StringVar(self.button, value=var_value)

    def get_var(self):
        return self.var.get()


class MainWindow:
    """The whole window that does all of everything"""
    def __init__(self, db_name):
        get_location()

        # database credentials
        self.db_name = db_name

        # start the window (I know that your animations don't exist)
        self.window = ctk.CTk()

        # initial setup
        self.window.geometry("1000x700")
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(0, weight=0)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.title("Blur Part Organizer")
        self.popup_counter = 0
        self.form_mode_add = True
        self.search_mode = "part"
        self.selected_part_key = ""
        self.checkout_upc = ""
        self.output_frames = []
        self.is_fullscreen = True
        self.previous_screen = ""
        self.checkout_user = ""
        self.back_to_checkout = True

        # for interactions with the database
        self.controller = None
        self.postgres_exists = False
        self.connection = False
        self.db_connect()

        # left column
        l_col = ctk.CTkFrame(self.window, fg_color="transparent")
        l_col.grid(row=1, column=0, padx=10, pady=10, sticky="ns")
        side_buttons = {
            # these have to be lambda again because the frames haven't been defined yet.
            "Home": self.raise_home_frame,
            "Part Search": lambda: self.raise_search("part"),
            "User Search": lambda: self.raise_search("user"),
            "Manage Parts": lambda: self.raise_manage("part"),
            "Manage Users": lambda: self.raise_manage("user"),
            "Kiosk Mode": lambda: self.raise_kiosk()
        }
        for button_name, cmd in side_buttons.items():
            button = ctk.CTkButton(l_col, text=button_name, command=cmd)
            button.pack(padx=10, pady=13)

        danger_zone_button = ctk.CTkButton(l_col, **color_red, text="Danger Zone", command=lambda: self.danger_zone.tkraise())
        danger_zone_button.pack(side=ctk.BOTTOM, padx=10, pady=11)

        # fullscreen menu bar
        self.menu_bar = ctk.CTkFrame(self.window, fg_color="transparent")
        self.menu_bar.grid(row=0, column=0, columnspan=2, sticky="nsew")

        menu_button = {"fg_color": "transparent", "height": 30, "width": 40, "font": ("Arial", 15), "anchor": "n"}  # , "hover": False}
        menu_pack = {"side": "right", "padx": 5, "pady": 5}

        ctk.CTkButton(self.menu_bar, text="🗙", command=lambda: exit(0), hover_color="red", **menu_button).pack(**menu_pack)
        ctk.CTkButton(self.menu_bar, text="🗖", command=self.fullscreen, hover_color="#4a4a4a", **menu_button).pack(**menu_pack)
        ctk.CTkButton(self.menu_bar, text="🗕", command=self.minimize, hover_color="#4a4a4a", **menu_button).pack(**menu_pack)

        # workspace
        self.workspace = ctk.CTkFrame(self.window)
        self.workspace.grid(row=1, column=1, padx=10, sticky="news")
        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(0, weight=1)

        ##########################################
        # different frames
        ##########################################

        #################
        # checkout continue (user select)
        #################
        self.checkout_user_frame = ctk.CTkFrame(self.workspace)
        self.checkout_user_frame.grid(row=0, column=0, sticky="news")

        # back button
        ctk.CTkButton(self.checkout_user_frame, fg_color="transparent", hover_color=None, text="⇽ Back", anchor="w", hover=False, command=self.raise_previous).pack(fill="x", padx=40, pady=20)

        # title text
        ctk.CTkLabel(self.checkout_user_frame, text="Please select your account", font=title).pack(pady=10)

        # Search Box

        # search box in the user select frame
        self.reverse_users = {}
        checkout_width = 400
        self.checkout_user_search = ctk.CTkEntry(self.checkout_user_frame, placeholder_text="Search", width=checkout_width, height=35)
        self.checkout_user_search.pack(pady=15)
        self.checkout_user_search.bind("<KeyRelease>", self.checkout_update_search)

        # scrolling frame of users to pick from
        self.checkout_search_options = []
        self.checkout_scrolling_frame = ctk.CTkScrollableFrame(self.checkout_user_frame, width=checkout_width, height=500)
        self.checkout_scrolling_frame.pack()

        # Create new user button
        ctk.CTkButton(self.checkout_user_frame, text="+ Create User", font=subtitle, command=self.create_user).pack(pady=15)

        # seperator
        ctk.CTkLabel(self.checkout_user_frame, text="_"*46, fg_color="transparent", font=subtitle, text_color="grey").pack()

        # "Check out as Reuben Tart?" message
        self.checkout_message = ctk.CTkLabel(self.checkout_user_frame, text="FILLER TEXT", font=subtitle)
        self.checkout_message.pack()

        # check out button (not a trick like the 'go' button)
        self.checkout_finalize_button = ctk.CTkButton(self.checkout_user_frame, text="Check Out", command=self.checkout_finalize, font=subtitle, width=180, height=40, **button_disable)
        self.checkout_finalize_button.pack(pady=30)

        # prompt for force checkout
        self.force_prompt = ctk.CTkFrame(self.checkout_user_frame)
        self.prompt_text = ctk.CTkLabel(self.force_prompt)
        self.prompt_text.pack(pady=5, padx=7)
        buttons_frame = ctk.CTkFrame(self.force_prompt, fg_color="transparent")
        buttons_frame.pack(pady=10)
        ctk.CTkButton(buttons_frame, text="Yes", **color_green, command=lambda: self.checkout_finalize(force=True)).pack(side="left", padx=8)
        ctk.CTkButton(buttons_frame, text="Cancel", **color_red, command=self.raise_and_select).pack(side="left", padx=8)

        ###################
        # danger zone
        ###################
        _, danger_zone_middle = make_floating_frame(self.workspace, return_frame=True)
        self.danger_zone = _

        margin(danger_zone_middle)

        data = [  # Title, Description, Button text, command
            ("Format Database", "Resets the database with all default tables", "Format", self.format_database),
            ("Populate Database", "Fills the database up with random data. Useful for testing", "Populate", self.populate_database),
            ("Drop Database", "Completely delete the database. This window might no longer function as expected until the database is reformatted.", "Drop", self.drop_db),
            ("Change Location", "Change where this machine thinks that it is. Returned parts will show as being in the new location.", "Change", self.change_location)
        ]

        for args in data:
            stackable_frame(danger_zone_middle, *args)

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
        self.top_frame = ctk.CTkFrame(self.find_part, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="nsew", padx=40)

        inner_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        inner_frame.pack(side="top")

        ctk.CTkLabel(inner_frame, fg_color="transparent", text="Search:").pack(side="left", padx=10)

        self.search_box = ctk.CTkEntry(inner_frame, placeholder_text="Search for a part", width=600)
        self.search_box.pack(pady=20, side="left")
        self.search_box.bind("<KeyRelease>", self.update_search)

        self.search_labels = ctk.CTkLabel(self.top_frame, fg_color="#454547", font=listbutton_font)
        self.search_labels.pack(side="top", fill="x", expand=True)

        self.result_parts = ctk.CTkScrollableFrame(self.find_part, width=800)
        self.result_parts.grid(row=1, column=0, sticky="nsew", padx=40, pady=0)
        self.part_widgets = []
        self.selected_part = None

        # buttons that run along the bottom
        self.thin_frame = ctk.CTkFrame(self.find_part, fg_color="transparent")  # , height=25)   # add this back if you want a blank margin with no buttons
        self.blank_frame = ctk.CTkFrame(self.find_part, fg_color="transparent", height=20)

        self.check_in_out_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")

        self.check_in_out_buttons = []
        for name, cmd in [("🛒 Check Out", self.checkout_continue), ("⟳ Return", self.checkin_continue)]:
            new_button = ctk.CTkButton(self.check_in_out_frame, text=name, command=cmd, **button_disable)
            self.check_in_out_buttons.append(new_button)
            new_button.pack(side="left", padx=15, pady=20)

        # right side (display part info)
        part_info_display_frame = ctk.CTkFrame(self.find_part, fg_color="transparent", width=350)
        part_info_display_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")

        self.part_generic_info = ctk.CTkFrame(part_info_display_frame, fg_color="transparent")
        self.part_generic_info.pack(padx=0, pady=20, anchor="n", expand=True, fill="x")
        self.output_box = ctk.CTkFrame(self.part_generic_info, fg_color="transparent")
        self.output_box.pack(fill="both", expand=True)

        self.blank_frame.grid(column=0, row=2, columnspan=2, sticky="NEWS", padx=27)

        #############
        # Kiosk Mode
        #############

        self.kiosk_frame = ctk.CTkFrame(self.workspace)
        self.kiosk_frame.grid(row=0, column=0, sticky="news")

        ctk.CTkLabel(self.kiosk_frame, text="Scan a part or enter a UPC code", font=title).place(relx=0.5, rely=0.12, anchor=ctk.CENTER)
        self.kiosk_entry_var = ctk.StringVar()
        self.kiosk_entry = ctk.CTkEntry(self.kiosk_frame, width=500, height=40, textvariable=self.kiosk_entry_var)
        self.kiosk_entry.place(relx=0.5, rely=0.2, anchor=ctk.CENTER)
        self.kiosk_entry.bind("<KeyRelease>", self.kiosk_check_upc)

        # the buttons and text that appear on kiosk mode when you enter a valid code
        self.kiosk_message = ctk.CTkLabel(self.kiosk_frame, text="Part found: [PART NAME]", font=subtitle)
        self.kiosk_next_step = ctk.CTkFrame(self.kiosk_frame, width=1000, height=500, fg_color="transparent")

        button_size = 250

        for col_num, image_path, command in (
                (0, "images/Check_Out.png", self.checkout_continue),
                (1, "images/Return.png", self.checkin_continue)
        ):
            image = ctk.CTkImage(Image.open(image_path), size=(button_size, button_size))
            hover_image = ctk.CTkImage(Image.open(image_path[:-4]+"_hover"+image_path[-4:]), size=(button_size, button_size))

            image_button = ctk.CTkButton(self.kiosk_next_step, image=image, text="", corner_radius=100, command=command)
            image_button.grid(row=0, column=col_num, padx=50)

            for event, new_image in (("<Enter>", hover_image), ("<Leave>", image)):
                image_button.bind(event, lambda _=_, btn=image_button, img=new_image: btn.configure(image=img))

        #######################
        # add new part form
        #######################
        self.part_questions = {  # "field": (max length, required)
            "Manufacturer": (26, True),
            "Part number": (26, True),
            # "Placement location": (255, True),
            # previously the placement location wasn't the kiosk location, but a storage closet identification number.
            "Description": (0, False),
            "Link to original part": (0, False)
        }

        self.user_questions = {
            "First name": (50, True),
            "Last name": (50, True),
            "Email": (255, False)
        }

        self.add_part_entries = {}
        self.add_user_entries = {}
        self.new_part_form = self.make_new_form("part")
        self.new_user_form = self.make_new_form("user")

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

        #######################
        # manage parts/users
        #######################
        self.manage_parts_frame = ctk.CTkFrame(self.workspace)
        self.manage_parts_frame.grid(row=0, column=0, sticky="news")

        # margin
        margin(self.manage_parts_frame)

        # title
        self.manage_title = ctk.CTkLabel(self.manage_parts_frame, text="Manage Parts", font=title)
        self.manage_title.pack(pady=10)

        # subtitle
        self.manage_subtitle = ctk.CTkLabel(self.manage_parts_frame, text="", font=subtitle)
        self.manage_subtitle.pack(pady=10)

        # manage parts search box
        width = 800
        manage_part_finder_frame = ctk.CTkFrame(self.manage_parts_frame, fg_color="transparent", width=width)
        manage_finder_thin_frame = ctk.CTkFrame(manage_part_finder_frame, fg_color="transparent")
        self.manage_finder_widgets = []

        search_label = ctk.CTkLabel(manage_finder_thin_frame, text="Search:", width=80, fg_color="transparent")
        self.manage_finder_entry = ctk.CTkEntry(manage_finder_thin_frame, placeholder_text="Search for anything")
        self.manage_finder_entry.bind("<KeyRelease>", self.manage_finder_update)

        self.manage_finder_scrollbox_key = ctk.CTkLabel(manage_part_finder_frame, width=width, fg_color="#454547", anchor="w", font=manage_finder_font)
        self.manage_finder_scrollbox = ctk.CTkScrollableFrame(manage_part_finder_frame, width=width, height=500)

        search_label.pack(side="left", fill="y")
        manage_finder_thin_frame.pack(fill="x", expand="true")
        self.manage_finder_entry.pack(pady=20, side="left", fill="x", expand="true")
        self.manage_finder_scrollbox_key.pack(expand=True, fill="x")
        self.manage_finder_scrollbox.pack(expand=True, fill="x")
        manage_part_finder_frame.pack(pady=10)

        # search box
        self.manage_search_box = ctk.CTkLabel(self.manage_parts_frame, height=28, width=500, font=subtitle, fg_color="#484848")

        self.manage_search_box.pack(pady=20)

        # buttons that run under the search box
        thin_frame = ctk.CTkFrame(self.manage_parts_frame, fg_color="transparent")
        thin_frame.pack()

        # some button presets
        button_form = {"master": thin_frame, "width": 100, "height": 32}
        button_pack = {"side": "left", "padx": 10}

        # delete, edit, and print buttons (print disappears for users)
        ctk.CTkButton(**button_form, text="️🗑 Delete", command=self.remove_part).pack(**button_pack)
        ctk.CTkButton(**button_form, text="🖉 Edit", command=self.edit_part_form).pack(**button_pack)
        self.print_button = ctk.CTkButton(**button_form, text="🖨 Print", command=self.print_label)
        self.print_button.pack(**button_pack)

        # or add a part
        ctk.CTkLabel(self.manage_parts_frame, text="or", font=subtitle).pack(pady=20)
        self.add_part_button = ctk.CTkButton(self.manage_parts_frame, text="+ Add a part", command=self.add_part, height=32)
        self.add_part_button.pack()

        #####################
        # Home / README
        #####################

        a, b = make_floating_frame(self.workspace, return_frame=True, scrolling_frame=True)
        self.home_frame_base = a
        self.home_frame = b

        margin(self.home_frame)

        # include the readme (still part of home)
        try:
            # raise Exception("forced exception")
            try:
                readme = open("README.md", "r")
                document = "\n".join([s.rstrip() for s in readme.readlines()]).split("\n"*2)

            except FileNotFoundError as err:
                readme = requests.get("https://github.com/TotalHelix/Blur_organizer_v2/raw/main/README.md").text
                document = "\n".join([s.rstrip() for s in readme.split("\n")]).split("\n"*2)

            for line in document:
                line = line.replace("\n", " ")

                # skip blank lines
                if not line or line.isspace():
                    continue

                # images
                if line.startswith("![") and "](" in line and line.endswith(")"):
                    image_link = line.split("](")[1].replace(")", "")
                    alt_text = line.split("](")[0].replace("![", "")
                    try:
                        urllib.request.urlretrieve(image_link, "tmp.png")
                        my_img = Image.open("tmp.png")
                        ctk_image = ctk.CTkImage(light_image=my_img, dark_image=my_img, size=(my_img.width, my_img.height))
                        ctk.CTkLabel(self.home_frame, image=ctk_image, text="", anchor="w").pack(fill="both", expand="yes", padx=45)
                        os_remove("tmp.png")
                        continue
                    except urllib.error.URLError as err:
                        # if the image can't load
                        line_len = 40
                        text = "\n".join((str(err) + " "*line_len)[i * line_len: (i+1) * line_len] for i in range(math.ceil(len(str(err))/line_len)))

                        # ctk.CTkLabel(self.home_frame, width=300, height=300, text=f"We couldn't load this image. to see the image,\n click on the link below.", fg_color="#5e5e5e").pack()
                        hyperlink = ctk.CTkLabel(self.home_frame, cursor="hand2", text=f"View Image \"{alt_text}\" in browser.", text_color="#a4a2f2", font=subtitle, anchor="w")
                        hyperlink.pack(fill="both", expand=True, padx=25, pady=10)
                        hyperlink.bind("<Button-1>", lambda _, l=image_link: self.open_reference(ref=l))
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

                for label_line in self.width_splice(label_text, info[1]).split("\n"):
                    line_frame = ctk.CTkFrame(paragraph_frame, fg_color="transparent")
                    line_frame.pack(padx=40, anchor="w")

                    # inline formatting
                    # Split the line based on backticks
                    inline_segments = re_split(r'(`[^`]+`)', label_line)
                    for inline_segment in inline_segments:
                        if inline_segment.startswith('`') and inline_segment.endswith('`'):
                            # Remove backticks and format as a quote box
                            formatted_text = inline_segment[1:-1]
                            ctk.CTkLabel(
                                line_frame, text=self.width_splice(formatted_text, info[1]), fg_color="#414243", corner_radius=5, font=("cascadia mono", info[1])
                            ).pack(side="left", padx=2)
                        else:
                            # there has to be a better way to do this than this much nesting...
                            hyperlink_pattern = compile(r'\[(.*?)]\((.*?)\)')

                            # Split text and keep the parts with and without links
                            hyperlink_segments = hyperlink_pattern.split(inline_segment)

                            # Iterate over the parts and the matches to construct the new text
                            link_text = ""  # this line isn't actually necessary, but it makes IntelliJ happy.
                            for i, hyperlink_segment in enumerate(hyperlink_segments):
                                if i % 3 == 0:  # Normal text
                                    ctk.CTkLabel(line_frame, text=self.width_splice(hyperlink_segment, info[1]), font=("Arial", info[1])).pack(side="left", padx=2)

                                elif i % 3 == 1:  # Text with link attached
                                    link_text = hyperlink_segment

                                elif i % 3 == 2:  # Link attached to text (render text)
                                    link = hyperlink_segment
                                    hyperlink = ctk.CTkLabel(line_frame, text=self.width_splice(link_text, info[1]), text_color="#a4a2f2", font=("Arial", info[1]), cursor="hand2")
                                    hyperlink.pack(side="left", padx=2)
                                    hyperlink.bind("<Button-1>", lambda _, l=link: self.open_reference(ref=l))

        except Exception as e:
            self.home_frame.grid_forget()

            ctk.CTkLabel(
                self.home_frame_base, font=subtitle,
                text=f"We weren't able to load the home page.\n\nError: {str(e)}"
            ).grid(row=0, column=1)
            # raise e  # TODONE comment this out again
        finally:
            self.window.attributes('-fullscreen', True)
            # self.window.state("zoomed")

    def change_location(self):
        print("yeah this doesn't work yet")

    def create_user(self):
        self.search_mode = "user"
        self.back_to_checkout = True
        self.add_part()

    def checkout_update_search(self, *_):
        """update the data in the checkout user search box."""
        search_text = self.checkout_user_search.get()

        # clear the old list
        for thing in self.checkout_search_options:
            thing.pack_forget()
        self.checkout_search_options = []

        # scroll back to the top of the frame
        self.checkout_scrolling_frame.parent_canvas.yview_moveto(0)

        # make a button for each result
        users = self.controller.user_search(search_text, use_full_names=True)
        for user_id, values in users.items():
            # decide what to put on the button
            if values[0] == "No Results": button_text = "No Results"
            else: button_text = values[1]

            # make the button
            new_button = ctk.CTkButton(self.checkout_scrolling_frame, text=button_text, width=400, height=40, fg_color="transparent", command=lambda n=values[0]: self.checkout_user_select(n))
            new_button.pack()
            self.checkout_search_options.append(new_button)

    def checkout_user_select(self, user_name):
        """select the user in the checkout user select frame with the specified username"""
        print(f"called with name \"{user_name}\"")

        users_dict = self.controller.user_search(user_name, use_full_names=True)
        display_name = " ".join(list(users_dict.values())[0][1:2])

        print(f"\tthis results in full name \"{display_name}\"")

        self.checkout_user = user_name
        self.checkout_finalize_button.configure(**button_enable)
        self.checkout_message.configure(text=f"Check out as {display_name}?")

    def fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.window.attributes('-fullscreen', self.is_fullscreen)

    def minimize(self): self.window.wm_state("iconic")

    def print_hello_world(self, *args, **kwargs):
        """Test function: prints \"Hello World!\" along with all args and kwargs"""
        print("Hello world!")
        print("\tself:", self)
        print("\t*args:", args)
        print("\t**kwargs:", kwargs)

    def kiosk_check_upc(self, *_):
        """Make sure that the upc is 12 numeric characters"""

        raw_string = self.kiosk_entry_var.get()
        good_string = ""

        for char in raw_string:
            if char.isnumeric():
                good_string += char

        self.kiosk_entry_var.set(good_string)
        if not good_string: return

        if self.controller.upc_exists(good_string):
            self.selected_part_key = good_string
            self.kiosk_next_step.place(relx=0.5, rely=0.5, anchor=ctk.CENTER)
            self.kiosk_message.place(relx=0.5, rely=0.3, anchor=ctk.CENTER)

            part_num = self.controller.part_num_from_upc(good_string)
            self.kiosk_message.configure(text="Part found: "+part_num)
        else:
            self.kiosk_next_step.place_forget()
            self.kiosk_message.place_forget()

    def raise_previous(self):
        print("we were here")
        if self.previous_screen == "user" or self.previous_screen == "part":
            self.raise_search(self.previous_screen)
        elif self.previous_screen == "kiosk":
            self.raise_kiosk()
        else:
            warnings.warn("Invalid previous!")

    @handle_exceptions
    def manage_finder_update(self, *_):
        """Updates the search results for the search panel in the manage parts frame. Works the same as update_search"""
        search_term = self.manage_finder_entry.get()

        # scroll back to the top
        self.manage_finder_scrollbox.parent_canvas.yview_moveto(0)

        if self.search_mode == "part":
            self.manage_finder_scrollbox_key.configure(text="  "+list_button_format(("Part Number", "Manufacturer", "UPC", "Date Added", "Location", "Description", "Status"), "part"))
            result = self.controller.part_search(search_term)
        else:
            self.manage_finder_scrollbox_key.configure(text="  "+list_button_format(("User ID", "Name", "Email"), "user"))
            result = self.controller.user_search(search_term, use_full_names=True)

        if isinstance(result, dict):
            result = list(result.values())

        for old_widget in self.manage_finder_widgets: old_widget.pack_forget()

        for val in result:
            new_label = ctk.CTkLabel(master=self.manage_finder_scrollbox, font=manage_finder_font, fg_color="transparent", cursor="hand2", anchor="w")
            new_label.pack(expand=True, fill="x")
            self.manage_finder_widgets.append(new_label)

            if not val or len(val) == 6:
                new_label.configure(text=" No Results")
                continue

            widget_text = " "+list_button_format(val, self.search_mode).strip(" ")

            if len(val) == 3:
                identifier = val[0]
            elif len(val) > 3:
                identifier = val[2]
            else:
                identifier = "No Part Selected"

            # new_label = ctk.CTkTextbox(master=self.manage_finder_scrollbox, font=manage_finder_font, height=18, fg_color="transparent")
            new_label.configure(text=widget_text)

            # new_label.insert("0.0", widget_text)
            new_label.configure(state="disabled")
            new_label.bind("<Button-1>", lambda event=_, u=identifier: self.manage_finder_select(event, upc=u))

    @handle_exceptions
    def raise_and_select(self):
        self.raise_search(self.search_mode)
        self.window.after(20, self.list_button_select)

    @handle_exceptions
    def manage_finder_select(self, *_, upc):
        self.manage_search_box.configure(text=upc)

        # flash white
        frames = 10
        time = 0.09  # time in seconds to finish flash
        for i, hex_int in enumerate(range(255, 71, -9)):
            hex_str = "#"+str(hex(hex_int)).strip("0x").zfill(2)*3
            self.window.after(int((time*1000)*(i/frames)), lambda h=hex_str: self.manage_search_box.configure(fg_color=h))

    @handle_exceptions
    def width_splice(self, text, font_size, max_width=650, use_dict=False):
        """break text after a certain number of pixels in a font"""
        # just skip if there's not any text
        if text.isspace():
            return " "

        hyperlink_pattern = compile(r'\[(.*?)]\((.*?)\)')
        hyperlink_segments = hyperlink_pattern.split(text)
        true_words = {}
        link_text = ""
        for i, part in enumerate(hyperlink_segments):
            if i % 3 == 0:  # normal text
                for word in part.split(" "):
                    true_words[word] = word
            elif i % 3 == 1:  # hyperlinked text
                link_text = part.strip(" ")
            elif i % 3 == 2:  # link
                hyperlink = part.strip(" ")

                true_words[link_text] = f"[{link_text}]({hyperlink})"

        font = ImageFont.truetype("arial.ttf", font_size)
        lines = []
        current_line = ""
        current_width = 0

        for word, full_word in true_words.items():
            if "\n" in word:
                current_width = 0

            word_width = font.getlength(word + " ")
            if current_width + word_width <= max_width:
                current_line += full_word + " "
                current_width += word_width
            else:
                # lines.append(current_line.strip(" "))
                lines.append(current_line)
                current_line = word + " "
                current_width = word_width

        if current_line:
            lines.append(current_line.strip(" "))

        # don't break for hyperlinks
        # for i, line in enumerate(lines):
        #     if len(lines) > i + 2:
        #         lines[i+1] = " ".join((line[i], lines[i+1]))
        #         lines[i] = None

        # lines = [line for line in lines if line]

        return "\n".join(lines)

    @handle_exceptions
    def raise_home_frame(self):
        self.home_frame_base.tkraise()

    @handle_exceptions
    def db_connect(self):
        if self.controller:
            warnings.warn("this should not be here!")

        try:
            with Organizer("postgres", dbname=self.db_name) as _:
                # we were able to access postgres
                self.postgres_exists = True

            # now we should be able to connect as a customer with no problem
            self.controller = Organizer(f"customer_{self.db_name}", dbname=self.db_name)

            self.connection = True
        except p2er.OperationalError as error_msg:
            self.connection = False

    @handle_exceptions
    def print_label(self, upc=None):
        """print a label from a upc code"""
        if not upc:
            upc = self.manage_search_box.cget("text")
            if not (upc.isnumeric() and len(upc) == 12):
                self.popup_msg("Please enter a valid UPC!")
                return

        self.controller.upc_create(upc)

    @handle_exceptions
    def make_link_button(self, itf, ref):
        """
        make a button that links a checked out part to its holder or
        a user with a checkout to the part checked out
        """
        ctk.CTkButton(itf, width=20, height=30, text="Open", command=lambda reference=ref: self.open_reference(ref=ref)).pack(side="right")

    @handle_exceptions
    def open_reference(self, *_, ref):
        if ref.isnumeric():
            self.raise_search("part")
        elif ref.startswith("https://"):
            web_open(ref)
            return
        else:
            self.raise_search("user")

        self.list_button_select(database_key=ref)

    @handle_exceptions
    def checkout_finalize(self, force=False):
        """take the upc and user id and check out the part."""
        self.reverse_users = {" ".join(key[1:2]) if isinstance(key, tuple) else key: val for key, val in self.reverse_users.items()}

        if not self.controller.userid_exists(self.checkout_user):
            self.popup_msg("please select a valid user.")
            return

        upc = self.selected_part_key

        result = self.controller.part_checkout(upc, self.checkout_user, force)

        if result == "-CHECKOUT_SUCCESS-":
            self.popup_msg("Part checked out successfully", "success")
            tmp_key = self.selected_part_key
            if self.previous_screen == "part":
                # if the user was on the part search frame when they checked out
                self.raise_search("part")
                def reselect(): self.list_button_select(database_key=tmp_key)

                self.window.after(10, reselect)
            else:
                # if the user was on the kiosk screen when they checked out
                self.raise_kiosk()

        else:
            # if the part is already checked out by someone else

            # split into error message and part holder
            split_result = result.split(";;")

            # if the formatting doesn't make sense (if everything is working, this should never fire)
            if (not len(split_result) >= 2) or (not split_result[0] == "-PART_HOLDER-"):
                raise Exception("Something went wrong on our end. Try returning the part and returning to checkout.")

            # tell the user that the part is already checked out, and ask if he/she wants to force checkout
            popup = CTkMessagebox(
                title="Are you sure?",
                message=f"This part is already checked out by {split_result[1]}. Check out anyways?",
                options=["Yes", "Cancel"],
                icon="warning"
            )

            if popup.get() == "Yes":
                self.checkout_finalize(force=True)

    @handle_exceptions
    def make_new_form(self, search_mode):
        """makes a new form from a question dictionary"""

        if search_mode == "part":
            # entries_string_variable is a dictionary that links
            entries_storing_variable = self.add_part_entries
            questions_dict = self.part_questions
        else:
            entries_storing_variable = self.add_user_entries
            questions_dict = self.user_questions

        new_form = ctk.CTkFrame(self.workspace)
        new_form.grid(row=0, column=0, sticky="news")

        # back button
        ctk.CTkButton(new_form, fg_color="transparent", hover_color=None, text="⇽ Back", anchor="w", hover=False, command=lambda s=search_mode: self.raise_manage(s)).pack(fill="x", padx=40, pady=20)

        # main question fields
        for question, fields in questions_dict.items():
            # separate the fields
            length, required = fields
            start = "" if required else "(Optional) "

            # make a description text
            ctk.CTkLabel(new_form, text="\n"+start+question, font=("Ariel", 16)).pack()

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
        self.back_to_checkout = False  # don't go back to the kiosk screen

        if self.search_mode == "part":
            self.new_part_form.tkraise()
        else:
            self.new_user_form.tkraise()

        for name, entry in (self.add_part_entries | self.add_user_entries).items():

            entry.delete(0, "end")
            entry.configure(border_color="#565b5e")

    @handle_exceptions
    def edit_part_form(self):
        """edit the information on the selected part or user"""
        # from when search and manage where on the same tab

        user_id_or_upc = self.get_user_input()
        if user_id_or_upc == "-QUIT-": return

        self.form_mode_add = False  # set the form to edit mode and not add mode
        self.back_to_checkout = False  # don't return to kiosk mode

        # if editing a part
        if self.search_mode == "part":
            data = self.controller.part_data(user_id_or_upc)
            self.new_part_form.tkraise()
            self.selected_part_key = user_id_or_upc

            for name, entry in self.add_part_entries.items():
                entry.delete(0, "end")
                entry.insert(0, data[name])

        # if editing a user
        else:
            data = self.controller.user_data(user_id_or_upc)
            self.new_user_form.tkraise()
            for name, entry in self.add_user_entries.items():
                entry.delete(0, "end")
                entry.insert(0, data[name])

    @handle_exceptions
    def get_user_input(self):
        """Get the text from the manage users or manage parts screen"""
        id_upc = self.manage_search_box.cget("text")

        # go ahead and complain if there is nothing in the field
        if not id_upc or id_upc == "No Part Selected" or id_upc == "No User Selected":
            self.popup_msg("Please enter a valid id/upc")
            return "-QUIT-"

            # make sure the part exists
        if self.search_mode == "part":
            if (len(id_upc) != 12) or (not self.controller.part_search(search_term=id_upc, search_columns={"part_upc": True})):
                self.popup_msg("We couldn't find this part UPC")
                return "-QUIT-"
        else:
            results = self.controller.user_search(id_upc, columns={"user_id": True})
            found = False

            for line in results:
                if line == id_upc:
                    found = True
                    break

            if not found:
                self.popup_msg("We couldn't find user "+str(id_upc))
                return "-QUIT-"

        return id_upc

    @handle_exceptions
    def remove_part(self):
        """delete the selected part or user"""
        # get the user input from the search box
        id_upc = self.get_user_input()
        if id_upc == "-QUIT-": return

        ask_message = CTkMessagebox(title="Are you sure?", message=f"Delete {self.search_mode} {id_upc}?", options=["Yes", "Cancel"], icon="question")
        if ask_message.get() == "Cancel": return

        result = self.controller.delete_generic(id_upc, self.search_mode)

        if result == "-PARTS_STILL_CHECKED_OUT-":

            warning_msg = "This user still has parts checked out!" if self.search_mode == "user" else "This part is still checked out!"

            popup = CTkMessagebox(title="Warning!", message=f"{warning_msg}\nWould you like to return checked out part(s)?", options=["Yes", "Cancel"], icon="warning")
            result = popup.get()
            if result.lower() == "yes":
                self.controller.clear_checkout(id_upc)
                self.controller.delete_generic(id_upc, self.search_mode)
            else:
                return

        # things from before the manage users/parts were separated from the search
        # self.list_button_select()
        # self.update_search()

        self.popup_msg(f"Deleted {self.search_mode} {id_upc}", popup_type="success")
        self.manage_search_box.configure(f"No {self.search_mode.title()} Selected")
        self.manage_finder_update()

    @handle_exceptions
    def submit_controller(self):
        """either updates (edit mode) or adds (add mode) a new part depending on the submit mode"""
        fields = []

        if self.search_mode == "part":
            entries = self.add_part_entries
            reference_list = list(self.part_questions.values())
        else:
            entries = self.add_user_entries
            reference_list = list(self.user_questions.values())

        for i, item in enumerate(entries.values()):
            field_text = item.get()

            fields.append(field_text)
            if item.get() == "" and reference_list[i][1]:
                item.configure(border_color=red)

        i = 0
        for field in fields:
            # if a required field is left empty
            if field == "" and reference_list[i][1]:
                self.popup_msg("You have empty fields!")
                return

            i += 1

        result = ""

        # new part mode
        if self.form_mode_add:
            try:
                if self.search_mode == "part":
                    result = self.controller.add_part(fields[3], *fields[:3], *fields[4:])
                else:
                    result = self.controller.add_user(*fields)

                    if result == "-NAME_ALREADY_TAKEN-":
                        self.popup_msg("This name is already in use")
                        self.add_user_entries["First name"].configure(border_color=red)
                        self.add_user_entries["Last name"].configure(border_color=red)
                        return

            except p2er.UniqueViolation:
                raise Exception("a value that was entered that should be unique was already found in the database")

        # edit part mode
        else:
            if self.search_mode == "part":
                print("before")
                selected_part_upc = self.get_user_input()
                print("selected part upc: "+str(selected_part_upc))

                # if they somehow got here but didn't have a valid upc? not sure how this would happen.
                if selected_part_upc == "-QUIT-":
                    self.raise_search("part")
                    self.popup_msg("Invalid UPC")
                    return

                result = self.controller.update_part(selected_part_upc, mfr=fields[0], mfr_pn=fields[1], desc=fields[2], url=fields[3])

                if result == "-PLACEMENT_ALREADY_TAKEN-":
                    self.popup_msg("This placement location is already in use.")
                    return
            elif self.search_mode == "user":
                selected_part_key = self.get_user_input()

                # if they somehow got here but didn't have a valid upc? not sure how this would happen.
                if selected_part_key == "-QUIT-":
                    self.raise_search("user")
                    self.popup_msg("Invalid User ID")
                    return

                # try to update
                result = self.controller.update_user(selected_part_key, *fields[0:3])

                # if the database says that you can't do that
                if result == "-NAME_ALREADY_TAKEN-":
                    self.popup_msg("This name is already in use.")
                    return
                elif result == "-EMAIL_ALREADY_TAKEN-":
                    self.popup_msg("This email is already in use.")
                    return

        if self.back_to_checkout:
            self.checkout_continue(auto_select=result)
        else:
            self.raise_manage(self.search_mode)
            self.manage_search_box.configure(f"No {self.search_mode} Selected")
            self.manage_finder_update()

    @handle_exceptions
    def reconnect_db(self):
        # make a connection to the database
        try:
            self.controller = Organizer(f"customer_{self.db_name}", dbname=self.db_name)
            self.connection = True
        except Exception as er:
            # raise er
            self.connection = False
            self.popup_msg(er)

    @handle_exceptions
    def forget_popup(self, popup_id):
        if popup_id == self.popup_counter:
            self.popup_window.place_forget()

    @handle_exceptions
    def popup_msg(self, error_text, popup_type="error", display_time_sec=2):
        self.popup_counter += 1
        popup_id = self.popup_counter

        # draw
        error_text = self.width_splice(str(error_text), 17)
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
    def drop_db(self):
        """get rid of the db"""

        # confirm if the user wants to nuke everything
        popup = CTkMessagebox(title="Are you sure?", message="This will delete everything in the database.", icon="warning", options=["Drop database", "Cancel"])
        result = popup.get()
        if result.lower() != "drop database": return

        # make sure that we are able to connect to the database
        if not self.check_db_connection(accept_postgres=True): return

        # try to format the database as postgres
        with Organizer("postgres", dbname=self.db_name) as postgres:
            postgres.drop_db(self.db_name)
        self.popup_msg("Database dropped successfully", "success")

    @handle_exceptions
    def format_database(self):
        """delete the database and remake everything"""

        # confirm if the user wants to nuke everything
        # said "response is not yes" here instead of "response is no" because force
        # closing will count as a no, so one less way to accidentally nuke
        popup = CTkMessagebox(title="Are you sure?", message="This will delete everything in the database.", icon="warning", options=["Format", "Cancel"])
        result = popup.get()
        if result.lower() != "delete": return

        # make sure that we are able to connect to the database
        if not self.check_db_connection(accept_postgres=True): return

        # try to format the database as postgres
        try:
            with Organizer("postgres", dbname=self.db_name) as postgres:
                postgres.format_database(self.db_name)
            self.popup_msg("Database formatted successfully", "success")
        except Exception as error:
            # self.popup_msg(str(error))
            raise error
        finally:
            self.reconnect_db()

    @handle_exceptions
    def populate_database(self):
        """fill the database with sample data"""

        # confirmation
        popup = CTkMessagebox(title="Are you sure?", message="This will fill the database with junk data for testing.", icon="warning", options=["Populate", "Cancel"])
        result = popup.get()
        if result.lower() != "populate": return

        # make sure that we are able to connect to the database
        if not self.check_db_connection(accept_postgres=True): return

        # try to format the database as postgres
        try:
            with Organizer(f"customer_{self.db_name}", dbname=self.db_name) as postgres:
                postgres.populate_db(self.db_name)
                self.popup_msg("Database populated successfully", "success")
        except Exception as error:
            self.popup_msg(str(error))

    @handle_exceptions
    def checkin_continue(self, *_):
        # check for database connection, a srelected part, and in part mode
        if not self.check_db_connection(): return
        if not self.selected_part_key: return self.popup_msg("you need to select a part first!")

        popup = CTkMessagebox(message="Return part "+self.controller.part_num_from_upc(self.selected_part_key)+"?", title="Are you sure?", options=["Yes", "Cancel"], icon="question")
        response = popup.get()
        if response != "Yes": return

        if self.previous_screen == "kiosk": self.raise_kiosk()

        # database checkin
        upc = self.selected_part_key  # self.checkin_barcode.get()
        result = self.controller.part_checkin(upc)

        # relay the database message
        if "success" in result.lower():
            self.popup_msg(result, "success", 5)
        else:
            self.popup_msg(result)

        self.update_search()
        self.window.after(20, self.list_button_select)

    @handle_exceptions
    def checkout_continue(self, *_, auto_select=None):
        """check out a part. Was originally the second step after scanning the part code"""
        print("checkout continue!")

        # if a part is not selected, you can't check out
        if not self.selected_part_key:
            self.popup_msg("You need to select a part first!")
            return

        # check for database connection
        if not self.check_db_connection(): return

        # get the upc from the entry and make sure it's in the database
        upc = self.selected_part_key
        if not self.controller.upc_exists(upc):
            self.popup_msg("UPC code not found in database")
            return

        # clear out whatever old stuff might be in this or the next panel
        self.checkout_update_search()
        self.force_prompt.pack_forget()
        self.checkout_user_search.delete("0", "end")

        # deselect the user
        self.checkout_finalize_button.configure(**button_disable)
        self.checkout_message.configure(text="No account selected.")

        if auto_select: self.checkout_user_select(auto_select)

        # move on to the user selection page
        self.checkout_user_frame.tkraise()

    @handle_exceptions
    def clear_part_results(self):
        # clear the scrolling frame that contains all the parts
        for pwidget in self.part_widgets:
            pwidget.pack_forget()
        self.part_widgets = []

    @handle_exceptions
    def raise_kiosk(self):
        """Enter kiosk mode"""

        # clear old entry info
        self.kiosk_entry_var.set("")
        self.kiosk_check_upc()
        self.kiosk_next_step.place_forget()
        self.kiosk_message.place_forget()
        self.back_to_checkout = True
        self.kiosk_frame.tkraise()
        self.kiosk_entry.focus()
        self.previous_screen = "kiosk"

    @handle_exceptions
    def raise_manage(self, search_type):
        """raise the page for either the user or part management page"""

        # clear out the input box
        self.manage_search_box.configure(text="No Part Selected")

        # try again to connect to the database (why is this in the raise_manage function? does this need to be here?)
        # if (not self.controller) or self.controller.cursor_exists():
        #     self.db_connect()

        # make sure the search mode is valid
        if search_type.lower() in ["user", "part"]:
            self.search_mode = search_type.lower()
        else:
            raise Exception("Invalid search type: Must be either 'user' or 'part'. This is most likely a backend issue.")

        # change text of some elements
        id_type = "the User ID" if self.search_mode == "user" else "or scan the UPC"
        self.manage_subtitle.configure(text=f"Enter {id_type} of the {self.search_mode} that you would like to configure, or click \"Add\"")
        self.add_part_button.configure(text=f"+ Add a {self.search_mode.title()}")  # add a [part/user] button

        # show/hide the print button
        if search_type == "user":
            self.print_button.pack_forget()
            self.manage_title.configure(text="Mange Users")
        else:
            self.print_button.pack(side="left", padx=10)
            self.manage_title.configure(text="Mange Parts")

        # update the manage finder
        self.manage_finder_entry.delete("0", "end")
        self.manage_finder_update()

        # raise the management frame
        self.manage_parts_frame.tkraise()

    @handle_exceptions
    def raise_search(self, search_type):
        """clear the search box and raise either 'part search' or 'user search' depending on the search_type"""

        self.previous_screen = search_type

        # clear the selected part key, as no part is selected
        self.selected_part_key = None
        for button in self.check_in_out_buttons: button.configure(**button_disable)

        # try again to connect to the database
        if (not self.controller) or self.controller.cursor_exists():
            pass  # self.db_connect()

        # this should never be fired
        if search_type not in ["user", "part"]: raise Exception("Invalid search type: Must be either 'user' or 'part'. This is most likely a backend issue.")

        # configure app to new search type
        self.search_mode = search_type

        # search header
        if self.search_mode == "part":
            self.search_labels.configure(text="  "+list_button_format(("Part Number", "Manufacturer", "UPC", "Date Added", "Last Location", "Description", "Status"), "part"), anchor="w")
            self.check_in_out_frame.pack()
        else:
            self.search_labels.configure(text="  "+list_button_format(("User ID", "Name", "Email"), "user"), anchor="w")
            self.check_in_out_frame.pack_forget()
            self.thin_frame.grid_forget()

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
        if not active: return

        # scroll back to the top
        self.result_parts._parent_canvas.yview_moveto(0)

        search = self.search_box.get()
        if self.search_mode == "part":
            parts = self.controller.part_search(search)
            names_dict = {part[2]: tuple(part) for part in parts}
            parts = [part[2] for part in parts]
        elif self.search_mode == "user":
            names_dict = self.controller.user_search(search, use_full_names=True)
            parts = list(names_dict.keys())
        else:
            raise Exception("the search mode is not set to either part or user.")

        # add the parts into the scrolling frame
        for index, part in enumerate(parts):
            if part.isnumeric():  # parts
                button_text = names_dict[part]
                name_text = list_button_format(button_text, self.search_mode) if list(part)[0] != "No matching items" else "No matching items"
            else:  # users
                name_text = list_button_format(names_dict[part], "user")

            name_text = name_text.strip(" ")

            part_widget = ButtonWithVar(
                master=self.result_parts,
                var_value=part,
                text=name_text,
                fg_color="transparent",
                hover=not part == "No matching items",
                font=listbutton_font, anchor="w",
                command=lambda i=index, p=str(part): self.list_button_select(i, p),
                text_color="#afe3ac" if name_text.split(" ")[0] == "Available" else "#dce1ee"
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
        """select the targeted part and update the results accordingly"""
        if not database_key:
            database_key = self.selected_part_key

        if not button_index:
            for i, button in enumerate(self.part_widgets):
                if _int(button.get_var()) == _int(database_key):
                    button_index = i
                    break

        if (not button_index) and button_index != 0: return

        try:
            button = self.part_widgets[button_index]
        except Exception:     # who knows what could happen with this one
            #                   what does that mean???
            return

        if database_key.lower() == "no matching items": return

        # un-highlight the old selection
        if self.selected_part:
            self.selected_part.configure(fg_color="transparent")

        if database_key.lower() == "no results" or database_key.lower() == "no matching items": return

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

        # grey out either "check out" or "check in"
        active = 0 if button.cget("text")[0] == "A" else 1
        disabled = 1-active

        self.check_in_out_buttons[active].configure(**button_enable)
        self.check_in_out_buttons[disabled].configure(**button_disable)

        # display the part info
        self.clear_output_box()

        self.output_box.pack_forget()
        loading = ctk.CTkLabel(self.part_generic_info, text="\nLoading...", font=("Arial", 18))
        loading.pack()

        # make a holder for the content
        for key, value in part_info.items():
            # generate a frame to put the item and text side by side
            item_frame = ctk.CTkFrame(self.output_box, fg_color="transparent")

            # object description
            ctk.CTkLabel(item_frame, fg_color="transparent", text=key).pack(side="left")

            # object value
            if (key == "Parts checked out" or key == "Link to original part") and value != "None":
                # special rules for parts checked out
                if key == "Parts checked out" and False:
                    stack_boxes_frame = ctk.CTkScrollableFrame(item_frame, fg_color="transparent", height=400)
                else:
                    stack_boxes_frame = ctk.CTkFrame(item_frame, fg_color="transparent")  #, height=500)

                stack_boxes_frame.pack(side="right")

                if not isinstance(value, list):
                    value = [value]

                # make a box for each checkout
                for part in value:
                    yet_another_frame = ctk.CTkFrame(stack_boxes_frame, fg_color="transparent")
                    yet_another_frame.pack()
                    make_box(yet_another_frame, part, tall=True)
                    pn = part.split("\n")[0]
                    self.make_link_button(yet_another_frame, pn)
            elif key.lower() != "no results":
                # normal value boxes, skipping "no matching items".
                make_box(item_frame, value, key == "Description")

            # jump to reference button
            if key.lower() == "currently checked out by" and value.lower() != "not checked out":
                self.make_link_button(item_frame, value.split("(")[1][:-1])

            # save the item frame to a list so that we can draw everything at the same time
            self.output_frames.append(item_frame)
            item_frame.pack(fill="x", expand=True)

        loading.pack_forget()
        self.output_box.pack(fill="both", expand=True)
        # new_text = self.width_splice(new_text, 16, 400)

        # finally, highlight the selected item in the scrolling frame
        button.configure(fg_color="#1f6ba5")
        self.selected_part = button
        self.selected_part_key = database_key
