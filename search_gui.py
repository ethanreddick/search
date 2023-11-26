import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QLabel, QTextEdit, QRadioButton, QButtonGroup, QStackedWidget, QGridLayout, QFormLayout, QSizePolicy
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
import psycopg2 # Python/PostgreSQL database adapter

# Global variable to track the current page index
current_page_index = 0

# Database connection setup
def connect_database():
    try:
        return psycopg2.connect(
            host="localhost",
            database="scraper_db",
            user="ethan",
            password="search"
        )
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def search():
    # Grab user's query from the search bar
    query = search_bar.text()
    bias = bias_selector.currentText() # TODO: Build in bias functionality

    # Set up DB connection
    conn = connect_database()
    if conn:
        cur = conn.cursor()
        # Query the database, inserting wildcard characters on both sides of the query
        # Here the titles and headers are searched for the query, and results in a title are worth 5 times
        # the value of a match in the headers.
        cur.execute(
            """
            SELECT title, url, 5 as weight FROM page_details WHERE title ILIKE %s
            UNION
            SELECT title, url, 1 as weight FROM page_details WHERE headers ILIKE %s
            ORDER BY weight DESC, title
            """, 
            ('%' + query + '%', '%' + query + '%',)
            )
        results = cur.fetchall()
        cur.close()
        conn.close()

        # Build the results from the query
        results_text = " "
        for result in results:
            # Need to find correct order of results
            title, url = result[0], result[1]
            # Format the results for the user
            results_text += f"<b>{title}</b><br>{url}<br><br><br>"

        results_display.setHtml(results_text)
    else:
        results_display.setPlainText("Failed to connect to the database.")

    

def open_settings():
    global current_page_index
    current_page_index = 1  # Index 1 corresponds to the settings page
    stacked_widget.setCurrentIndex(current_page_index)

def close_settings():
    global current_page_index
    current_page_index = 0  # Index 0 corresponds to the main page
    stacked_widget.setCurrentIndex(current_page_index)

def apply_theme(theme_name):
    global current_theme
    current_theme = theme_name  # Store the current theme globally

    # Create a palette for the selected theme
    palette = QPalette()
    if theme_name == "Dark":
        palette.setColor(QPalette.Window, QColor(40, 40, 40))  # Dark background
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))  # Light text
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))  # Light text on buttons
        palette.setColor(QPalette.Highlight, QColor(100, 100, 100))  # Selection highlight
        search_bar.setStyleSheet("background-color: {}; color: white;".format(QColor(30, 30, 30).name()))  # Dark background and white text for search bar
        results_display.setStyleSheet("background-color: {}; color: white;".format(QColor(30, 30, 30).name()))  # Dark background and white text for results display
    elif theme_name == "Light":
        palette.setColor(QPalette.Window, QColor(255, 255, 255))  # Light background
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))  # Dark text
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))  # Dark text on buttons
        palette.setColor(QPalette.Highlight, QColor(200, 200, 200))  # Selection highlight
        search_bar.setStyleSheet("background-color: white; color: black;")  # Light background and black text for search bar
        results_display.setStyleSheet("background-color: #F0F0F0; color: black;")  # Light gray background and black text for results display

    # Set placeholder text color explicitly
    search_bar.setPlaceholderText("Enter your query here...")
    placeholder_palette = QPalette(palette)
    placeholder_palette.setColor(QPalette.PlaceholderText, QColor(128, 128, 128))  # Gray placeholder text color
    search_bar.setPalette(placeholder_palette)

    # Apply the palette to the entire application
    app.setPalette(palette)

    # Apply the palette to the combo boxes (including the currently selected item text color)
    for combo_box in [bias_selector, theme_selector]:
        combo_box.setPalette(palette)
        combo_box.setStyleSheet("color: {};" .format(palette.color(QPalette.WindowText).name()))

app = QApplication(sys.argv)

window = QMainWindow()
window.setWindowTitle('Search Engine')
window.setGeometry(100, 100, 800, 600)

# Central widget to hold all content
central_widget = QWidget()
window.setCentralWidget(central_widget)

# Set layout for central widget to occupy the entire window
central_layout = QVBoxLayout(central_widget)

# Stacked widget to switch between main page and settings page
stacked_widget = QStackedWidget(central_widget)

# Main page
main_page = QWidget()
main_layout = QVBoxLayout()

# Top layout
top_layout = QHBoxLayout()

# Settings button
settings_button = QPushButton('Settings')
settings_button.clicked.connect(open_settings)
top_layout.addWidget(settings_button)

# Search bar
search_bar = QLineEdit()
search_bar.setPlaceholderText("Enter your query here...")  # Placeholder text
top_layout.addWidget(search_bar)

# Search bias selector
bias_label = QLabel('Search Bias:')
top_layout.addWidget(bias_label)

# Capitalized search biases and added "Privacy"
bias_selector = QComboBox()
bias_selector.addItems(['Corporate', 'Research', 'Charity', 'Privacy'])
top_layout.addWidget(bias_selector)

# Search button
search_button = QPushButton('Search')
search_button.clicked.connect(search)
top_layout.addWidget(search_button)

# Enable return key for search
search_bar.returnPressed.connect(search)

# Adding top layout to main layout
main_layout.addLayout(top_layout)

# Results display
results_display = QTextEdit()
main_layout.addWidget(results_display)

# Pagination controls
pagination_layout = QHBoxLayout()
prev_button = QPushButton('Previous')
next_button = QPushButton('Next')
pagination_layout.addWidget(prev_button)
pagination_layout.addWidget(next_button)

# Adding pagination layout to main layout
main_layout.addLayout(pagination_layout)

# Setting main layout for the main page
main_page.setLayout(main_layout)

# Settings page
settings_page = QWidget()
settings_layout = QVBoxLayout()

# Create a grid layout for settings
settings_grid_layout = QGridLayout()

# X button for returning to the main page
x_button = QPushButton('←')  # Use a left arrow symbol
x_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)  # Make the button larger
x_button.clicked.connect(close_settings)

# Theme selector label
theme_label = QLabel('Theme:')
theme_selector = QComboBox()
theme_selector.addItems(['Dark', 'Light'])
theme_selector.setCurrentText('Dark')  # Set the default theme to Dark
theme_selector.currentIndexChanged.connect(lambda: apply_theme(theme_selector.currentText()))

# Add widgets to the grid layout
settings_grid_layout.addWidget(x_button, 0, 0, 1, 1)
settings_grid_layout.addWidget(theme_label, 1, 0, 1, 1)
settings_grid_layout.addWidget(theme_selector, 1, 1, 1, 1)

# Add the grid layout to the settings layout
settings_layout.addLayout(settings_grid_layout)
settings_layout.addStretch()  # Add stretchable space to align items to the top

# Setting layout for the settings page
settings_page.setLayout(settings_layout)

# Adding both pages to the stacked widget
stacked_widget.addWidget(main_page)
stacked_widget.addWidget(settings_page)

# Add the stacked widget to the central layout
central_layout.addWidget(stacked_widget)

# Apply the initial theme
apply_theme(theme_selector.currentText())

window.show()

sys.exit(app.exec_())
