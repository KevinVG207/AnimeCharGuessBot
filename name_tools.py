def generateInitials(character_data):
    char_name = character_data["en_name"].strip()
    out_string = ""
    try:
        initials = [segment[0] for segment in char_name.split(" ")]
    except IndexError:
        print("Initials error")
        print(character_data)
        initials = ["BRUH"]
    for initial in initials:
        out_string += f"{initial}. "
    return out_string.rstrip()


def nameToList(name):
    name_list = name.strip().split()
    out_list = []
    for segment in name_list:
        segment = "".join(char for char in segment.lower() if char.isalnum())
        out_list.append(romanizationFix(segment))
    return out_list


def romanizationFix(segment):
    replace_dict = {"oo": "o",
                    "ou": "o",
                    "uu": "u",
                    "ii": "i"}
    for before, after in replace_dict.items():
        segment = segment.replace(before, after)
    return segment
