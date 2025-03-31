import sys
import os
import re
import requests
from bs4 import BeautifulSoup
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QFileDialog, QTextEdit, QLineEdit,
                              QListWidget, QListWidgetItem, QSplitter, QComboBox,
                              QToolTip)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap  # Add QPixmap import

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

import re

# Add this function after the imports
def sanitize_filename(filename):
    """Remove/replace invalid Windows filename characters"""
    # Windows invalid filename characters
    invalid_chars = {'<': '', '>': '', ':': '-', '"': "'", '/': '-', 
                    '\\': '-', '|': '-', '?': '', '*': ''}
    
    for char, replacement in invalid_chars.items():
        filename = filename.replace(char, replacement)
    return filename.strip()

def extract_episode_number(filename):
    """Extract episode number from filename using regex"""
    episode_pattern = re.compile(
        r'(?:[Ss]?\d*[EePp](\d{1,2}))|(\d{1,2})(?:[_\-\. ]|$)')
    match = episode_pattern.search(filename)
    if match:
        episode_number = match.group(1) or match.group(2)
        return str(int(episode_number)).zfill(2)
    return None

class EpisodeRenamer(QWidget):
    def __init__(self):
        super().__init__()
        self.prefix_presets = {
            "Episode # - ": "Episode {ep_number} - {ep_title}",
            "Ep# - ": "Ep{ep_number} - {ep_title}",
            "Ep# - ": "Ep{ep_number} - {ep_title}",
            "E# - ": "E{ep_number} - {ep_title}",
            "# - ": "{ep_number} - {ep_title}"

        }
        self.current_prefix = "Episode # - "  # Default prefix
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Anime Episode Renamer")
        self.setGeometry(200, 200, 1000, 600)  # Increased width for wider columns

        # Initialize list widgets first
        self.episode_list = QListWidget(self)
        self.file_list = QListWidget(self)

        main_layout = QVBoxLayout()

        # Top section (existing controls)
        top_layout = QHBoxLayout()
        
        # Folder selection - simplified
        folder_section = QVBoxLayout()
        self.browse_button = QPushButton("Select Folder", self)
        self.browse_button.clicked.connect(self.select_folder)
        folder_section.addWidget(self.browse_button)

        # Add a placeholder for the thumbnail
        self.anime_thumbnail_label = QLabel(self)
        self.anime_thumbnail_label.setAlignment(Qt.AlignCenter)
        self.anime_thumbnail_label.setFixedSize(100, 150)  # Smaller size for the thumbnail
        folder_section.addWidget(self.anime_thumbnail_label)

        top_layout.addLayout(folder_section)

        # Anime title input and results
        title_section = QVBoxLayout()
        self.anime_title_input = QLineEdit(self)
        self.anime_title_input.setPlaceholderText("Enter anime title (or auto-detect)")
        self.anime_title_input.textChanged.connect(self.on_title_changed)
        
        self.anime_results_dropdown = QComboBox(self)
        self.anime_results_dropdown.setVisible(False)
        
        self.scrape_button = QPushButton("Fetch Episode Titles", self)
        self.scrape_button.clicked.connect(self.scrape_episodes)
        self.scrape_button.setEnabled(False)
        
        title_section.addWidget(self.anime_title_input)
        title_section.addWidget(self.anime_results_dropdown)
        title_section.addWidget(self.scrape_button)
        top_layout.addLayout(title_section)

        main_layout.addLayout(top_layout)

        # Split view for episode matching
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Episode titles from MAL
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.addWidget(QLabel("MAL Episode Titles"))
        left_layout.addWidget(self.episode_list)
        splitter.addWidget(left_container)

        # Center controls
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        
        # Add spacer at top
        center_layout.addStretch()
        
        # Match button
        self.match_button = QPushButton("Match Selected", self)
        self.match_button.clicked.connect(self.match_selected)
        self.match_button.setEnabled(False)
        center_layout.addWidget(self.match_button)

        # Hoverable question mark below the Match Selected button
        help_label = QLabel("?")
        help_label.setAlignment(Qt.AlignCenter)
        help_label.setStyleSheet("""
            QLabel {
                color: gray;
                font-size: 14px;
                border: 1px solid gray;
                border-radius: 8px;
                padding: 2px 6px;
                margin: 5px;
            }
        """)
        help_label.setToolTip("Select a MAL Episode, then select the equivalent file in folder to manually rename")
        center_layout.addWidget(help_label)

        center_layout.addStretch()
        splitter.addWidget(center_container)

        # Right side - Files in folder
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.addWidget(QLabel("Files in Folder"))
        right_layout.addWidget(self.file_list)
        splitter.addWidget(right_container)

        main_layout.addWidget(splitter)

        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        # Move prefix selection to bottom
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("Filename Format:"))
        self.prefix_dropdown = QComboBox()
        self.prefix_dropdown.addItems(self.prefix_presets.keys())
        self.prefix_dropdown.setCurrentText(self.current_prefix)
        self.prefix_dropdown.currentTextChanged.connect(self.on_prefix_changed)
        prefix_layout.addWidget(self.prefix_dropdown)
        bottom_layout.addLayout(prefix_layout)

        # Auto rename button
        self.rename_button = QPushButton("Auto Rename All", self)
        self.rename_button.clicked.connect(self.rename_episodes)
        self.rename_button.setEnabled(False)
        bottom_layout.addWidget(self.rename_button)

        main_layout.addLayout(bottom_layout)

        # Status area at bottom
        self.result_area = QTextEdit(self)
        self.result_area.setReadOnly(True)
        self.result_area.setMaximumHeight(100)
        main_layout.addWidget(self.result_area)

        self.setLayout(main_layout)

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.selected_folder = folder_path
            self.update_file_list()
            
            # Auto-detect anime title from folder name
            folder_name = os.path.basename(folder_path)
            self.anime_title_input.setText(folder_name)
            
            # Auto-select the first valid anime in the dropdown
            if self.anime_results_dropdown.count() > 1:
                self.anime_results_dropdown.setCurrentIndex(1)  # Auto-select the second entry
                self.display_anime_thumbnail()

    def display_anime_thumbnail(self):
        """Fetch and display the thumbnail of the selected anime"""
        selected_id = self.anime_results_dropdown.currentData()
        if not selected_id:
            return

        # Find the selected anime's image URL
        search_url = f"https://myanimelist.net/anime/{selected_id}"
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find the thumbnail image
            img_element = soup.select_one("img.ac")
            if img_element and "data-src" in img_element.attrs:
                img_url = img_element["data-src"]
            elif img_element and "src" in img_element.attrs:
                img_url = img_element["src"]
            else:
                img_url = None

            if img_url:
                # Fetch and display the image
                img_response = requests.get(img_url)
                img_response.raise_for_status()
                pixmap = QPixmap()
                pixmap.loadFromData(img_response.content)
                scaled_pixmap = pixmap.scaled(100, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Smaller size
                
                # Update the QLabel below the "Select Folder" button
                self.anime_thumbnail_label.setPixmap(scaled_pixmap)
        except requests.RequestException as e:
            self.result_area.setText(f"Error fetching thumbnail: {str(e)}")

    def search_mal(self, anime_title):
        """Search MyAnimeList and return the anime ID"""
        import time
        
        search_url = f"https://myanimelist.net/search/all?q={anime_title.replace(' ', '%20')}&cat=anime"
        try:
            time.sleep(1)  # Add a small delay to avoid rate limiting
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Find first search result
            result = soup.find("a", class_="hoverinfo_trigger")
            if result and "href" in result.attrs:
                anime_url = result["href"]
                anime_id = anime_url.split("/")[-2]  # Extract anime ID
                return anime_id
            return None
        except requests.RequestException as e:
            self.result_area.setText(f"Error searching MAL: {str(e)}")
            return None

    def fetch_episode_titles(self, anime_id):
        """Scrape MyAnimeList for episode titles"""
        anime_details_url = f"https://myanimelist.net/anime/{anime_id}"
        try:
            # Get anime details page
            response = requests.get(anime_details_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Get formatted title
            title_element = soup.select_one("h1.title-name")
            formatted_title = title_element.text.strip().replace(" ", "_") if title_element else ""

            # Get episodes page
            episodes_url = f"https://myanimelist.net/anime/{anime_id}/{formatted_title}/episode"
            response = requests.get(episodes_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            episode_titles = {}
            # Updated selector to match MAL's current structure
            episodes = soup.select("table.episode_list tbody tr")

            # Debug info
            print(f"URL being accessed: {episodes_url}")
            print(f"Number of episodes found: {len(episodes)}")

            for episode in episodes:
                try:
                    # Get episode number and ensure it's two digits
                    ep_number = episode.select_one("td.episode-number").text.strip().rstrip('.')
                    ep_number = str(int(ep_number)).zfill(2)  # Convert to consistent 2-digit format
                    
                    # Get episode title
                    ep_title = episode.select_one("td.episode-title a.fl-l.fw-b").text.strip()
                    
                    if ep_number and ep_title:
                        print(f"Debug - Found episode: {ep_number} - {ep_title}")  # Debug print
                        episode_titles[ep_number] = ep_title
                except (AttributeError, IndexError) as e:
                    print(f"Error parsing episode: {str(e)}")
                    continue

            if not episode_titles:
                self.result_area.setText("Could not parse episode titles. The page structure might have changed.")
                print("HTML content:", soup.prettify())  # Debug print
                return {}

            return episode_titles
        except requests.RequestException as e:
            self.result_area.setText(f"Error fetching episodes: {str(e)}")
            return {}

    def scrape_episodes(self):
        """Fetch episode titles for selected anime"""
        selected_id = self.anime_results_dropdown.currentData()
        if not selected_id:
            self.result_area.setText("Please select an anime from the dropdown!")
            return

        self.result_area.setText("Fetching episodes...")
        episode_titles = self.fetch_episode_titles(selected_id)

        if episode_titles:
            self.result_area.setText("\n".join(f"Episode {ep}: {title}" 
                                             for ep, title in episode_titles.items()))
            self.episode_titles = episode_titles
            self.update_episode_list()
            self.rename_button.setEnabled(True)
            self.match_button.setEnabled(True)
        else:
            self.result_area.setText("No episode titles found!")
            self.rename_button.setEnabled(False)

    def rename_files(self, folder_path, episode_titles):
        """Rename episode files based on scraped titles"""
        episode_files = os.listdir(folder_path)
        renamed_files = []
        
        print("Debug - Available episode titles:", episode_titles.keys())

        for file in episode_files:
            print(f"\nDebug - Processing file: {file}")
            ep_number = extract_episode_number(file)
            print(f"Debug - Extracted episode number: {ep_number}")
            
            if ep_number and ep_number in episode_titles:
                print(f"Debug - Match found for episode {ep_number}")
                old_path = os.path.normpath(os.path.join(folder_path, file))
                
                safe_title = sanitize_filename(episode_titles[ep_number])
                
                format_template = self.prefix_presets[self.current_prefix]
                new_filename = format_template.format(
                    ep_number=ep_number,
                    ep_title=safe_title
                ) + os.path.splitext(file)[1]
                
                new_path = os.path.normpath(os.path.join(folder_path, new_filename))

                try:
                    os.rename(old_path, new_path)
                    renamed_files.append(f"{file} → {new_filename}")
                    print(f"Debug - Successfully renamed to: {new_filename}")
                except OSError as e:
                    renamed_files.append(f"Error renaming {file}: {str(e)}")
                    print(f"Debug - Error: {str(e)}")
                    print(f"Debug - Old path: {old_path}")
                    print(f"Debug - New path: {new_path}")
            else:
                print(f"Debug - No match found for episode {ep_number}")

        return renamed_files

    def rename_episodes(self):
        """Handle the episode renaming process"""
        if not hasattr(self, 'selected_folder'):
            self.result_area.setText("Please select a folder first!")
            return

        if not hasattr(self, 'episode_titles'):
            self.result_area.setText("Please fetch episode titles first!")
            return

        # Update the call to use self.rename_files
        renamed_files = self.rename_files(self.selected_folder, self.episode_titles)
        
        if renamed_files:
            result_text = "Renamed files:\n" + "\n".join(renamed_files)
            self.result_area.setText(result_text)
            self.update_file_list()
        else:
            self.result_area.setText("No matching files found for renaming!")

    def match_selected(self):
        """Handle manual matching of selected episode and file"""
        episode_item = self.episode_list.currentItem()
        file_item = self.file_list.currentItem()
        
        if not episode_item or not file_item:
            self.result_area.setText("Please select both an episode and a file to match")
            return

        # Get episode number and title
        ep_number = episode_item.data(Qt.UserRole)  # Stored during scraping
        ep_title = sanitize_filename(self.episode_titles[ep_number])
        
        # Update the filename generation:
        format_template = self.prefix_presets[self.current_prefix]
        new_filename = format_template.format(
            ep_number=ep_number,
            ep_title=ep_title
        ) + os.path.splitext(file_item.text())[1]
        
        # Get file path and perform rename
        old_path = os.path.join(self.selected_folder, file_item.text())
        new_path = os.path.join(self.selected_folder, new_filename)

        try:
            os.rename(old_path, new_path)
            self.result_area.setText(f"Renamed: {file_item.text()} → {new_filename}")
            # Update the file list
            self.update_file_list()
        except OSError as e:
            self.result_area.setText(f"Error renaming file: {str(e)}")

    def update_file_list(self):
        """Update the list of files in the selected folder"""
        self.file_list.clear()
        if hasattr(self, 'selected_folder'):
            files = sorted(os.listdir(self.selected_folder))
            self.file_list.addItems(files)

    def update_episode_list(self):
        """Update the list of episode titles"""
        self.episode_list.clear()
        if hasattr(self, 'episode_titles'):
            for ep_num, title in sorted(self.episode_titles.items()):
                item = QListWidgetItem(f"Episode {ep_num}: {title}")
                item.setData(Qt.UserRole, ep_num)
                self.episode_list.addItem(item)

    def on_title_changed(self):
        """Handle anime title input changes"""
        title = self.anime_title_input.text().strip()
        if len(title) >= 3:  # Only search if 3 or more characters
            self.search_anime_titles(title)
        else:
            self.anime_results_dropdown.clear()
            self.anime_results_dropdown.setVisible(False)
            self.scrape_button.setEnabled(False)

    def search_anime_titles(self, title):
        """Search MAL for anime titles and populate dropdown"""
        search_url = f"https://myanimelist.net/search/all?q={title.replace(' ', '%20')}&cat=anime"
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all search results
            results = soup.find_all("a", class_="hoverinfo_trigger")
            
            self.anime_results_dropdown.clear()
            
            # Populate the dropdown with results
            valid_entries = []
            for result in results:
                if "href" in result.attrs and "/anime/" in result["href"]:
                    anime_url = result["href"]
                    anime_id = anime_url.split("/")[-2]
                    anime_title = result.text.strip()
                    
                    # Add the entry to the dropdown
                    self.anime_results_dropdown.addItem(anime_title, userData=anime_id)
                    valid_entries.append(anime_id)
            
            # Auto-select the second entry if available
            if len(valid_entries) > 1:
                self.anime_results_dropdown.setCurrentIndex(1)  # Default to the second entry
                self.scrape_button.setEnabled(True)
            else:
                self.scrape_button.setEnabled(False)
            
            self.anime_results_dropdown.setVisible(True)
            self.anime_results_dropdown.currentIndexChanged.connect(self.on_anime_selected)  # Ensure signal is connected
        except requests.RequestException as e:
            self.result_area.setText(f"Error searching MAL: {str(e)}")

    def on_anime_selected(self, index):
        """Handle anime selection from dropdown"""
        if index > 0:  # Skip invalid selections
            self.scrape_button.setEnabled(True)
            self.display_anime_thumbnail()  # Refresh the thumbnail when selection changes
        else:
            self.scrape_button.setEnabled(False)
            self.anime_thumbnail_label.clear()  # Clear the thumbnail if no valid selection

    def on_prefix_changed(self, new_prefix):
        """Handle prefix format selection"""
        self.current_prefix = new_prefix

# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EpisodeRenamer()
    window.show()
    sys.exit(app.exec())