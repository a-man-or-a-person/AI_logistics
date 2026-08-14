import re

def remove_known_coords():
    with open('backend/geocoder.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove KNOWN_COORDS dict
    # It starts with "KNOWN_COORDS: dict[str, tuple[float, float]] = {"
    # And ends with "}" at the start of a line (or just look for the regex)
    content = re.sub(r'KNOWN_COORDS: dict\[str, tuple\[float, float\]\] = \{[^}]+\}\n', '', content)

    # 2. Remove from geocode_town
    # Find:
    #     # 2. Встроенный словарь (пропускаем для деревень и поселков)
    #     is_rural = ...
    #     ...
    #     # 3. Nominatim
    pattern_town = r'    # 2\. Встроенный словарь.*?    # 3\. Nominatim'
    content = re.sub(pattern_town, '    # 2. Nominatim', content, flags=re.DOTALL)

    # 3. Remove from geocode_all_towns_background
    # Find:
    #         if not found:
    #             is_rural = ...
    #             if not is_rural:
    #                 ...
    #                 
    #         if not found:
    #             missing.append((town, region))
    pattern_bg = r'        if not found:\n            is_rural = any\(town_clean\.startswith\(prefix\).*?        if not found:\n            missing\.append\(\(town, region\)\)'
    content = re.sub(pattern_bg, '        if not found:\n            missing.append((town, region))', content, flags=re.DOTALL)

    with open('backend/geocoder.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Done")

if __name__ == '__main__':
    remove_known_coords()
