import os.path
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import  Service
from selenium.webdriver.common.by import By
import pytesseract
import  cv2
import numpy as np
from pyzbar.pyzbar import decode
import json
from selenium import webdriver as wd
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from pyaspeller import YandexSpeller
import sys
category = {
    "Сухие каши и крахмальные продукты":['каша', 'каша быстрого приготовления','мюсли', 'рис'],
    "Молочные продукты":['овсяная каша','рисовый пудинг','йогурт','мягкий сыр','заварной крем'],
    "Кондитерские изделия":['шоколад','лакрица','конфеты','марципан','жевательная фруктовая пастила','пастила'],
    "Напитки":['сок']
}

class recognizer():
    def __init__(self, model_path="Tesseract-OCR/tesseract.exe"):
        if os.path.exists(model_path):
            pytesseract.pytesseract.tesseract_cmd = model_path;

        else:
            print(model_path, " is incorrect model path")

    def recognize_text(self, imgPath):
        if os.path.exists(imgPath):
            img = cv2.imread(imgPath)
            imgTransformed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            kernel = np.ones((1, 1), np.uint8)
            imgTransformed = cv2.erode(imgTransformed, kernel, iterations=1)
            text = pytesseract.image_to_string(imgTransformed, lang='rus')
            return text
        return None

    def recognize_barcode(self, imgPath):

        if os.path.exists(imgPath):
            img = cv2.imread(imgPath)
            decoded_objects = decode(img)
            for obj in decoded_objects:
                return (obj.data.decode('utf-8'))
        return None

    def check_spelling(self, text):
        speller = YandexSpeller()
        return speller.spelled(text)


# will be replaced by API
class parser():
    service = None
    options = None

    def __init__(self, web_driver_path="geckodriver-v0.34.0-win32/geckodriver.exe", browser_path="firefox/firefox.exe"):
        parser.service = Service(executable_path=web_driver_path)
        parser.options = Options()
        parser.options.binary_location = browser_path
        parser.options.add_argument('--headless')

    def parse(self):
        driver = webdriver.Firefox(service=parser.service, options=parser.options)
        try:
            driver.set_page_load_timeout(2)
            driver.get("https://ean-online.ru/")
            elem = driver.find_element(By.ID, "isbn_input")
            elem.click()
            elem.send_keys(recognizer().recognize_barcode(cv2.imread("test_data/scan_test.png")))
            elem.send_keys(Keys.ENTER)
            time.sleep(1)
            res = driver.find_element(By.ID, "result").text
            driver.close()
            return res

        except Exception:
            driver.close()
            return ("parsing barcode:timeout exception, will be fixed in newer version with API")


class classificator():
    def __init__(self):
        pass
    def getdata(self):
        classificator.category = category

    def search_category(name_of_product):
        for i in category:
            for j in category.get(i):
                if j in name_of_product:
                    now_category = i
                    return now_category

    def search_energy(product_composition):
        if product_composition == None:
            return
        index = product_composition.find("ккал")
        return product_composition[index - 4:index]

    def normal_energy(name_of_product, product_composition):

        if product_composition == None or name_of_product==None:
            return
        now_category = classificator.search_category(name_of_product)
        now_kkal = int(classificator.search_energy(product_composition))
        if now_category == "Сухие каши и крахмальные продукты":
            if now_kkal >= 80:
                return (f"Данный товар по критерию 'Энергетическая ценность' соответствует рекомендациям ВОЗ")
            else:
                return ("Энергетическая ценность товара не соответствует рекомендациям ВОЗ")
        elif now_category == "Молочные продукты":
            if now_kkal >= 60:
                return (f"Данный товар по критерию 'Энергетическая ценность' соответствует рекомендациям ВОЗ")
            else:
                return ("Энергетическая ценность товара не соответствует рекомендациям ВОЗ")


def create_json(dbName,name,normal_energy_quantity,normal_energy_score,code):
    json_data = [{
        "name": name,
        "normal_energy_quantity": normal_energy_quantity,
        "normal_energy_score": normal_energy_score,
        "code":code,
    }
    ]
    with open(dbName, 'w') as file:
        file.write(json.dumps(json_data, indent=2, ensure_ascii=False))

def create_base_json(dbName,name,normal_energy_quantity,normal_energy_score,code):
    json_data = [{
        "name": name,
        "normal_energy_quantity": normal_energy_quantity,
        "normal_energy_score": normal_energy_score,
        "code":code,
    }
    ]
    with open(dbName, 'w') as file:
        file.write(json.dumps(json_data, indent=2, ensure_ascii=False))

def add_to_json(dbName,name,normal_energy_quantity,normal_energy_score,code):
    json_data = {
        "name": name,
        "normal_energy_quantity": normal_energy_quantity,
        "normal_energy_score": normal_energy_score,
        "code":code,
    }
    data = json.load(open(dbName))
    data.append(json_data)
    with open("db.json", "w") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

if __name__ == "__main__":

    def save_to_db(text):
        product_composition = None
        normal_energy_quantity = None
        normal_energy_score = None
        sub_massiv_text = text.lower().split('состав')
        name_of_product = sub_massiv_text[0]
        if name_of_product != None:
            name_of_product = name_of_product.replace("\n"," ")
            name_of_product = recognizer().check_spelling(name_of_product)
        if (len(sub_massiv_text) > 1):
            product_composition = sub_massiv_text[1]
        if (product_composition != None):
            normal_energy_score = classificator.normal_energy(name_of_product, product_composition)
            normal_energy_quantity = classificator.search_energy(product_composition)
        else:

            normal_energy_quantity = "-"
            normal_energy_score = "недостаточно информации"
        dbName = "db.json"
        if os.path.exists(dbName):
            add_to_json(dbName, name_of_product,normal_energy_quantity,normal_energy_score,"-")
        else:
            create_json(dbName, name_of_product,normal_energy_quantity,normal_energy_score,"-")

    def enter_data(img_path):

        text = recognizer().recognize_text(img_path)
        if text != None:

            product_composition = None
            print(recognizer().check_spelling(text))
            sub_massiv_text = recognizer().recognize_text(img_path).lower().split('состав')
            name_of_product = sub_massiv_text[0]
            if (len(sub_massiv_text) > 1):
                product_composition = sub_massiv_text[1]
            if (product_composition != None):

                normal_energy_score = classificator.normal_energy(name_of_product, product_composition)
                normal_energy_quantity = classificator.search_energy(product_composition)
                print(classificator.normal_energy(name_of_product, product_composition))
            else:

                normal_energy_quantity = "-"
                normal_energy_score = "недостаточно информации"
                print("недостаточно информации")
            save_to_db(text)
            print(parser().parse())
        else:
            print("text not detected")
    enter_data(sys.argv[1])

