import os
import imageio
import tempfile
from PIL import Image, ImageDraw

def draw_led_frame(path, states):
    """
    5 adet LED'i (yuvarlak) yatayda tam ortaya hizalı şekilde çizer. Aktif olanlar kırmızı, pasifler gri.
    Supersampling (4x) ve transparan arka plan ile pürüzsüz kenarlar sağlar.
    path: Kaydedilecek dosya yolu
    states: [True, False, ...] şeklinde 5 elemanlı liste
    """
    scale = 4  # Supersampling katsayısı
    width, height = 900, 250
    led_radius = 55
    led_count = 5
    led_spacing = 170
    total_leds_width = (led_count - 1) * led_spacing
    margin = (width - total_leds_width) // 2
    bg_color = (255, 255, 255, 0)  # Transparan arka plan
    led_on_color = (255, 0, 0, 255)
    led_off_color = (150, 150, 150, 255)
    outline_color = (0, 0, 0, 255)
    outline_width = 6 * scale

    # Yüksek çözünürlükte, transparan arka planlı çizim
    img = Image.new("RGBA", (width*scale, height*scale), bg_color)
    draw = ImageDraw.Draw(img)
    for i in range(led_count):
        cx = (margin + i * led_spacing) * scale
        cy = (height // 2) * scale
        r = led_radius * scale
        color = led_on_color if states[i] else led_off_color
        draw.ellipse(
            [(cx - r, cy - r), (cx + r, cy + r)],
            fill=color,
            outline=outline_color,
            width=outline_width
        )
    # Küçült ve kaydet (anti-aliasing)
    img = img.resize((width, height), Image.LANCZOS)
    img.save(path)

# draw_led_frame fonksiyonunu dışarıdan sağlamalısınız.
# Örnek: def draw_led_frame(path, states): ...

def repeat_frame(path, times):
    """Her frame'i n kez tekrar et"""
    return [path] * times

# Geçici klasör oluştur
with tempfile.TemporaryDirectory() as temp_dir:
    # Sirali Pattern (300ms adım arası görünürlüğü sağlamak için her adımı 8 frame olarak tekrar ediyoruz)
    sirali_frame_paths = []
    states = [False] * 5

    for i in range(5):
        states[i] = True
        path = os.path.join(temp_dir, f"delay_sirali_on_{i}.png")
        draw_led_frame(path, states)
        sirali_frame_paths.extend(repeat_frame(path, 8))  # 8x0.5s = 4s

    for i in range(5):
        states[i] = False
        path = os.path.join(temp_dir, f"delay_sirali_off_{i}.png")
        draw_led_frame(path, states)
        sirali_frame_paths.extend(repeat_frame(path, 8))

    # Çıktı dizini
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'report', 'screenshots')
    os.makedirs(output_dir, exist_ok=True)

    sirali_gif_delayed = os.path.join(output_dir, "sirali_pattern.gif")
    sirali_frames = [Image.open(f) for f in sirali_frame_paths]
    sirali_frames[0].save(
        sirali_gif_delayed,
        save_all=True,
        append_images=sirali_frames[1:],
        duration=50,  # ms cinsinden, 0.1 saniye
        loop=0
    )

    # Blink Pattern (her yak/söndür 300ms görünür olacak şekilde)
    blink_frame_paths = []
    states = [False] * 5

    for i in range(5):
        states[i] = True
        path_on = os.path.join(temp_dir, f"delay_blink_on_{i}.png")
        draw_led_frame(path_on, states)
        blink_frame_paths.extend(repeat_frame(path_on, 8))

        states[i] = False
        path_off = os.path.join(temp_dir, f"delay_blink_off_{i}.png")
        draw_led_frame(path_off, states)
        blink_frame_paths.extend(repeat_frame(path_off, 8))

    blink_gif_delayed = os.path.join(output_dir, "blink_pattern.gif")
    blink_frames = [Image.open(f) for f in blink_frame_paths]
    blink_frames[0].save(
        blink_gif_delayed,
        save_all=True,
        append_images=blink_frames[1:],
        duration=50,
        loop=0
    )

    # Hepsi Pattern (500ms açık, 500ms kapalı görünüm için her durum 5 frame)
    hepsi_frame_paths = []

    states = [True] * 5
    path_on = os.path.join(temp_dir, f"delay_hepsi_on.png")
    draw_led_frame(path_on, states)
    hepsi_frame_paths.extend(repeat_frame(path_on, 5))

    states = [False] * 5
    path_off = os.path.join(temp_dir, f"delay_hepsi_off.png")
    draw_led_frame(path_off, states)
    hepsi_frame_paths.extend(repeat_frame(path_off, 5))

    hepsi_gif_delayed = os.path.join(output_dir, "hepsi_pattern.gif")
    hepsi_frames = [Image.open(f) for f in hepsi_frame_paths]
    hepsi_frames[0].save(
        hepsi_gif_delayed,
        save_all=True,
        append_images=hepsi_frames[1:],
        duration=250,
        loop=0
    )
 