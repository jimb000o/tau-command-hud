"""The Night Line announcement picture, made from the island's own paintings (the ones the game shows), never from
the drawn plates of the first days:  python night_line_pic.py <art dir with index.json> <out.jpg>

The painted Radio Coco room at night (the game's night light, a little brighter so it reads on a phone), Rico's painted
portrait on the right, an ON AIR card on the left."""
import json, os, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1600, 900
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def font(size, mono=False):
    for p in ([os.path.join(FONTS, "JetBrainsMono.ttf")] if mono else []) + [os.path.join(FONTS, "Sora.ttf"), "/app/fonts/Sora.ttf"]:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            try:
                f.set_variation_by_axes([700])
            except Exception:
                pass
            return f
    return ImageFont.load_default(size)


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def main(art, out):
    sc = json.load(open(os.path.join(art, "index.json"))).get("scenes", {})
    if "radio" not in sc:
        sys.exit("no painted radio room in " + art)
    room = cover(Image.open(os.path.join(art, sc["radio"])).convert("RGB"), W, H)
    night = ImageChops.multiply(room, Image.new("RGB", (W, H), (120, 138, 200)))   # the game's night is (58,76,140); brighter for a phone
    glow = Image.new("RGB", (W, H)); ImageDraw.Draw(glow).ellipse([W * 0.25, H * 0.15, W * 0.75, H * 0.85], fill=(90, 60, 30))
    pic = ImageChops.add(night, glow.filter(ImageFilter.GaussianBlur(160)))
    b = sc.get("bust-rico")
    if b and os.path.exists(os.path.join(art, b)):
        bust = Image.open(os.path.join(art, b)).convert("RGBA")
        s = 640 / bust.height
        bust = bust.resize((round(bust.width * s), 640), Image.LANCZOS)
        tint = ImageChops.multiply(bust.convert("RGB"), Image.new("RGB", bust.size, (205, 205, 235)))
        pic.paste(tint, (W - bust.width - 40, H - bust.height), bust.split()[3])
    card = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(card)
    d.rounded_rectangle([56, 610, 800, 856], radius=18, fill=(8, 12, 24, 225))
    d.ellipse([90, 646, 116, 672], fill=(230, 70, 50, 255))
    d.text((132, 638), "ON AIR", font=font(36), fill=(230, 70, 50, 255))
    d.text((90, 692), "Radio Coco · the Night Line", font=font(42), fill=(242, 242, 242, 255))
    d.text((90, 754), "Islanders call Rico with their lagoon problems", font=font(26), fill=(195, 205, 215, 255))
    d.text((90, 798), "White Rabbit Key", font=font(26), fill=(120, 220, 140, 255))
    pic = Image.alpha_composite(pic.convert("RGBA"), card).convert("RGB")
    pic.save(out, quality=90)
    print("made", out, "from", sc["radio"], "and", b or "no portrait")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
