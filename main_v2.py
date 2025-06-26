from gui_elements_v2 import MainWindow, ctk


# define fonts
title = ("Arial", 20)
subtitle = ("Ariel", 18)
db_dict = {"Parts": "parts_organizer_db", "General": "my_new_database"}
selected_database = ""
global select_db_var
global selector_window


def start_button():
    print("start button hit")
    global selected_database
    global selector_window
    selected_database = select_db_var.get()
    selector_window.destroy()


def database_selector():
    global selector_window
    global select_db_var
    selector_window = ctk.CTk()
    selector_window.resizable(False, False)

    ################################
    # selector window widgets
    ################################

    # big test at the top "select a database
    ctk.CTkLabel(selector_window, text="Select a database to\n connect to.", font=title).pack(padx=150, pady=15)

    # dropdown
    select_db_var = ctk.StringVar(value="- Select -")
    ctk.CTkOptionMenu(selector_window, width=350, height=35, values=list(db_dict.keys()), variable=select_db_var, fg_color="#171717", button_color="#171717").pack(padx=150, pady=10)

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
    ctk.CTkButton(cnce_frame, text="Create New").grid(row=0, column=0, padx=20, pady=2)
    ctk.CTkButton(cnce_frame, text="Connect Existing").grid(row=0, column=1, padx=20)

    # empty space at bottom
    ctk.CTkLabel(selector_window, text="").pack()

    selector_window.mainloop()


if __name__ == "__main__":
    database_selector()

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
