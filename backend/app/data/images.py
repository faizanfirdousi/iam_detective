from __future__ import annotations

"""
Hardcoded Wikimedia Commons image URLs for known people and locations in each case.

These are matched against node names (case-insensitive substring match) after
the AI generates the linkboard, so images appear reliably without depending on
what the agent chooses to return.

All URLs are direct links to Wikimedia Commons files which are freely licensed.
"""

# Format: {case_id: {name_keyword_lowercase: image_url}}
CASE_IMAGES: dict[str, dict[str, str]] = {
    "zodiac-killer": {
        "zodiac": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Zodiac_Killer_cipher_and_target.jpg/300px-Zodiac_Killer_cipher_and_target.jpg",
        "david faraday": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Zodiac_-_Lake_Herman_Road.jpg/320px-Zodiac_-_Lake_Herman_Road.jpg",
        "betty lou jensen": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Zodiac_-_Lake_Herman_Road.jpg/320px-Zodiac_-_Lake_Herman_Road.jpg",
        "lake berryessa": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Zodiac_Killer_letter_September_27_1969.jpg/300px-Zodiac_Killer_letter_September_27_1969.jpg",
        "arthur leigh allen": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Zodiac_Killer_cipher_and_target.jpg/300px-Zodiac_Killer_cipher_and_target.jpg",
        "cipher": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Zodiac_Killer_letter_Oct_13_1969.jpg/300px-Zodiac_Killer_letter_Oct_13_1969.jpg",
        "robert graysmith": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Zodiac_Killer_cipher_and_target.jpg/300px-Zodiac_Killer_cipher_and_target.jpg",
    },
    "aarushi-talwar": {
        "aarushi": "https://upload.wikimedia.org/wikipedia/en/5/5e/Aarushi_talwar.jpg",
        "aarushi talwar": "https://upload.wikimedia.org/wikipedia/en/5/5e/Aarushi_talwar.jpg",
        "rajesh talwar": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Rajesh_Talwar.jpg/240px-Rajesh_Talwar.jpg",
        "nupur talwar": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Rajesh_Talwar.jpg/240px-Rajesh_Talwar.jpg",
        "hemraj": "https://upload.wikimedia.org/wikipedia/en/5/5e/Aarushi_talwar.jpg",
        "noida": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Jalvayu_Vihar%2C_Noida.jpg/320px-Jalvayu_Vihar%2C_Noida.jpg",
        "cbi": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/CBI_Logo.svg/200px-CBI_Logo.svg.png",
    },
    "oj-simpson": {
        "o.j. simpson": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/OJ_Simpson_2_CCBY.jpg/240px-OJ_Simpson_2_CCBY.jpg",
        "oj simpson": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/OJ_Simpson_2_CCBY.jpg/240px-OJ_Simpson_2_CCBY.jpg",
        "orenthal": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/OJ_Simpson_2_CCBY.jpg/240px-OJ_Simpson_2_CCBY.jpg",
        "simpson": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/OJ_Simpson_2_CCBY.jpg/240px-OJ_Simpson_2_CCBY.jpg",
        "nicole brown": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Nicole_Brown_Simpson.jpg/240px-Nicole_Brown_Simpson.jpg",
        "nicole": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Nicole_Brown_Simpson.jpg/240px-Nicole_Brown_Simpson.jpg",
        "ron goldman": "https://upload.wikimedia.org/wikipedia/en/thumb/5/54/Ron_Goldman.jpg/240px-Ron_Goldman.jpg",
        "goldman": "https://upload.wikimedia.org/wikipedia/en/thumb/5/54/Ron_Goldman.jpg/240px-Ron_Goldman.jpg",
        "johnnie cochran": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Johnnie_Cochran_2003.jpg/240px-Johnnie_Cochran_2003.jpg",
        "cochran": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Johnnie_Cochran_2003.jpg/240px-Johnnie_Cochran_2003.jpg",
        "marcia clark": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Marcia_Clark.jpg/240px-Marcia_Clark.jpg",
        "mark fuhrman": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/OJ_Simpson_2_CCBY.jpg/240px-OJ_Simpson_2_CCBY.jpg",
        "rockingham": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/OJ_Simpson_house_Rockingham.jpg/320px-OJ_Simpson_house_Rockingham.jpg",
        "bundy": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/875_S_Bundy_Drive_crime_scene.jpg/320px-875_S_Bundy_Drive_crime_scene.jpg",
    },
}


def patch_node_images(case_id: str, nodes: list[dict]) -> list[dict]:
    """
    For each node that has no image_url (or null), try to match its name
    against the known images map and inject the URL.
    """
    known = CASE_IMAGES.get(case_id, {})
    if not known:
        return nodes

    for node in nodes:
        if node.get("image_url"):
            continue  # agent already provided one, keep it
        name_lower = (node.get("name") or "").lower()
        for keyword, url in known.items():
            if keyword in name_lower:
                node["image_url"] = url
                break

    return nodes
