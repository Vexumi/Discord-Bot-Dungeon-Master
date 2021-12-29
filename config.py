import json


def get_settings():
    with open('settings.json', mode='r') as json_file:
        settings = json.load(json_file)
    return settings


def get_plants():
    with open('data/plants.json', mode='r', encoding='utf-8') as json_file:
        stats = json.load(json_file)
    return stats


def get_players():
    with open('data/players.json', mode='r', encoding='utf-8') as json_file:
        players = json.load(json_file)
    return players
