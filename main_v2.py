import json
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

# json of remembered databases
json_location = os.getenv("APPDATA") + "\\Blur_Part_Organizer\\"  # if you're changing this remember to change the one in db_interactions.py as well.
json_file_name = "saved_databases.json"
json_path = json_location+json_file_name
if os.path.exists(json_path):
    with open(json_path, "r") as read_json_file:
        db_dict = json.load(read_json_file)
else:
    os.makedirs(json_location, exist_ok=True)
    db_dict = {}


def random_word():
    """
    generate a single random word, all lowercase
    :return: the second word of a lorem ipsum random sentence.
    """

    return lorem.sentence().split(" ")[1]


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


def db_add_gui(edit_mode=False, add_db_name=""):
    """
    Bring up the form for adding a new database.
    :param edit_mode: list [display name, database name] of database option that you want to edit. If this option
        is left blank then the form will add a new part instead.
    :param add_db_name: the database name of the part that you are adding. This is used for adding a database from the
        "Connect Existing" gui
    :return: None. Edits the db_dict dictionary.
    """
    global db_dict
    global select_db_var

    if edit_mode:
        part_display = select_db_var.get()

        # make sure a valid db has been selected
        print(f"part_to_edit not in list(db_dict.keys()): {part_display not in list(db_dict.keys())}")
        print(f"part_to_edit: {part_display}, list(db_dict.keys()): {list(db_dict.keys())}")
        if edit_mode and part_display not in list(db_dict.keys()): return

        part_database = db_dict[part_display]
        part_to_edit = [part_display, part_database]
        fill_text = part_to_edit

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
    ctk.CTkButton(cc_frame, text="Confirm", command=lambda: accept_db_form(form_answers, form_window, part_display)).grid(row=0, column=0, padx=10)
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


def accept_db_form(entry_widgets, form_window, edit_entry=None):
    """
    Take all the entry widgets in the "create new database" form and add them to the dictionary
    :param entry_widgets: A list of length 2: [str Display Name, str Database Name]
    :param form_window: the window of the form so that it can be closed
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
    form_window.destroy()


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

    print(f"started with old_display_name of \"{old_display_name}\"")
    if display_name and db_name:
        print(f"accepted entries {display_name} and {db_name}.")
        if old_display_name:
            print("deleting old part" + old_display_name)
            del db_dict[old_display_name]

        db_dict[display_name] = db_name
        print(f"added new entry \"{display_name}\": \"{db_name}\"")

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
    ctk.CTkButton(se_frame, text="Edit", command=lambda: db_add_gui(True)).grid(row=0, column=1, padx=20)

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


def connect_existing():
    """Connect to a postgres database that already exists"""
    print("Hey guys! 🐶")

    # list default
    db_list = ["No Databases Found"]

    # try to get databases
    try:
        with Organizer(user="postgres") as pg:
            db_list = [item[0] for item in pg.select_all_db()]

    # give an error message if we can't get a database
    except Exception as er:
        CTkMessagebox(title="Error", message="Something went wrong!\nError: "+str(er), option_1="OK", icon="cancel")

    # db selector window
    db_con_window = ctk.CTk()
    db_con_window.title("Existing database to add")
    db_con_window.resizable(False, False)

    # frame to hold all the databases
    db_disp_frame = ctk.CTkScrollableFrame(db_con_window)
    for db_name in db_list:
        new_button = ctk.CTkButton(db_disp_frame, text=db_name, fg_color="transparent", command=lambda n=db_name: db_add_gui(add_db_name=n))

        new_button.pack()
    db_disp_frame.pack(padx=13, pady=13)

    # Done button
    ctk.CTkButton(db_con_window, text="Done", command=db_con_window.destroy).pack(pady=13)

    # start the window
    db_con_window.mainloop()


if __name__ == "__main__":
    database_selector()

    # write to the json file
    with open(json_path, "w") as f:
        json.dump(db_dict, f, indent=4)

    print(f"selected database: {selected_database}")

    if selected_database in list(db_dict.keys()):
        database = db_dict[selected_database]
        print(f"{selected_database} is the key for {database}! Launching {database}...")
        app = MainWindow(db_name=database)

        app.window.mainloop()
    else:
        print(f"{selected_database} wasn't a key in the database dict")
        # you fail
        pass
