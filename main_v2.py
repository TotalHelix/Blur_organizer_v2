import json

from gui_elements_v2 import MainWindow, ctk
import os
import lorem


# define fonts
title = ("Arial", 20)
subtitle = ("Ariel", 18)
selected_database = ""
global select_db_var
global selector_window
global options_menu

# json of remembered databases
json_location = os.getenv("APPDATA") + "\\Blur_Part_Organizer\\"
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
    print("start button hit")
    global selected_database
    global selector_window
    selected_database = select_db_var.get()
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


def db_add_gui(part_to_edit=None):
    """
    Bring up the form for adding a new database.
    :param part_to_edit: list [display name, database name] of database option that you want to edit. If this option
        is left blank then the form will add a new part instead.
    :return: None. Edits the db_dict dictionary.
    """

    ####################
    # Create the GUI
    ####################

    # new window
    form_window = ctk.CTk()
    form_window.resizable(False, False)

    # form questions
    form_questions = ["Display Name", "Database Name"]
    form_answers = []
    if part_to_edit:
        fill_text = part_to_edit
    else:
        fill_text = ["" for _ in range(2)]

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
    ctk.CTkButton(cc_frame, text="Confirm", command=lambda: accept_db_form(form_answers, form_window, part_to_edit)).grid(row=0, column=0, padx=10)
    ctk.CTkButton(cc_frame, text="Cancel", command=form_window.destroy).grid(row=0, column=1, padx=10)
    cc_frame.pack(pady=30)

    form_window.mainloop()
    print("form closed")


def accept_db_form(entry_widgets, form_window, edit_entry):
    """
    Take all the entry widgets in the "create new database" form and add them to the dictionary
    :param entry_widgets: A list of length 2: [str Display Name, str Database Name]
    :param form_window: the window of the form so that it can be closed
    :return: None
    """
    update_options(
        entry_widgets[0].get(),  # display name
        entry_widgets[1].get()   # database name
    )

    form_window.destroy()


def update_options(display_name=None, db_name=None):
    """
    Refresh the OptionsMenu and optionally add a new value at the same time
    ** If either display_name or db_name is left blank a new entry will NOT be added. **

    :param display_name: optional new item to add to the list. This is the name that will be displayed in the GUI
    :param db_name: the database actual name that will be fired when the display name above is clicked.
    :return: None
    """
    global db_dict

    if display_name and db_name:
        db_dict[display_name] = db_name

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
    ctk.CTkButton(se_frame, text="Edit", command=lambda: db_add_gui([select_db_var.get(), db_dict[select_db_var.get()]])).grid(row=0, column=1, padx=20)

    # OR
    ctk.CTkLabel(selector_window, text="OR").pack(pady=15)

    # Create New and Connect Existing buttons
    cnce_frame = ctk.CTkFrame(selector_window, fg_color="transparent")
    cnce_frame.pack()
    ctk.CTkButton(cnce_frame, text="Create New", command=create_new).grid(row=0, column=0, padx=20, pady=2)
    ctk.CTkButton(cnce_frame, text="Connect Existing").grid(row=0, column=1, padx=20)

    # empty space at bottom
    ctk.CTkLabel(selector_window, text="").pack()

    selector_window.mainloop()


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
