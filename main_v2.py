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
    return lorem.sentence().split(" ")[1]


def start_button():
    print("start button hit")
    global selected_database
    global selector_window
    selected_database = select_db_var.get()
    selector_window.destroy()


def create_new():
    print("create_new_fired")
    global db_dict
    global options_menu

    db_dict[str(random_word())] = random_word()
    # TODO not sure how do properly do this ⬇
    options_menu.values = list(db_dict.keys())
    print("assigned")


def database_selector():
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
    ctk.CTkButton(se_frame, text="Edit").grid(row=0, column=1, padx=20)

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
