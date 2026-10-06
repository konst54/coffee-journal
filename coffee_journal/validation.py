"""Strict contract v1 validation; absent optional measurements remain null.

Masses: 0..100000 g (coffee dose and initial weight strictly positive).
Durations: 0..86400 s. Temperature: 0..100 C. Percentages: 0..100.
Text: at most 100000 characters; names at most 500 characters.
"""
from datetime import date, datetime
import math
import re
import uuid

FIELDS = {
    'coffee': 'name roaster origin process variety roast_level labeled_notes notes',
    'batch': 'coffee_id roast_date initial_weight_g notes',
    'equipment': 'name kind notes',
    'recipe': 'name brewer_id steps notes',
    'brew': 'batch_id brewer_id grinder_id recipe_id brewed_at temperature_c grind_setting coffee_g water_g duration_s rating taste_notes recipe_notes bypass_water_g output_g tds extraction_yield sensory',
}
FIELDS = {key: value.split() + ['source_text', 'source_refs'] for key, value in FIELDS.items()}
PRIVATE_FIELDS = frozenset({'source_text', 'source_refs'})
LIMITS = {'initial_weight_g': (0, 100000), 'coffee_g': (0, 100000),
          'water_g': (0, 100000), 'bypass_water_g': (0, 100000), 'output_g': (0, 100000),
          'temperature_c': (0, 100), 'duration_s': (0, 86400),
          'tds': (0, 100), 'extraction_yield': (0, 100), 'rating': (1, 100)}


def valid_uuid(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', value):
        raise ValueError('Invalid UUID')
    uuid.UUID(value)
    return value


def finite_json(value, depth=0):
    if depth > 20:
        raise ValueError('JSON nesting too deep')
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, list):
        for item in value:
            finite_json(item, depth + 1)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            finite_json(item, depth + 1)
        return
    raise ValueError('Invalid JSON value')


def number(key, value):
    low, high = LIMITS[key]
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid numeric value')
    if key in ('coffee_g', 'initial_weight_g') and value == 0:
        raise ValueError('Mass must be positive')
    if key == 'rating' and type(value) is not int:
        raise ValueError('Rating must be an integer')


def validate(entity, payload):
    if entity not in FIELDS or not isinstance(payload, dict):
        raise ValueError('Invalid entity or object')
    if set(payload) - (set(FIELDS[entity]) | {'id'}):
        raise ValueError('Unknown field')
    finite_json(payload)
    if entity in ('coffee', 'equipment', 'recipe'):
        name = payload.get('name')
        if not isinstance(name, str) or not name.strip() or len(name) > 500:
            raise ValueError('Name required')
    if entity == 'brew' and payload.get('batch_id') is None:
        raise ValueError('Batch required')
    if entity == 'batch' and payload.get('coffee_id') is None:
        raise ValueError('Coffee required')
    if entity == 'equipment' and payload.get('kind') not in ('brewer', 'grinder'):
        raise ValueError('Equipment kind required')
    for key, value in payload.items():
        if key == 'id':
            valid_uuid(value)
        elif value is None:
            continue
        elif key.endswith('_id'):
            valid_uuid(value)
        elif key in LIMITS:
            number(key, value)
        elif key == 'source_refs':
            if not isinstance(value, list) or len(value) > 1000 or any(not isinstance(v, str) or not v or len(v) > 4096 or '\x00' in v for v in value):
                raise ValueError('Invalid source references')
        elif key == 'sensory':
            axes = {'aroma', 'sweetness', 'acidity', 'aftertaste', 'body', 'flavor', 'balance', 'cleanliness', 'complexity'}
            if not isinstance(value, dict) or set(value) - axes:
                raise ValueError('Invalid sensory axes')
            for score in value.values():
                if score is not None and (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 100):
                    raise ValueError('Sensory score must be 0..100')
        elif key == 'steps':
            if not isinstance(value, list) or len(value) > 1000:
                raise ValueError('Invalid steps')
            for step in value:
                if not isinstance(step, dict) or set(step) - {'name', 'instruction', 'duration_s', 'water_g'}:
                    raise ValueError('Invalid step')
                for field, item in step.items():
                    if item is None:
                        continue
                    if field in LIMITS:
                        number(field, item)
                    elif not isinstance(item, str) or len(item) > 100000:
                        raise ValueError('Invalid step text')
        elif not isinstance(value, str) or len(value) > 100000:
            raise ValueError('Invalid text')
        elif key == 'kind' and value not in ('brewer', 'grinder'):
            raise ValueError('Invalid equipment kind')
        elif key == 'roast_date':
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('Invalid date')
            date.fromisoformat(value)
        elif key == 'brewed_at':
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
                raise ValueError('Timezone timestamp required')
            if datetime.fromisoformat(value).utcoffset() is None:
                raise ValueError('Timezone required')
    return {key: payload.get(key) for key in FIELDS[entity]} | ({'id': payload['id']} if 'id' in payload else {})
