# from PIL import Image
# import os

# # Путь к папке с изображениями
# folder = "assets/objects/stove/connect"

# # ОРИЕНТАЦИЯ: 'vertical' или 'horizontal'
# orientation = "v"  # <--- поменяй на "horizontal" при необходимости
# name_object = "stove_food_3"
# # Получаем список изображений
# images = [

#     Image.open(os.path.join(folder, file))
#     for file in sorted(os.listdir(folder))
#     if file.lower().endswith(('.png', '.jpg', '.jpeg'))
# ]

# if not images:
#     raise Exception("Нет подходящих изображений в папке.")

# if orientation == "v":
#     max_width = max(img.width for img in images)
#     total_height = sum(img.height for img in images)
#     result = Image.new("RGBA", (max_width, total_height))
    
#     y_offset = 0
#     for img in images:
#         result.paste(img, (0, y_offset))
#         y_offset += img.height

# elif orientation == "h":
#     total_width = sum(img.width for img in images)
#     max_height = max(img.height for img in images)
#     result = Image.new("RGBA", (total_width, max_height))

#     x_offset = 0
#     for img in images:
#         result.paste(img, (x_offset, 0))
#         x_offset += img.width

# else:
#     raise ValueError("Ориентация должна быть 'vertical' или 'horizontal'.")

# result.save("assets/objects/stove/"+name_object+".png")
# for file in os.listdir(folder):
#     os.remove(os.path.join(folder, file))
# print(f"Изображения объединены по {orientation} и сохранены как combined_image.png")
