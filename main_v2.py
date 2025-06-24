from gui_elements_v2 import MainWindow
import customtkinter as _ctk


# define fonts
title = ("Arial", 20)
subtitle = ("Ariel", 18)

def database_selector():
    selector_window = _ctk.CTk()

    ################################
    # selector window widgets
    ################################

    # big test at the top "select a database
    _ctk.CTkLabel(selector_window, text="Select a database to\n connect to.", font=title).pack(padx=150, pady=15)

    # dropdown

    selector_window.mainloop()


if __name__ == "__main__":
    database = database_selector()

    if database:
        app = MainWindow(db_name=database)

        app.window.mainloop()
    else:
        # you fail
        pass
