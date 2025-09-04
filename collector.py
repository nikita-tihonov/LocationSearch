from openai import OpenAI
import csv
import json
import time


def create_composite_key_index(csv_file):
    """Создает индекс с составными ключами (id, word)"""
    index = {}
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            key = (int(row['Здание ID']), row['Тип здания'])
            index[key] = row
    return index


def final_ai(text):

    client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key="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",
    )
    print(len(text))
    completion = client.chat.completions.create(
      extra_headers={
        "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
        "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
      },
      extra_body={},
      model="deepseek/deepseek-r1:free",
      messages=[
        {
          "role": "user",
          "content": f"{text}\nЗадача: отобрать локации в городе для размещения кофейных аппаратов внутри здания. Прикрепляю таблицу с информацией по каждому зданию и организациям внутри него. Тебе нужно проанализировать все параметры. Ответ обоснуй."
        }
      ]
    )
    data = completion.choices[0].message.content
    print(data)

    with open(f"final.txt", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=None)


index = create_composite_key_index('report_onestep_briefly.csv')

all_data = ""
for i in range(0, 4):
    with open(f"info_{i}_new.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    for elem in data:
        res = index.get((elem['id'], elem['type']))
        if res is not None:
            all_data += str(res)
            all_data += '\n'

print(all_data)

final_ai(all_data)