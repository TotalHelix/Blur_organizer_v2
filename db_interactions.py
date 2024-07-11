# label printing
import os
from barcode.writer import ImageWriter
from barcode import UPCA
from PIL import Image
from textwrap import wrap
from zpl import Label
from zebra import Zebra

# database
from psycopg2 import connect
import psycopg2.errors
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import date, datetime

# random generation (populate database)
import lorem
from random import randint, choice
from names import get_first_name, get_last_name


def find_common_elements(list_to_compare):
    print(list_to_compare)
    if not list_to_compare or list_to_compare == [[['No matching items', 'No matching items']]]:
        return [(" ", " ", " ")]

    # Start with the first list's elements as the base set
    common_elements = set(list_to_compare[0])

    # Intersect with the remaining lists
    for lst in list_to_compare[1:]:
        common_elements.intersection_update(lst)

    print(list(common_elements))
    return list(common_elements)


def upc_new(upc_code):
    """generate a simple barcode upc"""

    # generate the barcode object
    # the code should already be a string but just in case
    my_code = UPCA(str(upc_code), writer=ImageWriter())
    my_code.save("tmp_code")

    # resize the barcode
    code_img = Image.open("tmp_code.png")
    # code_img.thumbnail((57, 25))
    code_img.save("tmp_code.png")

    # os.system("mspaint /PT ./tmp_code.png")  # for some reason the only way to automate printing with zebra is to tell microsoft paint to send the printer something

    # delete the barcode
    os.remove("tmp_code.png")


def render_upc(code, placement, desc_text, printer="Zebra "):
    """the new and improved way to render upc codes using zebra
    returns the error that took place when printing (or none)"""
    upc_new(code)

    args = (code, placement, desc_text, printer)
    print("in render_upc!", "; ".join(args))
    # generate a zpl command

    # change the code to a number
    if code.isnumeric():
        code = int(code)
    else:
        print(f"somehow, {code} was generated as a upc")
        return "invalid code", *args
    # zero pad the code
    code_string = "{0:011d}".format(code)

    # format the description so that it fits
    desc_lines = wrap(desc_text, 32)
    desc = "\\&".join(desc_lines[:5])
    if ' '.join(desc_lines[:5]) != desc_text: desc += "..."

    # set up the label
    label = Label(25, 57)
    label.set_darkness(30)

    # the barcode frame
    label.origin(2, 1)
    label.draw_box(300, 255, 3)
    label.endorigin()

    # write the barcode
    label.origin(4.6, 5)
    label.barcode('2', code_string, height=155, check_digit='N')
    label.endorigin()

    # write the word 'description'
    label.origin(29, 10.5)
    label.write_text("DESCRIPTION:", char_height=1, char_width=.5, font="F")
    label.endorigin()

    # write the description
    label.origin(28, 13.5)
    label.write_text(desc, char_height=2, char_width=2, line_spaces=0, line_width=99, max_line=99)
    label.endorigin()

    # write the word 'home' (placement)
    label.origin(29, 1)
    label.write_text("HOME:", char_height=1, char_width=.5, font="F")
    label.endorigin()

    # write the placement
    label.origin(37, 1.8)
    label.write_text(placement, char_height=8, char_width=6)  # , font="H")
    label.endorigin()

    # the horizontal divider
    label.origin(28, 9)
    label.draw_box(300, 0, 4)
    label.endorigin()

    # preview the label for testing
    # label.preview()
    # return

    # print the label
    try:
        # print to zebra printer
        if "zebra" in printer.lower():
            # generate the command
            zpl_command = label.dumpZPL()
            print(zpl_command)

            # get the printer
            printer = Zebra()

            # set the printer queue
            queue = printer.getqueues()
            selected_queue = None

            # find which printer is the zebra
            for queue_item in queue:
                if "zebra technologies" in str(queue_item).lower():
                    selected_queue = queue_item
                    print("selected queue:", selected_queue)
                    break

            # if no printer is found
            if not selected_queue:
                raise Exception("No Zebra printer found")

            # set the queue to the zebra
            printer.setqueue(selected_queue)

            # print to the printer
            printer.output(zpl_command)
            print("program has been output")

        elif "preview" in printer.lower():
            label.preview()

        # invalid printer type
        else:
            return "Invalid printer type. This is most likely an issue with the program.", code, placement, desc_text, printer

        print('got to end of program')
    except Exception as e:
        raise e


def random_word():
    """generate a single randon word"""
    return lorem.sentence().split(" ")[0].lower()


def strip_string(string_text):
    """Remove special characters and stuff from searches so that you don't miss something because of a dot"""
    return string_text.translate(
        {ord(filter_char): None
         for filter_char in list(" ,.-_")
         }).lower()


class Organizer:
    def __init__(self, user="customer", password="blur4321"):
        """connect to a database and return the connection"""

        # if the user is trying to set up the database, connect to the postgres database
        if user == "postgres":
            self.conn = connect(
                f"user=postgres password=blur4321"
            )
        else:
            self.conn = connect(
                f"dbname=parts_organizer_db user={user} password={password}"
            )

        self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # set up the connection and cursor, this is how we talk to the database
        self.cursor = self.conn.cursor()

    def __enter__(self, user="customer"):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def user_id_from_name(self, name):
        name_split = name.split()
        first_name, last_name = name_split[0], name_split[-1]
        search_sql = f"SELECT user_id FROM users WHERE first_name = '{first_name}' AND last_name = '{last_name}'"

        self.cursor.execute(search_sql)
        return self.cursor.fetchall()[0][0]

    def upc_exists(self, upc):
        """check a upc to see if it exists in the database"""
        self.cursor.execute(f"SELECT * FROM parts WHERE part_upc = {upc}")
        return self.cursor.fetchall()

    def format_database(self):
        """set up all the tables of the database"""

        # find out if the database already exists and needs to be dropped
        # this could probably be done in sql, but is simpler to do in python
        get_db_list = "SELECT datname FROM pg_database"
        self.cursor.execute(get_db_list)

        # if the database does already exist
        if "parts_organizer_db" in [name[0] for name in self.cursor.fetchall()]:
            print("there was a database in there")
            # disconnect from db
            terminate_conn = """
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE 
                pid <> pg_backend_pid()
                AND datname = 'parts_organizer_db';
            """
            self.cursor.execute(terminate_conn)
            self.refresh_cursor()

            # drop database
            drop_db = "DROP DATABASE parts_organizer_db;"
            self.cursor.execute(drop_db)

            self.conn.commit()

        # create a new database
        new_db_sql = "CREATE DATABASE parts_organizer_db;"
        self.cursor.execute(new_db_sql)

        # first thing before switching to the new db, drop anything from the customer role in postgres
        self.disconnect_customer()

        # ----- now that the right database exists, let's connect to it
        # close the old connection
        self.cursor.close()
        self.conn.commit()
        self.conn.close()

        # start a new connection
        self.conn = connect("dbname=parts_organizer_db user=postgres password=blur4321")
        self.cursor = self.conn.cursor()

        self.refresh_cursor()
        # table of database layout
        # i swear if I have to do anything else with this table i'm going to turn it into a spreadsheet
        tables_setup = {
            "users":
                [
                    # name              data type              len   primary key references extra tags
                    ["user_id", "varchar", "53", True, None, "NOT NULL"],
                    ["first_name", "varchar", "50", False, None, "NOT NULL"],
                    ["last_name", "varchar", "50", False, None, "NOT NULL"],
                    ["email", "varchar", "255", False, None, "NOT NULL"]
                ],

            "manufacturers":
                [
                    # name                  data type            len     primary key references extra tags
                    ["mfr_id", "serial", None, True, None, "NOT NULL"],
                    ["mfr_name", "varchar", "255", False, None, "NOT NULL UNIQUE"],
                    ["number_of_parts", "smallint", None, False, None, "NOT NULL"]
                ],

            "parts":
                [
                    # name                  data type       len     primary key references           extra tags
                    ["part_upc",            "bigint",       None,   True,       None,               "NOT NULL"],
                    ["part_placement", "varchar", "4", False, None, "NOT NULL UNIQUE"],
                    ["mfr_pn", "varchar", "255", False, None, ""],
                    ["part_mfr", "varchar", "255", False, 'manufacturers; mfr_id', "NOT NULL"],
                    ["part_desc", "varchar", None, False, None, "NOT NULL"],
                    ["qty", "smallint", None, False, None, ""]
                ],

            "part_locations":
                [
                    # name                  data type                       len     primary key references  extra tage
                    ["checked_out_part", "NA", "NA", False, "parts; part_upc", "NOT NULL UNIQUE"],
                    ["current_holder", "NA", "NA", False, "users; user_id", "NOT NULL"],
                    ["checkout_timestamp", "timestamp without time zone", None, False, None, "NOT NULL"]
                ]
        }

        for table in tables_setup.keys():
            # drop any old tables that might exist with the old name

            create_command = f"""
    DROP TABLE IF EXISTS public.{table} CASCADE;
    CREATE TABLE public.{table} 
    (\n"""

            # go through every column and add it to the create command
            for column in tables_setup.get(table):  # for every column in the table
                # add the column name to the command
                create_command += column[0]

                # draw from the reference in the case of foreign keys
                source = column
                source_path = ""
                if column[4]:  # if column has a reference listed
                    source_path = column[4].split("; ")
                    source_table = tables_setup.get(source_path[0])
                    for elem in source_table:  # find the referenced table
                        if elem[0] == source_path[1]:
                            source = elem
                            break

                # add the date type
                create_command += f" {source[1]}"

                # add max length
                if source[2]:
                    create_command += f"({source[2]})"

                # add extra tags (not null, etx.)
                create_command += " " + column[5]

                # add primary key tag
                if column[3]:
                    create_command += " PRIMARY KEY"

                # separate out the create command lines
                create_command += ",\n"

                # add foreign key line
                if column[4]:
                    reference = f"{source_path[0]}({source_path[1]})"
                    create_command += f"""CONSTRAINT fk_{column[0]} FOREIGN KEY({column[0]}) REFERENCES {reference},\n"""

            # chop off the last comma and close the command
            create_command = create_command[:-2] + "\n);"

            self.cursor.execute(create_command)
            self.conn.commit()

            # remake the customer
            self.new_user()
            self.conn.commit()

            # recreate the

    def mfr_id_from_name(self, mfr_name):
        """get return the mfr id given the mfr name"""
        mfr_id_sql = f"SELECT mfr_id FROM manufacturers WHERE lower(mfr_name) = '{mfr_name.lower()}'"
        self.cursor.execute(mfr_id_sql)
        mfr_id = self.cursor.fetchall()

        # return the id if it's found, otherwise don't return anything
        if mfr_id: return mfr_id[0][0]

    def get_checkouts(self, key, keyword="USER"):
        """get all the parts that would need to be checked out to delete a user
        I might also add this to the user list system because that would be nice to see"""

        # what table to look in
        table = "part_locations"

        # because manufacturers are special
        if keyword == "MANUFACTURER":
            # set the right table
            table = "parts"

            # get the mfr id of the mfr
            key = self.mfr_id_from_name(key)

        # what column to compare
        column = {"USER": "current_holder",
                  "PART": "checked_out_part",
                  "MANUFACTURER": "part_mfr"
                  }[keyword]

        # what column to read
        read_col = "part_upc" if keyword == "MANUFACTURER" else "checked_out_part"

        # crop zeros from the front of the key
        if isinstance(key, str) and key.isnumeric():
            key_cropped = int(key)
        else:
            key_cropped = key

        search_sql = f"SELECT {read_col} FROM {table} WHERE CAST({column} as varchar) = '{key_cropped}'"
        self.cursor.execute(search_sql)
        results = self.cursor.fetchall()
        return [str(row[0]) for row in results]

    def update_user(self, old_id, fname, lname, email):
        """update the user account so that it has the new information"""
        # capitalize your name!
        fname = fname.title()
        lname = lname.title()

        # block existing emails
        email_matches = f"SELECT user_id FROM users WHERE email = '{email}'"
        self.cursor.execute(email_matches)
        email_results = [row for row in self.cursor.fetchall() if row[0] != old_id]
        if email_results: return "-EMAIL_ALREADY_TAKEN-"

        # block existing names
        name_matches = f"SELECT user_id FROM users WHERE last_name = '{lname}' AND first_name = '{fname}'"
        self.cursor.execute(name_matches)
        # matching_names = [row for row in self.cursor.fetchall() if row[0] != fname]
        if self.cursor.fetchall(): return "-NAME_ALREADY_TAKEN-"

        # I was going to have this change the userid as well but that was more complicated than expected, as thew userid is a primary key
        update_sql = f"UPDATE users SET (first_name, last_name, email) = ('{fname}', '{lname}', '{email}') WHERE user_id = '{old_id}'"
        self.cursor.execute(update_sql)
        self.conn.commit()

        return old_id

    def upc_create(self, code):
        print("this doesn't work yet")
        upc_new(code)

    def rename_mfr(self, mfr_id, new_name):
        """rename the mfr with id mfr_id to new_name"""

        # get the name of the mfr to begin with
        old_name_sql = f"SELECT * FROM manufacturers WHERE mfr_id = {mfr_id}"
        self.cursor.execute(old_name_sql)
        old_name_row = self.cursor.fetchall()
        if old_name_row:
            old_name = old_name_row[0][0]
        else:
            return "Something went wrong. Please try again."

        # find mfrs that already have this name
        search_sql = f"SELECT * FROM manufacturers WHERE mfr_name = '{new_name}'"
        self.cursor.execute(search_sql)
        results = [row for row in self.cursor.fetchall() if row[0] != old_name]
        if results: return "This name is already taken"

        # update the mfr
        update_sql = f"UPDATE manufacturers SET mfr_name = '{new_name}' WHERE mfr_id = {mfr_id}"
        self.cursor.execute(update_sql)
        self.conn.commit()
        return "Success"

    def disconnect_customer(self):
        """drop all dependencies on the customer role"""

        # see if the customer role exists
        self.cursor.execute("SELECT pg_roles.rolname FROM pg_roles WHERE pg_roles.rolname = 'customer'")

        # if it does:
        if self.cursor.fetchall():
            disconnect_role = """
            REASSIGN OWNED BY customer TO postgres;
            DROP OWNED BY customer;"""
            self.cursor.execute(disconnect_role)
            self.refresh_cursor()

    def new_user(self):
        """dumb function that creates a user because it gets mad when it's in the other one"""
        # first off, get rid of role dependencies of they exist
        self.disconnect_customer()

        # connect to the database
        self.cursor.close()
        self.conn.commit()
        self.conn.close()
        self.conn = connect("user=postgres password=blur4321 dbname=parts_organizer_db")
        self.cursor = self.conn.cursor()

        user_create = """
        DROP ROLE IF EXISTS customer;
        CREATE ROLE customer  WITH
            LOGIN
            NOINHERIT
            PASSWORD 'blur4321';
        
        GRANT CONNECT ON DATABASE parts_organizer_db TO customer;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO customer;
        GRANT INSERT ON ALL TABLES IN SCHEMA public TO customer;
        GRANT DELETE ON ALL TABLES IN SCHEMA public TO customer;
        GRANT UPDATE ON ALL TABLES IN SCHEMA public TO customer;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO customer;
        
        GRANT CONNECT ON DATABASE parts_organizer_db TO postgres;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO postgres;
        GRANT INSERT ON ALL TABLES IN SCHEMA public TO postgres;
        GRANT DELETE ON ALL TABLES IN SCHEMA public TO postgres;
        GRANT UPDATE ON ALL TABLES IN SCHEMA public TO postgres;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO postgres;
        """
        self.cursor.execute(user_create)
        self.conn.commit()

    def get_rows(self, column_name):
        """get all the values for a specified column"""
        # get the table that the column is in
        self.cursor.execute(f"SELECT table_name from information_schema.columns WHERE column_name = '{column_name}'  ")
        table = self.cursor.fetchall()[0][0]

        # get the rows of the column
        self.cursor.execute(f"SELECT {column_name} FROM {table}")
        values = self.cursor.fetchall()

        rows = []
        for value in values:
            rows.append(value[0])

        return rows

    def refresh_cursor(self):
        """close and reopen the cursor and connection"""
        self.conn.commit()
        self.cursor.close()

        self.cursor = self.conn.cursor()

    def populate_db(self):
        """fill the desired table with sample data"""

        # get the current tables
        get_tables_sql = "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        self.cursor.execute(get_tables_sql)
        print(self.cursor.fetchall())

        # first off, this does not need superuser
        self.cursor.close()
        self.conn.commit()
        self.conn.close()
        self.conn = connect("dbname=parts_organizer_db user=customer password=blur4321")
        self.cursor = self.conn.cursor()

        # ----- fill out all the databases

        # the users table
        for _ in range(randint(8, 37)):
            # first and last name
            f_name = get_first_name()
            l_name = get_last_name()

            # get the user id
            user_id = (f_name[0] + l_name).lower()  # add the last name to the first letter of the first name
            counter = 0  # the number after the userid for duplicates
            taken = True  # current number is taken
            while taken:
                # add extension if counter exists
                ext = ""
                if counter:
                    ext = str(counter)

                self.cursor.execute(f"SELECT * FROM users WHERE user_id = '{user_id + ext}'")
                if self.cursor.fetchall():
                    counter += 1
                else:
                    taken = False

            if counter > 0:  # if an identifier is necessary
                user_id += str(counter)

            # define the email
            email = choice([user_id, f_name, f_name + l_name[0], f_name + "_" + l_name])
            email += "@"
            email += choice(["gmail.com", "hotmail.com", "blurpd.com", "wcpss.net", "yahoo.com"])

            self.cursor.execute(f"INSERT INTO users VALUES ('{user_id}', '{f_name}', '{l_name}', '{email}')")
        # the manufacturers table
        for _ in range(randint(6, 21)):
            # pick a random name for the mfr
            mfr_name = choice([
                get_last_name(),
                "DigiKey",
                random_word().title() + random_word().title(),
                get_last_name() + random_word(),
                random_word().title()
            ])

            # insert into tabel if it doesn't already exist
            if mfr_name not in self.get_rows("mfr_name"):
                # the other two columns are mfr id, serial; and number of kits, 0 to start
                self.cursor.execute(f"INSERT INTO manufacturers VALUES (default, '{mfr_name}', 0)")
        # parts table

        # get a list of all the upcs already used
        used_codes_sql = "SELECT checked_out_part FROM part_locations"
        self.cursor.execute(used_codes_sql)
        used_codes = [elem[0] for elem in self.cursor.fetchall()]
        for _ in range(randint(16, 47)):
            # pick a location
            placement = "A1"
            placement_search = f"SELECT * FROM parts WHERE part_placement = '"
            while True:
                self.cursor.execute(placement_search + placement + "'")
                if self.cursor.fetchall():
                    placement = str(randint(1, 22)) + choice(
                        ["A", "B", "C", "D", "E", "F", "G", "H", "I"])
                else:
                    break
            # pick a manufacturing part number
            mfr_pn = hex(randint(1000000000, 999999999999999999))
            # pick a manufacturer
            mfr = choice(self.get_rows("mfr_id"))
            # come up with a description
            desc = lorem.sentence()

            # create the appropriate upc code
            other_mfrs = self.get_rows("part_mfr")
            unique_id = 1
            for other_instance in other_mfrs:
                if other_instance == mfr:
                    unique_id += 1

            # zero padded mfr id
            upc = "{0:03d}".format(mfr)
            # padded pn
            upc += "{0:04d}".format(unique_id)
            # current date
            upc += date.today().strftime("%m%d%y")

            # make a quantity, weighted heavily to lower numbers
            qty = randint(1, randint(1, randint(1, 50)))

            sql = f"INSERT INTO parts VALUES ({upc}, '{placement}', '{mfr_pn}', '{mfr}', '{desc}', {qty})"
            self.cursor.execute(sql)

            # change the mfr table to display the number of parts
            update_mfrs_table = f"""
UPDATE manufacturers SET number_of_parts = {unique_id} WHERE mfr_id = {mfr}"""
            self.cursor.execute(update_mfrs_table)
        # the table that holds the locations of all the checked out parts
        for _ in range(randint(2, 16)):
            # the timestamp that the part was checked out
            # just use CURRENT_TIMESTAMP for the real one
            time_now = datetime.fromtimestamp(randint(0, 1826244364))
            time_string = time_now.strftime("%Y-%m-%d %H:%M:") + str(randint(0, 59999999) / 1000000)

            # the part that is checked out
            part = choice(self.get_rows("part_upc"))
            # the person who checked out the kit
            holder = choice(self.get_rows("user_id"))

            # the insert command
            if part not in used_codes:
                sql = f"INSERT INTO part_locations VALUES ({part}, '{holder}', '{time_string}')"
                self.cursor.execute(sql)

            # because this is never going to be used, we're doing it the dumb way
            # just have a list of the codes that I've inserted
            used_codes.append(part)

    def name_is_taken(self, fname, lname):
        """see if a user exists that has the same first and last name"""

        # get all the users with the same first name
        sql = f"SELECT last_name FROM users WHERE first_name = '{fname}'"
        self.cursor.execute(sql)
        last_names = self.cursor.fetchall()

        # if the last name is in the list of names
        for name_compare in last_names:
            if name_compare[0] == lname:
                return True

        # if no matches were found
        return False

    def clear_checkout(self, usr_part_id):
        """
        check in all the parts that the user depends on
        that line sounds like a supervillain
        """

        # column that we want to search in
        search_col = "checked_out_part" if usr_part_id.isnumeric() else "current_holder"

        # get the parts that the user has checked out
        self.cursor.execute(f"SELECT checked_out_part FROM part_locations WHERE {search_col} = '{usr_part_id}'")
        parts_out = self.cursor.fetchall()

        for part in parts_out:
            print(part, part[0])
            self.part_checkin(part[0])

        self.conn.commit()

    def clear_delete(self, parts_out):
        """like clear_checkout, but deletes instead."""  # woah when would this need to be used?

        for part in parts_out:
            delete_cascade_sql = """
DELETE FROM part_locations WHERE checked_out_part = {0};
DELETE FROM parts WHERE part_upc = {0} """.format(part)
            self.cursor.execute(delete_cascade_sql)

        self.conn.commit()

    def delete_generic(self, key, keyword):
        """delete the selected item on the list"""
        self.refresh_cursor()  # still don't know if this was actually the fix

        # get the table from the keyword
        location = {
            "user": ["users", "user_id"],
            "part": ["parts", "part_upc"],
            "manufacturer": ["manufacturers", "mfr_name"]
        }[keyword]

        # try to delete
        try:
            self.cursor.execute(f"DELETE FROM {location[0]} WHERE {location[1]} = '{key}'")
        except psycopg2.errors.ForeignKeyViolation as fail_location:
            return "-PARTS_STILL_CHECKED_OUT-"

        self.conn.commit()
        return "-SUCCESS-"

    def add_part(self, desc, mfr_name, mfr_pn, placement, qty):
        """inset a row into the parts database"""
        # ----- get rid of special characters in the description

        desc = "".join([char for char in desc if char.isalnum() or char in " !\"#$%&'()*+,-./:;<=>?@[]{}\\^_`|~"])

        # ----- manufacturer stuff

        # find if the input mfr already exists
        all_mfrs = self.get_rows("mfr_name")

        # if there is already some manufacturers to sort through
        mfr_id = None
        if len(all_mfrs) > 0:
            # remove spaces, dots, dashes, capitalization, etc. in the name
            mfr_formatted = strip_string(mfr_name)

            # search for other manufacturers that have the same name
            for other_mfr_name in all_mfrs:
                other_formatted = strip_string(other_mfr_name)

                # if the input mfr is in the table
                if other_formatted == mfr_formatted:
                    # get the id of the mfr that has the matching name
                    sql = f"SELECT mfr_id FROM manufacturers WHERE mfr_name = '{other_mfr_name}'"
                    self.cursor.execute(sql)
                    raw_table = self.cursor.fetchall()
                    mfr_id = raw_table[0][0]
                    break

            # I don't think this does anything, but I'm afraid to remove it.
            self.conn.commit()

        # if we weren't able to find an existing mfr with the same id
        if not mfr_id:
            # create a new mfr

            mfr_id = self.add_mfr(mfr_name)

        # ----- upc code stuff

        # generate the unique id
        other_part_mfrs = self.get_rows("part_mfr")
        unique_id = 1
        for other_instance in other_part_mfrs:
            if other_instance == mfr_id:
                unique_id += 1

        # zero padded mfr id
        upc = "{0:03d}".format(mfr_id)
        # padded pn
        upc += "{0:03d}".format(unique_id)
        # current date
        upc += date.today().strftime("%m%d%y")

        # make sure that the upc is actually available
        upc_check_base = "SELECT * FROM parts WHERE part_upc = "
        while True:
            # find matching parts
            self.cursor.execute(upc_check_base + str(upc))
            matching_upcs = self.cursor.fetchall()

            # check if the current upc is taken or is too long
            if len(upc) > 12 or matching_upcs:
                # if there is a match just start guess and check
                upc_int = randint(0, 999999999999)
                upc = "{0:012d}".format(upc_int)
            else:
                break

        # capitalize the placement
        placement = placement.upper()
        # make apostrophes safe
        safe_desc = desc.replace("'", "''")
        safe_mfr_pn = mfr_pn.replace("'", "''")
        safe_placement = placement.replace("'", "''")

        # ----- perform the insertion
        sql = f"INSERT INTO parts VALUES ({upc}, '{safe_placement}', '{safe_mfr_pn}', '{mfr_id}', '{safe_desc}', {qty})"
        self.cursor.execute(sql)

        # change the mfr table to display the number of parts
        update_mfrs_table = f"""
UPDATE manufacturers SET number_of_parts = {unique_id} WHERE mfr_id = {mfr_id}"""
        self.cursor.execute(update_mfrs_table)

        return render_upc(upc, safe_placement, desc, printer="Zebra ")
        # return upc

    def add_mfr(self, mfr_name):
        self.cursor.execute(f"INSERT INTO manufacturers VALUES (default, '{mfr_name}', 0) RETURNING mfr_id")
        self.conn.commit()

        return self.cursor.fetchall()[0][0]

    def transfer_parts(self, old_mfr_name, new_mfr_name):
        """transfer all parts under the old mfr to the new mfr so that it can be deleted"""

        # get the mfr id's of both
        old_mfr_id = self.mfr_id_from_name(old_mfr_name)
        new_mfr_id = self.mfr_id_from_name(new_mfr_name)

        # if one of these is missing
        if not old_mfr_id or not new_mfr_id:
            print("one manufacturer couldn't find an id")
            return

        # do the transferring
        transfer_sql = f"UPDATE parts SET part_mfr = {new_mfr_id} WHERE part_mfr = {old_mfr_id}"
        self.cursor.execute(transfer_sql)
        self.conn.commit()

    def part_checkin(self, upc):
        """check a part back in"""
        # what to put at the end of the popup
        pos_message = " Please return part to "

        # also get the part location and add it to the message
        search_sql = f"SELECT part_placement FROM parts WHERE part_upc = {upc}"
        self.cursor.execute(search_sql)
        part_search = self.cursor.fetchall()

        # if the part exists in the db
        if len(part_search) > 0:
            # while we have the part row, add the part location to the message
            pos_message += part_search[0][0]

            # search for the part in the checked out parts
            search_sql = f"SELECT * FROM part_locations WHERE checked_out_part = {upc}"
            self.cursor.execute(search_sql)
            location_search = self.cursor.fetchall()

            # if the part was checked out
            if len(location_search) > 0:
                # actually check in the part
                checkin_sql = f"DELETE FROM part_locations WHERE checked_out_part = {upc}"
                self.cursor.execute(checkin_sql)

                self.conn.commit()
                return "Successfully checked in." + pos_message
            else:
                return "The scanned part was never checked out." + pos_message

        else:
            # if the part can't be found in the parts table
            return """This hasn't been added yet.
Please click "Add part" to add a part for the first time"""

    def get_users(self, search_term):
        """return a dictionary {"F_name L_name - email": "user_id} of all users that have the search term

        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠛⠋⠉⠉⠀⠀⠀⠀⠀⠀⠛⠘⠛⠛⠛⠿⠿⠿⠿⠿⣽⠙⣛⡛⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⠋⠁⠀⠀⠀⠀⠀⢀⣀⣀⣀⣀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠂⠈⠙⠛⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢋⣰⢋⣴⠻⣿⡟⢹⡟⠋⠀⠀⠀⠀⢀⣠⣴⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣶⣶⣶⣶⣶⣶⣶⣿⣿⣿⣷⣶⣶⣦⣤⣄⣀⠀⠀⠉⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⡀⠏⣰⠟⠁⡰⢋⠀⠀⠀⠀⠀⢀⣠⣾⣿⣿⣿⡿⠟⠛⣛⣽⣯⣿⣽⣯⣿⣟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣖⡄⠀⠀⠉⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⠀⣠⠾⠋⠀⢊⡴⠋⠀⠀⠀⣀⣴⣿⣿⣿⡿⠋⢀⣠⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⣿⣿⣽⣿⣯⣿⣯⣿⣽⣯⣿⢿⣷⣷⣄⠀⠀⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⠀⢠⠞⠁⠀⠀⣰⠋⠀⠀⢀⣤⣾⣿⣿⣿⠿⣋⣴⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⣝⣛⡫⠷⣿⡿⣯⣿⢿⣺⣄⠀⠈⠋⠙⣿⡻⣧⠹⣏⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠁⠀⢀⡴⠋⠀⠀⢠⡾⠁⠀⢀⣴⣿⣿⣿⣿⣿⣿⣾⠿⠛⣩⣽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣭⣛⣿⣿⣻⣿⣷⣤⠀⠀⠘⢷⠘⣧⠹⣆⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠋⠀⢀⡰⠍⠀⠀⢀⣴⡟⠁⢀⣶⣿⣿⣿⣿⣿⣿⠟⣋⠴⢂⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡄⠀⠀⠀⠹⣦⠘⠀⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠀⠀⢀⠀⠀⠀⢰⣾⠏⢀⣴⣾⣿⣿⡿⣻⡿⢛⣡⠞⣁⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢿⣻⣽⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣄⢠⡀⠁⠘⢧⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀⠠⠀⠀⠀⣿⠏⣴⣿⣿⣿⡿⣋⣾⠟⣱⠋⢂⣶⣿⣿⣿⣿⣿⣿⡿⣯⣿⣽⢿⡾⣟⣿⡽⣾⢽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠱⠀⠀⠈⢧⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⡋⠀⠠⢀⠏⠀⠀⠀⠀⠀⠀⢋⣾⣿⣿⣿⣿⣷⠟⡡⠞⢁⣼⣿⣿⣿⣿⣿⢟⣿⢿⣽⣟⡷⣯⣟⡿⣽⢯⡿⣽⢊⢷⣻⣟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣽⣿⣟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡂⠀⠀⠀⢫⠄⠀⠘⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⡈⠁⡌⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⠟⢁⢮⡱⣳⢾⣟⠋⣿⣿⡿⠃⣼⢯⡟⣾⡽⣳⠶⣭⠿⣽⣛⡞⣷⡈⢎⢷⡹⣯⣟⣿⣿⣿⣿⣿⣿⡿⣿⣿⣿⣿⣿⣿⣯⣿⣿⣿⣿⣿⣿⣟⣿⣿⣿⣿⣿⣿⣿⣷⡆⠀⠀⠀⠫⡄⠀⠈⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⡔⠀⢈⠆⠀⠀⠀⣠⣾⣿⣿⣿⣿⢛⢋⡰⣋⢮⡱⢏⡾⠍⣰⣿⡿⠁⡼⣏⠷⡘⢼⣓⠧⡓⡜⣯⢳⣭⣛⢶⡁⢊⠶⣙⢧⡻⣷⣻⣯⣿⢿⣷⣿⢿⣯⣿⢿⣽⣾⢿⣳⣿⣽⡿⣿⣿⡿⣟⣾⣽⣻⢿⣿⣿⣿⣿⣧⠀⠀⠀⠄⠀⠀⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡧⠀⡘⠀⡀⠌⡐⠀⠀⣼⣿⣿⣿⣿⣿⠃⢀⠦⡓⢭⡲⢭⣓⠞⢠⣿⡟⢀⣼⢳⡍⠧⡑⠈⡝⠦⡑⡍⡖⣏⢶⡩⢞⠁⡄⠘⡱⢎⡵⢫⢷⣻⣽⣿⣻⣾⢿⣽⡾⣟⣯⡿⣟⣿⣳⣯⢿⡟⣿⣿⣟⡿⣞⡿⣯⣟⣿⢿⣿⣯⡀⠀⢀⠂⠀⠀⠟⡛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠠⠘⠰⢀⡘⠔⢀⣾⣿⣿⣿⣿⣿⠃⠀⡎⠵⣙⠶⣹⢣⡞⠁⣾⡿⢁⡾⣡⠗⡬⠑⢀⡆⡙⢆⠱⡘⠼⣘⠦⣝⢪⠀⣗⡀⠙⡼⣘⢏⡞⡵⣛⡾⣽⢯⣟⠾⡽⣭⢿⣹⢟⣷⡻⣎⢯⢳⡌⢿⣾⣟⣯⢳⡝⣺⠽⣻⣽⣻⡇⠀⠀⠀⠀⢰⡄⠸⡈⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠂⡍⡖⠀⠌⣠⣿⣿⣿⡿⣿⡿⠃⠀⡜⣌⠳⣬⢛⡴⢫⡜⢸⣿⠃⡼⣱⢃⠞⡠⢁⣾⠁⢹⠠⢃⢌⠣⡝⣚⢬⢣⠀⣿⣦⠀⠰⡩⠞⡼⣱⢫⡝⣧⢟⡾⢫⡕⣣⢏⢞⡹⢲⡝⡜⣊⠖⠲⠈⢿⣾⣻⠸⡜⣥⠫⣝⡷⣟⡧⠀⠀⠀⠀⠰⣃⠐⢠⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⢀⠱⢠⠄⠈⣴⣿⣿⣿⠟⣼⡿⢡⠃⡜⡰⢊⢷⡸⣍⢞⡣⠄⣿⣏⠴⣣⠧⣉⠎⢁⣼⣯⠇⠰⣉⠌⡄⠳⣌⠧⢎⢧⠀⣿⡽⣷⠀⠈⠽⡰⢣⠳⣜⢬⢫⡜⣳⠸⣑⢎⠎⡕⢣⠜⡰⢡⠎⣡⢃⠘⣿⣽⡆⢹⠰⣍⢲⡹⣟⣿⠀⠀⠀⢀⡃⠲⠀⢠⠂⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠄⡂⡜⢀⣾⣿⣿⣿⢋⣾⣟⢠⠃⡸⢰⡑⢯⡒⢷⣘⢮⡑⢸⣯⢏⡞⣡⠞⡤⠁⣾⠋⣾⠡⠐⡥⢂⠈⡱⣈⢮⡙⢦⠐⣏⠻⣿⣷⣤⠈⠱⣋⠳⣜⢪⡓⡼⣡⠳⣉⢎⢎⡙⠦⡙⡔⠣⢎⠔⡈⠆⢹⣯⣧⠈⡳⢌⠦⣱⣛⣮⠀⠀⠀⠆⡌⢡⠃⠄⢂⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠆⡑⢠⣾⣿⣿⡻⢃⣾⣿⠋⠆⠰⣁⠦⣙⠦⣏⠳⡜⢦⠁⣾⣏⠞⡴⢱⢊⠀⣼⢏⣾⣿⡅⠈⠴⠈⠐⢠⡑⢦⡙⣧⠈⣟⣦⠹⣿⣿⣄⠀⠉⠷⣌⠳⡜⣥⢃⠯⣜⣊⢦⡙⢦⠱⣌⠳⡌⢎⠱⡈⠄⢻⣿⡄⡹⢌⠲⡡⢞⡵⠀⠀⠀⡇⠄⡃⠥⢈⠄⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⡈⠂⣴⣟⠫⡍⠰⢁⣾⣿⠃⡜⢀⠣⣐⠣⣍⠞⣌⢳⢩⢚⠀⡿⣌⠏⡼⢡⠂⠰⣿⡾⢿⣿⣇⠀⠓⡄⡄⠂⡜⢢⡝⡶⠐⣸⣿⣷⡜⢿⣿⣷⡠⠘⢌⡳⢍⠶⣩⠞⡴⣊⢦⡙⢆⡳⢌⠣⡜⣌⠲⡁⠎⠈⣿⣷⡱⢋⡒⠥⣫⠖⠀⠠⢌⡓⠌⡰⢁⠎⡐⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⢀⡾⢋⡌⢣⠌⢁⣿⡿⠁⡜⠀⢢⠑⡄⠳⣈⠞⡌⢎⠦⡉⢸⡗⡭⢊⡵⠁⣰⣶⣤⣤⣌⡙⠉⠷⠈⠄⢣⠐⣈⠳⣜⣳⠀⣿⣿⣿⣿⣦⡙⣿⣷⡀⠈⠼⣩⠞⣥⢛⡴⣍⠶⣉⠦⣑⠮⣑⢮⣐⢣⠱⡈⠅⠸⣷⡏⡵⢘⡐⢧⣻⠀⡡⢂⡝⢠⠐⡩⠐⢠⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠂⡰⢋⠔⠣⠘⢠⠃⣾⡟⠄⡐⢀⡘⠄⠣⢌⠱⠠⢎⡐⢣⡘⠁⣾⢸⡱⢋⠄⣘⣿⣿⣿⣿⣿⣿⣿⡦⠀⠁⢸⡄⢠⢋⢾⣱⠠⣿⣿⣿⣿⣿⣿⣌⢻⣿⣤⠈⢱⡚⢦⡛⣶⡩⢞⢥⠓⣜⢢⡍⠶⣨⢆⢣⡑⠌⡀⢿⣷⢡⠣⡘⠦⣏⠔⡁⠢⣜⠠⠂⢥⠃⠄⠂⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠅⢀⠰⠌⡌⢁⠊⠄⣸⡟⠀⡐⠀⡄⢢⢉⠒⡌⢂⠇⢢⠘⢤⠘⢰⠋⣦⡙⠂⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⡄⠘⢸⣧⠀⡚⣼⢳⠀⣿⣿⣿⣿⣿⣿⣿⡷⢈⢁⣤⠀⠍⡧⡝⢦⠻⣍⢮⡙⣤⠣⡜⢳⡰⢎⠲⣌⠒⡀⠘⣿⣎⠱⣀⠛⡼⢐⡈⠔⣌⠂⡉⠔⡨⢈⠄⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠃⠈⠐⠈⠆⢠⠂⠌⡐⢰⡿⠂⡐⠀⠰⡈⠆⡌⠒⡌⢌⡘⠤⡉⢆⠁⣼⣙⢦⠙⣠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠈⣿⡇⠘⡴⣻⠀⣹⣿⣿⣿⣿⣿⣿⣶⣾⣷⣿⡖⠀⠱⣩⠏⣝⢮⠳⡜⢤⠓⣍⠲⣱⢪⡑⢆⠣⡔⠁⢹⣎⠧⢠⠙⣞⠀⢎⠐⣌⠂⣁⠚⠄⢢⠀⢽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠗⢀⣠⣶⠁⠌⠂⡌⢀⠂⢠⡿⠁⠀⠀⠀⣎⠡⡘⢠⠃⢌⠢⠄⡃⠜⡠⢀⡿⣜⠋⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⢿⣿⡆⢱⢻⠀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣆⣄⠑⢮⡱⢎⠿⣜⠦⡙⢤⠛⣤⠓⡼⣈⠇⣆⠡⠀⢻⡜⡠⢙⡼⠈⠆⡌⣰⠡⠠⠘⡌⠠⠂⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⢛⣡⣴⣿⣿⡏⠐⢨⠀⠆⠠⠁⣼⠃⠀⠀⠀⡜⢄⠢⠑⡄⢊⠄⡃⠜⡠⢃⠔⠰⣯⠍⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣾⣿⣿⣀⠹⡇⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡦⡀⠹⢎⡝⣮⢧⠙⣢⠙⣤⠛⣔⢣⡚⢤⢃⠅⡈⠞⠤⡁⢞⡥⠘⡄⢲⠀⡅⢣⠐⡡⠁⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⡈⠄⡘⢠⠁⢸⠇⠀⠀⠀⣼⠱⡈⠄⡡⠐⠌⢂⡘⠤⠑⠢⠀⣼⠇⠀⠀⠉⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣄⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⣀⠉⢞⡬⣛⣇⠰⣉⠦⡹⢌⡖⡍⣆⠫⡔⡀⢈⠱⢈⠺⣄⠱⣌⠲⢁⠰⢀⠇⠄⡡⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠠⠐⢡⡘⠤⢀⡏⠀⠀⠀⣸⡱⢂⡁⠂⠄⡑⠈⡄⠰⡈⢡⠁⠐⡟⢀⣶⣤⣄⣀⠀⠀⠈⠙⠿⣿⣿⡙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⢀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⡈⠲⡝⡾⣇⠈⡖⣩⠲⣌⠳⣌⢳⣜⡰⠀⠄⠊⣜⣣⢘⡧⡘⠄⢂⠡⢊⡐⠐⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠇⠠⣉⠐⢆⠂⡼⠀⠀⠀⣼⢣⢇⠃⠠⢈⠐⠠⠁⢄⠃⠤⠁⠌⡀⢡⣿⣿⣿⣿⣿⣿⣷⣦⣄⠀⠀⠙⠻⢷⣬⣙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⣿⣿⣿⣿⠿⠟⠛⠛⠁⠀⠘⠵⣻⡄⠸⣄⠳⣌⠳⣌⠧⣿⢰⢃⠘⡀⠰⣧⢸⠲⡍⠂⡌⢐⡃⢄⡉⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⢂⠤⡙⡄⢰⠁⠀⠀⢬⡷⣩⠎⡄⠁⠄⡈⠄⡁⢂⠌⠄⣉⠰⠀⢠⣿⡟⠉⠉⠉⠉⠀⠁⠈⠁⠀⠀⠀⠀⠈⣹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⢡⣶⠾⠟⠋⠉⠀⠀⠀⢀⣀⣀⣠⣤⣤⡀⠓⠋⡀⢨⠓⣌⠳⣌⢳⡌⢠⡋⠄⠀⠐⣽⢸⠣⡅⢃⠐⢂⡅⢂⠰⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⡌⢂⡜⠀⠃⠀⠀⡜⢲⡝⠂⣁⡀⠈⡀⠄⡐⠐⡠⢈⠂⢄⠒⠀⠈⣿⣷⣀⣠⣤⣤⣶⣶⣶⣶⣶⣶⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⠁⠀⠀⠀⠀⠀⠶⠾⣿⣿⣿⣿⣿⣿⣿⣿⠄⠀⠱⠀⡹⢄⣛⠈⣁⡘⢂⣇⠈⠆⠀⢘⣯⠃⡜⣀⠊⢄⡒⠈⡔⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠇⡐⢌⠒⠆⡈⠀⢠⠘⣌⢻⠌⣸⣿⠇⠀⢀⠐⠠⢁⡐⠠⠌⠂⢌⠀⠀⢹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣦⣤⣄⣀⠀⠀⠀⠉⠙⠻⢿⣿⡏⠀⠐⡀⠅⢀⠣⠎⠐⣿⣧⡀⢺⡀⠌⢡⠘⣮⠑⡌⠤⠈⡔⢨⢁⠰⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⡰⢈⢜⡂⠀⢀⡎⠴⡨⡇⢰⣿⣿⡁⠀⠀⠌⡐⠠⠀⡡⠘⡈⠤⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⣄⣀⣠⣿⡟⠀⡈⠄⡐⠌⡄⢀⠩⠀⢿⣿⡄⠠⡇⠈⠄⠢⣝⠢⠜⡠⢃⡐⢃⠄⢊⠁⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠠⡐⠡⡸⠀⢠⢃⡜⢰⠱⠇⣼⣿⣿⠄⠀⠈⠄⠠⠁⠠⢂⠡⡐⠐⡀⢠⣶⡎⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠠⠀⢂⠄⠃⠀⣬⣂⠀⢼⣿⣧⠀⢳⠈⠌⢡⢘⡇⡱⠄⡃⠌⡆⡘⠤⠁⢹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⡰⢁⠣⡅⡘⢄⠺⡄⢣⠛⢰⣿⣿⣿⠀⠀⠌⠠⠁⣴⣆⠁⢂⠔⠡⠀⣿⣿⣿⡸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀⡅⠀⢠⣄⡀⢈⣿⣿⣄⠈⣿⣿⣄⠈⠧⡘⢀⠎⡖⢱⡈⠔⡡⢚⡀⢆⡁⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡯⠀⡔⢡⢊⡵⢈⠜⣸⠐⣣⠁⣾⣿⣿⠿⠀⠀⠌⢀⣾⣿⡏⠀⠌⡠⢁⠀⠻⣿⣿⣷⡜⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⠿⠿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢋⣄⠀⡘⠀⠠⠘⢻⡻⣿⣿⣿⣿⠆⣿⣿⣧⠀⢃⠆⡡⢂⢝⠢⠜⡠⢁⠧⡈⢄⠒⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠰⡈⢆⣩⠆⣅⠚⣤⠙⡄⠸⣽⣿⣿⠁⠀⠀⣠⣿⣿⡿⠰⠀⢂⡁⢂⠀⣆⡈⠻⣿⣿⣦⡹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⣻⢖⡶⣹⢖⡶⣤⠦⠄⣹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣡⣿⡟⠠⠁⣀⠃⢀⢸⣿⣿⣿⣿⣿⡇⢿⣿⣿⡄⠈⢆⠡⢂⠌⣇⠓⠤⡉⢖⠡⠊⡌⢈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠅⢢⠑⡌⡲⢌⡄⣋⠴⣉⠀⣩⣿⣿⡏⠀⢀⣴⣿⣿⣿⢁⣿⡅⢀⠒⠠⢀⣿⣷⣆⡈⠛⠿⠛⠛⠻⠿⠿⠿⢿⣿⣿⣿⣿⣷⡈⠻⣜⣧⣻⡜⡧⠋⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⣋⣴⣿⡿⠀⠀⠐⠤⠁⣾⣇⢹⣿⡿⢿⣿⣿⢸⣿⣿⣯⠀⢨⠂⡅⢊⡼⡘⠤⡑⢎⠰⢡⠘⡀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⢢⡉⠴⣙⠤⡘⢤⡓⠌⢠⣾⣿⣿⠀⣠⣾⣿⣿⣿⠇⣾⣿⣯⠀⠌⡡⠠⣿⣿⣿⣿⣦⣄⣀⠀⠂⠀⠀⠀⠀⠀⠀⠀⠉⠛⢿⣷⣬⣌⣁⣭⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⣋⣥⣾⣿⣿⣿⢃⡆⠀⢩⢀⣾⣿⣿⡌⢿⣿⣎⣿⣿⡄⣿⣿⣿⡆⢀⠳⣸⠠⡹⢄⠣⡘⢼⢀⠣⡘⡀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡷⢀⠣⡘⢔⡫⢰⡉⢦⠍⠂⣸⣿⣿⡿⠁⣾⡟⣽⣿⡟⣰⣿⣿⣿⡀⢂⠡⢐⣿⣿⣿⣿⣿⣿⣿⣷⣤⠀⠀⠀⠋⠀⠀⠂⠀⠀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠋⣁⣀⣀⣉⣙⣛⣻⣿⣧⣞⠀⠨⢀⣾⣿⣿⣿⣿⡘⣿⣿⡜⣿⣷⠸⣿⣿⣷⡀⠱⢸⠅⣟⠄⢣⠑⢮⠠⢃⠴⠁⢺⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⢈⣒⣉⠆⠛⣀⣈⣐⢃⣴⣿⣿⣿⠅⢘⣿⣽⢿⡿⢠⣿⣿⣿⣿⣧⠀⠆⢈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣶⢢⣤⡠⢤⣤⣤⡴⢿⣿⣿⣿⣿⣿⣿⡿⠿⣛⣭⠇⣠⡴⣹⣿⣿⣿⣿⣿⣿⣿⣿⣿⠇⠀⢠⣾⣿⣿⣿⣿⣿⣧⢹⣿⣷⣽⣿⡆⢿⣿⣿⣷⡄⢚⣉⣈⠋⠠⣍⣺⠀⠉⠦⣉⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠠⠚⣃⣋⣰⣿⣿⣿⣟⣡⣿⣿⣿⣿⣿⣿⣿⡤⣶⢀⣾⣿⣿⣿⣿⣿⣂⠨⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣬⠛⡓⢦⡙⠻⣿⣷⣬⣍⣛⣭⣵⣶⣾⡿⢋⣡⠞⣉⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⡆⢩⣦⣛⣿⣿⣾⣿⣿⣿⣧⡙⢿⣿⣯⡑⣈⣑⣋⠳⢢⡀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⡄⢰⣿⣿⣿⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡔⡌⢿⣽⣿⣿⣿⣿⣿⣿⠄⠠⣿⣿⣿⣿⣿⣿⣿⣿⡿⢃⡿⣷⣶⠉⢢⡽⣷⣬⣙⠻⢿⣿⣿⠟⢋⣡⣴⢟⣡⡾⣽⣦⢿⣝⡻⣿⣿⣿⣿⣿⣿⠛⢀⣾⣿⣿⣿⣿⣿⣿⣿⡿⠻⠉⣄⣾⣿⣿⣿⣿⣿⣿⣿⣿⣼⣿⣿⣷⡘⣿⣿⡗⠀⢷⡀⣿⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⣇⢸⡁⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣮⢽⠃⠙⢿⣿⣿⣿⣷⠀⢿⣿⣿⣿⣿⡿⠛⠁⣶⢏⣼⣿⣿⣷⣦⣿⣿⣿⣿⡗⢢⡙⣡⢾⣿⣿⣿⣿⣿⣿⣿⣿⣷⣟⣿⡈⠻⠿⣿⣿⣿⣷⣾⣿⣿⣿⣿⣿⡿⠟⠡⡄⣊⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡗⠠⣸⠇⢹⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⣿⠇⠸⣷⡀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣀⠸⣦⣈⠻⢿⣿⣧⣿⣿⣿⣿⣿⠀⠘⡇⢻⣼⣿⣿⣿⣿⣿⣿⣿⣿⠿⢿⣦⠙⢹⠏⣿⣿⣿⣿⣿⣿⠟⢿⣿⣿⣿⠀⠳⣀⢻⣿⣿⣿⣿⣿⣿⣿⠿⢋⣤⡞⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⣰⡿⢀⢸⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⣿⡏⠀⠀⠙⢷⡄⠹⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣟⠀⠈⠙⢷⣆⡙⢿⣿⣿⣿⣿⣿⠁⢠⣆⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⠗⣀⣄⣤⣤⣌⡐⢼⣿⣿⡿⠁⢰⡦⢙⠿⡿⢀⣃⠈⣿⣿⣿⣿⣿⣿⠛⣡⡶⠟⠁⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠋⢀⣼⠟⠀⠠⠈⣿⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠈⠛⢷⣄⡙⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡗⠀⠀⠀⠀⠙⢷⣆⠹⣿⣿⡿⠃⠄⣸⡆⠀⢻⣿⣿⣿⣿⣿⣿⡟⠁⢰⡿⣯⢿⡽⣯⢿⡀⢻⣿⠁⢠⣧⣶⡏⣰⠁⢸⣇⠀⠈⣿⣿⣿⠏⢀⣶⠟⠁⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠉⣀⣴⠿⠉⠀⠀⠀⠁⠸⣿⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⡿⠁⠀⠀⠀⠀⠀⠀⠀⠉⠻⢶⣄⡙⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠙⣷⡌⠻⣧⠐⣰⣿⣷⠀⠈⢿⣿⣿⣿⡿⠋⡁⠔⢺⠿⣽⢫⡽⣯⣟⠲⠄⡙⠿⣦⣍⡛⣰⠏⠀⣿⣿⡄⠀⢨⡿⠃⣴⡟⠁⠀⠀⠀⠀⠀⠀⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠏⢁⣁⣴⠞⠋⠁⠀⠀⠀⠀⠀⠀⠀⢹⣿⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠷⣦⣄⡉⠛⠻⢿⣿⣿⣿⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣄⠁⣰⣾⣿⣿⣧⠀⠈⠉⢉⣀⣴⡾⣷⡀⠈⢻⣓⣯⣙⡳⠃⣀⣶⣌⣐⠠⢠⡉⢀⠀⣶⡿⣿⣿⣄⠘⠁⣼⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠐⢯⢿⣿⡿⡿⠻⠛⢉⣀⣤⡾⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿
        ⣿⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠻⠶⣤⡈⠉⠙⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⢁⠂⠀⣿⠀⠙⣿⣿⣽⣿⣿⣿⣷⣾⡿⣷⣻⢷⣻⠀⢠⣟⡾⣽⢣⠀⣾⣿⣿⣻⣷⣶⣶⣿⣯⣿⣷⢿⣿⡟⠀⢸⠃⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⢀⣠⡴⠚⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⣿
        ⣿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠙⠲⢍⡖⣆⠦⠤⠤⠤⢠⣄⡌⣤⢤⣤⣙⠖⢠⣿⣿⣻⣾⣿⣿⣿⣷⣿⣳⣽⣻⣿⠇⢸⣞⡽⣽⢫⠐⠿⣿⣷⣿⣿⣿⣿⣿⣿⣿⣿⣾⣿⡃⠐⣮⣤⢤⠤⣤⠤⣄⠤⠤⢤⢒⡤⢎⡜⠣⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿
        ⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠓⠉⠓⠾⠜⠻⠞⠙⠁⣰⣾⣿⣿⣽⣿⣿⣿⣿⣿⣷⣿⣞⣿⣿⠀⢸⣎⣟⢮⣏⠀⢺⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⣀⠙⠋⠛⠲⠛⠜⠉⠛⠈⠁⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣿
        ⣿⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢺⠀⣿⣿⣿⣿⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⣿⠀⢸⡮⣝⡞⡼⠀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⢸⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⣿
        ⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠀⡿⣼⡹⣜⡱⠂⣽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡅⠈⢸⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿
        ⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⡿⢃⠀⡿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢠⢳⢧⡝⢦⡹⡁⢹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠄⢈⠻⣿⣧⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡰⢻⣿⣿⠇⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⢰⣋⢶⡹⢎⡵⣁⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⣝⢿⣿⣿⡄⠈⠰⣿⣿⣿⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣰⣿⣿⡘⣿⠅⠠⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠸⡜⡶⣩⢳⢎⡵⢸⣿⣿⣿⡏⠹⠿⠿⠟⠻⠛⡟⠻⠟⠀⣿⣿⣷⡀⠠⠙⣿⡏⣸⣿⣶⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⡇⠝⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠂⢼⡹⣱⢏⡾⣘⠖⠘⣿⣿⣿⣿⣦⣉⣉⣭⣭⣤⣭⣤⣈⣸⣿⣿⣿⣧⠀⠘⢿⢀⣿⣿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⠀⠊⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⢧⡛⡽⢪⠵⣩⠞⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠹⣿⣿⣿⣿⣆⠈⠀⢸⣿⣿⣿⣿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⣿⣿⣿⣿⡿⠂⠀⢸⣿⣿⣿⣟⡳⢯⣛⠿⣻⢿⡿⣿⠻⣟⣿⣿⣿⣿⠀⣎⠵⣩⢳⡙⢦⢫⠄⢻⣿⣿⣿⣿⢿⣻⡟⣿⢫⠟⡵⢪⢇⣹⣿⣿⣿⣿⡇⢈⠹⣿⣿⣿⣿⣿⣿⣿⣷⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⣠⣾⢿⣿⡗⢮⡑⢣⠘⡬⢑⠮⡑⢎⡱⢎⡞⡽⢹⡃⠀⡎⢧⠣⢧⣝⢣⢏⠆⡸⣏⠿⣱⢎⢳⡘⡜⢢⢋⡜⢌⡑⢊⠴⢻⣿⣿⣿⡇⠈⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀

        """
        # get the full users table
        sql = "SELECT * FROM users"
        self.cursor.execute(sql)
        users_table = self.cursor.fetchall()

        # the table that all the results go into
        filtered_users = {}

        # iterate through the whole table
        for row in users_table:
            # if the search term in the row
            if search_term in " ".join(row).lower():
                filtered_users[f"{row[1]} {row[2]}  -  {row[3]}"] = row[0]
                #                first name  last name   email      user id

        return filtered_users

    def update_part(self, part_number, placement, mfr_pn, mfr, desc, qty):
        """update the row in the parts table with the new date for the part"""
        # convert the mfr if a name is given instead of an id
        if isinstance(mfr, str) and not mfr.isnumeric():

            placement = placement.upper()

            new_mfr = self.mfr_id_from_name(mfr)
            # if the new manufacturer isn't in the database
            if not new_mfr:
                mfr = self.add_mfr(mfr)
            else:
                mfr = new_mfr

        # make sure unique part placement
        find_placement = f"SELECT part_upc FROM parts WHERE part_placement = '{placement}'"
        self.cursor.execute(find_placement)

        matches = [result for result in self.cursor.fetchall() if int(result[0]) != int(part_number)]
        if matches: return "-PLACEMENT_ALREADY_TAKEN-"

        # do the update
        update_sql = f"UPDATE parts SET (part_placement, mfr_pn, part_mfr, part_desc, qty) = ('{placement}', '{mfr_pn}', {mfr}, '{desc}', {qty}) WHERE part_upc = {part_number}"
        print(update_sql)
        self.cursor.execute(update_sql)
        self.conn.commit()

    def placement_taken(self, placement):
        """make sure that the placement location provided isn't already in use"""

        # find the part in the database
        sql = f"SELECT * FROM parts WHERE part_placement = '{placement}'"
        self.cursor.execute(sql)
        results = self.cursor.fetchall()

        return bool(results)

    def part_checkout(self, part_id, user_id, force=False):
        """add the part to the currently checked out parts table"""

        # first: check if there is a matching part
        find_part_sql = f"SELECT * FROM parts where part_upc = {part_id}"
        self.cursor.execute(find_part_sql)

        # if len(self.cursor.fetchall()) <= 0:
        #     gui_window.confirm("This upc code does not belong to a known part")
        #     return

        # check if the value already exists
        search_sql = f"SELECT current_holder FROM part_locations WHERE checked_out_part = {part_id}"
        self.cursor.execute(search_sql)
        results_table = self.cursor.fetchall()

        # if results are found
        if len(results_table) > 0:
            # find the old userid in the users table
            old_user_sql = f"SELECT first_name, last_name FROM users WHERE user_id = '{results_table[0][0]}'"
            self.cursor.execute(old_user_sql)
            user_results = self.cursor.fetchall()
            old_holder = " ".join([user_results[0][0], user_results[0][1]])

            # tell the user that the part is already checked out
            if not force:
                return "-PART_HOLDER-;;"+old_holder

            # if the user has already gotten the prompt and confirmed that they would like to force check out
            else:
                # update the original row
                update_sql = f"""
UPDATE part_locations 
SET current_holder = '{user_id}', checkout_timestamp = CURRENT_TIMESTAMP 
WHERE checked_out_part = {part_id}"""
                self.cursor.execute(update_sql)

                # have a nice day
                return "-CHECKOUT_SUCCESS-"
        # if no results are found
        else:
            # sql to add the row
            insert_sql = f"INSERT INTO part_locations VALUES ({part_id}, '{user_id}', CURRENT_TIMESTAMP)"
            self.cursor.execute(insert_sql)

            return "-CHECKOUT_SUCCESS-"

    def add_user(self, f_name, l_name, email):
        """create a new user and return the userid"""

        # capitalize your name!
        f_name = f_name.title()
        l_name = l_name.title()

        # check if the email address is already used
        email_check_sql = f"SELECT * FROM users WHERE email = '{email}'"
        self.cursor.execute(email_check_sql)
        email_results = self.cursor.fetchall()

        # if there are matching emails
        if len(email_results) > 0:
            return "-EMAIL_ALREADY_TAKEN-"

        # if the first and last name is taken
        if self.name_is_taken(f_name, l_name):
            return "-NAME_ALREADY_TAKEN-"

        # generate a userid
        userid = (f_name[0] + l_name).lower()
        unique_id = 1
        userid_search_sql = f"SELECT * FROM users WHERE user_id = '{userid}'"

        # until a unique id is found
        while True:
            # execute the last set sql
            self.cursor.execute(userid_search_sql)
            userid_results = self.cursor.fetchall()

            # if no results
            if len(userid_results) <= 0: break

            # move up the id and try again
            unique_id += 1
            full_id = userid + str(unique_id if unique_id > 1 else '')
            userid_search_sql = f"SELECT * FROM users WHERE user_id = '{full_id}'"

        # if the email isn't already taken, add the user
        full_id = userid + str(unique_id if unique_id > 1 else '')
        add_user_sql = f"INSERT INTO users VALUES ('{full_id}', '{f_name}', '{l_name}', '{email}')"
        self.cursor.execute(add_user_sql)
        self.conn.commit()

        # return the userid
        return full_id

    def search_general(self, search_sql, search_term, filters, raw_table=False):
        """
        general search function that all the other search functions are built off of

        splits the input into individual words and uses search_general_word to get
        the results for each section. If a result in found in every section, that's a match.
        """

        # if there is no search term, return everything
        if search_term.isspace() or search_term == "":
            return self.search_general_word(search_sql, search_term, filters, raw_table)

        search_results = []
        for word in search_term.split():
            search_results.append(self.search_general_word(search_sql, word, filters, raw_table))

        return find_common_elements(search_results)

    def search_general_word(self, search_sql, search_term, filters, raw_table):
        """
        The original search_general; handles the input as a single string.
        This made it so that searching something like "John Doe" would have no
        results, as "John" is the first_name column and "Doe" is the last_name
        column.
        """
        # add each filter if it exists
        # filters in order: "DESC", "MFR", "MFR_PN", "LOC"
        connector = "WHERE"

        # I didn't event think of scanning into the search box, but this will let you do it now ig
        if search_term.isnumeric(): search_term = str(int(search_term))

        # remove white space
        search_term = search_term.replace("'", "''")
        for filter_name, state in filters.items():
            # if the filter is active (do search in that area, so not much of a filter is it?)
            if state:
                # add "where" or change the next clause to "or"
                search_sql += connector + " lower(cast("
                connector = "OR"

                # add the filter table
                search_sql += filter_name  # .split('-')[2]

                # finish off the line
                search_sql += f" as varchar)) LIKE '%{search_term.lower()}%'\n"

        self.cursor.execute(search_sql)
        search_results = self.cursor.fetchall()

        # change the table into a list of matching upcs
        formatted_results = [row[0] for row in search_results]

        # if there are no results
        if len(formatted_results) <= 0 or connector == "WHERE":
            formatted_results = ["No matching items"]
            search_results = [["No matching items", "No matching items"]]

        if raw_table: return search_results
        return formatted_results

    def search_for(self, keyword, search_key):
        """make a general search from the search area (keyword) and the search term (search_key)"""
        keyword = keyword.lower()

        # if a upc was selected
        if not search_key or search_key == "No matching items":
            return {"No result": ""}

        # remove extra characters from the search key
        if search_key.isnumeric(): search_key = str(int(search_key))

        # insert the data into the output box
        get_info_func = getattr(self, keyword + "_data")
        return get_info_func(search_key)

    def update_mfr_part_count(self, mfr_name):
        """update the number of parts for the mfr"""

        # get the mfr_id
        mfr_id = self.mfr_id_from_name(mfr_name)
        if not mfr_id: return

        # get the number of parts that have the mfr
        search_sql = f"SELECT * FROM parts WHERE part_mfr = {mfr_id}"
        self.cursor.execute(search_sql)
        parts_count = len(self.cursor.fetchall())

        # update the mfr data
        update_sql = f"UPDATE manufacturers SET number_of_parts = {parts_count}"
        self.cursor.execute(update_sql)
        self.conn.commit()

    # ------ functions unique to each search area
    # the [part/user]_search makes the list that you see and can pick from
    # the [part/user]_data generates that right hand column with all the info

    # parts
    def part_search(self, search_term, search_columns=None):
        """get the matching upc codes to a search term"""
        # sql to search for search term

        if search_columns is None:
            search_columns = {
                "part_upc": True,
                "part_placement": True,
                "mfr_pn": True,
                "mfr_name": True,
                "part_desc": True
            }


        search_sql = f"""
SELECT part_upc FROM parts 
JOIN manufacturers ON parts.part_mfr = manufacturers.mfr_id
"""
        results = self.search_general(search_sql, search_term, search_columns)
        return [str(item).zfill(12) for item in results]

    def part_data(self, target_upc, raw=False):
        """get the part information for a upc code"""
        # sql to search for search term
        search_sql = f"""
SELECT part_upc, part_placement, mfr_name, mfr_pn, part_desc, qty FROM parts 
JOIN manufacturers ON parts.part_mfr = manufacturers.mfr_id
WHERE cast(part_upc as varchar) = '{int(target_upc)}'"""
        self.cursor.execute(search_sql)
        search_results = self.cursor.fetchall()

        # get if the part is checked out
        check_checkout_sql = f"SELECT current_holder FROM part_locations WHERE checked_out_part = {int(target_upc)}"
        self.cursor.execute(check_checkout_sql)
        holder_id_table = self.cursor.fetchall()

        # if someone has the part checked out
        if holder_id_table:
            holder_id = holder_id_table[0][0]

            get_user_name_sql = f"SELECT first_name, last_name FROM users WHERE user_id = '{holder_id}'"
            self.cursor.execute(get_user_name_sql)
            holder_row = self.cursor.fetchall()[0]
            checkout_holder = f"{holder_row[0]} {holder_row[1]} ({holder_id})"

        # if nobody has the part checked out
        else:
            checkout_holder = "Not checked out"

        # take the first row
        if search_results:
            search_results = search_results[0]
        else:
            return {"No results": ""}

        # the mfr pn
        mfr_pn = search_results[3]
        mfr_pn = mfr_pn if mfr_pn else "Unknown"

        # change the table into a dictionary
        formatted_results = {
            "UPC code": str(search_results[0]).zfill(12),
            "Placement location": search_results[1],
            "Manufacturer": search_results[2],
            "Manufacturer's part number": mfr_pn,
            "Currently checked out by": checkout_holder,
            "Quantity": search_results[5],
            "Description": search_results[4]
        }

        # return raw results if requested
        if raw: return search_results[4], search_results[1]

        return formatted_results

    # users
    def user_search(self, search_term, columns=None, use_full_names=False):
        """get the matching user ids to a search term"""

        if not columns:
            columns = {
                "user_id": True,
                "first_name": True,
                "last_name": True,
                "email": True
            }

        # sql to search for search term
        search_sql = f"""
SELECT user_id, first_name, last_name FROM users
"""

        results_table = self.search_general(search_sql, search_term, columns, raw_table=True)
        results_dict = {row[0]: " ".join(row[1:]) for row in results_table}

        if use_full_names: return results_dict
        else: return results_dict.keys()

    def user_data(self, target_id, raw=False):
        """get the user information for a user id"""
        # sql to search for search term
        search_sql = f"""
SELECT user_id, first_name, last_name, email FROM users
WHERE user_id = '{target_id}'"""
        self.cursor.execute(search_sql)
        search_results = self.cursor.fetchall()

        # take the first row
        if search_results:
            search_results = search_results[0]
        else:
            return {"No results": ""}

        # get the number of parts checked out by the user
        checkout_search = f"SELECT checked_out_part, checkout_timestamp FROM part_locations WHERE current_holder = '{target_id}'"
        self.cursor.execute(checkout_search)
        parts_out = [str(part) + time.strftime("\non %b %d, %Y - %I:%M %p") for part, time in self.cursor.fetchall()]
        print(parts_out)
        print(type(parts_out))

        # if the program wants raw data and not a nice table
        if raw:
            return [search_results[i + 1] for i in range(3)]
        else:
            # change the table into a dictionary
            formatted_results = {
                "User ID": search_results[0],
                "First name": search_results[1],
                "Last name": search_results[2],
                "Email": search_results[3],
                "Parts checked out": parts_out
            }
            print(type(parts_out))
            return formatted_results

    # checked out parts
    def checkout_search(self, search_term, filters):
        """get the matching upc codes to a search term"""
        # sql to search for search term
        search_sql = f"""
SELECT checked_out_part FROM part_locations
JOIN parts ON part_locations.checked_out_part = parts.part_upc
JOIN users ON part_locations.current_holder = users.user_id
"""
        results = self.search_general(search_sql, search_term, filters)
        return [str(item).zfill(12) for item in results]

    def checkout_data(self, target_upc):
        """get the part information for a upc code"""
        # sql to search for search term
        search_sql = f"""
SELECT checked_out_part, part_desc, current_holder, first_name, last_name, checkout_timestamp FROM part_locations
JOIN parts ON part_locations.checked_out_part = parts.part_upc
JOIN users ON part_locations.current_holder = users.user_id
WHERE cast(checked_out_part as varchar) = '{target_upc}'"""
        self.cursor.execute(search_sql)
        search_results = self.cursor.fetchall()

        # take the first row
        if search_results:
            search_results = search_results[0]
        else:
            return {"No results": ""}

        # change the table into a dictionary
        formatted_results = {
            "Part UPC": search_results[0],
            "Part description": search_results[1],
            "Checked out by": f"{search_results[3]} {search_results[4]} ({search_results[2]})",
            "Checked out on": search_results[5].strftime("%A, %B %d, %I:%M %p, %Y")
        }

        return formatted_results

        # manufacturers

    def manufacturer_search(self, search_term, filters):
        """get the matching mfrs to a search"""

        # sql to search for search term
        search_sql = f"""
SELECT mfr_id FROM manufacturers
"""
        # normal
        internal_results = self.search_general(search_sql, search_term, filters)

        # if the no results message is here, just pass it on.
        if isinstance(internal_results[0], str): return internal_results

        # turn search list into a string list
        result_strings = [str(term) for term in internal_results]

        # search for the mfr names using the provided id's
        search_list = "(" + ", ".join(result_strings) + ")"
        new_search = "SELECT mfr_name FROM manufacturers WHERE mfr_id in " + search_list

        # get the results
        self.cursor.execute(new_search)
        results = self.cursor.fetchall()

        # return the formatted list
        return [item[0] for item in results]

    def manufacturer_data(self, target_name):
        """get the part information for a upc code"""

        # first off, update the checked out parts for the mfr
        self.update_mfr_part_count(target_name)

        # sql to search for search term
        search_sql = f"""
SELECT mfr_id, mfr_name, number_of_parts FROM manufacturers
WHERE mfr_name = '{target_name}'"""
        self.cursor.execute(search_sql)
        search_results = self.cursor.fetchall()

        # take the first row
        if search_results:
            search_results = search_results[0]
        else:
            return {"No results": ""}

        # change the table into a dictionary
        formatted_results = {
            "Unique serial ID": search_results[0],
            "Manufacturer name": search_results[1],
            "Number of parts in database": search_results[2]
        }

        return formatted_results

    def customer_exists(self):
        user_check_sql = "SELECT 1 FROM pg_roles WHERE rolname='customer'"
        self.cursor.execute(user_check_sql)

        return "customer" in self.cursor.fetchall()
