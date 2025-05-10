import os
import math
import json
import time
import base64
import subprocess
import configparser
import io
import re
from PIL import Image, ImageFilter
import FreeSimpleGUI as sg
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4, legal

sw, sh = sg.Window.get_screen_size()
sg.theme("DarkTeal2")

def popup(middle_text):
    return sg.Window(
        middle_text,
        [
            [sg.Sizer(v_pixels=20)],
            [sg.Sizer(h_pixels=20), sg.Text(middle_text), sg.Sizer(h_pixels=20)],
            [sg.Sizer(v_pixels=20)],
        ],
        no_titlebar=True,
        finalize=True,
    )


loading_window = popup("Loading...")
loading_window.refresh()

cwd = os.path.dirname(__file__)
image_dir = os.path.join(cwd, "images")
crop_dir = os.path.join(image_dir, "crop")
print_json = os.path.join(cwd, "print.json")
img_cache = os.path.join(cwd, "img.cache")
for folder in [image_dir, crop_dir]:
    if not os.path.exists(folder):
        os.mkdir(folder)

config = configparser.ConfigParser()
config.read(os.path.join(cwd, "config.ini"))
cfg = config["DEFAULT"]

def grey_out(main_window):
    the_grey = sg.Window(
        title="",
        layout=[[]],
        alpha_channel=0.6,
        titlebar_background_color="#888888",
        background_color="#888888",
        size=main_window.size,
        disable_close=True,
        location=main_window.current_location(more_accurate=True),
        finalize=True,
    )
    the_grey.disable()
    the_grey.refresh()
    return the_grey


def draw_cross(can, x, y, c=6, s=1):
    dash = [s, s]
    can.setLineWidth(s)
    can.setDash(dash)
    can.setStrokeColorRGB(255, 255, 255)
    can.line(x, y - c, x, y + c)
    can.setStrokeColorRGB(0, 0, 0)
    can.line(x - c, y, x + c, y)
    can.setDash(dash, s)
    can.setStrokeColorRGB(255, 255, 255)
    can.line(x - c, y, x + c, y)
    can.setStrokeColorRGB(0, 0, 0)
    can.line(x, y - c, x, y + c)


def pdf_gen(p_dict, size):
    rgx = re.compile(r"\W")
    img_dict = p_dict["cards"]
    w, h = 2.48 * 72, 3.46 * 72
    rotate = bool(p_dict["orient"] == "Landscape")
    size = tuple(size[::-1]) if rotate else size
    pw, ph = size
    pdf_fp = os.path.join(
        cwd,
        f"{re.sub(rgx, '', p_dict['filename'])}.pdf"
        if len(p_dict["filename"]) > 0
        else "_printme.pdf",
    )
    pages = canvas.Canvas(pdf_fp, pagesize=size)
    cols, rows = int(pw // w), int(ph // h)
    rx, ry = round((pw - (w * cols)) / 2), round((ph - (h * rows)) / 2)
    total_cards = sum(img_dict.values())
    pbreak = cols * rows
    i = 0
    for img in img_dict.keys():
        img_path = os.path.join(crop_dir, img)
        for n in range(img_dict[img]):
            p, j = divmod(i, pbreak)
            y, x = divmod(j, cols)
            if j == 0 and i > 0:
                pages.showPage()
            pages.drawImage(
                img_path,
                x * w + rx,
                y * h + ry,
                w,
                h,
            )
            if j == pbreak - 1 or i == total_cards - 1:
                # Draw lines
                cross = 6
                for cy in range(rows + 1):
                    for cx in range(cols + 1):
                        draw_cross(pages, rx + w * cx, ry + h * cy)
            i += 1
    saving_window = popup("Saving...")
    saving_window.refresh()
    pages.save()
    saving_window.close()
    try:
        subprocess.Popen([pdf_fp], shell=True)
    except Exception as e:
        print(e)


def cropper(folder, img_dict):
    if cfg.getboolean("Vibrance.Bump"):
        with open(os.path.join(cwd, "vibrance.CUBE")) as f:
            lut_raw = f.read().splitlines()[11:]
        lsize = round(len(lut_raw) ** (1 / 3))
        row2val = lambda row: tuple([float(val) for val in row.split(" ")])
        lut_table = [row2val(row) for row in lut_raw]
        lut = ImageFilter.Color3DLUT(lsize, lut_table)
    i = 0
    if not os.path.exists(crop_dir):
        os.mkdir(crop_dir)
    for img_file in os.listdir(folder):
        if (
            os.path.splitext(img_file)[1] not in [".gif", ".jpg", ".jpeg", ".png"]
            or os.path.isdir(img_file)
            or os.path.exists(os.path.join(folder, "crop", img_file))
        ):
            continue
        with Image.open(os.path.join(folder, img_file)) as im:
            i += 1
            w, h = im.size
            c = round(0.12 * min(w / 2.72, h / 3.7))
            dpi = c*(1/0.12)
            print(
                f"{img_file} - DPI calculated: {dpi}, cropping {c} pixels around frame"
            )
            crop_im = im.crop((c, c, w - c, h - c))
            if dpi > cfg.getint("Max.DPI"):
                crop_im = crop_im.resize(
                    (
                        int(round(crop_im.size[0]*cfg.getint("Max.DPI")/dpi)),
                        int(round(crop_im.size[1]*cfg.getint("Max.DPI")/dpi)),
                    ),
                    Image.Resampling.BICUBIC,
                )
                crop_im = crop_im.filter(ImageFilter.UnsharpMask(1, 20, 8))
            if cfg.getboolean("Vibrance.Bump"):
                crop_im = crop_im.filter(lut)
            crop_im.save(os.path.join(crop_dir, img_file), quality=98)
    return cache_previews(img_cache, crop_dir) if i>0 else img_dict


def to_bytes(file_or_bytes, resize=None):
    """
    Will convert into bytes and optionally resize an image that is a file or a base64 bytes object.
    Turns into PNG format in the process so that can be displayed by tkinter
    :param file_or_bytes: either a string filename or a bytes base64 image object
    :param resize:  optional new size
    :return: (bytes) a byte-string object
    """
    if isinstance(file_or_bytes, str):
        img = Image.open(file_or_bytes)
    else:
        try:
            img = Image.open(io.BytesIO(base64.b64decode(file_or_bytes)))
        except Exception as e:
            dataBytesIO = io.BytesIO(file_or_bytes)
            img = Image.open(dataBytesIO)

    cur_width, cur_height = img.size
    if resize:
        new_width, new_height = resize
        scale = min(new_height / cur_height, new_width / cur_width)
        img = img.resize(
            (int(cur_width * scale), int(cur_height * scale)), Image.Resampling.LANCZOS
        )
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    del img
    return bio.getvalue()


def cache_previews(file, folder, data={}):
    for f in os.listdir(folder):
        if f in data.keys(): continue
        fn = os.path.join(folder, f)
        with Image.open(fn) as im:
            w, h = im.size
            r = 248 / w
        data[f] = (
            str(to_bytes(fn, (round(w * r), round(h * r))))
            if f not in data
            else data[f]
        )
    with open(file, "w") as fp:
        json.dump(data, fp, ensure_ascii=False)
    return data


def img_frames_refresh(max_cols):
    frame_list = []
    for cardname, number in print_dict["cards"].items():
        if not os.path.exists(os.path.join(crop_dir, cardname)):
            print(f"{cardname} not found.")
            continue
        idata = eval(
            img_dict[cardname]
            if cardname in img_dict
            else to_bytes(os.path.join(crop_dir, cardname))
        )
        img_layout = [
            sg.Push(),
            sg.Image(
                data=idata,
                key=f"CRD:{cardname}",
                enable_events=True,
            ),
            sg.Push(),
        ]
        button_layout = [
            sg.Push(),
            sg.Button(
                "-",
                key=f"SUB:{cardname}",
                target=f"NUM:{cardname}",
                size=(5, 1),
                enable_events=True,
            ),
            sg.Input(number, key=f"NUM:{cardname}", size=(5, 1)),
            sg.Button(
                "+",
                key=f"ADD:{cardname}",
                target=f"NUM:{cardname}",
                size=(5, 1),
                enable_events=True,
            ),
            sg.Push(),
        ]
        frame_layout = [[sg.Sizer(v_pixels=5)], img_layout, button_layout]
        title = cardname if len(cardname) < 35 else cardname[:28]+"..."+cardname[cardname.rfind(".")-1:]
        frame_list += [
            sg.Frame(
                title=f" {title} ",
                layout=frame_layout,
                title_location=sg.TITLE_LOCATION_BOTTOM,
                vertical_alignment="center",
            )
        ]
    new_frames = [
        frame_list[i : i + max_cols] for i in range(0, len(frame_list), max_cols)
    ]
    if len(new_frames)==0:
        return sg.Push()
    return sg.Column(
        layout=new_frames, scrollable=True, vertical_scroll_only=True, expand_y=True
    )


def window_setup(cols):
    column_layout = [
        [
            sg.Button(button_text=" Config ", size=(10, 1), key="CONFIG"),
            sg.Text("Paper Size:"),
            *[
                sg.Radio(
                    size,
                    "PAPER",
                    default=bool(print_dict["pagesize"] == size),
                    key=f"PAPER:{size}",
                    enable_events=True,
                )
                for size in print_dict["page_sizes"]
            ],
            sg.VerticalSeparator(),
            sg.Text("Orientation:"),
            sg.Radio(
                "Portrait",
                "ORI",
                default=bool(print_dict["orient"] == "Portrait"),
                key="ORIENT:Portrait",
                enable_events=True,
            ),
            sg.Radio(
                "Landscape",
                "ORI",
                default=bool(print_dict["orient"] == "Landscape"),
                key="ORIENT:Landscape",
                enable_events=True,
            ),
            sg.VerticalSeparator(),
            sg.Text("PDF Filename:"),
            sg.Input(
                print_dict["filename"], size=(20, 1), key="FILENAME", enable_events=True
            ),
            sg.Push(),
            sg.Button(button_text=" Run Cropper ", size=(10, 1), key="CROP"),
            sg.Button(button_text=" Save Project ", size=(10, 1), key="SAVE"),
            sg.Button(button_text=" Render PDF ", size=(10, 1), key="RENDER"),
        ],
        [
            sg.Frame(
                title="Card Images", layout=[[img_frames_refresh(cols)]], expand_y=True
            )
        ],
    ]
    layout = [
        [
            sg.Push(),
            sg.Column(layout=column_layout, expand_y=True),
            sg.Push(),
        ],
    ]
    window = sg.Window(
        "PDF Proxy Printer",
        layout,
        resizable=True,
        finalize=True,
        element_justification="center",
        enable_close_attempted_event=True,
        size=print_dict["size"],
    )
    window.bind("<Configure>", "Event")
    return window

crop_list = os.listdir(crop_dir)
img_dict = {}
if os.path.exists(img_cache):
    with open(img_cache, "r") as fp:
        img_dict = json.load(fp)
if len(img_dict.keys()) < len(crop_list):
    img_dict = cache_previews(img_cache, crop_dir, img_dict)
img_dict = cropper(image_dir, img_dict)

if os.path.exists(print_json):
    with open(print_json, "r") as fp:
        print_dict = json.load(fp)
    # Check that we have all our cards accounted for
    if len(print_dict["cards"].items()) < len(os.listdir(crop_dir)):
        for img in os.listdir(crop_dir):
            if img not in print_dict["cards"].keys():
                print_dict["cards"][img] = 1
else:
    # Initialize our values
    print_dict = {
        "cards": {},
        # program window settings
        "size": (1480, 920),
        "columns": 5,
        # pdf generation options
        "pagesize": "Letter",
        "page_sizes": ["Letter", "A4", "Legal"],
        "orient": "Portrait",
        "filename": "_printme",
    }
    for img in os.listdir(crop_dir):
        print_dict["cards"][img] = 1

window = window_setup(print_dict["columns"])
old_size = window.size
for k in window.key_dict.keys():
    if "CRD:" in str(k):
        window[k].bind("<Button-1>", "-LEFT")
        window[k].bind("<Button-3>", "-RIGHT")
loading_window.close()
while True:
    event, values = window.read()

    if event == sg.WIN_CLOSED or event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT:
        break

    if "ADD:" in event or "SUB:" in event or "CRD:" in event:
        name = event[4:]
        if "-RIGHT" in name:
            name = name.replace("-RIGHT", "")
            e = "SUB:"
        elif "-LEFT" in name:
            name = name.replace("-LEFT", "")
            e = "ADD:"
        else:
            e = event[:4]
        key = "NUM:" + name
        num = int(values[key])
        num += 1 if "ADD" in e else 0 if num <= 0 else -1
        print_dict["cards"][name] = num
        window[key].update(str(num))

    if "ORIENT:" in event:
        print_dict["orient"] = event.replace("ORIENT:", "")

    if "PAPER:" in event:
        print_dict["pagesize"] = event.replace("PAPER:", "")

    if "FILENAME" in event:
        print_dict["filename"] = window["FILENAME"].get()

    if "CONFIG" in event:
        subprocess.Popen(["config.ini"], shell=True)

    if "SAVE" in event:
        with open(print_json, "w") as fp:
            json.dump(print_dict, fp)

    if event in ["CROP", "RENDER"]:
        config.read(os.path.join(cwd, "config.ini"))
        cfg = config["DEFAULT"]

    if "CROP" in event:
        oldwindow = window
        oldwindow.disable()
        grey_window = grey_out(window)

        img_dict = cropper(image_dir, img_dict)
        for img in os.listdir(crop_dir):
            if img not in print_dict["cards"].keys():
                print(f"{img} found and added to list.")
                print_dict["cards"][img] = 1
                
        window = window_setup(print_dict["columns"])
        window.enable()
        window.bring_to_front()
        oldwindow.close()
        grey_window.close()
        window.refresh()
        for k in window.key_dict.keys():
            if "CRD:" in str(k):
                window[k].bind("<Button-1>", "-LEFT")
                window[k].bind("<Button-3>", "-RIGHT")

    if "RENDER" in event:
        window.disable()
        grey_window = grey_out(window)
        render_window = popup("Rendering...")
        render_window.refresh()
        lookup = {"Letter": letter, "A4": A4, "Legal": legal}
        pdf_gen(print_dict, lookup[print_dict["pagesize"]])
        render_window.close()
        grey_window.close()
        window.enable()
        window.bring_to_front()
        window.refresh()

    if event and print_dict["size"] != window.size:
        print_dict["size"] = window.size

with open(print_json, "w") as fp:
    json.dump(print_dict, fp)
window.close()