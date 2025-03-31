import re

def extract_episode_number(filename):
    """Extract episode number from filename using regex"""
    episode_pattern = re.compile(
        r'(?:[Ss]?\d*[EePp](\d{1,2}))|(\d{1,2})(?:[_\-\. ]|$)'
    )
    match = episode_pattern.search(filename)
    if match:
        episode_number = match.group(1) or match.group(2)
        return str(int(episode_number)).zfill(2)
    return None

print(extract_episode_number("2 Zom 100 [AnimeKaizoku]"))

print(extract_episode_number("Season1_episode09.avi"))

print(extract_episode_number("[AK] Link Click [S1EP05] [720p] [Dual] AnimeKaizoku"))