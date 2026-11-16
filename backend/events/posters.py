"""Generate distinctive, local 16:9 EventEase event poster artwork."""

from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SIZE = (1200, 675)
PALETTES = {
    "film": ((15, 23, 42), (214, 67, 81), (248, 208, 106)),
    "community": ((15, 76, 75), (45, 148, 121), (242, 196, 109)),
    "wellness": ((40, 63, 91), (233, 151, 102), (255, 220, 157)),
    "science": ((17, 38, 87), (62, 130, 193), (107, 224, 211)),
    "business": ((29, 34, 54), (102, 82, 176), (231, 183, 107)),
    "sports": ((24, 57, 48), (81, 157, 104), (231, 211, 130)),
    "design": ((51, 37, 82), (206, 91, 133), (247, 190, 101)),
    "food": ((106, 44, 35), (221, 113, 55), (245, 203, 115)),
    "photo": ((31, 49, 67), (49, 120, 145), (232, 185, 100)),
    "jazz": ((23, 24, 48), (119, 63, 122), (240, 174, 91)),
    "music": ((34, 27, 72), (120, 67, 185), (255, 108, 133)),
    "default": ((31, 57, 79), (64, 135, 143), (239, 185, 106)),
}


def _theme(title, category=""):
    text = f"{title} {category}".casefold()
    for key, words in {
        "film": ("film", "cinema", "screening"),
        "community": ("community", "neighborhood", "forum", "ideas"),
        "wellness": ("mindful", "morning", "wellness", "yoga"),
        "science": ("science", "lecture", "astronomy", "education"),
        "business": ("founder", "network", "business", "startup"),
        "sports": ("running", "run", "fitness", "sports"),
        "design": ("design", "product", "prototype", "workshop"),
        "food": ("food", "culinary", "festival", "cuisine"),
        "photo": ("photography", "camera", "photo", "walk"),
        "jazz": ("jazz", "saxophone"),
        "music": ("music", "concert", "live performance"),
    }.items():
        if any(word in text for word in words):
            return key
    return "default"


def _font(size, bold=False):
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def _background(theme, visual_key):
    base, accent, highlight = PALETTES[theme]
    digest = sha256(visual_key.encode("utf-8")).digest()
    image = Image.new("RGB", SIZE)
    pixels = image.load()
    for y in range(SIZE[1]):
        t = y / (SIZE[1] - 1)
        color = tuple(round(base[i] * (1 - t) + accent[i] * t * 0.55) for i in range(3))
        for x in range(SIZE[0]):
            pixels[x, y] = color
    draw = ImageDraw.Draw(image, "RGBA")
    # A unique, quiet editorial geometry field behind the theme illustration.
    for i in range(9):
        x = 650 + ((digest[i] * 7 + i * 79) % 520)
        y = (digest[(i + 9) % len(digest)] * 2 + i * 41) % 675
        radius = 45 + digest[(i + 17) % len(digest)] % 105
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(*highlight, 32), width=2)
    return image, draw, accent, highlight


def _illustrate(draw, theme, accent, highlight):
    cream = (255, 241, 208, 235)
    if theme == "film":
        draw.rounded_rectangle((760, 115, 1110, 410), radius=20, fill=(10, 12, 24, 210), outline=cream, width=5)
        draw.polygon(((800, 180), (1010, 265), (800, 350)), fill=(*highlight, 230))
        for y in (85, 440):
            draw.rounded_rectangle((715, y, 1150, y + 30), radius=10, fill=(8, 11, 22, 190))
            for x in range(735, 1130, 44):
                draw.rounded_rectangle((x, y + 7, x + 20, y + 22), radius=3, fill=cream)
        for x, y, r in ((970, 115, 54), (1075, 365, 46)):
            draw.ellipse((x-r, y-r, x+r, y+r), outline=(*highlight, 225), width=12)
            draw.ellipse((x-12, y-12, x+12, y+12), fill=cream)
    elif theme == "community":
        for x, y, r, color in ((810, 190, 52, highlight), (975, 150, 60, cream), (1080, 230, 48, (*accent, 255)), (895, 365, 55, (*accent, 255))):
            draw.ellipse((x-r, y-r, x+r, y+r), fill=color)
            draw.rounded_rectangle((x-r-20, y+r, x+r+20, y+r+145), radius=48, fill=color)
        for x, y in ((805, 100), (940, 70), (1045, 135)):
            draw.rounded_rectangle((x, y, x+100, y+46), radius=20, fill=(255,255,255,70), outline=cream, width=2)
            draw.polygon(((x+20,y+44),(x+39,y+62),(x+48,y+44)), fill=cream)
    elif theme == "wellness":
        draw.ellipse((785, 86, 1085, 386), fill=(*highlight, 230))
        draw.rectangle((720, 355, 1150, 500), fill=(28, 55, 76, 210))
        for i in range(4):
            draw.arc((705-i*24, 280+i*36, 1160+i*24, 580+i*36), 190, 350, fill=(*cream[:3], 160), width=5)
        # Calm seated yoga silhouette.
        draw.ellipse((920, 320, 985, 385), fill=(28, 44, 64, 255))
        draw.line((952, 382, 952, 465), fill=(28,44,64,255), width=19)
        draw.line((948, 410, 875, 453), fill=(28,44,64,255), width=14)
        draw.line((955, 410, 1030, 450), fill=(28,44,64,255), width=14)
        draw.line((950, 462, 870, 495), fill=(28,44,64,255), width=18)
        draw.line((950, 462, 1040, 495), fill=(28,44,64,255), width=18)
    elif theme == "science":
        cx, cy = 950, 280
        for angle in (0, 55, -55):
            box = (cx-190, cy-80, cx+190, cy+80)
            draw.ellipse(box, outline=(*highlight, 220), width=7)
            layer = Image.new("RGBA", SIZE)
            layer_draw = ImageDraw.Draw(layer)
            layer_draw.ellipse(box, outline=(*highlight, 0), width=0)
            layer = layer.rotate(angle, center=(cx, cy))
            draw.bitmap((0,0), layer, fill=None)
        draw.ellipse((925,255,975,305), fill=cream)
        draw.ellipse((780,155,810,185), fill=cream)
        draw.ellipse((1090,365,1120,395), fill=cream)
    elif theme == "business":
        for x, w, h in ((760,90,200),(870,115,300),(1008,72,230),(1095,68,355)):
            draw.rounded_rectangle((x, 460-h, x+w, 460), radius=8, fill=(18,24,43,225), outline=cream, width=3)
            for wy in range(480-h, 440, 44):
                for wx in range(x+18,x+w-8,30):
                    draw.rectangle((wx,wy,wx+9,wy+14), fill=(*highlight,210))
        draw.line((730,460,1175,460), fill=cream, width=5)
        for x, y in ((800,105),(1020,90),(1110,130)):
            draw.ellipse((x-22,y-22,x+22,y+22),fill=(*accent,255))
            draw.arc((x-50,y+18,x+50,y+126),180,360,fill=cream,width=13)
    elif theme == "sports":
        # Runner silhouette in motion with an athletic track motif.
        draw.arc((730,190,1160,580),185,350,fill=(*highlight,150),width=16)
        draw.arc((780,250,1105,540),185,350,fill=(*highlight,110),width=8)
        draw.ellipse((938,125,1018,205),fill=cream)
        draw.line((970,205,920,318),fill=cream,width=25)
        draw.line((943,245,840,280),fill=cream,width=18)
        draw.line((947,255,1050,230),fill=cream,width=18)
        draw.line((925,310,820,400),fill=cream,width=23)
        draw.line((925,310,1055,355),fill=cream,width=23)
        draw.line((815,400,780,398),fill=cream,width=14)
        draw.line((1050,355,1115,418),fill=cream,width=14)
        for x,y in ((770,140),(1105,120),(1090,495)):
            draw.ellipse((x-10,y-10,x+10,y+10),fill=(*highlight,240))
    elif theme == "design":
        draw.polygon(((925,92),(1125,205),(925,320),(725,205)),fill=(*highlight,220),outline=cream)
        draw.polygon(((725,205),(925,320),(925,500),(725,385)),fill=(*accent,230),outline=cream)
        draw.polygon(((1125,205),(925,320),(925,500),(1125,385)),fill=(30,28,63,225),outline=cream)
        for x,y,r in ((795,130,22),(1050,145,19),(840,415,24),(1060,430,30)):
            draw.ellipse((x-r,y-r,x+r,y+r),fill=cream)
        draw.line((835,260,1020,365), fill=(255,255,255,180), width=7)
    elif theme == "food":
        draw.ellipse((735,95,1150,510),fill=(250,236,205,240),outline=cream,width=8)
        draw.ellipse((780,140,1105,465),fill=(141,69,38,255),outline=(217,178,124,255),width=10)
        for x,y,r,c in ((860,245,54,(185,63,46,255)),(1010,225,47,(232,171,57,255)),(920,360,66,(72,129,74,255)),(1050,355,37,(207,91,56,255)),(820,365,31,(243,208,128,255))):
            draw.ellipse((x-r,y-r,x+r,y+r),fill=c)
        draw.arc((850,165,1050,440), 15, 165, fill=(255,246,222,180), width=7)
        for x in (765,1100):
            draw.ellipse((x,520,x+16,536),fill=cream)
    elif theme == "photo":
        for x,y,w,h,c in ((740,205,100,270,(36,52,70,255)),(855,140,120,335,(43,71,89,255)),(990,230,86,245,(31,48,66,255)),(1088,100,76,375,(48,63,78,255))):
            draw.rectangle((x,y,x+w,y+h),fill=c,outline=(*highlight,180),width=3)
            for wy in range(y+25,y+h-20,45):
                for wx in range(x+14,x+w-10,26): draw.rectangle((wx,wy,wx+9,wy+16),fill=(*highlight,190))
        draw.rounded_rectangle((820,315,1020,455),radius=24,fill=(15,20,31,235),outline=cream,width=7)
        draw.ellipse((865,335,975,445),fill=(*accent,255),outline=cream,width=9)
        draw.ellipse((895,365,945,415),fill=(27,54,68,255))
        draw.rectangle((850,285,920,320),fill=(15,20,31,235),outline=cream,width=4)
    elif theme in ("jazz", "music"):
        # Stage beams, crowd and a gold saxophone-like curve for jazz.
        for points, color in [(((760,80),(920,300),(805,300)),(*highlight,74)),(((1110,70),(1000,305),(1150,305)),(*accent,100))]:
            draw.polygon(points,fill=color)
        draw.rectangle((735,425,1165,456),fill=(14,15,31,235))
        for x in range(755,1160,48):
            draw.ellipse((x,470,x+31,505),fill=(10,14,28,240))
            draw.polygon(((x-10,505),(x+40,505),(x+55,610),(x-20,610)),fill=(10,14,28,240))
        draw.arc((850,130,1040,410),20,300,fill=cream,width=17)
        draw.ellipse((970,370,1017,417),fill=(*highlight,255),outline=cream,width=4)
        draw.line((940,165,985,130),fill=cream,width=15)
        for x,y in ((795,150),(1080,180),(1035,95)):
            draw.ellipse((x-8,y-8,x+8,y+8),fill=(*highlight,255))
    else:
        # A polished abstract event stage for uncategorized records.
        draw.ellipse((805,110,1120,425),outline=(*highlight,235),width=13)
        draw.ellipse((860,165,1065,370),fill=(*accent,145),outline=cream,width=5)
        draw.polygon(((730,490),(970,160),(1180,490)),fill=(255,255,255,24),outline=cream)


def render_poster(title, category="", destination=None, identity=None):
    """Save a title-specific 1200×675 JPEG and return the output path."""
    theme = _theme(title, category)
    image, draw, accent, highlight = _background(theme, f"{title}\0{identity or ''}")
    _illustrate(draw, theme, accent, highlight)

    # Add a subtle dark title field for clear readable typography.
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, 690, 675), fill=(8, 14, 28, 120))
    draw.rounded_rectangle((74, 74, 254, 112), radius=18, fill=(*highlight, 240))
    draw.text((92, 82), "EVENTEASE", font=_font(18, True), fill=(25, 27, 44, 255))

    words = title.split()
    font_size = 68
    while font_size > 38:
        font = _font(font_size, True)
        lines, line = [], ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] > 560 and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        if len(lines) <= 3 and max(draw.textbbox((0, 0), row, font=font)[2] for row in lines) <= 570:
            break
        font_size -= 3
    y = 220 if len(lines) <= 2 else 185
    for row in lines:
        draw.text((76, y), row, font=font, fill=(255, 251, 241, 255), stroke_width=1, stroke_fill=(9, 15, 29, 255))
        y += font_size + 15
    draw.rounded_rectangle((78, 555, 206, 563), radius=4, fill=(*highlight, 255))

    output = Path(destination) if destination else Path.cwd() / f"{title.lower().replace(' ', '-')}.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="JPEG", quality=91, optimize=True, progressive=True)
    return output
