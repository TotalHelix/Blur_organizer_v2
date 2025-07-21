import json
import shutil
import requests
from gui_elements_v2 import MainWindow, ctk, Organizer, CTkMessagebox
import os
import lorem


# define fonts
title = ("Arial", 20)
subtitle = ("Ariel", 18)
selected_database = ""
red_button = {"fg_color": "#d62c20", "hover_color": "#781610"}
global select_db_var
global selector_window
global options_menu


"""
OK this is how the db_dict works:

Display Name: {
    "type": "local",
    "connection data": {
        "username": username,
        "database": database name,
        "password": password
    }
}, 

Display Name: {
    "type": "remote",
    "connection data": {
        "username": username, 
        "database": database name, 
        "port": port, 
        "host": ip, 
        "password": password
    }
}
"""


# json of remembered databases
json_location = os.getenv("APPDATA") + "\\Blur_Part_Organizer\\"  # if you're changing this remember to change the ones in the other files as well.
json_file_name = "saved_databases.json"
json_path = json_location+json_file_name
if os.path.exists(json_path):
    with open(json_path, "r") as read_json_file:
        db_dict = json.load(read_json_file)
else:
    os.makedirs(json_location, exist_ok=True)
    db_dict = {}


def start_button():
    """
    Function for when the start button is pressed. Takes the current database selected in the options menu and launches
        the program centered for that database.
    Destroys the selector window when called.
    :return: None
    """
    global selected_database
    global selector_window

    selected_database = select_db_var.get()

    # don't start if no database is selected
    if selected_database == "- Select -": return

    # close the selector window
    selector_window.destroy()


def create_new():
    """
    Opens the gui to create a new database
    :return: None
    """
    global db_dict
    global options_menu

    db_add_gui()

    # update the options menu
    update_options()


def db_add_gui(edit_mode=False, add_db_name="", windows_to_close=None):
    """
    Bring up the form for adding a new database.
    :param edit_mode: list [display name, database name] of database option that you want to edit. If this option
        is left blank then the form will add a new part instead.
    :param add_db_name: the database name of the part that you are adding. This is used for adding a database from the
        "Connect Existing" gui
    :param windows_to_close: list of windows that are closed when submitted.
    :return: None. Edits the db_dict dictionary.
    """
    global db_dict
    global select_db_var
    if edit_mode:
        part_display = select_db_var.get()

        # make sure a valid db has been selected
        if part_display not in db_dict.keys(): return

        part_database = db_dict[part_display]["connection data"]["database"]
        fill_text = [part_display, part_database]

    else:
        fill_text = ["", add_db_name]
        part_display = None

    ####################
    # Create the GUI
    ####################

    # new window
    form_window = ctk.CTk()
    form_window.title = "Database Info"
    form_window.resizable(False, False)

    # default windows to close
    if not windows_to_close: windows_to_close = []
    windows_to_close.append(form_window)

    # form questions
    form_questions = ["Display Name", "Database Name"]
    form_answers = []

    for i, question in enumerate(form_questions):
        # space
        ctk.CTkLabel(form_window, text="").pack(padx=150)

        # question text
        ctk.CTkLabel(form_window, text=question, font=subtitle).pack()

        # input box
        question_input_box = ctk.CTkEntry(form_window, width=200, height=30, placeholder_text=fill_text[i])
        question_input_box.pack()
        form_answers.append(question_input_box)

    # Confirm Cancel
    cc_frame = ctk.CTkFrame(form_window, fg_color="transparent")
    ctk.CTkButton(cc_frame, text="Confirm", command=lambda: accept_db_form(form_answers, windows_to_close, part_display)).grid(row=0, column=0, padx=10)
    ctk.CTkButton(cc_frame, text="Cancel", command=form_window.destroy).grid(row=0, column=1, padx=10)
    if edit_mode: ctk.CTkButton(cc_frame, text="Delete", command=lambda: delete_db_link(part_display, form_window), **red_button).grid(row=1, column=0, columnspan=2, pady=12)
    cc_frame.pack(pady=30)

    form_window.mainloop()


def delete_db_link(db_display_name, form_window=None):
    """
    Delete the database, and optionally close the form window
    :param form_window: optional tkinter window to close.
    :param db_display_name: The display name of the database to delete from the dictionary.
    :return: None
    """
    global db_dict
    global select_db_var

    # Are you sure?
    popup = CTkMessagebox(
        title="Are you sure?",
        message="This will only delete the database link and NOT the actual data.",
        icon="warning",
        option_1="Delete",
        option_2="Cancel"
    )

    # again, answer isn't delete is safer than answer is cancel.
    if popup.get() != "Delete": return

    del db_dict[db_display_name]
    form_window.destroy()
    update_options()

    if len(db_dict) > 0:
        select_db_var.set(list(db_dict.keys())[0])
    else:
        select_db_var.set("- Select -")


def value_or_default(entry_widget):
    """
    If there is text in the entry widget, return that. Otherwise, return the placeholder text.
    :param entry_widget:
    :return:
    """

    # try to get the entry text first
    entry_text = entry_widget.get()
    if entry_text: return entry_text

    # get the placeholder text
    return entry_widget.cget("placeholder_text")


def accept_db_form(entry_widgets, form_windows, edit_entry=None):
    """
    Take all the entry widgets in the "create new database" form and add them to the dictionary
    :param entry_widgets: A list of length 2: [str Display Name, str Database Name]
    :param form_windows: list of windows to be closed.
    :param edit_entry: string display name of the part that you're editing. Adds new part if value is None (default)
    :return: None
    """
    global select_db_var

    new_display_name = value_or_default(entry_widgets[0])
    new_db_name      = value_or_default(entry_widgets[1])

    # update the option
    update_options(
        new_display_name,   # display name
        new_db_name,        # database name
        edit_entry          # old display name to delete
    )

    # select the new option
    select_db_var.set(new_display_name)

    # close the windows
    for window in form_windows:
        window.destroy()


def update_options(display_name=None, db_name=None, old_display_name=None):
    """
    Refresh the OptionsMenu and optionally add a new value at the same time
    ** If either display_name or db_name is left blank a new entry will NOT be added. **

    :param display_name: optional new item to add to the list. This is the name that will be displayed in the GUI
    :param db_name: the database actual name that will be fired when the display name above is clicked.
    :param old_display_name: string name of the dictionary entry to remove.
    :return: None
    """
    global db_dict

    # if a valid display name and database name exist
    if display_name and db_name:

        # if there is an old database to delete (e.g. we're editing)
        if old_display_name:
            del db_dict[old_display_name]

        db_dict[display_name] = {
            "type": "local",
            "connection data": {
                "database": db_name,
                "password": "blur4321",
                "user": "postgres"
            }
        }

    options_menu.configure(values=list(db_dict.keys()))


def database_selector():
    """
    The main database selector program. This is where a user picks a database
    :return: None. The selected database is stored in the global `selected_db_var` StringVar, get it with
        `selected_database_string = selected_db_var.get()`
    """
    global selector_window
    global select_db_var
    global options_menu
    selector_window = ctk.CTk()
    selector_window.title("Connect the Organizer to a database")
    selector_window.resizable(False, False)

    ################################
    # selector window widgets
    ################################

    # big test at the top "select a database
    ctk.CTkLabel(selector_window, text="Select a database to\n connect to.", font=title).pack(padx=150, pady=15)

    # dropdown
    select_db_var = ctk.StringVar(value="- Select -")
    options_menu = ctk.CTkOptionMenu(selector_window, width=350, height=35, values=list(db_dict.keys()), variable=select_db_var, fg_color="#171717", button_color="#171717")
    options_menu.pack(padx=150, pady=10)

    # Start and Edit buttons
    se_frame = ctk.CTkFrame(selector_window, fg_color="transparent")
    se_frame.pack()
    ctk.CTkButton(se_frame, text="Start!", command=start_button).grid(row=0, column=0, padx=20, pady=2)
    ctk.CTkButton(se_frame, text="Edit", command=edit_db).grid(row=0, column=1, padx=20)

    # OR
    ctk.CTkLabel(selector_window, text="OR").pack(pady=15)

    # Create New and Connect Existing buttons
    cnce_frame = ctk.CTkFrame(selector_window, fg_color="transparent")
    cnce_frame.pack()
    ctk.CTkButton(cnce_frame, text="Create New", command=create_new).grid(row=0, column=0, padx=20, pady=2)
    ctk.CTkButton(cnce_frame, text="Connect Existing", command=connect_existing).grid(row=0, column=1, padx=20)

    # empty space at bottom
    ctk.CTkLabel(selector_window, text="").pack()

    selector_window.mainloop()


def edit_db():
    """edit the currently selected database"""
    global select_db_var
    global db_dict

    # get the database name and data
    db_name = select_db_var.get()
    print(db_name, "in", list(db_dict.keys()))
    if db_name not in list(db_dict.keys()): return
    db_data = db_dict[db_name]

    # if this is a local database
    if db_data["type"] == "local":
        db_add_gui(edit_mode=True)

    # if we're connecting to a remote database
    elif db_data["type"] == "remote":
        remote_con_options(edit_mode=True)

    # if it's something else??
    else:
        raise Exception(f"Unexpected database type: {db_data['type']}")


def connect_existing():
    """Connect to a postgres database that already exists"""

    # list default
    no_db_msg = "No Databases Found"
    db_list = [no_db_msg]

    # try to get databases
    try:
        with Organizer(conn_type="local", conn_info={"database": "postgres", "user": "postgres", "password": "blur4321"}) as pg:
            db_list = [item[0] for item in pg.select_all_db()]

    # give an error message if we can't get a database
    except Exception as er:
        CTkMessagebox(title="Error", message="Something went wrong!\nError: "+str(er), option_1="OK", icon="cancel")

    # db selector window
    db_con_window = ctk.CTk()
    db_con_window.title("Existing database to add")
    db_con_window.resizable(False, False)

    # subtitle message for local databases
    ctk.CTkLabel(db_con_window, text="Connect to a local database").pack(padx=30, pady=6)

    # frame to hold all the databases
    db_disp_frame = ctk.CTkScrollableFrame(db_con_window)
    for db_name in db_list:
        new_button = ctk.CTkButton(db_disp_frame, text=db_name, fg_color="transparent", command=lambda n=db_name, w=db_con_window: db_add_gui(add_db_name=n, windows_to_close=[w]))
        new_button.pack()

    db_disp_frame.pack(padx=13, pady=7)

    # Done button
    ctk.CTkButton(db_con_window, text="Done", command=db_con_window.destroy).pack(pady=13)

    # subtitle message for remote databases
    edge = "-"*25
    ctk.CTkLabel(db_con_window, text=edge+" OR "+edge).pack(padx=50)
    ctk.CTkButton(db_con_window, text="Remote Database", command=lambda w=db_con_window: remote_con_options(w)).pack(padx=30, pady=12)

    # start the window
    db_con_window.mainloop()


def remote_con_options(connect_window=None, edit_mode=False):
    global select_db_var

    remote_add_window = ctk.CTk()
    selected_db_name = select_db_var.get()  # only used in edit mode

    # link each field prompt (keys) to the json value (values)
    fields = {
        "IP Address": "host",
        "Port": "port",
        "Username": "user",
        "Password": "password",
        "Database Name": "database",
        "Display Name": "Display Name"
    }

    field_responses = {}

    for field_prompt, json_val in fields.items():
        # the frame to hold it
        long_frame = ctk.CTkFrame(remote_add_window, fg_color="transparent")
        long_frame.pack(pady=7)

        # make the variable for the entry
        string_var = ctk.StringVar(long_frame, value="")
        field_responses[json_val] = string_var

        # The label and entry box
        ctk.CTkLabel(long_frame, text=field_prompt, width=150).grid(row=0, column=0)
        ctk.CTkEntry(long_frame, textvariable=string_var).grid(row=0, column=1, padx=20)

        # default text for edit mode
        if edit_mode:
            # the display name is a bit different, as it's a key not a value
            if json_val == "Display Name": string_var.set(selected_db_name)

            # set the filed text
            else: string_var.set(db_dict[selected_db_name]["connection data"][json_val])

    # the "connect" button
    ctk.CTkButton(remote_add_window, text="Connect", command=lambda: add_remote(field_responses, [remote_add_window, connect_window], edit_mode=edit_mode)).pack(pady=10)

    # the "delete" button (if in edit mode
    if edit_mode: ctk.CTkButton(remote_add_window, text="Delete", command=lambda n=selected_db_name, r=remote_add_window: delete_db_link(n, r), **red_button).pack(pady=10)

    remote_add_window.mainloop()


def add_remote(entries_list, windows_to_close, edit_mode=False):
    """Add a remote connection to the dictionary from the list of entries that we have."""
    global db_dict
    global select_db_var

    # if we're in edit mode, delete the original first to avoid overlap
    if edit_mode:
        del db_dict[select_db_var.get()]

    display_name = entries_list.pop("Display Name").get()
    db_dict[display_name] = {
        "type": "remote",
        "connection data": {
            val_to_add: value_or_default(entries_list[val_to_add])
            for val_to_add in ["database", "user", "password", "host", "port"]
        }
    }

    # destroy all open windows (except for the main one of course)
    for window in windows_to_close:
        if window: window.destroy()

    select_db_var.set(display_name)


def setup():
    """Pull important resources from the cloud to the local machine.
    Right now this is just images for image buttons."""
    resources_path = json_location+"resources\\"

    # if this path doesn't exist yet, create the resources folder
    if not os.path.exists(resources_path):
        os.makedirs(resources_path)

    remote_resources_path = "https://github.com/TotalHelix/Blur_organizer_v2/raw/main/"
    images_to_download = [
        "images/Check_Out.png",
        "images/Check_Out_hover.png",
        "images/Return.png",
        "images/Return_hover.png",
        "images/Uncheck Stack Builder.png",
        "images/connect_local_db.png",
        "images/connect_remote.png",
        "images/Database_Connection.png",
        "images/new_database_details.png",
        "README.md"
    ]

    for file in images_to_download:
        local_path = resources_path+file.replace("images/", "")

        # if the file already exists, we don't need to re-download it
        if os.path.isfile(local_path): continue

        # get the image from github
        image_data = requests.get(remote_resources_path+file, stream=True)

        # write the image bytes file
        with open(local_path, "wb") as image_file:
            shutil.copyfileobj(image_data.raw, image_file)


if __name__ == "__main__":
    setup()

    database_selector()

    # write to the json file
    with open(json_path, "w") as f:
        json.dump(db_dict, f, indent=4)

    print(f"selected database: {selected_database}")

    # if the database is in the json file/dictionary
    if selected_database in list(db_dict.keys()):
        database = db_dict[selected_database]["connection data"]
        print(f"{selected_database} is the key for {database}! Launching {database}...")

        app = MainWindow(conn_info=database)
        app.window.mainloop()
    else:
        print(f"{selected_database} wasn't a key in the database dict")
        # you fail
        pass
