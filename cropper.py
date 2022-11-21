import os
from PIL import Image

folder = os.path.join(os.path.dirname(__file__), "images")
if not os.path.exists(os.path.join(folder, "crop")):
    print("Creating \\crop\\ and moving cropped images into it")
    os.mkdir(os.path.join(folder, "crop"))
for img_file in os.listdir(folder):
    if (
        os.path.splitext(img_file)[1] not in [".gif", ".jpg", ".jpeg", ".png"]
        or os.path.isdir(img_file)
        or os.path.exists(os.path.join(folder, "crop", img_file))
    ):
        continue
    with Image.open(os.path.join(folder, img_file)) as im:
        w, h = im.size
        c = round(0.12 * min(w / 2.72, h / 3.7))
        print(
            f"{img_file} - DPI calculated: {c*(1/0.12)}, cropping {c} pixels around frame"
        )
        crop_im = im.crop((c, c, w - c, h - c))
        crop_im.save(os.path.join(folder, "crop", img_file), quality=98)
