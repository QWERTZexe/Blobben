import sys, os
from PyQt6.QtCore import QUrl, QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QToolBar, QLineEdit, QPushButton, QVBoxLayout, QWidget, QTabWidget, QFrame
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWebEngineCore import QWebEngineUrlScheme, QWebEngineProfile
from PyQt6.QtWebEngineCore import QWebEngineUrlSchemeHandler, QWebEngineUrlRequestJob

# <a href="https://www.flaticon.com/free-icons/return" title="return icons">Return icons created by Kiranshastry - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/reload" title="reload icons">Reload icons created by Uniconlabs - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/home" title="home icons">Home icons created by Freepik - Flaticon</a>

cwd = os.path.dirname(os.path.abspath(sys.argv[0]))
    
class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loadFinished.connect(self.onLoadFinished)

    def onLoadFinished(self, ok):
        if ok:
            self.runJavaScript("""
                window.blobbenSearch = function(searchTerm) {
                    window.location.href = 'https://www.bing.com/search?q=' + encodeURIComponent(searchTerm);
                };
            """)

class Toolbar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Toolbar
        self.toolbar = QToolBar()
        self.layout.addWidget(self.toolbar)

        # Back button
        self.back_button = QPushButton()
        self.back_button.setIcon(QIcon(f"{cwd}/assets/go-back"))
        self.back_button.setFixedSize(QSize(35, 35))
        self.back_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.back_button)

        # Forward button
        self.forward_button = QPushButton()
        self.forward_button.setIcon(QIcon(f"{cwd}/assets/go-forward"))
        self.forward_button.setFixedSize(QSize(35, 35))
        self.forward_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.forward_button)

        # Reload button
        self.reload_button = QPushButton()
        self.reload_button.setIcon(QIcon(f"{cwd}/assets/reload"))
        self.reload_button.setFixedSize(QSize(35, 35))
        self.reload_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.reload_button)
        
        # Home button
        self.home_button = QPushButton()
        self.home_button.setIcon(QIcon(f"{cwd}/assets/home"))
        self.home_button.setFixedSize(QSize(35, 35))
        self.home_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.home_button)

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setFixedHeight(30)
        self.url_bar.setFont(QFont("Calibri", 13))
        self.toolbar.addWidget(self.url_bar)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.separator.setLineWidth(1)
        self.layout.addWidget(self.separator)

        # WebView
        self.web_view = QWebEngineView()
        self.web_view.setPage(CustomWebEnginePage(self.web_view))
        self.layout.addWidget(self.web_view)

        # Connect signals
        self.back_button.clicked.connect(self.web_view.back)
        self.forward_button.clicked.connect(self.web_view.forward)
        self.reload_button.clicked.connect(self.web_view.reload)
        self.home_button.clicked.connect(lambda: self.web_view.setUrl(QUrl.fromLocalFile(f"{cwd}/sites/home.html")))
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.web_view.urlChanged.connect(self.update_url)

    def navigate_to_url(self):
        q = QUrl(self.url_bar.text())
        if self.url_bar.text() == "blobben://":
            q = QUrl(f"file:///{cwd.replace("\\","/")}/sites/home.html")
        elif self.url_bar.text().startswith("blobben://"):
            q = QUrl(f"file:///{cwd.replace("\\","/")}/sites/{self.url_bar.text().replace("blobben://","")}" if self.url_bar.text().endswith(".html") else f"file:///{cwd.replace("\\","/")}/sites/{self.url_bar.text().replace("blobben://","")}.html")
        if q.scheme() == "":
            if not self.url_bar.text() == "":
                q = QUrl(f"https://bing.com/search?q={self.url_bar.text()}")
            else:
                q = QUrl(f"file:///{cwd.replace("\\","/")}/sites/aboutblank.html")
        self.web_view.setUrl(q)

    def update_url(self, q):
        a=f"file:///{cwd.replace("\\","/")}/sites/".lower()

        if a.lower() in q.toString().lower():
            self.url_bar.setText(f"{q.toString().lower().replace(a,"blobben://")}")
            if self.url_bar.text().endswith(".html"):
                self.url_bar.setText(self.url_bar.text().replace(".html",""))
        else:
            self.url_bar.setText(q.toString())


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blobben v0.1")
        self.setWindowIcon(QIcon(f"{cwd}/assets/icon.png"))

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)

        # Add new tab button
        self.tabs.setCornerWidget(QPushButton("+", clicked=self.add_new_tab))

        self.add_new_tab()
        self.showMaximized()

    def add_new_tab(self, qurl=None):
        if qurl is None or isinstance(qurl,bool):
            urlcwd = cwd.replace("\\","/")
            qurl = QUrl.fromLocalFile(f"{cwd}/sites/home.html")

        toolbar = Toolbar(self)
        toolbar.web_view.setUrl(qurl)
        i = self.tabs.addTab(toolbar, "New Tab")
        self.tabs.setCurrentIndex(i)
        toolbar.web_view.titleChanged.connect(lambda title, index=i: self.update_tab_title(index, title))
        toolbar.web_view.iconChanged.connect(lambda icon, index=i: self.update_tab_icon(index, icon))

    def close_current_tab(self, i):
        if self.tabs.count() < 2:
            return
        self.tabs.removeTab(i)

    def update_tab_title(self, index, title):
        self.tabs.setTabText(index, title)

    def update_tab_icon(self, index, icon):
        self.tabs.setTabIcon(index, icon)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Browser()
    window.show()
    sys.exit(app.exec())