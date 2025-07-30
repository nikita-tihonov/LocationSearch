import requests
import time
import pandas as pd


def get_all_info(city: str) -> dict:
    """Получает информацию обо всех зданиях и организациях в указанном городе"""
    overpass_url = "https://overpass-api.de/api/interpreter"

    query = f"""
    [out:json][timeout:1800];
    area["name"="{city}"]->.searchArea;
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

    response = requests.get(overpass_url, data={'data': query})
    data = response.json()

    return data


def join_building_with_organization(data: dict) -> pd.DataFrame:
    """Соединяет здание с организациями в нем и возвращает DataFrame представление"""
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
            results.append(building_data)
            organizations = []

        elif element['type'] == 'node':
            organizations.append(element)

    report = pd.DataFrame([{
            'Здание ID': r['building_id'],
            'Тип здания': r['building_type'],
            'Информация о здании': r['tags'],
            'Кол-во организаций': r['organizations_count'],
            'Организации': "\n".join(f"{o}" for o in r['organizations'])
        } for r in results])

    return report


if __name__ == "__main__":
    city = "Жуковский"

    start_time = time.time()
    print(f"Собираем данные для {city}...")
    data = get_all_info(city)
    end_time = time.time()
    print(f"Найдено элементов: {len(data['elements'])} за {round(end_time - start_time, 2)} сек")

    print("Соединяем данные...")
    report = join_building_with_organization(data)
    output_file = f"report_onestep.csv"
    report.to_csv(output_file, index=False)
    print(f"Отчет сохранен в {output_file}")