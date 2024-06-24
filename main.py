import sys, os, json, subprocess
from PyQt6.QtCore import QUrl, QSize, QDateTime, Qt, QByteArray, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QToolBar, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QFrame, QLabel, QProgressBar, QToolButton, QMenu, QTextEdit, QSplitter, QSplitter
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineDownloadRequest
from PyQt6.QtGui import QIcon, QFont, QAction
from PyQt6.QtWebEngineCore import QWebEngineUrlScheme, QWebEngineProfile, QWebEngineCookieStore
from PyQt6.QtNetwork import QNetworkCookie

# <a href="https://www.flaticon.com/free-icons/return" title="return icons">Return icons created by Kiranshastry - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/reload" title="reload icons">Reload icons created by Uniconlabs - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/home" title="home icons">Home icons created by Freepik - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/save" title="save icons">Save icons created by Bharat Icons - Flaticon</a>

cwd = os.path.dirname(os.path.abspath(sys.argv[0]))
version = "0.1"

class DownloadManager(QObject):
    downloadStarted = pyqtSignal()
    downloadFinished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloads = []
        self.download_history_file = f"{cwd}/cache/downloads.json"
        self.load_download_history()

    def add_download(self, download: QWebEngineDownloadRequest):
        download_info = {
            'id': len(self.downloads),
            'url': download.url().toString(),
            'filename': download.downloadFileName(),
            'path': os.path.join(download.downloadDirectory(), download.downloadFileName()),
            'size': download.totalBytes(),
            'received': 0,
            'status': 'In Progress'
        }
        self.downloads.append(download_info)
        
        download.receivedBytesChanged.connect(lambda: self.update_progress(download_info['id'], download))
        download.stateChanged.connect(lambda: self.update_state(download_info['id'], download))
        download.accept()

        self.downloadStarted.emit()

    def update_progress(self, download_id, download):
        self.downloads[download_id]['received'] = download.receivedBytes()

    def update_state(self, download_id, download):
        if download.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.downloads[download_id]['status'] = 'Completed'
            self.downloadFinished.emit()
        elif download.state() == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            self.downloads[download_id]['status'] = 'Canceled'
            self.downloadFinished.emit()
        elif download.state() == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            self.downloads[download_id]['status'] = 'Failed'
            self.downloadFinished.emit()
        
        self.save_download_history()

    def save_download_history(self):
        with open(self.download_history_file, 'w') as f:
            json.dump(self.downloads, f, indent=4)

    def load_download_history(self):
        if os.path.exists(self.download_history_file):
            with open(self.download_history_file, 'r') as f:
                self.downloads = json.load(f)

    def get_all_downloads(self):
        return self.downloads
    
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
            
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if message.startswith("Open in explorer$"):
            print(message)
            path = message.split("$")[1].strip()
            self.show_in_explorer(path)

    def show_in_explorer(self, path):
        if os.name == 'nt':  # Windows
            print(path)
            os.startfile(os.path.dirname(path))
        elif os.name == 'posix':  # macOS and Linux
            try:
                subprocess.call(["open", "-R", path])
            except:
                subprocess.call(["xdg-open", os.path.dirname(path)])

class Toolbar(QWidget):
    resetColor = pyqtSignal()
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
        self.back_button.setIcon(QIcon(f"{cwd}/assets/go-back.png"))
        self.back_button.setFixedSize(QSize(35, 35))
        self.back_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.back_button)

        # Forward button
        self.forward_button = QPushButton()
        self.forward_button.setIcon(QIcon(f"{cwd}/assets/go-forward.png"))
        self.forward_button.setFixedSize(QSize(35, 35))
        self.forward_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.forward_button)

        # Reload button
        self.reload_button = QPushButton()
        self.reload_button.setIcon(QIcon(f"{cwd}/assets/reload.png"))
        self.reload_button.setFixedSize(QSize(35, 35))
        self.reload_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.reload_button)
        
        # Home button
        self.home_button = QPushButton()
        self.home_button.setIcon(QIcon(f"{cwd}/assets/home.png"))
        self.home_button.setFixedSize(QSize(35, 35))
        self.home_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.home_button)

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setFixedHeight(30)
        self.url_bar.setFont(QFont("Calibri", 13))
        self.toolbar.addWidget(self.url_bar)

        self.download_button = QPushButton()
        self.download_button.setIcon(QIcon(f"{cwd}/assets/download.png"))
        self.download_button.setFixedSize(QSize(35, 35))
        self.download_button.setIconSize(QSize(25, 25))
        self.toolbar.addWidget(self.download_button)

        # Download menu
        # self.download_menu = QMenu(self)
        # self.download_menu.aboutToShow.connect(self.on_download_button_clicked)
        # self.download_button.setMenu(self.download_menu)
        # self.download_complete = False

        # View all downloads action
        # view_all_action = QAction("View all downloads", self)
        # view_all_action.triggered.connect(self.view_all_downloads)
        # self.download_menu.addAction(view_all_action)
        # self.download_menu.addSeparator()

        # Source code button
        self.source_button = QPushButton()
        self.source_button.setIcon(QIcon(f"{cwd}/assets/source.png"))
        self.source_button.setFixedSize(QSize(35, 35))
        self.source_button.setIconSize(QSize(25, 25))
        self.source_button.clicked.connect(self.toggle_source_view)
        self.toolbar.addWidget(self.source_button)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.separator.setLineWidth(1)
        self.layout.addWidget(self.separator)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.separator.setLineWidth(1)
        self.layout.addWidget(self.separator)

        # WebView
        # WebView and Editor Container
        self.web_container = QWidget()
        self.web_layout = QHBoxLayout(self.web_container)
        self.web_layout.setContentsMargins(0, 0, 0, 0)
        self.web_layout.setSpacing(0)

        # WebView
        self.web_view = QWebEngineView()
        self.web_view.setPage(CustomWebEnginePage(self.web_view))
        self.web_layout.addWidget(self.web_view)

        self.layout.addWidget(self.web_container)

        # Editor (initially not created)
        self.editor = None
        # Connect signals
        self.back_button.clicked.connect(self.web_view.back)
        self.forward_button.clicked.connect(self.web_view.forward)
        self.reload_button.clicked.connect(self.reload_page)
        self.download_button.clicked.connect(self.on_download_button_clicked)
        self.home_button.clicked.connect(lambda: self.web_view.setUrl(QUrl.fromLocalFile(f"{cwd}/sites/home.html")))
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.web_view.urlChanged.connect(self.update_url)

        # Connect download signals
        parent.download_manager.downloadStarted.connect(self.on_download_started)
        parent.download_manager.downloadFinished.connect(self.on_download_finished)

        self.download_complete = False
        self.editor = None
        self.is_source_visible = False

    def reset_download_icon(self):
        self.download_button.setIcon(QIcon(f"{cwd}/assets/download.png"))

    def toggle_source_view(self):
        if self.is_source_visible:
            self.hide_source()
        else:
            self.show_source()

    def show_source(self):
        self.original_url = self.web_view.url()
        self.web_view.page().toHtml(self.create_source_view)

    def create_source_view(self, html):
        if self.editor is None:
            self.editor = QTextEdit()
            self.editor.textChanged.connect(self.update_page_source)
            self.web_layout.addWidget(self.editor)

        self.editor.setPlainText(html)
        self.editor.show()
        self.web_layout.setStretch(0, 1)  # WebView
        self.web_layout.setStretch(1, 1)  # Editor
        self.is_source_visible = True
        self.source_button.setIcon(QIcon(f"{cwd}/assets/source-on.png"))

    def hide_source(self):
        if self.editor is not None:
            self.editor.hide()
            self.web_layout.setStretch(0, 1)  # WebView
            self.web_layout.setStretch(1, 0)  # Editor
        self.is_source_visible = False
        self.source_button.setIcon(QIcon(f"{cwd}/assets/source.png"))

    def update_page_source(self):
        if self.editor is not None and self.is_source_visible:
            html = self.editor.toPlainText()
            self.web_view.setHtml(html,self.original_url)

    def reload_page(self):
        current_url = self.web_view.url()
        self.web_view.setUrl(current_url)

    # def view_all_downloads(self):
        # a=cwd.replace("\\", "/")
        # self.web_view.setUrl(QUrl(f"file:///{a}/sites/downloads.html"))

    # def update_download_menu(self, downloads):
        # Clear previous download items
        # for action in self.download_menu.actions()[2:]:
            # self.download_menu.removeAction(action)

        # Add recent downloads (limit to 5 for example)
        # for download in downloads[:5]:
            # action = QAction(f"{download['filename']} - {download['status']}", self)
            # self.download_menu.addAction(action)

        # if len(downloads) > 5:
            # self.download_menu.addAction("View more in Downloads page")

    def on_download_started(self):
        self.download_button.setIcon(QIcon(f"{cwd}/assets/download-red.png"))
        self.download_complete = False

    def on_download_finished(self):
        self.download_button.setIcon(QIcon(f"{cwd}/assets/download-green.png"))
        self.download_complete = True

    def on_download_button_clicked(self):
        if self.download_complete:
            self.resetColor.emit()
            self.download_button.setIcon(QIcon(f"{cwd}/assets/download.png"))
            self.download_complete = False 
        a=cwd.replace("\\", "/")
        self.web_view.setUrl(QUrl(f"file:///{a}/sites/downloads.html"))

    def navigate_to_url(self):
        q = QUrl(self.url_bar.text())
        b = cwd.replace("\\","/")
        c = self.url_bar.text().replace("blobben://","")
        if self.url_bar.text().startswith("about:"):
            q = QUrl(f"file:///{b}/sites/aboutblank.html")
        if self.url_bar.text() == "blobben://":
            q = QUrl(f"file:///{b}/sites/home.html")
        elif self.url_bar.text().startswith("blobben://"):
            q = QUrl(f"file:///{b}/sites/{c}" if self.url_bar.text().endswith(".html") else f"file:///{b}/sites/{c}.html")
        if q.scheme() == "":
            if not self.url_bar.text() == "":
                q = QUrl(f"https://www.bing.com/search?q={self.url_bar.text()}")
            else:
                q = QUrl(f"file:///{b}/sites/aboutblank.html")
        self.web_view.setUrl(q)

    def update_url(self, q):
        b = cwd.replace("\\","/")
        a=f"file:///{b}/sites/".lower()
        c = q.toString().lower().replace(a,"blobben://")
        if a.lower() in q.toString().lower():
            self.url_bar.setText(f"{c}")
            if self.url_bar.text().endswith(".html"):
                self.url_bar.setText(self.url_bar.text().replace(".html",""))
        else:
            self.url_bar.setText(q.toString())


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Blobben v{version}")
        self.setWindowIcon(QIcon(f"{cwd}/assets/icon.png"))

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)
        self.cookie_file = f"{cwd}/cache/cookies.json"
        self.load_cookies()
        if not os.path.exists(self.cookie_file):
            os.makedirs(f"{cwd}/cache/",exist_ok=True)
            with open(self.cookie_file, "w") as f:
                f.write(r"{}")

        if not os.path.exists(f"{cwd}/cache/downloads.json"):
            os.makedirs(f"{cwd}/cache/",exist_ok=True)
            with open(f"{cwd}/cache/downloads.json", "w") as f:
                f.write(r"[]")

        # Set up persistent storage for cookies and other web data
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.setCachePath(f"{cwd}/cache")
        self.profile.setPersistentStoragePath(f"{cwd}/cache/persistent")
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setHttpCacheMaximumSize(100 * 1024 * 1024)  # 100 MB

        # Set up cookie store debugging
        self.cookie_store = self.profile.cookieStore()
        self.cookie_store.cookieAdded.connect(self.on_cookie_added)
        self.cookie_store.cookieRemoved.connect(self.on_cookie_removed)

        self.cookies = self.load_cookies()

        # Add new tab button
        self.tabs.setCornerWidget(QPushButton("+", clicked=self.add_new_tab))

        self.download_manager = DownloadManager(self)
        self.download_manager.downloadStarted.connect(self.on_download_started)
        self.download_manager.downloadFinished.connect(self.on_download_finished)
        self.profile.downloadRequested.connect(self.download_manager.add_download)

        self.add_new_tab()
        self.showMaximized()
        self.apply_cookies()
    def on_download_started(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, Toolbar):
                tab.download_button.setIcon(QIcon(f"{cwd}/assets/download_red.png"))

    def on_download_finished(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, Toolbar):
                tab.download_button.setIcon(QIcon(f"{cwd}/assets/download_green.png"))
    def update_download_menu(self, downloads):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, Toolbar):
                tab.update_download_menu(downloads)
                tab.reset_download_icon()
            
    def on_cookie_added(self, cookie):
        self.cookies[cookie.domain()] = self.cookies.get(cookie.domain(), {})
        self.cookies[cookie.domain()][cookie.name().data().decode()] = {
            'value': cookie.value().data().decode(),
            'path': cookie.path(),
            'expiration': cookie.expirationDate().toString(Qt.DateFormat.ISODate) if cookie.expirationDate().isValid() else None,
            'secure': cookie.isSecure(),
            'httpOnly': cookie.isHttpOnly()
        }
        self.save_cookies()

    def on_cookie_removed(self, cookie):
        domain = cookie.domain()
        name = cookie.name().data().decode()
        if domain in self.cookies and name in self.cookies[domain]:
            del self.cookies[domain][name]
            if not self.cookies[domain]:
                del self.cookies[domain]
        self.save_cookies()

    def save_cookies(self):
        with open(self.cookie_file, 'w') as f:
            json.dump(self.cookies, f, indent=4)

    def load_cookies(self):
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file, 'r') as f:
                return json.load(f)
        return {}

    def apply_cookies(self):
        for domain, cookies in self.cookies.items():
            for name, data in cookies.items():
                cookie = QNetworkCookie(
                    QByteArray(name.encode()),
                    QByteArray(data['value'].encode())
                )
                cookie.setDomain(domain)
                cookie.setPath(data['path'])
                if data['expiration']:
                    cookie.setExpirationDate(QDateTime.fromString(data['expiration'], Qt.DateFormat.ISODate))
                cookie.setSecure(data['secure'])
                cookie.setHttpOnly(data['httpOnly'])
                self.cookie_store.setCookie(cookie)

    def closeEvent(self, event):
        self.save_cookies()
        super().closeEvent(event)

    def resetColors(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, Toolbar):
                tab.download_button.setIcon(QIcon(f"{cwd}/assets/download.png"))

    def add_new_tab(self, qurl=None):
        if qurl is None or isinstance(qurl,bool):
            urlcwd = cwd.replace("\\","/")
            qurl = QUrl.fromLocalFile(f"{cwd}/sites/home.html")

        toolbar = Toolbar(self)
        toolbar.resetColor.connect(self.resetColors)
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
    if os.name == "nt":
        import ctypes
        if sys.argv[0].endswith("py"):
            myappid = f'app.qwertz.blobben.{version}'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    window = Browser()
    window.show()
    sys.exit(app.exec())