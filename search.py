import time
import requests
import pandas as pd


def get_all_buildings(city: str) -> list:
    """Получает все здания в городе"""
    overpass_url = "https://overpass-api.de/api/interpreter"

    query = f"""
    [out:json];
    area["name"="{city}"]->.searchArea;
    (
      way["building"](area.searchArea);
      relation["building"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """

    try:
        response = requests.get(overpass_url, params={'data': query})
        response.raise_for_status()

        buildings = []
        for element in response.json()['elements']:

            if element['type'] in ['way', 'relation']:
                tags = element.get('tags', {})

                buildings.append({
                    'osm_id': element['id'],
                    'osm_type': element['type'],
                    'name': tags.get('name', ''),
                    'type': tags.get('building', ''),
                    'address': f"{tags.get('addr:street', '?')} {tags.get('addr:housenumber', '?')}",
                    'full_address': f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}, {city}".strip(
                        ', '),
                    'tags': tags
                })

        return buildings

    except Exception as e:
        print(f"Ошибка при получении зданий: {e}")
        return []


def get_all_organizations_in_building(building: dict) -> list:
    """Получает все организации внутри здания"""
    overpass_url = "https://overpass-api.de/api/interpreter"

    if building['osm_type'] == 'way':
        query = f"""
        [out:json];
        way({building['osm_id']});
        map_to_area -> .building_area;
        node(area.building_area)(if: count_tags() > 0);
        out body;
        >;
        out skel qt;
        """
    else:
        query = f"""
        [out:json];
        relation({building['osm_id']});
        map_to_area -> .building_area;
        node(area.building_area)(if: count_tags() > 0);
        out body;
        >;
        out skel qt;
        """

    try:
        response = requests.get(overpass_url, params={'data': query})
        response.raise_for_status()

        organizations = []
        for element in response.json()['elements']:
            if element['type'] == 'node' and 'tags' in element:
                tags = element['tags']

                # Определяем тип организации
                # org_type = next(
                #     (t for t in ['shop', 'amenity', 'office', 'tourism', 'leisure', 'craft']
                #      if t in tags),
                #     'other'
                # )

                organizations.append({
                    'id': element['id'],
                    'lat': element['lat'],
                    'lon': element['lon'],
                    'name': tags.get('name', 'Без названия'),
                    # 'type': org_type,
                    # 'category': tags.get(org_type, ''),
                    'tags': tags
                })

        return organizations

    except Exception as e:
        print(f"Ошибка для здания {building['osm_id']}: {e}")
        return []


def create_full_report(city: str, limit: int = None) -> pd.DataFrame:
    """Создает полный отчет по всем зданиям и организациям"""
    print(f"Получаем здания в {city}...")
    buildings = get_all_buildings(city)
    print(f"Здания в {city} получены")

    if limit:
        buildings = buildings[:limit]

    print(buildings)

    results = []

    for i, building in enumerate(buildings, 1):
        print(f"\nОбработка здания {i}/{len(buildings)}: {building['name']}")

        start_time = time.time()
        orgs = get_all_organizations_in_building(building)
        end_time = time.time()
        print(f"Обработано за {end_time - start_time}")

        building_data = {
            'building_id': building['osm_id'],
            'building_name': building['name'],
            'building_type': building['type'],
            'address': building['full_address'],
            'organizations_count': len(orgs),
            'organizations': orgs
        }

        results.append(building_data)

    df = pd.DataFrame([{
        'Здание ID': r['building_id'],
        'Название здания': r['building_name'],
        'Тип здания': r['building_type'],
        'Адрес': r['address'],
        'Кол-во организаций': r['organizations_count'],
        'Организации': "\n".join(f"{o['name']}" for o in r['organizations'])
    } for r in results])

    return df


if __name__ == "__main__":
    city = "Жуковский"
    limit = 10

    print(f"Старт сбора данных для {city}...")
    report = create_full_report(city, limit)
    print("Поиск завершен")

    output_file = f"{city}_report.csv"
    report.to_csv(output_file, index=False)
    print(f"\nОтчет сохранен в {output_file}")

    print("\nСтатистика:")
    print(f"Всего зданий: {len(report)}")
    print("\nПример данных:")
    print(report.head(3))