# from PIL import Image
# import os
# image = Image.open("assets/object_tilests/!$Fireplace_kitchen.png")

# width = 48
# height = 48
# path = "assets/objects/stove"
# for h in range(int(image.height/height)):  
#     for w in range(int(image.width/width)):  
#         cropped = image.crop((w*width, h*height, (w+1)*width, (h+1)*height))
#         cropped.save(path+"/"+str(h)+"_"+str(w)+".png")  

# print("Изображения сохранены!")
# print(f"Размер изображения: {image.width}x{image.height}")
# print(f"Размер тайла: {width}x{height}")
# print(f"Количество тайлов: {int(image.width/width)}x{int(image.height/height)} = {int(image.width/width)*int(image.height/height)}")