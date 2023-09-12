import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QLabel, QTextEdit

def search():
    query = search_bar.text()
    bias = bias_selector.currentText()
    print(f"Search query: {query}, Search bias: {bias}")

def open_settings():
    print("Settings clicked")

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle('Search Engine')
window.setGeometry(100, 100, 800, 600)

# Top layout
top_layout = QHBoxLayout()

# Settings button
settings_button = QPushButton('Settings')
settings_button.clicked.connect(open_settings)
top_layout.addWidget(settings_button)

# Search bar
search_bar = QLineEdit()
top_layout.addWidget(search_bar)

# Search bias selector
bias_label = QLabel('Search Bias:')
top_layout.addWidget(bias_label)

bias_selector = QComboBox()
bias_selector.addItems(['corporate', 'research', 'charity'])
top_layout.addWidget(bias_selector)

# Search button
search_button = QPushButton('Search')
search_button.clicked.connect(search)
top_layout.addWidget(search_button)

# Main layout
main_layout = QVBoxLayout()

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

# Setting main layout for the window
window.setLayout(main_layout)

window.show()

sys.exit(app.exec_())
