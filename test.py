import re

def extract_episode_number(filename):
    """Extract episode number from filename using regex"""
    # Match numbers that are followed by various separators including dots
    episode_pattern = re.compile(r'(\d{1,2})(?:[_\-\. ]|$)')
    match = episode_pattern.search(filename)
    if match:
        # Convert to string and zfill to ensure consistent formatting
        return str(int(match.group(1))).zfill(2)
    return None

# print(extract_episode_number("AnimePahe_Suisei_no_Gargantia_-_Meguru_Kouro_Haruka_-_02_BD_720p_Vivid.mp4"))
print(extract_episode_number("2 Zom 100 [AnimeKaizoku]"))

print(extract_episode_number("Season1_episode09.avi"))