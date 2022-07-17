import json
import os
import sys
import logging

logger = logging.getLogger(__name__)


def abspath(rel_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, rel_path.replace('\\', '/'))


ANALYSER_SETTINGS_PATH = 'data/settings/analyser_settings.json'
GRAPH_SETTINGS_PATH = 'data/settings/graph_settings.json'


class FileManager:
    @classmethod
    def load_analyser_settings(cls) -> dict:
        try:
            with open(abspath(ANALYSER_SETTINGS_PATH), encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info('Can`t found analyser settings file.')
            return {}

    @classmethod
    def load_graph_settings(cls) -> dict:
        try:
            with open(abspath(GRAPH_SETTINGS_PATH), encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info('Can`t found graph settings file.')
            return {}

    @classmethod
    def save_analyser_settings(cls, data):
        with open(abspath(ANALYSER_SETTINGS_PATH), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    @classmethod
    def save_graph_settings(cls, data):
        with open(abspath(GRAPH_SETTINGS_PATH), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
