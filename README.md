# Blur part organizer

This program is intended to help organize parts, calibrated equipment,
etc. by utilizing a PostgreSQL database. This program should be set up
on a dedicated kiosk machine near the parts intended to be organized.

If you're reading this in the program, to begin, select one of the sections on the left side of the window.

If you're reading this from GitHub, this README file is displayed on the program's home 
screen.

### Initial setup

1. first, download the latest version of [PostgreSQL](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
and the [Zebra ZSB Drivers](https://zsbportal.zebra.com/apps). 

2. Go through the Zebra ZSB setup. To log into the Zebra workspace,
use the email blur.zebra@gmail.com and the password #Blur2018!!!

3. Run the PostgreSQL setup, unchecking the box for Stack Builder

![Uncheck Stack Builder](https://raw.githubusercontent.com/TotalHelix/Blur_organizer_v2/refs/heads/main/images/Uncheck%20Stack%20Builder.png)

4. Continue through the installer accepting all defaults, entering `blur4321` when 
prompted for a password

5. In the Blur Organizer under the `Danger Zone` tab, select `Format Database` to
set up the database

## Example Program Use
![Screenshot of program filled with sample data](https://raw.githubusercontent.com/TotalHelix/Blur_organizer_v2/refs/heads/main/images/Example%20Program%20Use.png)

### Checking out parts

Under the `Part Search` tab, select the part that you want to check out or return, and the click on the `Check Out` or `Return` buttons at the bottom.

### Adding a part or user

To add a part or user, go to the appropriate `Manage Parts` or `Manage Users` tab, and click on the `+ Add` button below the search box. Fill out the form according to the part/user that you want to add, and then click `Submit`.

### Finding a part or user

If you are looking for a part, the search box in `Part Search` can search by UPC, description,
manufacturer, manufacturer's part number, or placement location.

If you're looking for a user, the search in `User Search` can find by either user id, name, 
or email.

### Making a label

With the part that you want to make a label for selected in the `Find a part` screen, click 
the `Print` button.
