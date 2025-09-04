import requests
import time
import json
import re
import pandas as pd
from tqdm import tqdm
from openai import OpenAI


class ApiSourceOSM:

    def __init__(self, location):
        self.location = location

    @staticmethod
    def join_building_with_organization(data: dict) -> pd.DataFrame:
        """
        Соединяет здание с организациями в нем и возвращает DataFrame представление
        """

        results = []
        organizations = []
        for element in data['elements']:
            if element['type'] in ['way', 'relation']:
                building_data = {
                    'building_id': element['id'],
                    'building_type': element['type'],
                    'tags': element['tags'],
                    'organizations_count': len(organizations),
                    'organizations': organizations
                }

                # Отсеиваем здания, в которых нет организаций
                if building_data['organizations_count'] != 0:
                    results.append(building_data)

                organizations = []

            elif element['type'] == 'node':
                organizations.append(element)

        report = pd.DataFrame([{
            'id': r['building_id'],
            'type': r['building_type'],
            'info': r['tags'],
            'orgs_count': r['organizations_count'],
            'orgs': "\n".join(f"{org}" for org in r['organizations'])
        } for r in results])

        return report

    def download_info_from_osm(self):
        """
        Получает информацию обо всех зданиях и организациях в указанном городе
        """

        overpass_url = "https://overpass-api.de/api/interpreter"

        query = f"""
        [out:json][timeout:36000];
        area["name"="{self.location}"]->.searchArea;
        (
          way["building"](area.searchArea);
          relation["building"](area.searchArea);
        )->.all_buildings;
        foreach.all_buildings -> .b {{
          (
            .b map_to_area -> .area;
            node(area.area)(if: count_tags() > 0);
            .b;
          );
          out;
        }};
        """

        print("Отправляем запрос в OSM...")
        start_time = time.time()
        response = requests.get(overpass_url, data={'data': query})
        end_time = time.time()
        print(f"Ответ получен. Время выполения {round(end_time - start_time, 2)} сек")
        data = response.json()

        report = self.join_building_with_organization(data)

        output_file = f"report_{self.location}.csv"
        report.to_csv(output_file, index=False)
        print(f"Отчет сохранен в {output_file}")


class ModelAI:

    MODEL_AI = "deepseek/deepseek-r1:free"
    API_KEY = "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"

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY,
    )
    context = 100000

    @staticmethod
    def clean_and_save_ai_response(response_text, output_file):
        """
        Очищает ответ модели и сохраняет JSON
        """

        try:
            # Удаляем Markdown обертку ```json и ```
            cleaned = re.sub(r'```json|```', '', response_text)

            # Заменяем экранированные символы
            cleaned = cleaned.replace('\\"', '"')
            cleaned = cleaned.replace('\\n', '\n')
            cleaned = cleaned.replace('\\t', '\t')
            cleaned = cleaned.replace('\\r', '\r')

            # Убираем лишние пробелы в начале и конце
            cleaned = cleaned.strip()

            # print("Очищенный текст для отладки:")
            # print(repr(cleaned))  # Покажем начало для отладки

            data = json.loads(cleaned)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✓ JSON успешно сохранен в {output_file}")
            return data

        except json.JSONDecodeError as e:
            print(f"✗ Ошибка парсинга JSON: {e}")
            print(f"Текст для отладки: {repr(cleaned[:200])}")
            return None
        except Exception as e:
            print(f"✗ Другая ошибка: {e}")
            return None

    def process_info_with_ai(self, database):

        request_text = f"Задача: отобрать локации в городе для удачного размещения "
        f"кофейных аппаратов внутри здания. Прикрепляю таблицу с информацией по каждому "
        f"зданию и организациям внутри него. Для этого проанализируй все параметры каждого здания: "
        f"количество организаций внутри, их профиль и любую другую информацию, "
        f"которая может быть полезна. Самое главное - оцени проходимость внутри здания. "
        f"Ответ пришли в формате: название здания (количество этажей), полный адрес, телефон для связи "
        f"(все, которые найдешь), количество организаций внутри и их перечисление, "
        f"дай оценку проходимости в здании и рекомендации по размещению кофейного аппарата. "
        f"Каждый пункт пиши с новой строки, между каждым зданием делай два переноса строки. "

        with open(database, "r", encoding="utf-8") as file:
            file_content = file.read()

        print(f"Длина файла {len(file_content)} символов.")

        for i in tqdm(range(0, len(file_content), self.context), "Идет обработка контента моделью "):

            start = i
            if i + self.context > len(file_content):
                end = len(file_content)
            else:
                end = i + self.context

            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Site URL for rankings on openrouter.ai.
                    "X-Title": "<YOUR_SITE_NAME>",  # Optional. Site title for rankings on openrouter.ai.
                },
                extra_body={},
                model=self.MODEL_AI,
                messages=[
                    {
                        "role": "user",
                        "content": f"{file_content[start:end]}\n{request_text}"
                    }
                ]
            )
            data = completion.choices[0].message.content

            # self.clean_and_save_ai_response(data, f"info_{i // self.context}.json")
            # print(f"Ответ сохранен в файле info_{i // self.context}.json")

            with open(f"info_0_{i // self.context}.txt", 'w', encoding='utf-8') as f:
                f.write(data)

            print(f"Ответ сохранен в файле info_{i // self.context}.txt")

            time.sleep(5)


if __name__ == "__main__":
    city = "Пенза"

    penza = ApiSourceOSM(city)
    penza.download_info_from_osm()

    model = ModelAI()
    model.process_info_with_ai(f"report_{city}.csv")