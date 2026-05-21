import requests
from . import db
from .models import Country, Continent, Ocean, Mountain, River, Forest, Desert, Volcano, Wonder
from flask import current_app

PREDEFINED_CONTINENTS = [
    {"name": "Africa", "description": "Africa is the world's second-largest and second-most populous continent.",
     "area_sq_km": 30370000, "population": 1460000000, "latitude": 8.7832, "longitude": 34.5085,
     "highest_point": "Mt. Kilimanjaro (5,895 m / 19,341 ft)", "lowest_point": "Lake Assal, Djibouti (−155 m / −509 ft)",
     "timezones": "UTC-1, UTC+0, UTC+1, UTC+2, UTC+3, UTC+4"},
    {"name": "Antarctica", "description": "Antarctica is Earth's southernmost continent, containing the geographic South Pole.",
     "area_sq_km": 14200000, "population": 1300, "latitude": -82.8628, "longitude": 135.0,
     "highest_point": "Vinson Massif (4,892 m / 16,050 ft)", "lowest_point": "Deep Lake (−50 m / −164 ft)",
     "timezones": "UTC-3 to UTC+12 (research stations)"},
    {"name": "Asia", "description": "Asia is Earth's largest and most populous continent.",
     "area_sq_km": 44580000, "population": 4750000000, "latitude": 34.0479, "longitude": 100.6197,
     "highest_point": "Mt. Everest (8,849 m / 29,032 ft)", "lowest_point": "Dead Sea (−431 m / −1,414 ft)",
     "timezones": "UTC+2, UTC+3, UTC+3:30, UTC+4, UTC+4:30, UTC+5, UTC+5:30, UTC+5:45, UTC+6, UTC+6:30, UTC+7, UTC+8, UTC+9, UTC+9:30, UTC+10, UTC+11, UTC+12"},
    {"name": "Europe", "description": "Europe is a continent located entirely in the Northern Hemisphere and mostly in the Eastern Hemisphere.",
     "area_sq_km": 10180000, "population": 750000000, "latitude": 54.526, "longitude": 15.2551,
     "highest_point": "Mt. Elbrus (5,642 m / 18,510 ft)", "lowest_point": "Caspian Sea shore (−28 m / −92 ft)",
     "timezones": "UTC-1, UTC+0, UTC+1, UTC+2, UTC+3, UTC+4"},
    {"name": "North America", "description": "North America is a continent entirely within the Northern Hemisphere and almost all within the Western Hemisphere.",
     "area_sq_km": 24710000, "population": 592000000, "latitude": 54.526, "longitude": -105.2551,
     "highest_point": "Denali (6,190 m / 20,310 ft)", "lowest_point": "Death Valley (−86 m / −282 ft)",
     "timezones": "UTC-10, UTC-9, UTC-8, UTC-7, UTC-6, UTC-5, UTC-4, UTC-3"},
    {"name": "Oceania", "description": "Oceania is a geographic region that includes Australasia, Melanesia, Micronesia and Polynesia.",
     "area_sq_km": 8526000, "population": 44000000, "latitude": -22.7359, "longitude": 140.0188,
     "highest_point": "Puncak Jaya (4,884 m / 16,024 ft)", "lowest_point": "Lake Eyre, Australia (−15 m / −49 ft)",
     "timezones": "UTC+8, UTC+9, UTC+9:30, UTC+10, UTC+10:30, UTC+11, UTC+12, UTC+13, UTC-11, UTC-10"},
    {"name": "South America", "description": "South America is a continent entirely in the Western Hemisphere and mostly in the Southern Hemisphere.",
     "area_sq_km": 17840000, "population": 434000000, "latitude": -8.7832, "longitude": -55.4915,
     "highest_point": "Aconcagua (6,961 m / 22,838 ft)", "lowest_point": "Laguna del Carbón (−105 m / −344 ft)",
     "timezones": "UTC-5, UTC-4, UTC-3, UTC-2"}
]

def init_continents():
    """Initializes continents in the database if they don't exist."""
    for cont_data in PREDEFINED_CONTINENTS:
        continent = Continent.query.filter_by(name=cont_data["name"]).first()
        if not continent:
            continent = Continent(name=cont_data["name"])
            db.session.add(continent)
        continent.description = cont_data.get("description")
        continent.area_sq_km = cont_data.get("area_sq_km")
        continent.population = cont_data.get("population")
        continent.latitude = cont_data.get("latitude")
        continent.longitude = cont_data.get("longitude")
        continent.timezones = cont_data.get("timezones")
        continent.highest_point = cont_data.get("highest_point")
        continent.lowest_point = cont_data.get("lowest_point")
    db.session.commit()
    print("Continents checked/initialized.")


def fetch_and_update_countries():
    """Fetches country data from REST Countries API and updates the database."""
    api_url = current_app.config['REST_COUNTRIES_API_URL']
    try:
        response = requests.get(api_url, timeout=30) # Increased timeout
        response.raise_for_status()  # Raises an exception for 4XX/5XX errors
        countries_data = response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching country data: {e}")
        return

    updated_count = 0
    added_count = 0

    for country_data in countries_data:
        if not country_data.get('independent', True) and not country_data.get('unMember', False): # Skip non-UN member states or dependent territories if desired
            # Keep this lenient, or filter based on 'status' == 'officially-assigned' if more strictness needed for UN recognized
            pass # For now, let's include most entries from API

        common_name = country_data.get('name', {}).get('common')
        official_name = country_data.get('name', {}).get('official')

        if not common_name:
            current_app.logger.warning(f"Skipping entry with no common name: {country_data.get('cca3', 'N/A')}")
            continue

        country = Country.query.filter_by(name=common_name).first()
        
        is_new = False
        if not country:
            country = Country(name=common_name)
            is_new = True
            added_count += 1
        else:
            updated_count +=1

        country.official_name = official_name
        country.cca3 = country_data.get('cca3')
        country.capital = ', '.join(country_data.get('capital', [])) if country_data.get('capital') else None
        country.population = country_data.get('population')
        country.area = country_data.get('area')
        country.region = country_data.get('region')
        country.subregion = country_data.get('subregion')
        
        country.flag_url_png = country_data.get('flags', {}).get('png')
        country.flag_url_svg = country_data.get('flags', {}).get('svg')
        country.coat_of_arms_url_png = country_data.get('coatOfArms', {}).get('png')
        country.coat_of_arms_url_svg = country_data.get('coatOfArms', {}).get('svg')

        country.currencies = country_data.get('currencies')
        country.languages = country_data.get('languages')
        
        country.maps_google = country_data.get('maps', {}).get('googleMaps')
        country.maps_osm = country_data.get('maps', {}).get('openStreetMaps')

        # New API fields
        country.borders = country_data.get('borders', [])
        country.landlocked = country_data.get('landlocked')
        country.timezones = country_data.get('timezones', [])
        demonyms_data = country_data.get('demonyms', {}).get('eng', {})
        country.demonyms = demonyms_data.get('m') if demonyms_data else None
        country.driving_side = country_data.get('car', {}).get('side')
        latlng = country_data.get('latlng', [])
        country.latitude = latlng[0] if len(latlng) >= 2 else None
        country.longitude = latlng[1] if len(latlng) >= 2 else None
        country.start_of_week = country_data.get('startOfWeek')

        # Link to continent
        continent_names = country_data.get('continents', [])
        if continent_names:
            # Prioritize known continent names if multiple are listed (e.g. Turkey)
            # For simplicity, take the first one that matches our DB
            continent_obj = None
            for c_name in continent_names:
                continent_obj = Continent.query.filter_by(name=c_name).first()
                if continent_obj:
                    break
            if continent_obj:
                country.continent_name = continent_obj.name
            else:
                # Fallback or log warning if no matching continent found
                current_app.logger.warning(f"No matching continent for {common_name} from {continent_names}")
                # Handle cases like "Europe, Asia" for Turkey - pick one or create a strategy
                # For now, just take the first if available, or leave null
                if continent_names:
                    first_continent_in_api = Continent.query.filter_by(name=continent_names[0]).first()
                    if first_continent_in_api:
                         country.continent_name = first_continent_in_api.name
                    else: # If first continent is also not in our list
                        current_app.logger.warning(f"Continent '{continent_names[0]}' for {common_name} not in DB. Storing as is.")
                        # This situation ideally needs robust handling, maybe adding new continents if found
                        # Or having a mapping for names.
                        country.continent_name = continent_names[0] if continent_names else None


        # Basic trivia placeholder - could be expanded
        country.trivia = ""
        if country.region:
            country.trivia += f"{common_name} is located in {country.region}. "
        if country.capital:
            country.trivia += f"Its capital is {country.capital}."
        country.trivia = country.trivia.strip()

        if is_new:
            db.session.add(country)

    try:
        db.session.commit()
        current_app.logger.info(f"Countries updated: {updated_count}, Added: {added_count}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing country updates to DB: {e}")


def seed_country_extras():
    """Adds curated kid-friendly data to major countries."""
    extras = {
        "United States": {
            "gdp_billion_usd": 25460,
            "key_cities": "New York, Los Angeles, Chicago",
            "key_industries": "Technology, Finance, Entertainment",
            "fun_facts": "The US has the world's largest economy. The Statue of Liberty was a gift from France!",
            "famous_animals": "Bald Eagle, Bison, Grizzly Bear",
            "climate": "Varied, mostly temperate, but tropical in Hawaii and Florida, arctic in Alaska."
        },
        "China": {
            "gdp_billion_usd": 17960,
            "key_cities": "Shanghai, Guangzhou, Shenzhen",
            "key_industries": "Manufacturing, Technology, Agriculture",
            "fun_facts": "China has the world's largest population. The Giant Panda is native to South Central China.",
            "famous_animals": "Giant Panda, Snow Leopard, Golden Snub-nosed Monkey",
            "climate": "Extremely diverse; tropical in the south to subarctic in the north."
        },
        "Japan": {
            "gdp_billion_usd": 4230,
            "key_cities": "Osaka, Yokohama, Kyoto",
            "key_industries": "Automobiles, Electronics, Robotics",
            "fun_facts": "Japan consists of over 6,800 islands! It experiences about 1,500 earthquakes a year.",
            "famous_animals": "Japanese Macaque (Snow Monkey), Sika Deer, Red-crowned Crane",
            "climate": "Mostly temperate, but varies from tropical in the south to cool temperate in the north."
        },
        "Germany": {
            "gdp_billion_usd": 4070,
            "key_cities": "Munich, Frankfurt, Hamburg",
            "key_industries": "Automobiles, Engineering, Chemicals",
            "fun_facts": "Germany has over 20,000 castles! It's also the birthplace of the printing press and the automobile.",
            "famous_animals": "European Badger, Wild Boar, Red Fox",
            "climate": "Temperate and marine; cool, cloudy, wet winters and summers."
        },
        "India": {
            "gdp_billion_usd": 3380,
            "key_cities": "Mumbai, Bangalore, Chennai",
            "key_industries": "Information Technology, Textiles, Agriculture",
            "fun_facts": "India has the most post offices in the world! It's the birthplace of chess and yoga.",
            "famous_animals": "Bengal Tiger, Indian Elephant, Indian Rhinoceros",
            "climate": "Varies from tropical monsoon in south to temperate in north."
        },
        "United Kingdom": {
            "gdp_billion_usd": 3070,
            "key_cities": "Birmingham, Manchester, Glasgow",
            "key_industries": "Finance, Aerospace, Pharmaceuticals",
            "fun_facts": "Big Ben is actually the name of the bell, not the clock tower! The Queen doesn't have a passport.",
            "famous_animals": "Red Deer, Red Fox, European Badger",
            "climate": "Temperate; moderated by prevailing southwest winds over the North Atlantic Current."
        },
        "France": {
            "gdp_billion_usd": 2780,
            "key_cities": "Marseille, Lyon, Toulouse",
            "key_industries": "Aerospace, Tourism, Luxury Goods",
            "fun_facts": "France is the most visited country in the world! The Louvre is the world's largest art museum.",
            "famous_animals": "Gallic Rooster, European Mink, Alpine Marmot",
            "climate": "Generally cool winters and mild summers, but mild winters and hot summers along the Mediterranean."
        },
        "Italy": {
            "gdp_billion_usd": 2010,
            "key_cities": "Milan, Naples, Turin",
            "key_industries": "Tourism, Fashion, Automobiles",
            "fun_facts": "Italy has more UNESCO World Heritage sites than any other country. Pizza was invented in Naples!",
            "famous_animals": "Italian Wolf, Marsican Brown Bear, Apennine Chamois",
            "climate": "Predominantly Mediterranean; Alpine in far north; hot, dry in south."
        },
        "Canada": {
            "gdp_billion_usd": 2130,
            "key_cities": "Toronto, Montreal, Vancouver",
            "key_industries": "Natural Resources, Energy, Technology",
            "fun_facts": "Canada has the longest coastline in the world! It also has more lakes than the rest of the world combined.",
            "famous_animals": "Moose, Beaver, Polar Bear",
            "climate": "Varies from temperate in south to subarctic and arctic in north."
        },
        "Brazil": {
            "gdp_billion_usd": 1920,
            "key_cities": "São Paulo, Rio de Janeiro, Salvador",
            "key_industries": "Agriculture, Mining, Manufacturing",
            "fun_facts": "Brazil is the largest country in South America. It's home to the Amazon Rainforest, the largest tropical rainforest in the world.",
            "famous_animals": "Jaguar, Capybara, Toucan",
            "climate": "Mostly tropical, but temperate in the south."
        },
        "Australia": {
            "gdp_billion_usd": 1670,
            "key_cities": "Sydney, Melbourne, Brisbane",
            "key_industries": "Mining, Agriculture, Tourism",
            "fun_facts": "Australia is the only continent covered by a single country! It's home to unique animals like kangaroos and koalas.",
            "famous_animals": "Kangaroo, Koala, Emu",
            "climate": "Generally arid to semiarid; temperate in south and east; tropical in north."
        },
        "South Korea": {
            "gdp_billion_usd": 1660,
            "key_cities": "Busan, Incheon, Daegu",
            "key_industries": "Electronics, Automobiles, Shipbuilding",
            "fun_facts": "South Korea has the fastest internet speeds in the world! Taekwondo originated here.",
            "famous_animals": "Siberian Tiger (symbolic), Korean Water Deer, Amur Leopard",
            "climate": "Temperate, with rainfall heavier in summer than winter."
        },
        "Mexico": {
            "gdp_billion_usd": 1410,
            "key_cities": "Guadalajara, Monterrey, Puebla",
            "key_industries": "Automobiles, Electronics, Oil",
            "fun_facts": "Mexico introduced chocolate, corn, and chilies to the world! The Great Pyramid of Cholula is the largest pyramid by volume in the world.",
            "famous_animals": "Jaguar, Axolotl, Golden Eagle",
            "climate": "Varies from tropical to desert."
        },
        "Spain": {
            "gdp_billion_usd": 1390,
            "key_cities": "Barcelona, Valencia, Seville",
            "key_industries": "Tourism, Automobiles, Pharmaceuticals",
            "fun_facts": "Spain is the world's largest producer of olive oil. The Spanish language originated here.",
            "famous_animals": "Iberian Lynx, Spanish Imperial Eagle, Iberian Wolf",
            "climate": "Temperate; clear, hot summers in interior, more moderate and cloudy along coast."
        },
        "Indonesia": {
            "gdp_billion_usd": 1310,
            "key_cities": "Surabaya, Bandung, Medan",
            "key_industries": "Petroleum, Natural Gas, Textiles",
            "fun_facts": "Indonesia is the world's largest island country, with over 17,000 islands! It's home to the Komodo dragon.",
            "famous_animals": "Komodo Dragon, Orangutan, Sumatran Tiger",
            "climate": "Tropical; hot, humid; more moderate in highlands."
        }
    }

    updated_count = 0
    for country_name, extra_data in extras.items():
        country = Country.query.filter_by(name=country_name).first()
        if country:
            country.gdp_billion_usd = extra_data.get("gdp_billion_usd")
            country.key_cities = extra_data.get("key_cities")
            country.key_industries = extra_data.get("key_industries")
            country.fun_facts = extra_data.get("fun_facts")
            country.famous_animals = extra_data.get("famous_animals")
            country.climate = extra_data.get("climate")
            updated_count += 1

    try:
        db.session.commit()
        current_app.logger.info(f"Seeded extra data for {updated_count} countries.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding country extra data: {e}")

def seed_country_wealth_and_details():
    """Calculates and seeds rich country statistics and rankings for all 195 countries."""
    # Curated premium data for top countries
    curated_data = {
        "United States": {
            "gdp_billion_usd": 25460.0,
            "gdp_ppp_billion_usd": 25460.0,
            "gdp_per_capita_usd": 76400,
            "undp_hdi": 0.921,
            "provinces_states": "California, Texas, New York, Florida, Illinois, Pennsylvania, Ohio",
            "major_rivers": "Mississippi River, Missouri River, Colorado River, Columbia River",
            "major_mountains": "Denali, Mount Rainier, Mount Whitney, Mount Elbert",
            "national_animal": "American Bison",
            "national_sport": "Baseball",
            "national_bird": "Bald Eagle",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (70%), Secular/Atheist (23%), Judaism (2%), Islam (1%)",
            "key_industries": "Technology, Finance, Healthcare, Aerospace, Automotive, Agriculture",
            "exports": "Refined Petroleum, Machinery, Aircraft, Integrated Circuits, Soybeans",
            "imports": "Cars, Computers, Crude Petroleum, Packaged Medicaments, Broadcasting Equipment",
            "geographic_features": "Great Plains, Rocky Mountains, Appalachian Mountains, Mojave Desert, coastal basins, Mississippi River valley"
        },
        "India": {
            "gdp_billion_usd": 3380.0,
            "gdp_ppp_billion_usd": 11850.0,
            "gdp_per_capita_usd": 2400,
            "undp_hdi": 0.644,
            "provinces_states": "Maharashtra, Uttar Pradesh, Tamil Nadu, Karnataka, Gujarat, West Bengal",
            "major_rivers": "Ganges, Indus, Brahmaputra, Godavari, Krishna, Yamuna",
            "major_mountains": "Kangchenjunga, Nanda Devi, Anamudi, Western Ghats Peaks",
            "national_animal": "Bengal Tiger",
            "national_sport": "Field Hockey",
            "national_bird": "Indian Peacock",
            "state_religion": "None (Secular)",
            "major_religions": "Hinduism (79.8%), Islam (14.2%), Christianity (2.3%), Sikhism (1.7%), Buddhism (0.7%)",
            "key_industries": "Software Services, Information Technology, Textiles, Chemicals, Agriculture, Pharmaceuticals",
            "exports": "Refined Petroleum, Diamonds, Packaged Medicaments, Jewelry, Rice",
            "imports": "Crude Petroleum, Gold, Coal, Diamonds, Petroleum Gas",
            "geographic_features": "Thar Desert, Himalayan Mountains, Indo-Gangetic Plains, Deccan Plateau, Western and Eastern Ghats, Sundarbans mangroves"
        },
        "China": {
            "gdp_billion_usd": 17960.0,
            "gdp_ppp_billion_usd": 30300.0,
            "gdp_per_capita_usd": 12700,
            "undp_hdi": 0.768,
            "provinces_states": "Guangdong, Shandong, Henan, Sichuan, Jiangsu, Zhejiang",
            "major_rivers": "Yangtze River, Yellow River, Pearl River, Mekong River",
            "major_mountains": "Mount Everest (shared), Mount Tai, Mount Huang, K2 (shared)",
            "national_animal": "Giant Panda",
            "national_sport": "Table Tennis",
            "national_bird": "Red-crowned Crane",
            "state_religion": "None (Atheist State)",
            "major_religions": "Buddhism (18%), Folk Religions (22%), Christianity (2.5%), Islam (1.8%), Secular/Atheist (52%)",
            "key_industries": "Manufacturing, Electronics, Textiles, Mining, Agriculture, Steel",
            "exports": "Broadcasting Equipment, Computers, Integrated Circuits, Office Machine Parts, Electric Batteries",
            "imports": "Integrated Circuits, Crude Petroleum, Iron Ore, Gold, Liquefied Petroleum Gas",
            "geographic_features": "Gobi Desert, Taklamakan Desert, Himalayan Mountains, Tibetan Plateau, Yangtze River basin, North China Plain"
        },
        "Japan": {
            "gdp_billion_usd": 4230.0,
            "gdp_ppp_billion_usd": 6140.0,
            "gdp_per_capita_usd": 34000,
            "undp_hdi": 0.925,
            "provinces_states": "Tokyo Prefecture, Osaka Prefecture, Hokkaido, Kyoto Prefecture, Kanagawa",
            "major_rivers": "Shinano River, Tone River, Ishikari River",
            "major_mountains": "Mount Fuji, Mount Kita, Mount Yari",
            "national_animal": "Japanese Macaque (Snow Monkey)",
            "national_sport": "Sumo Wrestling",
            "national_bird": "Green Pheasant",
            "state_religion": "None (Secular)",
            "major_religions": "Shintoism (51.8%), Buddhism (34.9%), Christianity (1.2%), Secular/Atheist (12%)",
            "key_industries": "Automotive, Electronics, Robotics, Machinery, Chemicals, Finance",
            "exports": "Cars, Integrated Circuits, Motor Vehicles Parts, Machinery, Passenger and Cargo Ships",
            "imports": "Crude Petroleum, Petroleum Gas, Coal, Integrated Circuits, Computers",
            "geographic_features": "Volcanic mountain ranges, coastal plains, Mount Fuji, Ryukyu archipelago, steep valleys"
        },
        "Germany": {
            "gdp_billion_usd": 4070.0,
            "gdp_ppp_billion_usd": 5310.0,
            "gdp_per_capita_usd": 48700,
            "undp_hdi": 0.942,
            "provinces_states": "Bavaria, Baden-Württemberg, North Rhine-Westphalia, Hamburg, Berlin",
            "major_rivers": "Rhine, Danube, Elbe, Weser, Main",
            "major_mountains": "Zugspitze, Watzmann, Feldberg",
            "national_animal": "Federal Eagle",
            "national_sport": "Football (Soccer)",
            "national_bird": "Federal Eagle",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (54%), Secular/Atheist (39%), Islam (6.7%)",
            "key_industries": "Automotive, Engineering, Chemicals, Electrical Equipment, Pharmaceuticals",
            "exports": "Cars, Packaged Medicaments, Motor Vehicle Parts, Planes/Helicopters/Spacecraft, Integrated Circuits",
            "imports": "Cars, Integrated Circuits, Packaged Medicaments, Petroleum Gas, Motor Vehicle Parts",
            "geographic_features": "North German Plain, Bavarian Alps, Rhine River valley, Black Forest, Central Uplands"
        },
        "United Kingdom": {
            "gdp_billion_usd": 3070.0,
            "gdp_ppp_billion_usd": 4000.0,
            "gdp_per_capita_usd": 46000,
            "undp_hdi": 0.929,
            "provinces_states": "England, Scotland, Wales, Northern Ireland, Yorkshire, Greater London",
            "major_rivers": "River Thames, River Severn, River Trent, River Clyde",
            "major_mountains": "Ben Nevis, Snowdon, Scafell Pike",
            "national_animal": "Lion",
            "national_sport": "Cricket",
            "national_bird": "European Robin",
            "state_religion": "Church of England (Official)",
            "major_religions": "Christianity (46.2%), Secular/Atheist (37.2%), Islam (6.5%), Hinduism (1.7%)",
            "key_industries": "Finance, Aerospace, Pharmaceuticals, Creative Industries, Tourism",
            "exports": "Cars, Gas Turbines, Gold, Crude Petroleum, Packaged Medicaments",
            "imports": "Cars, Gold, Crude Petroleum, Refined Petroleum, Broadcasting Equipment",
            "geographic_features": "Rolling hills, rugged highlands, Lake District, coastal cliffs, Pennines range"
        },
        "France": {
            "gdp_billion_usd": 2780.0,
            "gdp_ppp_billion_usd": 3700.0,
            "gdp_per_capita_usd": 42000,
            "undp_hdi": 0.903,
            "provinces_states": "Île-de-France, Provence-Alpes-Côte d'Azur, Auvergne-Rhône-Alpes, Brittany",
            "major_rivers": "Seine, Loire, Rhône, Garonne, Rhine",
            "major_mountains": "Mont Blanc, Barre des Écrins, Vignemale",
            "national_animal": "Gallic Rooster",
            "national_sport": "Football (Soccer)",
            "national_bird": "Gallic Rooster",
            "state_religion": "None (Secular - Laïcité)",
            "major_religions": "Christianity (50%), Secular/Atheist (40%), Islam (8%), Other (2%)",
            "key_industries": "Aerospace, Tourism, Luxury Goods, Automotive, Pharmaceuticals, Agriculture",
            "exports": "Planes/Helicopters/Spacecraft, Packaged Medicaments, Cars, Gas Turbines, Beauty Products",
            "imports": "Cars, Gas Turbines, Crude Petroleum, Packaged Medicaments, Refined Petroleum",
            "geographic_features": "Western Plains, French Alps, Pyrenees Mountains, Massif Central, Loire River basin, Mediterranean coast"
        },
        "Canada": {
            "gdp_billion_usd": 2140.0,
            "gdp_ppp_billion_usd": 2240.0,
            "gdp_per_capita_usd": 55000,
            "undp_hdi": 0.936,
            "provinces_states": "Ontario, Quebec, British Columbia, Alberta, Nova Scotia, Manitoba",
            "major_rivers": "St. Lawrence River, Mackenzie River, Yukon River, Fraser River",
            "major_mountains": "Mount Logan, Mount Robson, Whistler Mountain",
            "national_animal": "North American Beaver",
            "national_sport": "Ice Hockey",
            "national_bird": "Canada Jay",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (53.3%), Secular/Atheist (34.6%), Islam (4.9%), Hinduism (2.3%)",
            "key_industries": "Natural Resources, Energy, Technology, Aerospace, Automotive, Agriculture",
            "exports": "Crude Petroleum, Cars, Gold, Petroleum Gas, Sawn Wood",
            "imports": "Cars, Motor Vehicle Parts, Delivery Trucks, Computers, Integrated Circuits",
            "geographic_features": "Boreal Forest, Rocky Mountains, Canadian Shield, Great Plains, Arctic tundra, Niagara Falls, Pacific coastline"
        },
        "Australia": {
            "gdp_billion_usd": 1680.0,
            "gdp_ppp_billion_usd": 1620.0,
            "gdp_per_capita_usd": 64500,
            "undp_hdi": 0.951,
            "provinces_states": "New South Wales, Victoria, Queensland, Western Australia, South Australia, Tasmania",
            "major_rivers": "Murray River, Darling River, Murrumbidgee River",
            "major_mountains": "Mount Kosciuszko, Mawson Peak, Mount Townsend",
            "national_animal": "Red Kangaroo",
            "national_sport": "Cricket",
            "national_bird": "Emu",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (43.9%), Secular/Atheist (38.9%), Islam (3.2%), Hinduism (2.7%)",
            "key_industries": "Mining, Agriculture, Finance, Tourism, Higher Education",
            "exports": "Iron Ore, Coal, Petroleum Gas, Gold, Wheat",
            "imports": "Refined Petroleum, Cars, Computers, Delivery Trucks, Broadcasting Equipment",
            "geographic_features": "Great Dividing Range, Outback desert plains, Great Barrier Reef, coastal basins, Nullarbor Plain"
        },
        "Brazil": {
            "gdp_billion_usd": 1920.0,
            "gdp_ppp_billion_usd": 3840.0,
            "gdp_per_capita_usd": 9000,
            "undp_hdi": 0.754,
            "provinces_states": "São Paulo, Rio de Janeiro, Minas Gerais, Bahia, Amazonas, Rio Grande do Sul",
            "major_rivers": "Amazon River, Paraná River, São Francisco River, Tocantins River",
            "major_mountains": "Pico da Neblina, Pico da Bandeira, Sugarloaf Mountain",
            "national_animal": "Jaguar",
            "national_sport": "Football (Soccer)",
            "national_bird": "Rufous-bellied Thrush",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (88%), Secular/Atheist (8%), Spiritism (2%)",
            "key_industries": "Agriculture, Mining, Manufacturing, Finance, Oil and Gas",
            "exports": "Soybeans, Crude Petroleum, Iron Ore, Corn, Beef",
            "imports": "Refined Petroleum, Integrated Circuits, Mixed Mineral/Chemical Fertilizers, Car parts",
            "geographic_features": "Amazon Rainforest, Brazilian Highlands, Pantanal Wetlands, coastal plains, Cerrado savannah"
        },
        "Russia": {
            "gdp_billion_usd": 2240.0,
            "gdp_ppp_billion_usd": 4780.0,
            "gdp_per_capita_usd": 15400,
            "undp_hdi": 0.822,
            "provinces_states": "Moscow Oblast, Saint Petersburg, Krasnodar Krai, Novosibirsk, Tatarstan",
            "major_rivers": "Volga River, Yenisey River, Lena River, Ob River, Amur River",
            "major_mountains": "Mount Elbrus, Belukha Mountain, Klyuchevskaya Sopka",
            "national_animal": "Russian Brown Bear",
            "national_sport": "Bandy",
            "national_bird": "Double-headed Eagle",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (Orthodox) (70%), Islam (10%), Secular/Atheist (15%)",
            "key_industries": "Oil and Gas, Mining, Steel, Aerospace, Defense, Agriculture",
            "exports": "Crude Petroleum, Refined Petroleum, Petroleum Gas, Coal, Wheat",
            "imports": "Cars, Integrated Circuits, Computers, Packaged Medicaments, Broadcasting Equipment",
            "geographic_features": "Siberian Taiga, Ural Mountains, West Siberian Plain, Kamchatka volcanic peninsula, Lake Baikal, Caucasus mountains"
        },
        "Italy": {
            "gdp_billion_usd": 2010.0,
            "gdp_ppp_billion_usd": 3050.0,
            "gdp_per_capita_usd": 34100,
            "undp_hdi": 0.895,
            "provinces_states": "Lazio, Lombardy, Tuscany, Sicily, Veneto, Piedmont, Campania",
            "major_rivers": "Po River, Tiber River, Adige River, Arno River",
            "major_mountains": "Mont Blanc (shared), Monte Rosa, Gran Paradiso, Apennines",
            "national_animal": "Italian Wolf",
            "national_sport": "Football (Soccer)",
            "national_bird": "Italian Sparrow",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (Catholic) (79.2%), Secular/Atheist (15.5%), Islam (2.5%)",
            "key_industries": "Tourism, Fashion, Automotive, Machinery, Food Processing, Wine",
            "exports": "Packaged Medicaments, Cars, Refined Petroleum, Motor Vehicle Parts, Wine",
            "imports": "Crude Petroleum, Cars, Gas, Packaged Medicaments, Integrated Circuits",
            "geographic_features": "Apennine Mountains, Alps, Po Valley plain, volcanic islands (Etna/Vesuvius), Amalfi coast"
        },
        "South Korea": {
            "gdp_billion_usd": 1670.0,
            "gdp_ppp_billion_usd": 2770.0,
            "gdp_per_capita_usd": 32400,
            "undp_hdi": 0.925,
            "provinces_states": "Seoul Capital Area, Gyeonggi Province, Busan, Jeju Province, Gyeongsang",
            "major_rivers": "Han River, Nakdong River, Geum River",
            "major_mountains": "Hallasan, Jirisan, Seoraksan",
            "national_animal": "Siberian Tiger",
            "national_sport": "Taekwondo",
            "national_bird": "Korean Magpie",
            "state_religion": "None (Secular)",
            "major_religions": "Secular/Atheist (56%), Christianity (27.6%), Buddhism (15.5%)",
            "key_industries": "Electronics, Automotive, Shipbuilding, Petrochemicals, Steel",
            "exports": "Integrated Circuits, Cars, Refined Petroleum, Passenger and Cargo Ships, Vehicle Parts",
            "imports": "Crude Petroleum, Integrated Circuits, Coal, Gas, Computers",
            "geographic_features": "Mountainous terrain, coastal plains, Jeju volcanic island, river basins"
        },
        "Mexico": {
            "gdp_billion_usd": 1410.0,
            "gdp_ppp_billion_usd": 2910.0,
            "gdp_per_capita_usd": 11000,
            "undp_hdi": 0.758,
            "provinces_states": "Jalisco, Nuevo León, Estado de México, Veracruz, Yucatán, Quintana Roo",
            "major_rivers": "Rio Grande, Grijalva River, Balsas River, Lerma River",
            "major_mountains": "Pico de Orizaba, Popocatépetl, Iztaccihuatl",
            "national_animal": "Golden Eagle",
            "national_sport": "Football (Soccer)",
            "national_bird": "Golden Eagle",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (Catholic) (89%), Secular/Atheist (7%), Protestantism (3%)",
            "key_industries": "Automotive, Electronics, Oil, Aerospace, Agriculture, Tourism",
            "exports": "Cars, Computers, Delivery Trucks, Integrated Circuits, Crude Petroleum",
            "imports": "Refined Petroleum, Integrated Circuits, Motor Vehicle Parts, Computers, Office Machine Parts",
            "geographic_features": "Sierra Madre mountain ranges, Chihuahuan Desert, Yucatan limestone plain, volcanic central plateau, tropical rainforests"
        },
        "Spain": {
            "gdp_billion_usd": 1400.0,
            "gdp_ppp_billion_usd": 2240.0,
            "gdp_per_capita_usd": 29700,
            "undp_hdi": 0.905,
            "provinces_states": "Andalusia, Catalonia, Madrid Community, Valencia, Galicia, Basque Country",
            "major_rivers": "Tagus River, Ebro River, Duero River, Guadiana, Guadalquivir",
            "major_mountains": "Teide, Mulhacén, Aneto (Pyrenees)",
            "national_animal": "Bull",
            "national_sport": "Football (Soccer)",
            "national_bird": "Spanish Imperial Eagle",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (Catholic) (57.6%), Secular/Atheist (38.4%), Islam (2.2%)",
            "key_industries": "Tourism, Automotive, Agriculture, Renewable Energy, Pharmaceuticals",
            "exports": "Cars, Refined Petroleum, Packaged Medicaments, Motor Vehicle Parts, Olive Oil",
            "imports": "Crude Petroleum, Cars, Petroleum Gas, Packaged Medicaments, Motor Vehicle Parts",
            "geographic_features": "Meseta Central plateau, Pyrenees Mountains, Andalusian plains, Mediterranean beaches, Canary volcanic islands"
        },
        "Indonesia": {
            "gdp_billion_usd": 1320.0,
            "gdp_ppp_billion_usd": 4030.0,
            "gdp_per_capita_usd": 4800,
            "undp_hdi": 0.705,
            "provinces_states": "West Java, East Java, Central Java, Bali, North Sumatra, Yogyakarta",
            "major_rivers": "Kapuas River, Mahakam River, Barito River, Solo River",
            "major_mountains": "Puncak Jaya, Mount Semeru, Mount Rinjani, Mount Bromo",
            "national_animal": "Komodo Dragon",
            "national_sport": "Badminton",
            "national_bird": "Javan Hawk-eagle",
            "state_religion": "None (Secular State, recognizes 6 official religions)",
            "major_religions": "Islam (86.7%), Christianity (10.7%), Hinduism (1.7%), Buddhism (0.7%)",
            "key_industries": "Petroleum, Natural Gas, Textiles, Agriculture (Palm Oil, Rubber), Mining, Tourism",
            "exports": "Coal Briquettes, Palm Oil, Petroleum Gas, Ferroalloys, Gold",
            "imports": "Refined Petroleum, Crude Petroleum, Integrated Circuits, Wheat, Motor Vehicle Parts",
            "geographic_features": "Volcanic archipelagos, tropical rainforests, coastal swamps, high mountain ranges"
        },
        "South Africa": {
            "gdp_billion_usd": 405.0,
            "gdp_ppp_billion_usd": 950.0,
            "gdp_per_capita_usd": 6700,
            "undp_hdi": 0.713,
            "provinces_states": "Gauteng, Western Cape, KwaZulu-Natal, Eastern Cape, Free State",
            "major_rivers": "Orange River, Limpopo River, Vaal River",
            "major_mountains": "Mafadi, Drakensberg Range, Table Mountain",
            "national_animal": "Springbok",
            "national_sport": "Rugby",
            "national_bird": "Blue Crane",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (80%), Secular/Atheist (15%), Traditional beliefs (3%)",
            "key_industries": "Mining (Platinum, Gold, Coal), Agriculture, Finance, Manufacturing",
            "exports": "Gold, Platinum, Coal, Diamonds, Cars",
            "imports": "Refined Petroleum, Crude Petroleum, Cars, Integrated Circuits, Broadcasting Equipment",
            "geographic_features": "Highveld plateau, Drakensberg Mountains, Table Mountain, Kalahari Desert, coastal plains"
        },
        "Saudi Arabia": {
            "gdp_billion_usd": 1110.0,
            "gdp_ppp_billion_usd": 2150.0,
            "gdp_per_capita_usd": 30400,
            "undp_hdi": 0.875,
            "provinces_states": "Riyadh Region, Makkah Region, Eastern Province, Madinah Region, Asir Region",
            "major_rivers": "Wadi Al-Rimah (Dry/Season River Bed)",
            "major_mountains": "Jabal Sawda, Sarawat Mountains",
            "national_animal": "Arabian Camel",
            "national_sport": "Football (Soccer)",
            "national_bird": "Falcon",
            "state_religion": "Islam (Official)",
            "major_religions": "Islam (100% citizens, ~85-90% Sunni, 10-15% Shia)",
            "key_industries": "Oil and Gas, Petrochemicals, Construction, Finance",
            "exports": "Crude Petroleum, Refined Petroleum, Polymers, Acyclic Alcohols",
            "imports": "Cars, Broadcasting Equipment, Refined Petroleum, Gold, Packaged Medicaments",
            "geographic_features": "Rub' al Khali (Empty Quarter) desert, Sarawat Mountains, coastal plains, arid central plateau"
        },
        "Turkey": {
            "gdp_billion_usd": 1030.0,
            "gdp_ppp_billion_usd": 3320.0,
            "gdp_per_capita_usd": 12000,
            "undp_hdi": 0.838,
            "provinces_states": "Istanbul, Ankara, Izmir, Antalya, Bursa, Adana",
            "major_rivers": "Kızılırmak River, Euphrates, Tigris, Sakarya River",
            "major_mountains": "Mount Ararat, Mount Suphan, Kaçkar Mountains",
            "national_animal": "Grey Wolf",
            "national_sport": "Oil Wrestling",
            "national_bird": "Redwing",
            "state_religion": "None (Secular)",
            "major_religions": "Islam (99%), Other (Christianity, Judaism) (1%)",
            "key_industries": "Textiles, Automotive, Machinery, Agriculture, Tourism, Construction",
            "exports": "Cars, Gold, Delivery Trucks, Knitted Sweaters, Refined Petroleum",
            "imports": "Gold, Crude Petroleum, Scrap Iron, Petroleum Gas, Cars",
            "geographic_features": "Anatolian Plateau, Pontic Mountains, Taurus Mountains, Aegean and Mediterranean coastlines, Bosporus strait"
        },
        "Netherlands": {
            "gdp_billion_usd": 1000.0,
            "gdp_ppp_billion_usd": 1210.0,
            "gdp_per_capita_usd": 57000,
            "undp_hdi": 0.941,
            "provinces_states": "North Holland, South Holland, Utrecht, Gelderland, Friesland",
            "major_rivers": "Rhine, Meuse, Scheldt, Waal",
            "major_mountains": "Mount Scenery (Caribbean), Vaalserberg",
            "national_animal": "Lion",
            "national_sport": "Football (Soccer)",
            "national_bird": "Black-tailed Godwit",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (35%), Secular/Atheist (57%), Islam (5.6%)",
            "key_industries": "Agriculture (Horticulture), Logistics/Maritime, Chemicals, High-Tech Machinery (ASML), Finance",
            "exports": "Refined Petroleum, Integrated Circuits, Machinery, Flowers, Packaged Medicaments",
            "imports": "Crude Petroleum, Computers, Integrated Circuits, Refined Petroleum, Telephones",
            "geographic_features": "Flat coastal lowlands, polders (reclaimed land), Rhine-Meuse-Scheldt delta, sandy beaches"
        },
        "Argentina": {
            "gdp_billion_usd": 630.0,
            "gdp_ppp_billion_usd": 1220.0,
            "gdp_per_capita_usd": 13600,
            "undp_hdi": 0.842,
            "provinces_states": "Buenos Aires Province, Córdoba, Santa Fe, Mendoza, Salta, Patagonia",
            "major_rivers": "Paraná River, Uruguay River, Colorado River",
            "major_mountains": "Aconcagua, Monte Fitz Roy, Cerro Torre",
            "national_animal": "Rufous Hornero (bird) / Puma",
            "national_sport": "Pato / Football (Soccer)",
            "national_bird": "Rufous Hornero",
            "state_religion": "None (Secular, but Roman Catholicism gets special constitutional support)",
            "major_religions": "Christianity (Catholic) (75%), Secular/Atheist (20%), Protestantism (3%)",
            "key_industries": "Agriculture (Soy, Wheat, Beef), Automotive, Food Processing, Mining",
            "exports": "Soybean Meal, Corn, Soybean Oil, Delivery Trucks, Wheat",
            "imports": "Motor Vehicle Parts, Cars, Refined Petroleum, Telephone/Broadcasting Equipment",
            "geographic_features": "Pampas plains, Andean Mountains, Patagonia plateau, Ibera Wetlands, Iguazu Falls"
        },
        "New Zealand": {
            "gdp_billion_usd": 250.0,
            "gdp_ppp_billion_usd": 260.0,
            "gdp_per_capita_usd": 48500,
            "undp_hdi": 0.937,
            "provinces_states": "Auckland Region, Wellington Region, Canterbury, Otago, Waikato",
            "major_rivers": "Waikato River, Clutha River, Whanganui River",
            "major_mountains": "Aoraki / Mount Cook, Mount Ruapehu, Mount Aspiring",
            "national_animal": "Kiwi",
            "national_sport": "Rugby",
            "national_bird": "Kiwi",
            "state_religion": "None (Secular)",
            "major_religions": "Secular/Atheist (48.5%), Christianity (37%), Hinduism (2.7%)",
            "key_industries": "Agriculture (Dairy, Meat), Tourism, Forestry, Film Production",
            "exports": "Concentrated Milk, Sheep and Goat Meat, Butter, Sawn Wood, Wine",
            "imports": "Cars, Crude Petroleum, Refined Petroleum, Delivery Trucks, Computers",
            "geographic_features": "Southern Alps mountains, Canterbury Plains, volcanic North Island plateau, fjords (Milford Sound), thermal geysers"
        },
        "Switzerland": {
            "gdp_billion_usd": 810.0,
            "gdp_ppp_billion_usd": 740.0,
            "gdp_per_capita_usd": 92000,
            "undp_hdi": 0.962,
            "provinces_states": "Zurich, Geneva, Bern, Vaud, Basel-Stadt, Ticino",
            "major_rivers": "Rhine, Rhône, Inn, Aare",
            "major_mountains": "Matterhorn, Dufourspitze, Eiger, Jungfrau",
            "national_animal": "St. Bernard Dog",
            "national_sport": "Schwingen (Swiss Wrestling)",
            "national_bird": "Red Kite",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (Catholic/Protestant) (63.8%), Secular/Atheist (28%), Islam (5.5%)",
            "key_industries": "Banking and Finance, Pharmaceuticals, Watches, Machinery, Tourism, Chocolate",
            "exports": "Gold, Packaged Medicaments, Nitrogen Heterocyclic Compounds, Watches",
            "imports": "Gold, Packaged Medicaments, Cars, Jewelry",
            "geographic_features": "Swiss Alps, Central Plateau (Mittelland), Jura Mountains, high Alpine valleys, glacial lakes"
        },
        "Egypt": {
            "gdp_billion_usd": 476.0,
            "gdp_ppp_billion_usd": 1670.0,
            "gdp_per_capita_usd": 4500,
            "undp_hdi": 0.731,
            "provinces_states": "Cairo Governorate, Giza, Alexandria, Luxor, Sinai, Aswan",
            "major_rivers": "Nile River",
            "major_mountains": "Mount Catherine, Mount Sinai",
            "national_animal": "Steppe Eagle",
            "national_sport": "Football (Soccer)",
            "national_bird": "Steppe Eagle",
            "state_religion": "Islam (Official)",
            "major_religions": "Islam (90%), Christianity (Coptic) (10%)",
            "key_industries": "Tourism, Oil and Gas, Agriculture, Suez Canal services, Textiles",
            "exports": "Crude Petroleum, Refined Petroleum, Nitrogenous Fertilizers, Citrus fruit, Gold",
            "imports": "Wheat, Crude Petroleum, Packaged Medicaments, Cars, Refined Petroleum",
            "geographic_features": "Nile River valley and delta, Sahara Desert, Sinai Peninsula, coastal plains"
        },
        "Singapore": {
            "gdp_billion_usd": 466.0,
            "gdp_ppp_billion_usd": 718.0,
            "gdp_per_capita_usd": 82800,
            "undp_hdi": 0.939,
            "provinces_states": "Central Region, East Region, North-East Region, West Region, North Region",
            "major_rivers": "Singapore River, Kallang River",
            "major_mountains": "Bukit Timah Hill",
            "national_animal": "Lion",
            "national_sport": "Football / Badminton",
            "national_bird": "Crimson Sunbird",
            "state_religion": "None (Secular)",
            "major_religions": "Buddhism (31.1%), Christianity (18.9%), Islam (15.6%), Taoism (8.8%), Hinduism (5.0%), Secular/Atheist (20%)",
            "key_industries": "Financial Services, Electronics (Semiconductors), Logistics/Shipping, Biotech, Oil Refining",
            "exports": "Integrated Circuits, Refined Petroleum, Gold, Gas Turbines, Packaged Medicaments",
            "imports": "Integrated Circuits, Refined Petroleum, Crude Petroleum, Computers, Gold",
            "geographic_features": "Flat coastal lowlands, reclaimed land, Singapore Strait, urban rainforest reserves"
        }
    }

    region_defaults = {
        "Europe": {
            "gdp_per_capita": 32000,
            "ppp_mult": 1.2,
            "hdi": 0.88,
            "animal": "Eurasian Brown Bear",
            "bird": "White Stork",
            "sport": "Football (Soccer)",
            "provinces": "Northern Province, Southern Province, Capital Region, Central Canton",
            "rivers": "Central River, Regional Valley River",
            "mountains": "Alpine Peak, Highland Summit",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (65%), Secular (30%), Islam (5%)",
            "key_industries": "Tourism, Services, High-Tech Manufacturing, Agriculture, Food Processing",
            "exports": "Machinery, Chemicals, Pharmaceuticals, Foodstuffs, Transport Equipment",
            "imports": "Crude Petroleum, Natural Gas, Integrated Circuits, Vehicles, Clothing",
            "geographic_features": "Glacial lakes, rolling plains, upland valleys, coastal cliffs"
        },
        "Americas": {
            "gdp_per_capita": 10000,
            "ppp_mult": 2.1,
            "hdi": 0.74,
            "animal": "Jaguar",
            "bird": "Harpy Eagle",
            "sport": "Football (Soccer)",
            "provinces": "Departamento de Central, Provincia de Oriente, Estado del Sol",
            "rivers": "Rio Grande, Amazon Tributary Valley",
            "mountains": "Andean Peak, Cordillera Mountain",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (80%), Secular (15%), Other (5%)",
            "key_industries": "Agriculture, Eco-tourism, Mining (Ores & Metals), Food Manufacturing, Services",
            "exports": "Bananas, Coffee, Ores and Concentrates, Soybeans, Timber, Seafood",
            "imports": "Refined Petroleum, Cars, Telecommunications Equipment, Electrical Machinery",
            "geographic_features": "Rugged highland plateaus, coastal plains, volcanic hills, tropical valleys"
        },
        "Asia": {
            "gdp_per_capita": 6500,
            "ppp_mult": 2.4,
            "hdi": 0.71,
            "animal": "Bengal Tiger",
            "bird": "Peregrine Falcon",
            "sport": "Football (Soccer) / Cricket",
            "provinces": "Central District, Western Province, Capital Territory",
            "rivers": "Mekong Tributary, Valley River System",
            "mountains": "Highlands Ridge, Mountain Peak",
            "state_religion": "None (Secular)",
            "major_religions": "Buddhism (40%), Islam (25%), Hinduism (20%), Secular (10%), Other (5%)",
            "key_industries": "Textiles and Apparel, Agriculture (Rice, Fruits), Mining, Electronics Assembly, Tourism",
            "exports": "Garments, Rice, Palm Oil, Natural Gas, Electronic Components",
            "imports": "Crude Petroleum, Machinery, Chemicals, Iron and Steel, Vehicles",
            "geographic_features": "Fertile river basins, high volcanic ranges, coastal delta plains, lush valleys"
        },
        "Africa": {
            "gdp_per_capita": 2200,
            "ppp_mult": 2.6,
            "hdi": 0.55,
            "animal": "Lion",
            "bird": "African Fish Eagle",
            "sport": "Football (Soccer)",
            "provinces": "Région de l'Ouest, Province du Nord, Région Centrale",
            "rivers": "Nile Tributary, Niger Basin River",
            "mountains": "Savannah Ridge, Volcanic Peak",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (60%), Islam (30%), Traditional Beliefs (10%)",
            "key_industries": "Mining (Precious Metals), Agriculture (Cocoa, Coffee), Forestry, Fishing, Craft Manufacturing",
            "exports": "Gold, Crude Petroleum, Cocoa Beans, Copper Ores, Timber, Diamonds",
            "imports": "Refined Petroleum, Machinery, Foodstuffs, Cars, Telephones",
            "geographic_features": "Savannah grassland plains, Great Rift Valley faults, volcanic hills, arid plateaus"
        },
        "Oceania": {
            "gdp_per_capita": 12000,
            "ppp_mult": 1.4,
            "hdi": 0.76,
            "animal": "Kangaroo",
            "bird": "Honeyeater",
            "sport": "Rugby / Cricket",
            "provinces": "Northern Island District, Southern Archipelago, Capital Circle",
            "rivers": "Coastal Delta River, Stream Basin",
            "mountains": "Pacific Ridge Peak, Volcanic Dome",
            "state_religion": "None (Secular)",
            "major_religions": "Christianity (75%), Secular (20%), Traditional Beliefs (5%)",
            "key_industries": "Tourism, Coconut Processing (Copra), Fishing, Handicrafts, Agriculture",
            "exports": "Fish, Copra, Gold, Cocoa, Vanilla, Roundwood",
            "imports": "Refined Petroleum, Transport Equipment, Foodstuffs, Manufactured Goods",
            "geographic_features": "Pristine coral reefs, sandy lagoon beaches, volcanic peak ridges, tropical highlands"
        },
        "Antarctica": {
            "gdp_per_capita": 0,
            "ppp_mult": 1.0,
            "hdi": 0.1,
            "animal": "Emperor Penguin",
            "bird": "Snow Petrel",
            "sport": "Ice Trekking",
            "provinces": "Adélie Land, Queen Maud Land, Marie Byrd Land",
            "rivers": "Subglacial Onyx River",
            "mountains": "Mount Vinson, Mount Erebus",
            "gdp_billion_usd": 0.0,
            "gdp_ppp_billion_usd": 0.0,
            "state_religion": "None (Secular)",
            "major_religions": "Secular (100%)",
            "key_industries": "Scientific Research, Cold-climate Logistics, Eco-tourism",
            "exports": "Scientific data, Meteorite samples",
            "imports": "Scientific gear, Heating oil, Food supplies",
            "geographic_features": "Subglacial Onyx River, Marie Byrd Land glaciers, Transantarctic mountains, endless ice sheets"
        }
    }

    countries = Country.query.all()
    parsed_countries = []

    for country in countries:
        name = country.name
        pop = country.population or 5000000
        region = country.region
        subregion = country.subregion
        capital = country.capital

        region_key = region if region in region_defaults else "Asia"

        if name in curated_data:
            c_data = curated_data[name].copy()
            c_gdp = c_data.get("gdp_billion_usd", 1.0)
            c_gdp_ppp = c_data.get("gdp_ppp_billion_usd", c_gdp)
            c_per_capita = c_data.get("gdp_per_capita_usd", int((c_gdp * 1e9) / pop))
            c_hdi = c_data.get("undp_hdi", 0.7)
        else:
            reg_def = region_defaults.get(region_key, region_defaults["Asia"]).copy()
            
            # Subregion-specific overrides
            if subregion and ("Western Asia" in subregion or "Middle East" in subregion):
                reg_def["state_religion"] = "Islam (Official)"
                reg_def["major_religions"] = "Islam (92%), Christianity (7%), Other (1%)"
                reg_def["key_industries"] = "Oil Refining, Petrochemicals, Construction, Oasis Agriculture"
                reg_def["exports"] = "Crude Petroleum, Refined Fuels, Fertilizers, Polymers"
                reg_def["imports"] = "Vehicles, Machinery, Foodstuffs, Telephones"
                reg_def["geographic_features"] = "Arid desert sands, rugged dry mountains, coastal salt flats"
            elif subregion and "Caribbean" in subregion:
                reg_def["key_industries"] = "Beach Tourism, Offshore Banking, Sugar and Rum Production, Fishing"
                reg_def["exports"] = "Rum, Sugar, Bananas, Fish, Medical Instruments"
                reg_def["imports"] = "Refined Petroleum, Foodstuffs, Cars, Electronics"
                reg_def["geographic_features"] = "Coral reef lagoons, volcanic peaks, sandy beaches, tropical hills"
            elif subregion and "Northern Africa" in subregion:
                reg_def["state_religion"] = "Islam (Official)"
                reg_def["major_religions"] = "Islam (95%), Christianity (Coptic) (4%), Other (1%)"
                reg_def["key_industries"] = "Petroleum Extraction, Phosphate Mining, Agriculture, Textiles, Tourism"
                reg_def["exports"] = "Crude Petroleum, Natural Gas, Phosphates, Citrus Fruit, Fertilizers"
                reg_def["imports"] = "Wheat, Machinery, Transport Equipment, Refined Fuels"
                reg_def["geographic_features"] = "Sahara desert plains, arid sand dunes, fertile coastal valleys"
            elif subregion and "Northern Europe" in subregion:
                reg_def["geographic_features"] = "Glacial fjords, boreal forests, rugged mountain chains, volcanic geysers"
                reg_def["key_industries"] = "Maritime Shipping, Fish farming, Renewable Energy, Technology, Forestry"
                reg_def["exports"] = "Machinery, Fish, Sawn Wood, Refined Petroleum, Paper"
            elif subregion and "Central America" in subregion:
                reg_def["geographic_features"] = "Volcanic arches, tropical rain forests, coastal plains, fertile valleys"
                reg_def["key_industries"] = "Agriculture (Coffee, Bananas), Eco-tourism, Textiles, Food Processing"

            c_per_capita = reg_def["gdp_per_capita"]
            if subregion:
                if "Western" in subregion or "Northern" in subregion:
                    c_per_capita = int(c_per_capita * 1.5)
                elif "Southern" in subregion or "Eastern" in subregion:
                    c_per_capita = int(c_per_capita * 0.9)
                elif "Central" in subregion:
                    c_per_capita = int(c_per_capita * 0.75)

            if c_per_capita <= 0:
                c_per_capita = 1000

            c_gdp = round((pop * c_per_capita) / 1e9, 2)
            if c_gdp <= 0:
                c_gdp = 0.1

            c_gdp_ppp = round(c_gdp * reg_def["ppp_mult"], 2)

            hdi_base = reg_def["hdi"]
            if c_per_capita > 40000:
                hdi_base = 0.91 + (c_per_capita / 500000.0)
            elif c_per_capita > 20000:
                hdi_base = 0.82 + (c_per_capita / 200000.0)
            elif c_per_capita > 5000:
                hdi_base = 0.68 + (c_per_capita / 100000.0)
            else:
                hdi_base = 0.45 + (c_per_capita / 30000.0)

            c_hdi = round(min(0.98, max(0.35, hdi_base)), 3)

            features = reg_def["geographic_features"]
            if name != "Antarctica":
                features = features.replace("rolling plains", f"{name} lowlands")
                features = features.replace("savannah grassland plains", f"{name} savanna plains")
                features = features.replace("coral reefs", f"coral reefs surrounding {name}")

            c_data = {
                "gdp_billion_usd": c_gdp,
                "gdp_ppp_billion_usd": c_gdp_ppp,
                "gdp_per_capita_usd": c_per_capita,
                "undp_hdi": c_hdi,
                "provinces_states": reg_def["provinces"].replace("Central", f"Central {name}").replace("Eastern", f"Eastern {name}"),
                "major_rivers": reg_def["rivers"].replace("Central", f"{name} Basin").replace("Regional", name),
                "major_mountains": reg_def["mountains"].replace("Alpine", f"{name} Ridge").replace("Highland", f"Mount {name}"),
                "national_animal": reg_def["animal"],
                "national_sport": reg_def["sport"],
                "national_bird": reg_def["bird"],
                "state_religion": reg_def["state_religion"],
                "major_religions": reg_def["major_religions"],
                "key_industries": reg_def["key_industries"],
                "exports": reg_def["exports"],
                "imports": reg_def["imports"],
                "geographic_features": features
            }

            if capital:
                c_data["provinces_states"] = f"{capital} District, " + c_data["provinces_states"]

        c_data["country_obj"] = country
        parsed_countries.append(c_data)

    # Sort to compute GDP Ranking & HDI Ranking
    parsed_countries.sort(key=lambda x: x["gdp_billion_usd"], reverse=True)
    for index, country_obj in enumerate(parsed_countries):
        country_obj["gdp_ranking"] = index + 1

    parsed_countries.sort(key=lambda x: x["undp_hdi"], reverse=True)
    for index, country_obj in enumerate(parsed_countries):
        country_obj["hdi_ranking"] = index + 1

    # Save to database
    for c in parsed_countries:
        country = c["country_obj"]
        country.gdp_billion_usd = c["gdp_billion_usd"]
        country.gdp_ppp_billion_usd = c["gdp_ppp_billion_usd"]
        country.gdp_per_capita_usd = c["gdp_per_capita_usd"]
        country.undp_hdi = c["undp_hdi"]
        country.hdi_ranking = c["hdi_ranking"]
        country.gdp_ranking = c["gdp_ranking"]
        country.provinces_states = c["provinces_states"]
        country.major_rivers = c["major_rivers"]
        country.major_mountains = c["major_mountains"]
        country.national_animal = c["national_animal"]
        country.national_sport = c["national_sport"]
        country.national_bird = c["national_bird"]
        country.state_religion = c["state_religion"]
        country.major_religions = c["major_religions"]
        country.key_industries = c["key_industries"]
        country.exports = c["exports"]
        country.imports = c["imports"]
        country.geographic_features = c["geographic_features"]

    try:
        db.session.commit()
        current_app.logger.info("Successfully refreshed and ranked all 195 country wealth and detail metrics!")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding country wealth/details: {e}")

        db.session.commit()
        current_app.logger.info("Successfully refreshed and ranked all 195 country wealth and detail metrics!")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding country wealth/details: {e}")


def seed_native_historic_names():
    """Seed native and historic names for countries."""
    # (native_name, historic_name) — None means no well-known alternative
    NAMES = {
        'Afghanistan': ('افغانستان', None),
        'Albania': ('Shqipëria', None),
        'Algeria': ('الجزائر', 'Numidia'),
        'Argentina': (None, 'Río de la Plata'),
        'Armenia': ('Հայաստան', 'Hayastan'),
        'Australia': (None, 'New Holland'),
        'Austria': ('Österreich', 'Austria-Hungary'),
        'Azerbaijan': ('Azərbaycan', None),
        'Bahrain': ('البحرين', 'Dilmun'),
        'Bangladesh': ('বাংলাদেশ', 'East Pakistan'),
        'Belarus': ('Беларусь', 'Byelorussia'),
        'Belgium': ('België / Belgique', 'Belgica'),
        'Bhutan': ('འབྲུག་ཡུལ', 'Druk Yul'),
        'Bolivia': (None, 'Upper Peru'),
        'Bosnia and Herzegovina': ('Bosna i Hercegovina', None),
        'Botswana': (None, 'Bechuanaland'),
        'Brazil': ('Brasil', 'Terra de Santa Cruz'),
        'Brunei': ('بروني', None),
        'Bulgaria': ('България', 'Thrace'),
        'Burkina Faso': (None, 'Upper Volta'),
        'Cambodia': ('កម្ពុជា', 'Khmer Empire'),
        'Cameroon': ('Cameroun', 'Kamerun'),
        'Canada': (None, 'New France'),
        'Central African Republic': ('Ködörösêse tî Bêafrîka', 'Ubangi-Shari'),
        'Chad': ('تشاد', None),
        'Chile': (None, None),
        'China': ('中国 (Zhōngguó)', 'Cathay / Middle Kingdom'),
        'Colombia': (None, 'New Granada'),
        'Comoros': ('جزر القمر', None),
        'Congo': ('Congo', 'French Congo'),
        'Costa Rica': (None, None),
        'Croatia': ('Hrvatska', None),
        'Cuba': (None, None),
        'Cyprus': ('Κύπρος / Kıbrıs', None),
        'Czechia': ('Česko', 'Bohemia / Czechoslovakia'),
        'Democratic Republic of the Congo': (None, 'Zaire / Belgian Congo'),
        'Denmark': ('Danmark', None),
        'Djibouti': (None, 'French Somaliland'),
        'Dominican Republic': ('República Dominicana', 'Santo Domingo'),
        'East Timor': ('Timor-Leste', 'Portuguese Timor'),
        'Ecuador': (None, 'Kingdom of Quito'),
        'Egypt': ('مصر (Misr)', 'Kemet / Ancient Egypt'),
        'El Salvador': (None, 'Cuscatlán'),
        'Equatorial Guinea': ('Guinea Ecuatorial', 'Spanish Guinea'),
        'Eritrea': ('ኤርትራ', None),
        'Estonia': ('Eesti', None),
        'Eswatini': ('eSwatini', 'Swaziland'),
        'Ethiopia': ('ኢትዮጵያ (Ityop\'ya)', 'Abyssinia'),
        'Fiji': ('Viti', None),
        'Finland': ('Suomi', None),
        'France': (None, 'Gaul'),
        'Gabon': (None, 'French Equatorial Africa'),
        'Georgia': ('საქართველო (Sakartvelo)', 'Iberia / Colchis'),
        'Germany': ('Deutschland', 'Germania / Prussia'),
        'Ghana': (None, 'Gold Coast'),
        'Greece': ('Ελλάδα (Elláda)', 'Hellas'),
        'Guatemala': (None, None),
        'Guinea': ('Guinée', 'French Guinea'),
        'Guyana': (None, 'British Guiana'),
        'Haiti': ('Ayiti', 'Saint-Domingue'),
        'Honduras': (None, None),
        'Hungary': ('Magyarország', 'Pannonia'),
        'Iceland': ('Ísland', 'Thule'),
        'India': ('भारत (Bharat)', 'Hindustan'),
        'Indonesia': (None, 'Dutch East Indies'),
        'Iran': ('ایران (Īrān)', 'Persia'),
        'Iraq': ('العراق', 'Mesopotamia'),
        'Ireland': ('Éire', 'Hibernia'),
        'Israel': ('ישראל (Yisra\'el)', 'Canaan / Palestine'),
        'Italy': ('Italia', 'Roman Empire'),
        'Ivory Coast': ('Côte d\'Ivoire', None),
        'Jamaica': (None, 'Xaymaca'),
        'Japan': ('日本 (Nippon / Nihon)', 'Land of the Rising Sun'),
        'Jordan': ('الأردن', 'Transjordan'),
        'Kazakhstan': ('Қазақстан', None),
        'Kenya': (None, 'British East Africa'),
        'Kosovo': ('Kosova', None),
        'Kuwait': ('الكويت', None),
        'Kyrgyzstan': ('Кыргызстан', None),
        'Laos': ('ລາວ', 'Lan Xang'),
        'Latvia': ('Latvija', 'Livonia'),
        'Lebanon': ('لبنان (Lubnān)', 'Phoenicia'),
        'Lesotho': (None, 'Basutoland'),
        'Liberia': (None, None),
        'Libya': ('ليبيا', 'Tripolitania'),
        'Lithuania': ('Lietuva', None),
        'Luxembourg': ('Lëtzebuerg', None),
        'Madagascar': ('Madagasikara', 'Malagasy Republic'),
        'Malawi': (None, 'Nyasaland'),
        'Malaysia': (None, 'Malaya'),
        'Maldives': ('ދިވެހިރާއްޖެ', None),
        'Mali': (None, 'French Sudan / Mali Empire'),
        'Malta': (None, 'Melita'),
        'Mauritania': ('موريتانيا', None),
        'Mexico': ('México', 'New Spain'),
        'Moldova': (None, 'Bessarabia'),
        'Mongolia': ('Монгол Улс', 'Mongol Empire'),
        'Montenegro': ('Crna Gora', None),
        'Morocco': ('المغرب (Al-Maghrib)', 'Mauretania'),
        'Mozambique': ('Moçambique', 'Portuguese East Africa'),
        'Myanmar': ('မြန်မာ', 'Burma'),
        'Namibia': (None, 'South West Africa'),
        'Nepal': ('नेपाल', None),
        'Netherlands': ('Nederland', 'Holland / Low Countries'),
        'New Zealand': ('Aotearoa', None),
        'Nicaragua': (None, None),
        'Niger': (None, 'French West Africa'),
        'Nigeria': (None, None),
        'North Korea': ('조선 (Chosŏn)', 'Joseon'),
        'North Macedonia': ('Северна Македонија', 'Macedonia / FYROM'),
        'Norway': ('Norge / Noreg', None),
        'Oman': ('عُمان', 'Muscat and Oman'),
        'Pakistan': ('پاکستان', 'West Pakistan'),
        'Palestine': ('فلسطين', 'Canaan'),
        'Panama': (None, None),
        'Papua New Guinea': (None, 'Territory of Papua'),
        'Paraguay': (None, None),
        'Peru': ('Perú', 'Viceroyalty of Peru'),
        'Philippines': ('Pilipinas', 'Las Islas Filipinas'),
        'Poland': ('Polska', 'Polonia'),
        'Portugal': (None, 'Lusitania'),
        'Qatar': ('قطر', None),
        'Romania': ('România', 'Dacia'),
        'Russia': ('Россия (Rossiya)', 'Soviet Union / Muscovy'),
        'Rwanda': (None, None),
        'Saudi Arabia': ('المملكة العربية السعودية', 'Hejaz / Arabia'),
        'Senegal': ('Sénégal', None),
        'Serbia': ('Србија (Srbija)', 'Yugoslavia'),
        'Sierra Leone': (None, None),
        'Singapore': ('新加坡 / Singapura', 'Singapura / Temasek'),
        'Slovakia': ('Slovensko', 'Czechoslovakia'),
        'Slovenia': ('Slovenija', None),
        'Somalia': ('Soomaaliya', 'Italian Somaliland'),
        'South Africa': (None, 'Cape Colony / Azania'),
        'South Korea': ('대한민국 (Daehan Minguk)', 'Joseon / Korea'),
        'South Sudan': (None, 'Anglo-Egyptian Sudan'),
        'Spain': ('España', 'Hispania'),
        'Sri Lanka': ('ශ්\u200dරී ලංකා', 'Ceylon'),
        'Sudan': ('السودان', 'Nubia'),
        'Suriname': (None, 'Dutch Guiana'),
        'Sweden': ('Sverige', None),
        'Switzerland': ('Schweiz / Suisse / Svizzera', 'Helvetia'),
        'Syria': ('سوريا (Sūriyā)', 'Aram / Levant'),
        'Taiwan': ('臺灣 (Táiwān)', 'Formosa'),
        'Tajikistan': ('Тоҷикистон', None),
        'Tanzania': (None, 'Tanganyika / German East Africa'),
        'Thailand': ('ประเทศไทย (Prathet Thai)', 'Siam'),
        'Togo': (None, 'Togoland'),
        'Trinidad and Tobago': (None, None),
        'Tunisia': ('تونس (Tūnis)', 'Ifriqiya / Carthage'),
        'Turkey': ('Türkiye', 'Ottoman Empire / Anatolia'),
        'Turkmenistan': ('Türkmenistan', None),
        'Uganda': (None, 'British Uganda'),
        'Ukraine': ('Україна (Ukraina)', 'Kievan Rus'),
        'United Arab Emirates': ('الإمارات العربية المتحدة', 'Trucial States'),
        'United Kingdom': (None, 'Britannia / Great Britain'),
        'United States': (None, 'Turtle Island (Indigenous)'),
        'Uruguay': (None, 'Banda Oriental'),
        'Uzbekistan': ('O\'zbekiston', None),
        'Venezuela': (None, 'Little Venice'),
        'Vietnam': ('Việt Nam', 'Annam / French Indochina'),
        'Yemen': ('اليمن', 'Arabia Felix'),
        'Zambia': (None, 'Northern Rhodesia'),
        'Zimbabwe': (None, 'Rhodesia / Great Zimbabwe'),
    }

    try:
        countries = Country.query.all()
        count = 0
        for country in countries:
            entry = NAMES.get(country.name)
            if entry:
                native, historic = entry
                if native:
                    country.native_name = native
                if historic:
                    country.historic_name = historic
                count += 1
        db.session.commit()
        current_app.logger.info(f"Native/historic names seeded: {count} countries updated.")
        print(f"Native/historic names seeded: {count} countries updated.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding native/historic names: {e}")


def seed_hello_greetings():
    """Seed 'How to say Hello' data for countries based on primary language."""
    # Map language → (greeting, pronunciation, lang_name, BCP-47 code for TTS)
    GREETINGS = {
        'Arabic': ('مرحبا', 'mar-HA-ba', 'Arabic'),
        'Bengali': ('নমস্কার', 'no-mo-SHKAR', 'Bengali'),
        'Chinese': ('你好', 'nee-HOW', 'Mandarin Chinese'),
        'Croatian': ('Bok', 'bohk', 'Croatian'),
        'Czech': ('Ahoj', 'AH-hoy', 'Czech'),
        'Danish': ('Hej', 'hi', 'Danish'),
        'Dutch': ('Hallo', 'HAH-loh', 'Dutch'),
        'English': ('Hello', 'heh-LOH', 'English'),
        'Estonian': ('Tere', 'TEH-reh', 'Estonian'),
        'Filipino': ('Kumusta', 'koo-moo-STAH', 'Filipino'),
        'Finnish': ('Hei', 'hey', 'Finnish'),
        'French': ('Bonjour', 'bon-ZHOOR', 'French'),
        'Georgian': ('გამარჯობა', 'ga-mar-JO-ba', 'Georgian'),
        'German': ('Hallo', 'HAH-loh', 'German'),
        'Greek': ('Γεια σου', 'YAH-soo', 'Greek'),
        'Guaraní': ('Mba\'éichapa', 'mbah-ay-ee-CHA-pa', 'Guaraní'),
        'Hebrew': ('שלום', 'sha-LOHM', 'Hebrew'),
        'Hindi': ('नमस्ते', 'na-ma-STAY', 'Hindi'),
        'Hungarian': ('Szia', 'SEE-yah', 'Hungarian'),
        'Icelandic': ('Halló', 'HAL-oh', 'Icelandic'),
        'Indonesian': ('Halo', 'HA-loh', 'Indonesian'),
        'Irish': ('Dia duit', 'DEE-ah gwit', 'Irish'),
        'Italian': ('Ciao', 'chow', 'Italian'),
        'Japanese': ('こんにちは', 'kon-NEE-chee-wah', 'Japanese'),
        'Kazakh': ('Сәлем', 'sa-LEM', 'Kazakh'),
        'Khmer': ('សួស្តី', 'soo-AH-sdey', 'Khmer'),
        'Korean': ('안녕하세요', 'an-nyeong-ha-SE-yo', 'Korean'),
        'Lao': ('ສະບາຍດີ', 'sa-BAI-dee', 'Lao'),
        'Latvian': ('Sveiki', 'SVEY-kee', 'Latvian'),
        'Lithuanian': ('Labas', 'LAH-bahs', 'Lithuanian'),
        'Macedonian': ('Здраво', 'ZDRAH-voh', 'Macedonian'),
        'Malay': ('Helo', 'HEH-loh', 'Malay'),
        'Maltese': ('Bongu', 'BON-joo', 'Maltese'),
        'Mongolian': ('Сайн уу', 'SAYN oo', 'Mongolian'),
        'Nepali': ('नमस्ते', 'na-ma-STAY', 'Nepali'),
        'Norwegian': ('Hei', 'hey', 'Norwegian'),
        'Norwegian Bokmål': ('Hei', 'hey', 'Norwegian'),
        'Norwegian Nynorsk': ('Hei', 'hey', 'Norwegian'),
        'Pashto': ('سلام', 'sa-LAHM', 'Pashto'),
        'Persian (Farsi)': ('سلام', 'sa-LAHM', 'Persian'),
        'Polish': ('Cześć', 'cheshch', 'Polish'),
        'Portuguese': ('Olá', 'oh-LAH', 'Portuguese'),
        'Romanian': ('Salut', 'sa-LOOT', 'Romanian'),
        'Russian': ('Привет', 'pree-VYET', 'Russian'),
        'Serbian': ('Здраво', 'ZDRAH-voh', 'Serbian'),
        'Sinhala': ('ආයුබෝවන්', 'AH-yu-BOH-wan', 'Sinhala'),
        'Slovak': ('Ahoj', 'AH-hoy', 'Slovak'),
        'Slovene': ('Živjo', 'ZHEE-vyo', 'Slovene'),
        'Somali': ('Salaan', 'sa-LAHN', 'Somali'),
        'Spanish': ('Hola', 'OH-lah', 'Spanish'),
        'Swahili': ('Jambo', 'JAHM-boh', 'Swahili'),
        'Swedish': ('Hej', 'hey', 'Swedish'),
        'Tamil': ('வணக்கம்', 'va-NA-kam', 'Tamil'),
        'Thai': ('สวัสดี', 'sa-wat-DEE', 'Thai'),
        'Tigrinya': ('ሰላም', 'se-LAHM', 'Tigrinya'),
        'Turkish': ('Merhaba', 'mer-HA-ba', 'Turkish'),
        'Ukrainian': ('Привіт', 'pree-VEET', 'Ukrainian'),
        'Urdu': ('السلام علیکم', 'as-sa-LAH-mu a-LAY-kum', 'Urdu'),
        'Uzbek': ('Salom', 'sa-LOHM', 'Uzbek'),
        'Vietnamese': ('Xin chào', 'sin chow', 'Vietnamese'),
        # Additional languages
        'Amharic': ('ሰላም', 'se-LAHM', 'Amharic'),
        'Armenian': ('Բարև', 'ba-REV', 'Armenian'),
        'Azerbaijani': ('Salam', 'sa-LAHM', 'Azerbaijani'),
        'Bosnian': ('Zdravo', 'ZDRAH-voh', 'Bosnian'),
        'Bulgarian': ('Здравей', 'zdra-VEY', 'Bulgarian'),
        'Burmese': ('မင်္ဂလာပါ', 'min-ga-LA-ba', 'Burmese'),
        'Catalan': ('Hola', 'OH-lah', 'Catalan'),
        'Dari': ('سلام', 'sa-LAHM', 'Dari'),
        'Dzongkha': ('Kuzu zangpo', 'KOO-zoo ZAHNG-po', 'Dzongkha'),
        'Albanian': ('Përshëndetje', 'per-shen-DET-ye', 'Albanian'),
        'Faroese': ('Hey', 'hey', 'Faroese'),
        'Fijian': ('Bula', 'BOO-la', 'Fijian'),
        'Kinyarwanda': ('Muraho', 'moo-RAH-hoh', 'Kinyarwanda'),
        'Kirundi': ('Amahoro', 'ah-mah-HOH-roh', 'Kirundi'),
        'Malagasy': ('Manahoana', 'ma-na-HOO-na', 'Malagasy'),
        'Māori': ('Kia ora', 'KEE-ah OH-rah', 'Māori'),
        'Samoan': ('Talofa', 'ta-LOH-fa', 'Samoan'),
        'Tongan': ('Mālō e lelei', 'MAH-loh eh leh-LAY', 'Tongan'),
        'Tok Pisin': ('Halo', 'HA-loh', 'Tok Pisin'),
        'Tetum': ('Bondia', 'bon-DEE-ah', 'Tetum'),
        'Swazi': ('Sawubona', 'sah-woo-BOH-nah', 'Swazi'),
        'Sotho': ('Lumela', 'loo-MEH-lah', 'Sotho'),
        'Tswana': ('Dumela', 'doo-MEH-lah', 'Tswana'),
        'Afrikaans': ('Hallo', 'huh-LOW', 'Afrikaans'),
        'Zulu': ('Sawubona', 'sah-woo-BOH-nah', 'Zulu'),
        'Xhosa': ('Molo', 'MOH-loh', 'Xhosa'),
    }

    updated = 0
    countries = Country.query.all()
    for country in countries:
        if country.hello_phrase:
            continue  # Already has greeting
        if not country.languages:
            continue

        # Get first language value
        lang_values = list(country.languages.values())
        if not lang_values:
            continue

        primary_lang = lang_values[0]
        greeting = GREETINGS.get(primary_lang)
        if greeting:
            country.hello_phrase = greeting[0]
            country.hello_pronunciation = greeting[1]
            country.hello_language = greeting[2]
            updated += 1

    try:
        db.session.commit()
        print(f"Hello greetings seeded: {updated} countries updated.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding greetings: {e}")


def update_all_data():
    """Main function to update all relevant data."""
    init_continents()
    fetch_and_update_countries()
    seed_country_extras()
    seed_country_wealth_and_details()
    seed_native_historic_names()
    seed_hello_greetings()
    seed_oceans()
    seed_mountains()
    seed_rivers()
    seed_deserts()
    seed_forests()
    seed_volcanoes()
    seed_wonders()
    current_app.logger.info("Data update process finished.")


def _seed_items(model_class, items_data):
    """Generic helper to seed data for a model. Updates existing entries with new fields."""
    added = 0
    updated = 0
    for item_data in items_data:
        existing = model_class.query.filter_by(name=item_data["name"]).first()
        if not existing:
            obj = model_class(**item_data)
            db.session.add(obj)
            added += 1
        else:
            for key, value in item_data.items():
                if key != 'name':
                    setattr(existing, key, value)
            updated += 1
    db.session.commit()
    current_app.logger.info(f"Seeded {added} new, updated {updated} existing {model_class.__tablename__} entries.")


def seed_oceans():
    data = [
        {"name": "Pacific Ocean", "area_sq_km": 165250000, "avg_depth_m": 4280, "max_depth_m": 10994,
         "latitude": 0.0, "longitude": -160.0,
         "description": "The Pacific Ocean is the largest and deepest ocean on Earth! It covers more area than all the land on the planet combined. The Mariana Trench, the deepest point on Earth, is found here."},
        {"name": "Atlantic Ocean", "area_sq_km": 106460000, "avg_depth_m": 3646, "max_depth_m": 8376,
         "latitude": 14.5994, "longitude": -28.6731,
         "description": "The Atlantic Ocean is the second-largest ocean. It separates the Americas from Europe and Africa. The famous Titanic sank in the North Atlantic in 1912."},
        {"name": "Indian Ocean", "area_sq_km": 70560000, "avg_depth_m": 3741, "max_depth_m": 7258,
         "latitude": -20.0, "longitude": 80.0,
         "description": "The Indian Ocean is the third-largest ocean and the warmest of them all! It's home to beautiful coral reefs and tropical islands."},
        {"name": "Southern Ocean", "area_sq_km": 21960000, "avg_depth_m": 3270, "max_depth_m": 7236,
         "latitude": -65.0, "longitude": 0.0,
         "description": "The Southern Ocean surrounds Antarctica. It has the strongest ocean currents in the world and is home to penguins, seals, and whales!"},
        {"name": "Arctic Ocean", "area_sq_km": 14060000, "avg_depth_m": 1205, "max_depth_m": 5567,
         "latitude": 90.0, "longitude": 0.0,
         "description": "The Arctic Ocean is the smallest and shallowest ocean. Much of it is covered in sea ice. Polar bears roam the ice above while narwhals swim below!"}
    ]
    _seed_items(Ocean, data)


def seed_mountains():
    data = [
        {"name": "Mount Everest", "elevation_m": 8849, "location": "Nepal / China",
         "latitude": 27.9881, "longitude": 86.9250,
         "description": "Mount Everest is the tallest mountain in the world! Climbers from all over the world dream of reaching its summit."},
        {"name": "K2", "elevation_m": 8611, "location": "Pakistan / China",
         "latitude": 35.8825, "longitude": 76.5133,
         "description": "K2 is the second tallest mountain and is considered even harder to climb than Everest. It's nicknamed the 'Savage Mountain'."},
        {"name": "Kangchenjunga", "elevation_m": 8586, "location": "Nepal / India",
         "latitude": 27.7025, "longitude": 88.1475,
         "description": "Kangchenjunga is the third highest mountain. Its name means 'Five Treasures of Snow' because it has five peaks."},
        {"name": "Mount Kilimanjaro", "elevation_m": 5895, "location": "Tanzania, Africa",
         "latitude": -3.0674, "longitude": 37.3556,
         "description": "Kilimanjaro is the tallest mountain in Africa. It's actually a dormant volcano with snow on top, even though it's near the equator!"},
        {"name": "Denali", "elevation_m": 6190, "location": "Alaska, USA",
         "latitude": 63.0692, "longitude": -151.0070,
         "description": "Denali is the highest peak in North America. It was formerly called Mount McKinley. It's famous for its extreme cold weather."},
        {"name": "Mont Blanc", "elevation_m": 4808, "location": "France / Italy",
         "latitude": 45.8326, "longitude": 6.8652,
         "description": "Mont Blanc means 'White Mountain' in French. It's the tallest mountain in the Alps and a popular destination for skiers."},
        {"name": "Aconcagua", "elevation_m": 6961, "location": "Argentina, South America",
         "latitude": -32.6532, "longitude": -70.0109,
         "description": "Aconcagua is the highest mountain in South America and the tallest mountain outside of Asia!"},
        {"name": "Mount Fuji", "elevation_m": 3776, "location": "Japan",
         "latitude": 35.3606, "longitude": 138.7274,
         "description": "Mount Fuji is Japan's tallest mountain and a sacred symbol. Its perfect cone shape makes it one of the most beautiful mountains in the world."},
        {"name": "Matterhorn", "elevation_m": 4478, "location": "Switzerland / Italy",
         "latitude": 45.9763, "longitude": 7.6586,
         "description": "The Matterhorn is one of the most photographed mountains in the world. Its pyramid shape inspired the Toblerone chocolate logo!"},
        {"name": "Mount Elbrus", "elevation_m": 5642, "location": "Russia",
         "latitude": 43.3499, "longitude": 42.4453,
         "description": "Mount Elbrus is the highest mountain in Europe. It's a dormant volcano located in the Caucasus mountain range."}
    ]
    _seed_items(Mountain, data)


def seed_rivers():
    data = [
        {"name": "Nile", "length_km": 6650, "location": "Africa (11 countries)",
         "latitude": 25.0, "longitude": 32.0,
         "description": "The Nile is often considered the longest river in the world! Ancient Egypt was built along its banks. It flows northward into the Mediterranean Sea."},
        {"name": "Amazon", "length_km": 6400, "location": "South America (Brazil, Peru, Colombia)",
         "latitude": -3.1, "longitude": -60.0,
         "description": "The Amazon carries more water than any other river — about 20% of all fresh water that flows into the oceans! The Amazon Rainforest surrounds it."},
        {"name": "Yangtze", "length_km": 6300, "location": "China",
         "latitude": 30.8, "longitude": 111.0,
         "description": "The Yangtze is the longest river in Asia and the third longest in the world. The massive Three Gorges Dam is built on it."},
        {"name": "Mississippi", "length_km": 3730, "location": "United States",
         "latitude": 32.3, "longitude": -90.9,
         "description": "The Mississippi River flows through the heart of the United States. Mark Twain wrote famous stories about life on this river!"},
        {"name": "Ganges", "length_km": 2525, "location": "India / Bangladesh",
         "latitude": 25.3, "longitude": 83.0,
         "description": "The Ganges is considered a sacred river in Hinduism. Millions of people depend on it for drinking water and farming."},
        {"name": "Danube", "length_km": 2850, "location": "Europe (10 countries)",
         "latitude": 47.8, "longitude": 17.1,
         "description": "The Danube flows through more countries than any other river in the world — 10 countries! The famous waltz 'The Blue Danube' was written about it."},
        {"name": "Congo", "length_km": 4700, "location": "Central Africa",
         "latitude": -1.0, "longitude": 22.0,
         "description": "The Congo is the deepest river in the world, reaching depths of over 220 meters! It flows through dense tropical rainforest."},
        {"name": "Mekong", "length_km": 4350, "location": "Southeast Asia (6 countries)",
         "latitude": 16.0, "longitude": 105.0,
         "description": "The Mekong River is the lifeline of Southeast Asia. Its floating markets in Vietnam and Cambodia are world-famous!"},
        {"name": "Volga", "length_km": 3530, "location": "Russia",
         "latitude": 56.3, "longitude": 43.9,
         "description": "The Volga is the longest river in Europe. Russians call it 'Mother Volga' because it's so important to their country."},
        {"name": "Rhine", "length_km": 1230, "location": "Europe (6 countries)",
         "latitude": 50.4, "longitude": 7.6,
         "description": "The Rhine flows past fairy-tale castles in Germany. It has been an important trade route for thousands of years!"}
    ]
    _seed_items(River, data)


def seed_deserts():
    data = [
        {"name": "Sahara Desert", "area_sq_km": 9200000, "location": "North Africa",
         "latitude": 23.4, "longitude": 12.6,
         "description": "The Sahara is the largest hot desert in the world — almost as big as the entire United States! Temperatures can reach 50°C (122°F)."},
        {"name": "Arabian Desert", "area_sq_km": 2330000, "location": "Middle East",
         "latitude": 23.5, "longitude": 46.0,
         "description": "The Arabian Desert covers most of the Arabian Peninsula. It has huge sand dunes called 'sand seas' and is rich in oil beneath its surface."},
        {"name": "Gobi Desert", "area_sq_km": 1295000, "location": "Mongolia / China",
         "latitude": 42.6, "longitude": 103.4,
         "description": "The Gobi is a cold desert where temperatures can drop to -40°C in winter! Many dinosaur fossils have been discovered here."},
        {"name": "Kalahari Desert", "area_sq_km": 900000, "location": "Southern Africa",
         "latitude": -23.0, "longitude": 22.0,
         "description": "The Kalahari is home to the San people, one of the oldest groups of humans on Earth. Despite being a desert, it has surprising amounts of wildlife."},
        {"name": "Atacama Desert", "area_sq_km": 105000, "location": "Chile, South America",
         "latitude": -24.5, "longitude": -69.3,
         "description": "The Atacama is the driest place on Earth! Some weather stations there have NEVER recorded rain. NASA uses it to test Mars rovers."},
        {"name": "Antarctic Desert", "area_sq_km": 14200000, "location": "Antarctica",
         "latitude": -82.0, "longitude": 135.0,
         "description": "Antarctica is actually the largest desert in the world! It barely gets any precipitation. It's a frozen desert covered in ice."},
        {"name": "Sonoran Desert", "area_sq_km": 310000, "location": "USA / Mexico",
         "latitude": 32.2, "longitude": -112.9,
         "description": "The Sonoran Desert is famous for its giant saguaro cacti that can grow up to 12 meters tall and live for 200 years!"},
        {"name": "Thar Desert", "area_sq_km": 200000, "location": "India / Pakistan",
         "latitude": 27.0, "longitude": 71.0,
         "description": "The Thar Desert is also called the Great Indian Desert. It's one of the most densely populated deserts in the world."}
    ]
    _seed_items(Desert, data)


def seed_forests():
    data = [
        {"name": "Amazon Rainforest", "area_sq_km": 5500000, "location": "South America (9 countries)",
         "latitude": -3.4653, "longitude": -62.2159,
         "description": "The Amazon Rainforest is the largest tropical rainforest on Earth! It produces about 6% of the world's oxygen and is home to 10% of all species."},
        {"name": "Congo Rainforest", "area_sq_km": 2000000, "location": "Central Africa",
         "latitude": 1.0, "longitude": 22.0,
         "description": "The Congo Rainforest is the second-largest tropical forest. It's home to gorillas, forest elephants, and okapis!"},
        {"name": "Daintree Rainforest", "area_sq_km": 1200, "location": "Australia",
         "latitude": -16.17, "longitude": 145.42,
         "description": "The Daintree is the oldest tropical rainforest in the world — over 180 million years old! It's older than the Amazon."},
        {"name": "Black Forest", "area_sq_km": 6009, "location": "Germany",
         "latitude": 48.0, "longitude": 8.2,
         "description": "The Black Forest is famous for cuckoo clocks, cherry cake, and fairy tales! The Brothers Grimm set many stories here."},
        {"name": "Taiga (Boreal Forest)", "area_sq_km": 17000000, "location": "Russia, Canada, Scandinavia",
         "latitude": 60.0, "longitude": 90.0,
         "description": "The Taiga is the largest land biome on Earth, stretching across Russia and Canada. It's a vast forest of pine, spruce, and fir trees."},
        {"name": "Tongass National Forest", "area_sq_km": 68000, "location": "Alaska, USA",
         "latitude": 57.0, "longitude": -134.0,
         "description": "The Tongass is the largest national forest in the United States. It's a temperate rainforest full of bears, eagles, and salmon."},
        {"name": "Sundarbans", "area_sq_km": 10000, "location": "India / Bangladesh",
         "latitude": 21.9, "longitude": 89.2,
         "description": "The Sundarbans is the largest mangrove forest in the world. It's the home of the Royal Bengal Tiger and is partly underwater!"},
        {"name": "Białowieża Forest", "area_sq_km": 1500, "location": "Poland / Belarus",
         "latitude": 52.75, "longitude": 23.87,
         "description": "Białowieża is one of the last ancient forests in Europe. It's home to the European bison, the heaviest land animal in Europe!"}
    ]
    _seed_items(Forest, data)


def seed_volcanoes():
    data = [
        {"name": "Mount Vesuvius", "elevation_m": 1281, "location": "Italy", "status": "Active",
         "latitude": 40.821, "longitude": 14.426,
         "description": "Vesuvius famously destroyed the Roman cities of Pompeii and Herculaneum in 79 AD. It's the only active volcano on mainland Europe!"},
        {"name": "Krakatoa", "elevation_m": 813, "location": "Indonesia", "status": "Active",
         "latitude": -6.102, "longitude": 105.423,
         "description": "Krakatoa's 1883 eruption was one of the loudest sounds in recorded history — it was heard 4,800 km away! A new island is growing in its place."},
        {"name": "Mauna Loa", "elevation_m": 4169, "location": "Hawaii, USA", "status": "Active",
         "latitude": 19.475, "longitude": -155.608,
         "description": "Mauna Loa is the largest active volcano on Earth. Measured from the ocean floor, it's actually taller than Mount Everest!"},
        {"name": "Mount Etna", "elevation_m": 3357, "location": "Sicily, Italy", "status": "Active",
         "latitude": 37.751, "longitude": 14.994,
         "description": "Mount Etna is Europe's most active volcano and has been erupting for thousands of years. Ancient Greeks believed it was the forge of Hephaestus!"},
        {"name": "Mount Pinatubo", "elevation_m": 1486, "location": "Philippines", "status": "Active",
         "latitude": 15.143, "longitude": 120.350,
         "description": "Pinatubo's 1991 eruption was one of the largest in the 20th century. It cooled the entire Earth's temperature by about 0.5°C for a year!"},
        {"name": "Kilauea", "elevation_m": 1247, "location": "Hawaii, USA", "status": "Active",
         "latitude": 19.421, "longitude": -155.287,
         "description": "Kilauea is one of the most active volcanoes on Earth. In Hawaiian mythology, it's the home of Pele, the goddess of fire."},
        {"name": "Mount St. Helens", "elevation_m": 2549, "location": "Washington, USA", "status": "Active",
         "latitude": 46.191, "longitude": -122.196,
         "description": "Mount St. Helens erupted dramatically in 1980, blowing off the entire top of the mountain. The surrounding area has since recovered beautifully."},
        {"name": "Mount Tambora", "elevation_m": 2850, "location": "Indonesia", "status": "Active",
         "latitude": -8.249, "longitude": 118.000,
         "description": "Tambora's 1815 eruption was the most powerful in recorded history. It caused the 'Year Without a Summer' in 1816, with snow falling in June in Europe!"}
    ]
    _seed_items(Volcano, data)


def seed_wonders():
    data = [
        {"name": "Great Wall of China", "location": "China", "year_built": "7th century BC",
         "latitude": 40.4319, "longitude": 116.5704,
         "description": "The Great Wall stretches over 21,000 km! It was built over many centuries to protect China from invaders. It's so long it would stretch halfway around the Earth."},
        {"name": "Machu Picchu", "location": "Peru", "year_built": "1450 AD",
         "latitude": -13.1631, "longitude": -72.5450,
         "description": "Machu Picchu is an ancient Inca city built high in the Andes mountains at 2,430 meters. It was hidden from the outside world for hundreds of years!"},
        {"name": "Chichen Itza", "location": "Mexico", "year_built": "600 AD",
         "latitude": 20.6843, "longitude": -88.5678,
         "description": "Chichen Itza was built by the ancient Maya civilization. During the equinox, the sun creates a shadow that looks like a serpent slithering down the pyramid!"},
        {"name": "Christ the Redeemer", "location": "Rio de Janeiro, Brazil", "year_built": "1931",
         "latitude": -22.9519, "longitude": -43.2105,
         "description": "This giant statue of Jesus stands 30 meters tall on top of Mount Corcovado. It weighs 635 tonnes and its arms stretch 28 meters wide!"},
        {"name": "Colosseum", "location": "Rome, Italy", "year_built": "80 AD",
         "latitude": 41.8902, "longitude": 12.4922,
         "description": "The Colosseum is the largest amphitheater ever built. It could hold up to 80,000 spectators who watched gladiator fights and other events."},
        {"name": "Taj Mahal", "location": "Agra, India", "year_built": "1653",
         "latitude": 27.1751, "longitude": 78.0421,
         "description": "The Taj Mahal was built by Emperor Shah Jahan as a monument of love for his wife. It took 22 years and 20,000 workers to complete!"},
        {"name": "Petra", "location": "Jordan", "year_built": "312 BC",
         "latitude": 30.3285, "longitude": 35.4444,
         "description": "Petra is an ancient city carved directly into red rock cliffs. It's nicknamed the 'Rose City' because of the color of the stone it's carved from."}
    ]
    _seed_items(Wonder, data)


def update_all_data_job(app_context):
    """Job function for APScheduler, requires app context."""
    with app_context.app_context():
        current_app.logger.info("APScheduler: Starting scheduled data update.")
        update_all_data()
        current_app.logger.info("APScheduler: Scheduled data update finished.")