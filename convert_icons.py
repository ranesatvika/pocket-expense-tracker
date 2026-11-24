from PIL import Image, ImageDraw

def create_icon(size, filename):
    image = Image.new("RGB", (size, size), "#0f172a")
    draw = ImageDraw.Draw(image)

    scale = size / 512

    def box(coords, radius, fill):
        scaled = tuple(int(value * scale) for value in coords)
        draw.rounded_rectangle(
            scaled,
            radius=int(radius * scale),
            fill=fill
        )

    box((100, 145, 412, 375), 32, "#10b981")
    box((130, 110, 380, 185), 25, "#34d399")
    box((280, 215, 425, 315), 25, "#064e3b")

    circle = int(16 * scale)
    center_x = int(345 * scale)
    center_y = int(265 * scale)

    draw.ellipse(
        (center_x - circle, center_y - circle,
         center_x + circle, center_y + circle),
        fill="#ffffff"
    )

    draw.line(
        (int(155 * scale), int(240 * scale),
         int(245 * scale), int(240 * scale)),
        fill="#ffffff",
        width=int(22 * scale)
    )

    draw.line(
        (int(155 * scale), int(290 * scale),
         int(220 * scale), int(290 * scale)),
        fill="#d1fae5",
        width=int(22 * scale)
    )

    image.save(filename)

create_icon(192, "static/icon-192.png")
create_icon(512, "static/icon-512.png")

print("Both PNG icons created successfully!")