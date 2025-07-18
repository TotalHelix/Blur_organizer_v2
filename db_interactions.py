# label printing
import os
import random
import pywintypes
from textwrap import wrap
from zpl import Label
from zebra import Zebra

# database
from psycopg2 import connect
from psycopg2 import errors as db_err
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import date, datetime
from socket import gethostname

# random generation (populate database)
import lorem
from random import randint, choice
from names import get_first_name, get_last_name


file_location = os.getenv("APPDATA") + "\\Blur_Part_Organizer\\"
kiosk_location_name_file = "kiosk_name.txt"
kiosk_path = file_location + kiosk_location_name_file
params = {
    'database': 'postgres',
    'user': 'postgres',
    'password': 'blur4321',
    'host': '172.20.61.86',
    'port': 5432
}


def get_location():
    """return the name that will show up as the location when a part is checked out from this device
    If no location file exists the current hostname is set as the new locatoin. This can be changed in Danger Zone."""
    try:
        with open(kiosk_path, "r") as kiosk:
            return kiosk.read()
    except FileNotFoundError:
        new_name = gethostname()
        set_location(new_name)
        return new_name


def set_location(new_name):
    """Set a new name to appear when parts are checked out from this device"""
    # make apostrophes (') safe
    new_name = new_name.replace("'", "''")

    with open(kiosk_path, "w") as kiosk:
        kiosk.write(new_name)


def find_common_elements(list_to_compare):
    if not list_to_compare or list_to_compare == [[['No matching items', 'No matching items']]]:
        return None

    # Start with the first list's elements as the base set
    common_elements = set(list_to_compare[0])

    # Intersect with the remaining lists
    for lst in list_to_compare[1:]:
        common_elements.intersection_update(lst)

    return list(common_elements)


def render_upc(code, placement, desc_text, printer="Zebra "):
    """
    the new way to render upc codes using zebra zpl
    returns the error that took place when printing (or none)
    """
    # upc_new(code)

    args = (code, placement, desc_text, printer)
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
    # print to zebra printer
    if "zebra" in printer.lower():
        # generate the command
        zpl_command = label.dumpZPL()
        print(zpl_command)

        # get the printer
        z = Zebra()
        print(printer)

        # set the printer queue
        all_queues = z.getqueues()
        zsb_queues = [queue for queue in all_queues if "zsb" in queue.lower()]

        for zsb_queue in zsb_queues:
            try:
                z.setqueue(zsb_queue)

                # Output the ZPL command to the printer
                z.output(zpl_command)

                print(f"Print job sent to {zsb_queue}.")
            except pywintypes.error:
                print(f"Print failed on {zsb_queue}.")

    elif "preview" in printer.lower():
        label.preview()

    # invalid printer type
    else:
        return "Invalid printer type. This is most likely an issue with the program.", code, placement, desc_text, printer


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
    def __init__(self, conn_type="local", conn_info=None):
        """connect to a database and return the connection"""

        # default connection info
        if not conn_info: conn_info = {"database": "blur_organizer_db", "user": None, "password": "blur4321"}

        # define some variables
        self.db_name = conn_info["database"]
        self.conn_type = conn_type
        self.conn_info = conn_info
        self.postgres_info = self.conn_info
        self.postgres_info["database"] = "postgres"
        self.conn = None
        self.cursor = None

        # self.conn and self.cursor are set in self.db_connect()
        print("about to db connect")
        self.db_connect()
        print("db connected")

        # self.cursor.execute("\\set autocommit on")

    def __enter__(self, user=None):
        # This is here for the purpose of being able o say "with Organizer()" instead of creating a new Organizer.
        # if not user: user = f"customer_{self.db_name}"
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def db_connect(self, new_connection_info=None):
        """privilege will either be "customer" or "postgres" """

        if not new_connection_info: new_connection_info = self.conn_info

        # if this is local database
        print(f"about to invoke postgres. conn info: {new_connection_info}")
        try:
            self.conn = connect(**new_connection_info)
            print("connection established. Starting cursor")
            self.cursor = self.conn.cursor()
            self.conn.autocommit = True
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            print("cursor established.")
        except Exception as error:
            print(str(error))

    def userid_exists(self, userid):
        """check if the userid specified exists in the database"""
        search_sql = f"SELECT user_id FROM users WHERE user_id = '{userid}'"
        self.cursor.execute(search_sql)
        if self.cursor.fetchall()[0][0] == userid: return True
        else: return False

    def part_num_from_upc(self, upc):
        search_sql = f"SELECT mfr_pn FROM parts WHERE part_upc = {upc}"
        self.cursor.execute(search_sql)
        result = self.cursor.fetchall()[0][0]
        return result

    def select_all_db(self):
        search_sql = "SELECT datname FROM pg_database WHERE datistemplate = false;"
        self.cursor.execute(search_sql)
        result = self.cursor.fetchall()
        return result

    def user_id_from_name(self, name):
        name_split = name.split()
        first_name, last_name = name_split[0], name_split[-1]
        search_sql = f"SELECT user_id FROM users WHERE first_name = '{first_name}' AND last_name = '{last_name}'"

        self.cursor.execute(search_sql)
        result = self.cursor.fetchall()
        print("user_id result:", result)
        if result and result[0]:
            return result[0][0]
        else:
            return ["No matching items"]

    def upc_exists(self, upc):
        """check a upc to see if it exists in the database"""
        self.cursor.execute(f"SELECT * FROM parts WHERE part_upc = {upc}")
        return self.cursor.fetchall()

    def drop_db(self, db_name):
        """disconnect from the selected database and then drop it"""
        # disconnect from db
        terminate_conn = f"""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE 
                pid <> pg_backend_pid()
                AND datname = '{db_name}';
            """
        self.cursor.execute(terminate_conn)
        self.refresh_cursor()

        # drop database
        self.conn.commit()
        print("inside db drop func")
        drop_db = f"DROP DATABASE {db_name};"
        self.cursor.execute(drop_db)
        self.conn.commit()
        print("hey it worked")

        self.conn.commit()

    def format_database(self, db_name):
        """set up all the tables of the database"""
        print("format called")
        self.cursor.close()
        self.conn.commit()
        self.conn.close()

        self.db_connect(new_connection_info=self.postgres_info)
        print("established as postgres")

        # find out if the database already exists and needs to be dropped
        # this could probably be done in sql, but is simpler to do in python
        get_db_list = "SELECT datname FROM pg_database"
        self.cursor.execute(get_db_list)

        # if the database does already exist
        if db_name in [name[0] for name in self.cursor.fetchall()]:
            print("there was a database in there")

            print("about to drop db")
            self.drop_db(db_name)
            print("dropped db")
        print("after db drop")

        # create a new database
        new_db_sql = f"CREATE DATABASE {db_name};"
        self.cursor.execute(new_db_sql)

        # first thing before switching to the new db, drop anything from the customer role in postgres
        self.disconnect_customer()

        # ----- now that the right database exists, let's connect to it

        # i swear if I have to do anything else with this table i'm going to turn it into a spreadsheet
        tables_setup = {
            "users":
                [
                    # name              data type              len   primary key references extra tags
                    ["user_id", "varchar", "53", True, None, "NOT NULL"],
                    ["first_name", "varchar", "50", False, None, "NOT NULL"],
                    ["last_name", "varchar", "50", False, None, "NOT NULL"],
                    ["email", "varchar", "255", False, None, ""]
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
                    # name                  data type                       len     primary key references                  extra tags
                    ["part_upc",            "bigint",                       None,   True,       None,                       "NOT NULL"],
                    ["part_placement",      "varchar",                      "26",    False,      None,                       "NOT NULL"],  # UNIQUE"],
                    ["mfr_pn",              "varchar",                      "26",  False,      None,                       "NOT NULL"],
                    ["part_mfr",            "varchar",                      "255",  False,      'manufacturers; mfr_id',    "NOT NULL"],
                    ["part_desc",           "varchar",                      None,   False,      None,                       ""],
                    ["url",                 "varchar",                      None,   False,      None,                       ""],
                    ["date_added",          "timestamp without time zone",  None,   None,       None,                       "NOT NULL"]
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
                print("\t2")

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

            print("\t3")
            print(create_command)

            self.cursor.execute(create_command)
            self.conn.commit()

            # remake the customer
            self.new_user(db_name)
            self.conn.commit()

            # recreate the

    def mfr_id_from_name(self, mfr_name):
        """get return the mfr id given the mfr name"""
        mfr_id_sql = f"SELECT mfr_id FROM manufacturers WHERE lower(mfr_name) = '{mfr_name.lower()}'"
        self.cursor.execute(mfr_id_sql)
        mfr_id = self.cursor.fetchall()

        # return the id if it's found, otherwise don't return anything
        if mfr_id: return mfr_id[0][0]

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
        name_matches = f"SELECT user_id FROM users WHERE last_name = '{lname}' AND first_name = '{fname}' AND NOT user_id = '{old_id}'"
        self.cursor.execute(name_matches)
        # matching_names = [row for row in self.cursor.fetchall() if row[0] != fname]
        if self.cursor.fetchall(): return "-NAME_ALREADY_TAKEN-"

        # I was going to have this change the userid as well but that was more complicated than expected, as thew userid is a primary key
        update_sql = f"UPDATE users SET (first_name, last_name, email) = ('{fname}', '{lname}', '{email}') WHERE user_id = '{old_id}'"
        self.cursor.execute(update_sql)
        self.conn.commit()

        return old_id

    def upc_create(self, code):
        get_sql = f"SELECT part_placement, part_desc FROM parts WHERE part_upc = {code}"
        self.cursor.execute(get_sql)
        placement, desc = self.cursor.fetchall()[0]

        render_upc(code, placement, desc)

    def disconnect_customer(self):
        """drop all dependencies on the customer role"""

        # see if the customer role exists
        self.cursor.execute(f"SELECT pg_roles.rolname FROM pg_roles WHERE pg_roles.rolname = 'customer_{self.db_name}'")

        # if it does:
        if self.cursor.fetchall():
            disconnect_role = f"""
            REASSIGN OWNED BY customer_{self.db_name} TO postgres;
            DROP OWNED BY customer_{self.db_name};"""
            self.cursor.execute(disconnect_role)
            self.refresh_cursor()

    def new_user(self, db_name):
        """dumb function that creates a user because it gets mad when it's in the other one"""
        # first off, get rid of role dependencies of they exist
        self.disconnect_customer()

        # connect to the database
        self.cursor.close()
        self.conn.commit()
        self.conn.close()
        self.db_connect(new_connection_info=self.postgres_info)

        user_create = f"""
        REASSIGN OWNED BY customer_{db_name} TO postgres;
        DROP OWNED BY customer_{db_name};
        
        DROP ROLE IF EXISTS customer_{db_name};
        CREATE ROLE customer_{db_name}  WITH
            LOGIN
            NOINHERIT
            PASSWORD 'blur4321';
        
        GRANT CONNECT ON DATABASE {db_name} TO customer_{db_name};
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO customer_{db_name};
        GRANT INSERT ON ALL TABLES IN SCHEMA public TO customer_{db_name};
        GRANT DELETE ON ALL TABLES IN SCHEMA public TO customer_{db_name};
        GRANT UPDATE ON ALL TABLES IN SCHEMA public TO customer_{db_name};
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO customer_{db_name};
        
        GRANT CONNECT ON DATABASE {db_name} TO postgres;
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

    def populate_db(self, db_name):
        """fill the desired table with sample data"""

        # get the current tables
        # get_tables_sql = "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        # self.cursor.execute(get_tables_sql)
        # print(self.cursor.fetchall())

        # first off, this does not need superuser
        self.cursor.close()
        self.conn.commit()
        self.conn.close()
        self.db_connect()

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
            mfr_pn = ""
            for i in range(randint(4, 18)):
                mfr_pn += str(randint(0, 9))
            # pick a manufacturer
            mfr = choice(self.get_rows("mfr_id"))
            # come up with a description
            desc = lorem.sentence()
            # make a url
            url = "https://"+random_word()+random.choice((".org", ".com", ".net"))+"/"+hex(randint(1000000000, 999999999999999999)) if random.randint(1, 3) > 1 else None

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

            added_date = datetime.fromtimestamp(randint(0, 1826244364))
            added_str = added_date.strftime("%Y-%m-%d %H:%M:") + str(randint(0, 59999999) / 1000000)

            sql = f"INSERT INTO parts VALUES ({upc}, '{placement}', '{mfr_pn}', '{mfr}', '{desc}', '{url}', '{added_str}')"
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
            self.part_checkin(part[0])

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
        except db_err.ForeignKeyViolation:
            return "-PARTS_STILL_CHECKED_OUT-"

        self.conn.commit()
        return "-SUCCESS-"

    def add_part(self, desc, mfr_name, mfr_pn, placement="None", url="None"):
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

        # make apostrophes safe
        safe_desc = desc.replace("'", "''")
        safe_mfr_pn = mfr_pn.replace("'", "''")
        safe_placement = placement.replace("'", "''")

        # make sure the webpage starts with https
        if "." not in url: url = None
        elif not url.startswith("https://"): url = "https://"+url

        date_added = datetime.today().strftime("%Y-%m-%d %H:%M:")

        # ----- perform the insertion 😈
        sql = f"INSERT INTO parts VALUES ({upc}, '{safe_placement}', '{safe_mfr_pn}', '{mfr_id}', '{safe_desc}', '{url}', '{date_added}')"
        self.cursor.execute(sql)

        # change the mfr table to display the number of parts
        update_mfrs_table = f"""
UPDATE manufacturers SET number_of_parts = {unique_id} WHERE mfr_id = {mfr_id}"""
        self.cursor.execute(update_mfrs_table)

        # return render_upc(upc, safe_placement, desc, printer="Zebra ")
        return upc

    def add_mfr(self, mfr_name):
        self.cursor.execute(f"INSERT INTO manufacturers VALUES (default, '{mfr_name}', 0) RETURNING mfr_id")
        self.conn.commit()

        return self.cursor.fetchall()[0][0]

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

                self.update_location(upc)
                self.conn.commit()
                return "Part successfully returned."
            else:
                return "The scanned part was never checked out."

        else:
            # if the part can't be found in the parts table
            return """This hasn't been added yet.
Please click "Add part" to add a part for the first time"""

    def update_part(self, part_number, mfr_pn, mfr, desc, url):
        """update the row in the parts table with the new date for the part"""
        if url == "": url = None
        elif not url.startswith("https://"): url = "https://"+url

        # convert the mfr if a name is given instead of an id
        if isinstance(mfr, str) and not mfr.isnumeric():

            new_mfr = self.mfr_id_from_name(mfr)
            # if the new manufacturer isn't in the database
            if not new_mfr:
                mfr = self.add_mfr(mfr)
            else:
                mfr = new_mfr

        # do the update
        update_sql = f"UPDATE parts SET (mfr_pn, part_mfr, part_desc, url) = ('{mfr_pn}', {mfr}, '{desc}', '{url}') WHERE part_upc = {part_number}"
        self.cursor.execute(update_sql)
        self.conn.commit()

    def part_checkout(self, part_upc, user_id, force=False):
        """add the part to the currently checked out parts table"""

        # first: check if there is a matching part
        find_part_sql = f"SELECT * FROM parts where part_upc = {part_upc}"
        self.cursor.execute(find_part_sql)

        # check if the value already exists
        search_sql = f"SELECT current_holder FROM part_locations WHERE checked_out_part = {part_upc}"
        self.cursor.execute(search_sql)
        results_table = self.cursor.fetchall()

        # if the part is already checked out
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
WHERE checked_out_part = {part_upc}"""
                self.cursor.execute(update_sql)

                # have a nice day
                self.update_location(part_upc)
                return "-CHECKOUT_SUCCESS-"

        # if the part isn't checked out already
        else:
            # sql to add the row
            insert_sql = f"INSERT INTO part_locations VALUES ({part_upc}, '{user_id}', CURRENT_TIMESTAMP)"
            self.cursor.execute(insert_sql)

            self.update_location(part_upc)
            return "-CHECKOUT_SUCCESS-"

    def update_location(self, upc_to_update):
        """update the part location to the current kiosk location of this kiosk"""
        update_sql = f"UPDATE parts SET part_placement = '{get_location()}' WHERE parts.part_upc = {upc_to_update}"
        self.cursor.execute(update_sql)

    def add_user(self, f_name, l_name, email):
        """create a new user and return the userid"""

        # capitalize your name!
        f_name = f_name.title()
        l_name = l_name.title()

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
        print("search_term:", search_term)

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
        if (not search_results) or len(search_results[0]) > 1:
            formatted_results = search_results
        else:
            formatted_results = [row[0] for row in search_results]

        # if there are no results
        if len(formatted_results) <= 0 or connector == "WHERE":
            formatted_results = ["No matching items"]
            search_results = [["No matching items", "No matching items"]]

        if raw_table: return search_results
        return formatted_results

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
    def part_search(self, search_term, search_columns=None, more_info=True):
        """get the matching upc codes to a search term"""
        # sql to search for search term

        if search_columns is None:
            search_columns = {
                "part_upc": True,
                "part_placement": True,
                "mfr_pn": True,
                "mfr_name": True,
                "part_desc": True,
                "url": True
            }

        search_sql = f"""
SELECT mfr_pn, mfr_name, part_upc, part_placement, part_desc, date_added FROM parts 
JOIN manufacturers ON parts.part_mfr = manufacturers.mfr_id
"""
        results = self.search_general(search_sql, search_term, search_columns)
        if not more_info:
            return [str(item[2]).zfill(12) for item in results]
        else:
            if (not results) or results[0] == "No matching items": return [[' ', ' ', "No Results", *(" " for _ in range(3))]]
            unscrambled = [[str(row[2]).zfill(12), row[0], row[1], row[5].strftime("%m/%d/%Y"), row[3], row[4]] for row in results]
            why_another_stage = []

            for row in unscrambled:
                self.cursor.execute(f"SELECT first_name, last_name FROM part_locations JOIN users ON part_locations.current_holder = users.user_id WHERE checked_out_part = {row[0]}")
                result = self.cursor.fetchall()
                if result: result = " ".join(result[0])
                # why_another_stage.append([*row, "✖" if result else "✔"])  # looks better but there's a stray pixel on the check ):
                # why_another_stage.append([*row, chr(0x00A0) if result else "✓"])
                why_another_stage.append([*row, f"Out ({result})" if result else "Available"])

            return [[u[1], u[2], u[0], u[3], u[4], u[5], u[6]] for u in why_another_stage]

    def part_data(self, target_upc, raw=False):
        """get the part information for a upc code"""

        if not target_upc or (isinstance(target_upc, str) and not target_upc.isnumeric()):
            return {"Invalid Search": ""}

        # sql to search for search term
        search_sql = f"""
SELECT part_upc, part_placement, mfr_name, mfr_pn, part_desc, url, date_added FROM parts 
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

        print("search_results??", search_results)
        # change the table into a dictionary
        formatted_results = {
            "UPC code": str(search_results[0]).zfill(12),
            "Placement location": search_results[1],
            "Manufacturer": search_results[2],
            "Part number": mfr_pn,
            "Currently checked out by": checkout_holder,
            "Description": search_results[4],
            "Link to original part": search_results[5],
            "Date added": search_results[6].strftime("%b %d, %Y - %I:%M %p")
        }

        # return raw results if requested
        if raw: return search_results[4], search_results[1]

        return formatted_results

    # users
    def user_search(self, search_term, columns=None, use_full_names=False):
        """get the matching user ids to a search term
        :returns a dict {user_id: First Name, Last Name, Email} if use_full_names is True.
            otherwise it returns a list of user ids"""

        # NOTE: the columns argument is WHERE to look for matches, NOT what columns to return.
        if not columns:
            columns = {
                "user_id": True,
                "first_name": True,
                "last_name": True,
                "email": True
            }

        # sql to search for search term
        search_sql = f"""
SELECT user_id, first_name, last_name, email FROM users
"""
        results_table = self.search_general(search_sql, search_term, columns, raw_table=True)

        if (not results_table) or (not results_table[0]):
            return {"No Results": ("No Results", *(" " for _ in range(2)))}

        print(results_table[0])
        print(len(results_table[0]))
        if len(results_table[0]) > 2:
            results_dict = {row[0]: (row[0], " ".join(row[1:3]), row[3]) for row in results_table}
        else:
            results_dict = {"No Results": ("No Results", *(" " for _ in range(2)))}

        if list(results_dict.keys())[0] == " ":
            return {"No matching items": "No matching items"}
        elif use_full_names: return results_dict
        else: return list(results_dict.keys())

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
            return formatted_results

    def cursor_exists(self):
        return self.cursor
