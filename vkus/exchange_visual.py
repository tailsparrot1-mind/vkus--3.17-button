from __future__ import annotations

import math
import tkinter.font as tkfont
from pathlib import Path


def install_exchange_visuals():
    """Install the native Exchange renderer without changing search/data logic."""
    from .app import VkusApp
    VkusApp._exchange_redraw = _exchange_redraw


def _exchange_redraw(self, _event=None):
    """Draw the Vkus Exchange screen with native Tk Canvas primitives."""
    canvas = getattr(self, "exchange_canvas", None)
    if canvas is None:
        return

    w = max(1, canvas.winfo_width())
    h = max(1, canvas.winfo_height())
    # The reference's left rail and desktop chrome are already supplied by
    # Vkus' main window. Render only the Birzha workspace inside the tab.
    crop_x, crop_y, crop_w, crop_h = 8, 8, 1656, 925
    scale = min(w / crop_w, h / crop_h)
    rw, rh = int(crop_w * scale), int(crop_h * scale)
    ox, oy = (w - rw) // 2, (h - rh) // 2
    self.exchange_geometry = (scale, ox, oy, rw, rh)
    self.exchange_origin = (crop_x, crop_y)
    canvas.delete("all")
    canvas.configure(bg="#030817")

    def X(value):
        return ox + (value - crop_x) * scale

    def Y(value):
        return oy + (value - crop_y) * scale

    def rounded(x1, y1, x2, y2, fill, outline="#203568", radius=14, width=1):
        radius = max(2, min(radius, (x2 - x1) / 4, (y2 - y1) / 4)) * scale
        points = []
        corners = (
            (X(x2) - radius, Y(y1) + radius, -90),
            (X(x2) - radius, Y(y2) - radius, 0),
            (X(x1) + radius, Y(y2) - radius, 90),
            (X(x1) + radius, Y(y1) + radius, 180),
        )
        for cx, cy, start in corners:
            for step in range(7):
                angle = math.radians(start + step * 15)
                points.extend((cx + radius * math.cos(angle),
                               cy + radius * math.sin(angle)))
        canvas.create_polygon(
            *points, fill=fill, outline=outline,
            width=max(1, int(width * scale)), smooth=True
        )

    font_cache = {}

    def label(x, y, value, size=14, color="#edf3ff", weight="normal",
              anchor="nw", width=None, justify="left", fit=False):
        font_size = max(7, int(size * scale))
        font_spec = ("DejaVu Sans", font_size, weight)
        if fit and width is not None and "\n" not in str(value):
            available = max(1, int(width * scale))
            while font_size > 7:
                key = (font_size, weight)
                if key not in font_cache:
                    font_cache[key] = tkfont.Font(
                        root=canvas, family="DejaVu Sans",
                        size=font_size, weight=weight
                    )
                if font_cache[key].measure(str(value)) <= available:
                    break
                font_size -= 1
            key = (font_size, weight)
            if key not in font_cache:
                font_cache[key] = tkfont.Font(
                    root=canvas, family="DejaVu Sans",
                    size=font_size, weight=weight
                )
            font_spec = font_cache[key]
        options = {
            "text": value, "anchor": anchor, "fill": color,
            "font": font_spec, "justify": justify,
        }
        if width is not None:
            options["width"] = max(1, int(width * scale))
        canvas.create_text(X(x), Y(y), **options)

    def gradient_button(x1, y1, x2, y2, start, end, outline, radius=12):
        """Draw a clipped horizontal neon gradient with a crisp rounded border."""
        from PIL import ImageColor
        c1, c2 = ImageColor.getrgb(start), ImageColor.getrgb(end)
        steps = max(24, int((x2 - x1) * scale))
        r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
        for i in range(steps):
            t = i / max(1, steps - 1)
            color = "#%02x%02x%02x" % tuple(
                round(c1[j] + (c2[j] - c1[j]) * t) for j in range(3)
            )
            px = x1 + (x2 - x1) * (i + 0.5) / steps
            inset = 0.0
            if px < x1 + r:
                dx = (x1 + r) - px
                inset = r - math.sqrt(max(0.0, r*r - dx*dx))
            elif px > x2 - r:
                dx = px - (x2 - r)
                inset = r - math.sqrt(max(0.0, r*r - dx*dx))
            canvas.create_line(X(px), Y(y1 + inset), X(px), Y(y2 - inset),
                               fill=color, width=max(1.2, (x2-x1)/steps*scale + 0.7))
        rounded(x1, y1, x2, y2, "", outline, radius, 1.3)

    def rule(x1, y1, x2, y2, color="#1b2d58", width=1):
        canvas.create_line(X(x1), Y(y1), X(x2), Y(y2),
                           fill=color, width=max(1, int(width * scale)))

    def dot(x, y, radius, color, outline=""):
        canvas.create_oval(
            X(x - radius), Y(y - radius), X(x + radius), Y(y + radius),
            fill=color, outline=outline or color, width=max(1, int(scale))
        )

    def badge(x, y, text_value, color, fill="#0d1a38", width=1):
        rounded(x, y, x + 150, y + 27, fill, color, 13, width)
        label(x + 75, y + 6, text_value, 8, color, "bold", "n", width=142, fit=True)

    def image_icon(name, cx, cy, width, height):
        """Draw bundled image assets; no network requests occur at runtime."""
        try:
            from PIL import Image, ImageTk
            if name.startswith("source_"):
                source_name = {"source_vk":"vk", "source_telegram":"telegram", "source_avito":"avito", "source_youdo":"youdo", "source_profi":"profi", "source_forums":"forums"}.get(name, "")
                if not source_name:
                    return
                asset_name = {"vk": "vk_brand_vector", "telegram": "telegram_brand_vector"}.get(source_name, source_name)
                path = Path(__file__).resolve().parent / "assets" / "source_logos" / f"{asset_name}.png"
            else:
                path = Path(__file__).resolve().parent / "assets" / "exchange_icons" / f"{name}.png"
            if not path.exists():
                return
            cache = getattr(self, "_exchange_icon_photos", None)
            if cache is None:
                cache = {}
                self._exchange_icon_photos = cache
            size = (max(1, int(width * scale)), max(1, int(height * scale)))
            key = (str(path), size, path.stat().st_mtime_ns)
            photo = cache.get(key)
            if photo is None:
                source = Image.open(path).convert("RGBA")
                # Normalize transparent canvas padding first. Different source
                # logos have different native margins, so raw thumbnails look
                # optically misaligned even when their image centers match.
                alpha = source.getchannel("A")
                bbox = alpha.getbbox()
                if bbox:
                    source = source.crop(bbox)
                # Fit every brand mark into one consistent visual box while
                # preserving its original proportions and transparent edges.
                source.thumbnail(size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(source)
                cache[key] = photo
            canvas.create_image(X(cx), Y(cy), image=photo, anchor="center")
        except Exception:
            return

    # Real neon artwork layer generated for Vkus; cards remain native and interactive.
    try:
        from PIL import Image, ImageEnhance, ImageTk
        bg_path = Path(__file__).resolve().parent / "assets" / "exchange_neon_background.png"
        bg_size = (rw, rh)
        bg_photo = getattr(self, "_exchange_neon_photo", None)
        if bg_photo is None or getattr(self, "_exchange_neon_size", None) != bg_size:
            bg = Image.open(bg_path).convert("RGB")
            # Fill the viewport without distorting the generated neon artwork.
            ratio = max(rw / bg.width, rh / bg.height)
            bg = bg.resize((int(bg.width * ratio), int(bg.height * ratio)), Image.Resampling.LANCZOS)
            left = (bg.width - rw) // 2
            top = (bg.height - rh) // 2
            bg = bg.crop((left, top, left + rw, top + rh))
            # Keep the central workspace readable while retaining vivid neon at the edges.
            shade = Image.new("RGB", bg.size, (2, 5, 20))
            bg = Image.blend(bg, shade, 0.20)
            bg_photo = ImageTk.PhotoImage(bg)
            self._exchange_neon_photo = bg_photo
            self._exchange_neon_size = bg_size
        canvas.create_image(ox, oy, image=bg_photo, anchor="nw")
    except Exception:
        canvas.configure(bg="#07051c")
    rounded(crop_x, crop_y, crop_x + crop_w, crop_y + crop_h,
            "", "#7c35dc", 18, 1)

    # Left brand/navigation rail is part of the same canvas and same neon wallpaper.
    rounded(12, 14, 267, 927, "", "#49218f", 20, 1)
    label(48, 35, "♛", 42, "#c45cff", "bold")
    label(55, 78, "Vkus", 43, "#8e7bff", "bold")
    try:
        from PIL import Image, ImageTk
        tiger_path = Path(__file__).resolve().parent / "assets" / "exchange_tiger.png"
        tiger_size = (int(205*scale), int(205*scale))
        tiger_cache = getattr(self, "_exchange_tiger_photo", None)
        if tiger_cache is None or getattr(self, "_exchange_tiger_size", None) != tiger_size:
            tiger = Image.open(tiger_path).convert("RGBA").resize(tiger_size, Image.Resampling.LANCZOS)
            tiger_cache = ImageTk.PhotoImage(tiger)
            self._exchange_tiger_photo = tiger_cache
            self._exchange_tiger_size = tiger_size
        canvas.create_image(X(30), Y(151), image=tiger_cache, anchor="nw")
    except Exception:
        pass
    nav_items = (("nav_messages", "Сообщения"), ("nav_search", "Поиск"), ("nav_exchange", "Биржа"), ("nav_monitor", "Мониторинг"), ("nav_settings", "Настройки"))
    for i, (nav_icon, nav_name) in enumerate(nav_items):
        top = 374 + i*61
        if nav_name == "Биржа":
            rounded(13, top, 253, top+57, "#24105b", "#9c35ff", 13, 2)
        image_icon(nav_icon, 51, top+28, 34, 34)
        label(91, top+15, nav_name, 15, "#ffffff" if nav_name == "Биржа" else "#9aadd8", "bold" if nav_name == "Биржа" else "normal", width=150, fit=True)
    rounded(28, 728, 250, 855, "#071b35", "#2d79b6", 16, 1)
    label(46, 746, "Ваш статус", 13, "#b7c8ed")
    dot(54, 775, 7, "#00e5b4")
    label(68, 764, "Активен", 15, "#00e5b4", "bold")
    label(46, 806, "★  Премиум", 15, "#ffc34d", "bold")
    label(84, 832, "до 24.12.2026", 10, "#a6b6dc")
    label(36, 883, "Vkus v2.6", 12, "#8b9cc8")
    # Header and compact custom window controls.
    label(306, 43, "Биржа спроса и предложений", 38, "#cf74ff", "bold",
          width=1000, fit=True)
    label(307, 105,
          "Находите целевую аудиторию и потенциальных покупателей для любой ниши",
          18, "#e4eaff", width=980, fit=True)
    dot(1372, 42, 5, "#20e66c")
    label(1386, 30, "Онлайн", 13, "#49ed82", "bold", width=70, fit=True)
    label(1445, 82, "Спрос есть.", 18, "#bd6cff", "bold", width=190, fit=True)
    label(1445, 109, "Найдём вместе!", 18, "#bd6cff", "bold", width=190, fit=True)
    rule(1464, 143, 1606, 143, "#7432bc", 2)

    def glass_card(x, y, width, height, accent):
        """Create a local translucent gradient tile; no network assets."""
        try:
            from PIL import Image, ImageDraw, ImageFilter, ImageTk
            cache = getattr(self, "_exchange_kpi_glass", None)
            if cache is None:
                cache = {}
                self._exchange_kpi_glass = cache
            size = (max(2, int(width*scale)), max(2, int(height*scale)))
            key = (size, accent)
            photo = cache.get(key)
            if photo is None:
                rgb = tuple(int(accent[i:i+2], 16) for i in (1, 3, 5))
                layer = Image.new("RGBA", size, (7, 15, 39, 226))
                glow = Image.new("RGBA", size, (0, 0, 0, 0))
                gd = ImageDraw.Draw(glow)
                gd.ellipse((-size[0]*0.28, -size[1]*0.55,
                            size[0]*0.78, size[1]*1.2),
                           fill=(*rgb, 82))
                gd.ellipse((size[0]*0.38, size[1]*0.18,
                            size[0]*1.18, size[1]*1.3),
                           fill=(*rgb, 35))
                glow = glow.filter(ImageFilter.GaussianBlur(max(5, int(19*scale))))
                layer = Image.alpha_composite(layer, glow)
                mask = Image.new("L", size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, size[0]-1, size[1]-1),
                    radius=max(8, int(18*scale)), fill=255)
                layer.putalpha(mask)
                photo = ImageTk.PhotoImage(layer)
                cache[key] = photo
            canvas.create_image(X(x), Y(y), image=photo, anchor="nw")
        except Exception:
            rounded(x, y, x+width, y+height, "#09152e", accent, 19, 1)

    # Five platform KPI cards: exact platform order and metric labels from the
    # user's detailed Birzha specification. Values stay empty until connectors
    # are implemented; tiny sample lines are explicitly marked DEMO.
    platforms = (
        ("source_vk", "VK", "—", "Количество сообщений", "#2788ff"),
        ("source_telegram", "Telegram", "—", "Каналов и постов", "#31bdf5"),
        ("source_avito", "Avito", "—", "Объявлений", "#f18b42"),
        ("source_youdo", "YouDo", "—", "Заявок и услуг", "#a9b6d8"),
        ("source_profi", "Профи.ру", "—", "Специалистов", "#ff647e"),
    )
    kpi_positions = ((301, 550), (565, 814), (829, 1078),
                     (1093, 1342), (1357, 1606))
    spark_values = (
        (0.72, 0.48, 0.62, 0.36, 0.55, 0.24, 0.42),
        (0.66, 0.72, 0.45, 0.56, 0.31, 0.47, 0.28),
        (0.78, 0.61, 0.68, 0.39, 0.53, 0.32, 0.44),
        (0.63, 0.42, 0.58, 0.34, 0.49, 0.27, 0.39),
        (0.74, 0.52, 0.64, 0.41, 0.57, 0.30, 0.46),
    )
    for index, (logo, title, value, metric, accent) in enumerate(platforms):
        left, right = kpi_positions[index]
        # Individually tinted glass cards; the content remains native Canvas.
        glass_card(left, 171, right-left, 174, accent)
        rounded(left, 171, right, 345, "", accent, 19, 1)
        rounded(left + 3, 174, right - 3, 342, "", "#263c70", 16, 1)
        image_icon(logo, left + 34, 205, 30, 30)
        label(left + 61, 190, title, 16, "#f1f5ff", "bold",
              width=right-left-74, fit=True)
        label(left + 61, 224, value, 28, "#ffffff", "bold")
        label(left + 20, 278, metric, 10, "#bdc9e6",
              width=right-left-40, fit=True)
        # Mini sparkline is an explicitly marked visual sample, not source data.
        gx1, gx2 = left + 150, right - 17
        gy1, gy2 = 297, 328
        rule(gx1, gy2, gx2, gy2, "#293b65", 1)
        vals = spark_values[index]
        pts = []
        for j, val in enumerate(vals):
            px = gx1 + (gx2-gx1) * j / (len(vals)-1)
            py = gy2 - val * (gy2-gy1)
            pts.extend((X(px), Y(py)))
        canvas.create_line(*pts, fill=accent, width=max(2, int(2.2*scale)),
                           smooth=True, splinesteps=18)

    # Smart search panel with a bright blue perimeter.
    rounded(297, 370, 1348, 559, "", "#185fbd", 22, 3)
    rounded(300, 373, 1345, 556, "#091633", "#3866bd", 20, 1)
    image_icon("search", 340, 406, 34, 34)
    label(373, 394, "Умный поиск", 23, "#f2f5ff", "bold")
    label(1137, 402, "Расширенный поиск  ⌄", 15, "#38aaff",
          width=190, fit=True)
    rounded(320, 435, 1020, 488, "#071129", "#405a91", 12, 1)
    entry = getattr(self, "exchange_entry", None)
    if entry is not None:
        entry.place(x=X(332), y=Y(441),
                    width=max(20, X(1005) - X(332)),
                    height=max(18, Y(482) - Y(441)))
        entry.configure(
            font=("DejaVu Sans", max(9, int(13 * scale))),
            bg="#071129", fg="#a9badc",
            insertbackground="#ffffff", relief="flat",
            highlightthickness=0, bd=0
        )
    gradient_button(1032, 435, 1170, 488, "#8b32f5", "#2477ff", "#b98aff", 12)
    # Larger, clearly legible magnifier: circular lens plus diagonal handle.
    canvas.create_oval(X(1047), Y(450), X(1063), Y(466),
                       outline="#ffffff", width=max(2, int(2.2 * scale)))
    canvas.create_line(X(1060), Y(463), X(1068), Y(471),
                       fill="#ffffff", width=max(2, int(2.8 * scale)),
                       capstyle="round")
    label(1112, 449, "Найти ЦА", 12, "#ffffff", "bold", "n", width=91, fit=True)
    gradient_button(1180, 435, 1325, 488, "#087fda", "#24c9e8", "#70eaff", 12)
    label(1252, 449, "Все источники", 10, "#ffffff", "bold", "n", width=137, fit=True)

    # Filter controls.
    label(320, 502, "ПАРАМЕТРЫ ПОИСКА", 8, "#849ac8", "bold")
    filters = (
        ("filter_city", getattr(self, "exchange_city", "Оренбург"), 320, 478),
        ("filter_radius", "Радиус: " + getattr(self, "exchange_radius", "50 км"), 490, 684),
        ("filter_calendar", getattr(self, "exchange_period", "За всё время"), 696, 889),
        ("filter_categories", getattr(self, "exchange_category", "Все категории"), 901, 1094),
    )
    for symbol, value, left, right in filters:
        rounded(left, 518, right, 548, "#0a1734", "#293e70", 10, 1)
        image_icon(symbol, left + 19, 533, 19, 19)
        label(left + 34, 526, value + "  ⌄", 9, "#dce6fb", width=right-left-44, fit=True)

    # Source selectors with brand-specific wordmarks and a neon Avito selection.
    label(307, 572, "◎  Источники поиска", 17, "#f0f4ff", "bold")
    sources = (
        ("VK", "source_vk", "#2788ff"),
        ("Telegram", "source_telegram", "#31bdf5"),
        ("Avito", "source_avito", "#f18b42"),
        ("YouDo", "source_youdo", "#f4f5ff"),
        ("Профи.ру", "source_profi", "#ff647e"),
        ("Форумы", "source_forums", "#9b8cff"),
    )
    selected = getattr(self, "exchange_sources_selected", set())
    for index, (name, wordmark, accent) in enumerate(sources):
        left = 301 + index * 147
        active = name in selected
        if active:
            rounded(left - 3, 607, left + 135, 694, "#0b1233", "#d344ff", 18, 3)
            rounded(left, 610, left + 132, 691, "#17183b", "#2488ec", 16, 1)
        else:
            rounded(left, 610, left + 132, 691, "#09132e", "#293c78", 16, 1)
        image_icon(wordmark, left + 66, 634, 46, 36)
        label(left + 66, 661, name, 11, "#edf2ff", "bold", "n", width=116, fit=True)

    rounded(1185, 610, 1343, 691, "#09132e", "#8d5bdb", 16, 1)
    label(1264, 630, "+", 30, "#c9a7ff", "bold", "n")
    label(1264, 661, "Ещё 5", 13, "#eef2ff", "bold", "n")
    label(1264, 679, "источников", 8, "#a8b6dc", "normal", "n")

    # Right-hand discovery panel, aligned with the search module.
    rounded(1360, 373, 1618, 702, "#0b1430", "#8e39e7", 18, 1)
    image_icon("category_header", 1402, 394, 20, 22)
    label(1412, 393, "Что можно найти?", 17, "#f2f5ff", "bold",
          width=190, fit=True)
    categories = (
        "Потенциальные покупатели",
        "Люди с актуальной потребностью",
        "Интерес к товарам и услугам",
        "Обсуждения и рекомендации",
        "Целевая аудитория вашей ниши",
    )
    selected_categories = getattr(self, "exchange_categories_selected", set())
    for index, category in enumerate(categories):
        top = 438 + index * 39
        checked = category in selected_categories
        if checked:
            image_icon("category_check", 1397, top + 9, 20, 20)
        else:
            dot(1397, top + 9, 9, "#10213d", "#405078")
        label(1417, top + 1, category, 10, "#dce6ff",
              width=182, fit=True)
    rounded(1372, 631, 1607, 688, "#21104d", "#9c35ff", 12, 1)
    image_icon("vkus_lightning", 1428, 665, 30, 34)
    label(1445, 639, "Vkus анализирует,", 11, "#d98cff", "bold", width=155, fit=True)
    label(1445, 654, "чтобы вы находили", 9, "#e2d9ff", width=155, fit=True)
    label(1445, 668, "именно то, что нужно", 9, "#e2d9ff", width=155, fit=True)

    # Lower information area: findings, city geography, and the required
    # city-analysis chart. The chart's plotted curve is clearly labelled DEMO.
    # No fabricated counts or live activity are presented.
    rounded(300, 716, 720, 891, "#09152f", "#2b416f", 16, 1)
    label(322, 735, "ПОСЛЕДНИЕ НАХОДКИ", 9, "#9db3e3", "bold")
    image_icon("latest_find", 352, 805, 40, 38)
    label(385, 779, "Здесь появятся найденные публикации", 10,
          "#e1eaff", "bold", width=300, fit=True)
    label(385, 803, "после подключения поисковых источников", 9,
          "#8299c6", width=300, fit=True)
    badge(322, 847, "ОЖИДАЕТ ДАННЫХ", "#6f94c8", "#0c1b37")

    rounded(735, 716, 1175, 891, "#09152f", "#2b416f", 16, 1)
    label(757, 735, "АКТИВНОСТЬ ПО ГОРОДАМ", 9, "#9db3e3", "bold")
    label(757, 750, "География поиска · не статистика активности", 7,
          "#748dbb", width=260, fit=True)
    # Russia map with a live selected-city marker.
    try:
        from PIL import Image, ImageTk
        map_path = Path(__file__).resolve().parent / "assets" / "russia_activity_map.png"
        map_size = (int(265 * scale), int(116 * scale))
        map_cache = getattr(self, "_exchange_map_photos", None)
        if map_cache is None:
            map_cache = {}
            self._exchange_map_photos = map_cache
        map_photo = map_cache.get(map_size)
        if map_photo is None:
            map_im = Image.open(map_path).convert("RGBA")
            map_im = map_im.resize(map_size, Image.Resampling.LANCZOS)
            map_photo = ImageTk.PhotoImage(map_im)
            map_cache[map_size] = map_photo
        map_x, map_y, map_w, map_h = 750, 766, 265, 116
        canvas.create_image(X(map_x + map_w/2), Y(map_y + map_h/2),
                            image=map_photo, anchor="center")
        city_points = {
            "Санкт-Петербург": (0.06, .39), "Москва": (.11, .48), "Казань": (.20, .48),
            "Оренбург": (.24, .61), "Орск": (.25, .64), "Екатеринбург": (.29, .47),
            "Челябинск": (.27, .52), "Уфа": (.25, .51), "Самара": (.19, .56),
            "Пермь": (.29, .43), "Тюмень": (.34, .48), "Новосибирск": (.49, .50),
            "Омск": (.42, .53), "Томск": (.51, .47), "Красноярск": (.57, .48),
            "Иркутск": (.66, .56), "Улан-Удэ": (.69, .57), "Якутск": (.78, .34),
            "Хабаровск": (.88, .55), "Владивосток": (.91, .72),
        }
        selected_city = getattr(self, "exchange_city", "Оренбург")
        px, py = city_points.get(selected_city, city_points["Оренбург"])
        mx, my = X(map_x + px*map_w), Y(map_y + py*map_h)
        pulse = (getattr(self, "_exchange_map_pulse", 0) + 1) % 3
        self._exchange_map_pulse = pulse
        radius = (8 + pulse*2) * scale
        canvas.create_oval(mx-radius, my-radius, mx+radius, my+radius,
                           outline="#e34bff", width=max(1, int(2*scale)))
        canvas.create_oval(mx-3*scale, my-3*scale, mx+3*scale, my+3*scale,
                           fill="#ffffff", outline="#6df6ff", width=max(1, int(scale)))
        label(1030, 780, selected_city, 12, "#ffffff", "bold", width=128, fit=True)
        label(1030, 802, "Выбранный город", 8, "#9eb3df", width=128, fit=True)
        label(1030, 828, getattr(self, "exchange_radius", "50 км"), 11,
              "#d6b7ff", "bold", width=120, fit=True)
        label(1030, 847, "радиус поиска", 8, "#8da2ce", width=120, fit=True)
    except Exception:
        label(970, 820, "Карта регионов", 10, "#9eb3df", "bold", "center")

    # Right-bottom analysis-options card follows the supplied Birzha reference.
    # It is an options panel, not a fabricated time-series chart.
    rounded(1190, 716, 1618, 891, "#09152f", "#2b416f", 16, 1)
    image_icon("category_header", 1215, 742, 20, 22)
    label(1234, 731, "Опции анализа", 10, "#f2e9ff", "bold",
          width=260, fit=True)
    analysis_options = (
        "Определение намерения",
        "Подбор ниши",
        "Оценка спроса",
        "Уведомления о новых заявках",
    )
    for index, option in enumerate(analysis_options):
        top = 765 + index * 28
        image_icon("category_check", 1217, top + 7, 18, 18)
        label(1235, top, option, 8, "#dce6ff", width=345, fit=True)
    rounded(1430, 854, 1540, 880, "#28105c", "#7136c3", 10, 1)
    label(1485, 860, "Настроить", 8, "#e9d9ff", "bold", "n", width=100, fit=True)

    # Bottom status strip.
    rule(300, 904, 1618, 904, "#24345f")
    dot(315, 920, 3, "#e9b85a")
    label(326, 913, "Источники: ожидают подключения", 8, "#8fa4ce", width=380, fit=True)
    label(1020, 913, "Данные и статистика появятся после интеграции", 8,
          "#7188b6", "normal", "center", width=540, fit=True)
    label(1599, 913, "VKUS 3.28", 8, "#9b83c9", "bold", "ne")

    self.exchange_hit_scale = scale
