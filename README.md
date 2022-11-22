# print-proxy-prep
Crop bleed edges from proxy images and make PDFs for at-home printing.

![image](https://user-images.githubusercontent.com/103437609/203212263-1a029874-3611-4daf-8ac5-e1d23b429db6.png)

# Installation
You're gonna need <a href="https://www.python.org/downloads/">Python</a>, I'd say whatever the latest version is, should work.
When installing, make sure to add Python to PATH.
![image](https://user-images.githubusercontent.com/103437609/203196002-f04b0c0d-cb2e-4154-ba90-f2f9578ced95.png)

With Python installed, go ahead and download the zip and unzip it wherever you like.
![image](https://user-images.githubusercontent.com/103437609/203219985-019cea6e-2a85-4ea8-ba90-b96e7665eae7.png)

I made a couple batch scripts to help with installation if you're not savvy with Python, go ahead and run 1_SETUP.bat and it should make a folder called "images" and one called "venv". Then, it will use pip to install the dependancies from "requirements.txt" into that virtual environment.

Then, you can run main.py from the command line like "venv\scripts\python main.py", or I have "2_RUN.bat" that you can just click and it will pop up the GUI.

# Running the Program
![image](https://user-images.githubusercontent.com/103437609/203212112-50db47df-0a4e-4bf2-9c59-a8554f521b7c.png)

First, throw some images in the \images\ folder. Then, when you opem main.py or hit the "Run Cropper" button from the GUI, it will go through all the images and calculate and crop them.

You can either use the +/- buttons, left or right click the images themselves, or input whatever number you want (good for basic lands for example). I've included sizing for Letter (8.5" x 11"), A4 (8.27" x 11.69"), and Legal (8 1/2" x 14"), but other options would be easy to add if it's requested. Last, you can name your pdf. You don't need to add a ".pdf", I've got that covered for you.

When you're done getting your print order setup, hit "Render PDF" and it will make your PDF and open it up for you. Hopefully you can handle yourself from there.

# SOME NOTES:
- The program will automatically save if you close the window. It will not save if you close the console window or if it crashes! The data is stored in print.json.
- image.cache if a file that is made that stores the data for the thumbnails.
- Both of these should be deleted if they get out of sync with your images\crops folder, so they can be repopulated. When in doubt, close the program and open it again!

I'll be working on streamlining stuff, feel free to make suggestions.
