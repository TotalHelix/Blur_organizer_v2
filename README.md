# Blur part organizer

to begin, select one of the sections on the left side of the window.

### Initial setup

1. first, download the latest version of [PostgreSQL](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
   and the [Zebra ZSB Drivers](https://storage.googleapis.com/spg-zpc-p-printer-tools/Windows/ZSB%20Printer%20Tools%20Installer.exe?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=zsbpportal-service-account%40spg-zpc-p.iam.gserviceaccount.com%2F20240712%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20240712T170823Z&X-Goog-Expires=3600&X-Goog-SignedHeaders=host&X-Goog-Signature=d6e5111289a046e7a74d123185c5845c8ea8dec61edf3272523122382e3620f0e8c39b6032587000fad5e6cdf0b950498e5b89de47f01c5c9676e832770e5444dfc1bfa76cc00c2f0ab41a7224f24187500d074a3e587a53a71f6c1973f0de92b61c20bbb7b2cc43add18d8a1babb70ebe03155d13ae1f3dddf5b234d5992118f88762b3ec2aa48e03b9fa45e657b4a98a27a901d680aae437ba459cecc75fd2eef91e5994b5a61ceef60b9f6f412692d049473ec662c7db5e8de441942b9fd77c256c35dff23f7e551e7d7f96bf84b7bf0b04457bec22f1d589b4d2913a1d105179ce6aae21855b0151bbdc90535b21aae82d58dfe12038b6cb0e4f6f899eeb)

2. Run the PostgreSQL setup, unchecking the box for Stack Builder

![Uncheck Stack Builder](https://i.imgur.com/upIszbK.png)

3. Continue through the installer accepting all defaults, entering `blur4321` when 
prompted for a password

4. In the Blur Organizer under the `Danger Zone` tab, select `Format Database` to
set up the database

### Adding a part or user

To add a part, go to the `Part Search` tab, and click on the `+ Add` button below the     
search box. Fill out the form according to the part that you want to add, and then click
`Submit`.

### Finding a part or user

If you are looking for a part, the search box in `Part Search` can search by UPC, description,
manufacturer, manufacturer's part number, or placement location.

If you're looking for a user, the search in `User Search` can find by either user id, name, 
or email.

### Making a label

With the part that you want to make a label for selected in the `Find a part` screen, click 
the `🖨 Print` button.