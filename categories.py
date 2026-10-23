"""Shared category names and legacy-label translation."""
CATEGORIES = ['strength', 'mobility', 'recovery', 'longevity clinics']
CATEGORY_MAP = {
    'gym': 'strength',
    'yoga/stretching': 'mobility',
    'longevity': 'longevity clinics',
    **{category: category for category in CATEGORIES},
}


def translate_categories(values):
    mapped = []
    legacy = []
    for value in values:
        target = CATEGORY_MAP.get(value)
        destination = mapped if target else legacy
        result = target or value
        if result not in destination:
            destination.append(result)
    return mapped, legacy


def translate_branch(branch):
    result = dict(branch)
    categories, legacy = translate_categories(branch.get('categories', []))
    result['categories'] = categories
    if legacy:
        result['legacy_categories'] = list(dict.fromkeys(branch.get('legacy_categories', []) + legacy))
    return result
