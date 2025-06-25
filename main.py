import socket
import sys, os, json, subprocess
import threading
from PyQt6.QtCore import QUrl, QSize, QDateTime, Qt, QByteArray, QObject, pyqtSignal, QTimer, QFileSystemWatcher
from PyQt6.QtWidgets import QApplication, QMainWindow, QToolBar, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QFrame, QLabel, QProgressBar, QToolButton, QMenu, QTextEdit, QSplitter, QSplitter, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineDownloadRequest
from PyQt6.QtGui import QIcon, QFont, QAction, QPalette, QColor
from PyQt6.QtWebEngineCore import QWebEngineUrlScheme, QWebEngineProfile, QWebEngineCookieStore
from PyQt6.QtNetwork import QNetworkCookie, QNetworkProxy
import sites

# <a href="https://www.flaticon.com/free-icons/return" title="return icons">Return icons created by Kiranshastry - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/reload" title="reload icons">Reload icons created by Uniconlabs - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/home" title="home icons">Home icons created by Freepik - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/save" title="save icons">Save icons created by Bharat Icons - Flaticon</a>
# <a href="https://www.flaticon.com/free-icons/settings" title="settings icons">Settings icons created by logisstudio - Flaticon</a>

cwd = os.path.dirname(os.path.abspath(sys.argv[0]))
version = "0.3"
# Path to settings.json served by the built-in HTTP backend so both the
# HTML pages and the Qt application read/write the same file.
SETTINGS_PATH = f"{cwd}/sites/settings.json"

def load_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not load settings: {e}")
        # Default settings if file is missing or invalid
        return {
            "themeColor": "",  # empty means default (light)
            "darkMode": False,
            "forceHttps": False,
            "useProxy": False,
            "proxyType": "socks5h",
            "proxyIP": "127.0.0.1",
            "proxyPort": 1080,
            "startPage": "home",
            "customStartUrl": "",
            "homeLocation": "home",
            "customHomeUrl": "",
            "closeTabWarning": False,
            "restoreTabs": False,
            "downloadPrompt": True,
            "closeWarning": True  # Warn before closing browser
        }

def apply_proxy_settings(settings):
    if settings.get("useProxy"):
        proxy_type = settings.get("proxyType", "socks5h")
        proxy_ip = settings.get("proxyIP", "127.0.0.1")
        proxy_port = settings.get("proxyPort", 1080)
        # Map to Chromium's expected proxy scheme
        scheme = "socks5" if proxy_type == "socks5" else "socks5h"
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"--proxy-server={scheme}://{proxy_ip}:{proxy_port}"
        # Also update QtNetwork proxy immediately (useful for runtime changes)
        QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.ProxyType.Socks5Proxy, proxy_ip, proxy_port))
        print(f"Proxy enabled: {os.environ['QTWEBENGINE_CHROMIUM_FLAGS']}")
    else:
        # Remove proxy if not used
        os.environ.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)
        QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        print("Proxy disabled.")

HOST = "127.0.0.1"
PORT = 58352  # Pick a port not in use

def send_url_to_running_instance(url):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))
        client.send(url.encode())
        client.close()
        return True
    except Exception:
        return False
    
class DownloadManager(QObject):
    downloadStarted = pyqtSignal()
    downloadFinished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloads = []
        self.download_history_file = f"{cwd}/cache/downloads.json"
        self.load_download_history()

    def add_download(self, download: QWebEngineDownloadRequest):
        # Get the user's downloads directory and ensure proper path format
        downloads_dir = os.path.abspath(os.path.expanduser("~/Downloads"))
        download.setDownloadDirectory(downloads_dir)
        
        download_info = {
            'id': len(self.downloads),
            'url': download.url().toString(),
            'filename': download.downloadFileName(),
            'path': os.path.normpath(os.path.join(downloads_dir, download.downloadFileName())),
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
        # Update both received bytes and total bytes (in case size was unknown initially)
        self.downloads[download_id]['received'] = download.receivedBytes()
        self.downloads[download_id]['size'] = download.totalBytes()
        self.save_download_history()  # Save after each progress update

    def update_state(self, download_id, download):
        # Update final size and received bytes
        self.downloads[download_id]['size'] = download.totalBytes()
        self.downloads[download_id]['received'] = download.receivedBytes()
        
        if download.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.downloads[download_id]['status'] = 'Completed'
            # Ensure received matches total size for completed downloads
            if self.downloads[download_id]['size'] > 0:
                self.downloads[download_id]['received'] = self.downloads[download_id]['size']
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
        # Only accept messages from our downloads page
        if not sourceID.startswith("http://localhost:7859/downloads.html"):
            return
            
        if message.startswith("Open in explorer$"):
            print(message)
            path = message.split("$")[1]
            self.show_in_explorer(path)

    def show_in_explorer(self, path):
        print(path)
        try:
            # Normalize path and ensure proper format
            path = os.path.normpath(path.replace('/', os.path.sep))
            dir_path = os.path.dirname(os.path.abspath(path))
            
            # Create directory if it doesn't exist (Downloads folder might be missing)
            os.makedirs(dir_path, exist_ok=True)
            
            if os.name == 'nt':  # Windows
                # Use explorer.exe to ensure the folder opens
                subprocess.run(['explorer', dir_path], check=False)
            elif os.name == 'posix':  # macOS and Linux
                try:
                    subprocess.run(['open', dir_path], check=False)
                except:
                    subprocess.run(['xdg-open', dir_path], check=False)
            
            print(f"Opening directory: {dir_path}")
        except Exception as e:
            print(f"Error opening folder: {e}")

    # Handle links that request a new window (e.g., target="_blank", Bing ads etc.)
    def createWindow(self, _type):  # noqa: N802 (Qt override)
        # Traverse up the parents to find the Browser instance
        parent = self.parent()
        browser = None
        while parent is not None and browser is None:
            if isinstance(parent, Browser):
                browser = parent
            parent = parent.parent()

        if browser is None:
            return None  # fallback – block

        # Add a new tab and return its page so the navigation happens there
        browser.add_new_tab()
        new_toolbar = browser.tabs.currentWidget()
        if isinstance(new_toolbar, Toolbar):
            return new_toolbar.web_view.page()
        return None

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
        self.home_button.clicked.connect(self.go_home)
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

        # Source code button
        self.source_button = QPushButton()
        self.source_button.setIcon(QIcon(f"{cwd}/assets/source.png"))
        self.source_button.setFixedSize(QSize(35, 35))
        self.source_button.setIconSize(QSize(25, 25))
        self.source_button.clicked.connect(self.toggle_source_view)
        self.toolbar.addWidget(self.source_button)
        # Source code button
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(f"{cwd}/assets/settings.png"))
        self.settings_button.setFixedSize(QSize(35, 35))
        self.settings_button.setIconSize(QSize(25, 25))
        self.settings_button.clicked.connect(lambda: self.web_view.setUrl(QUrl(f"http://localhost:7859/settings.html")))
        self.toolbar.addWidget(self.settings_button)

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
        self.home_button.clicked.connect(self.go_home)
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
        self.web_view.setUrl(QUrl(f"http://localhost:7859/downloads.html"))

    def go_home(self):
        # Use home location setting
        home_location = current_settings.get("homeLocation", "home")
        if home_location == "startPage":
            # Use start page setting
            start_page = current_settings.get("startPage", "home")
            if start_page == "blank":
                self.web_view.setUrl(QUrl(f"http://localhost:7859/aboutblank.html"))
            elif start_page == "custom":
                custom_url = current_settings.get("customStartUrl", "")
                if custom_url:
                    self.web_view.setUrl(QUrl(custom_url))
                else:
                    self.web_view.setUrl(QUrl(f"http://localhost:7859/home.html"))
            else:  # default to home
                self.web_view.setUrl(QUrl(f"http://localhost:7859/home.html"))
        elif home_location == "custom":
            custom_url = current_settings.get("customHomeUrl", "")
            if custom_url:
                self.web_view.setUrl(QUrl(custom_url))
            else:
                self.web_view.setUrl(QUrl(f"http://localhost:7859/home.html"))
        else:  # default to home page
            self.web_view.setUrl(QUrl(f"http://localhost:7859/home.html"))

    def navigate_to_url(self):
        print("navigating")
        q = QUrl(self.url_bar.text())
        
        b = cwd.replace("\\","/")
        c = self.url_bar.text().replace("blobben://","")
        if self.url_bar.text().startswith("about:"):
            q = QUrl(f"http://localhost:7859/aboutblank.html")
        if self.url_bar.text() == "blobben://":
            q = QUrl(f"http://localhost:7859//home.html")
        elif self.url_bar.text().startswith("blobben://"):
            q = QUrl(f"http://localhost:7859/{c}" if self.url_bar.text().endswith(".html") else f"http://localhost:7859/{c}.html")
        if q.scheme() == "":
            if not self.url_bar.text() == "":
                q = QUrl(f"https://www.bing.com/search?q={self.url_bar.text()}")
            else:
                q = QUrl(f"http://localhost:7859/aboutblank.html")

        # Force HTTPS upgrade if enabled in settings
        try:
            if current_settings.get("forceHttps") and q.scheme() == "http":
                q = QUrl(q.toString().replace("http://", "https://", 1))
        except Exception:
            pass

        print(q)
        self.web_view.setUrl(q)

    def update_url(self, q):
        b = cwd.replace("\\","/")
        a=f"http://localhost:7859/".lower()
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

        # Clear downloads on startup
        downloads_file = f"{cwd}/cache/downloads.json"
        try:
            os.makedirs(os.path.dirname(downloads_file), exist_ok=True)
            with open(downloads_file, 'w') as f:
                json.dump([], f)
        except Exception as e:
            print(f"Error clearing downloads: {e}")

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
        self.profile.downloadRequested.connect(self.handle_download_request)

        # Restore tabs if enabled
        if current_settings.get("restoreTabs", False):
            try:
                with open(f"{cwd}/cache/tabs.json", "r") as f:
                    saved_tabs = json.load(f)
                    for url in saved_tabs:
                        self.add_new_tab(QUrl(url))
            except Exception:
                pass  # File doesn't exist or is invalid
        
        if not self.tabs.count():  # No tabs restored, add default
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
        # Check if warning is needed
        if current_settings.get("closeWarning", True):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Close Blobben?")
            msg.setInformativeText("Are you sure you want to close the browser?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg.exec() == QMessageBox.StandardButton.No:
                event.ignore()
                return

        # Save open tabs if enabled
        if current_settings.get("restoreTabs", False):
            tabs = []
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                if isinstance(widget, Toolbar):
                    url = widget.web_view.url().toString()
                    # Don't save internal pages
                    if not url.startswith("http://localhost:7859/"):
                        tabs.append(url)
            with open(f"{cwd}/cache/tabs.json", "w") as f:
                json.dump(tabs, f)
        
        self.save_cookies()
        super().closeEvent(event)

    def resetColors(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, Toolbar):
                tab.download_button.setIcon(QIcon(f"{cwd}/assets/download.png"))

    def add_new_tab(self, qurl=None):
        if qurl is None or isinstance(qurl,bool):
            # Use start page setting
            start_page = current_settings.get("startPage", "home")
            if start_page == "blank":
                qurl = QUrl(f"http://localhost:7859/aboutblank.html")
            elif start_page == "custom":
                custom_url = current_settings.get("customStartUrl", "")
                if custom_url:
                    qurl = QUrl(custom_url)
                else:
                    qurl = QUrl(f"http://localhost:7859/home.html")
            else:  # default to home
                qurl = QUrl(f"http://localhost:7859/home.html")
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
        
        # Check if warning is needed
        if current_settings.get("closeTabWarning", True):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Close this tab?")
            msg.setInformativeText("Are you sure you want to close this tab?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg.exec() == QMessageBox.StandardButton.No:
                return

        self.tabs.removeTab(i)

    def update_tab_title(self, index, title):
        self.tabs.setTabText(index, title)

    def update_tab_icon(self, index, icon):
        self.tabs.setTabIcon(index, icon)

    def handle_download_request(self, download):
        if current_settings.get("downloadPrompt", True):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setText("Download File")
            msg.setInformativeText(f"Do you want to download {download.downloadFileName()}?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg.exec() == QMessageBox.StandardButton.No:
                download.cancel()
                return
        
        self.download_manager.add_download(download)

# ---------------------------
#  Qt Dark-Theme helper
# ---------------------------
def apply_theme(app, color_hex: str | None, default_palette: QPalette | None = None):
    """Apply a custom palette using the provided base color in hex; if None/empty revert to default."""
    if not color_hex:
        if default_palette is not None:
            app.setPalette(default_palette)
            for w in QApplication.allWidgets():
                w.update()
        return

    app.setStyle("Fusion")
    base = QColor(color_hex)
    # Determine appropriate text color based on luminance
    luminance = 0.299 * base.red() + 0.587 * base.green() + 0.114 * base.blue()
    text_col = Qt.GlobalColor.black if luminance > 186 else Qt.GlobalColor.white

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, base)
    palette.setColor(QPalette.ColorRole.WindowText, text_col)
    palette.setColor(QPalette.ColorRole.Base, base.darker(120))
    palette.setColor(QPalette.ColorRole.AlternateBase, base.darker(110))
    palette.setColor(QPalette.ColorRole.ToolTipBase, text_col)
    palette.setColor(QPalette.ColorRole.ToolTipText, text_col)
    palette.setColor(QPalette.ColorRole.Text, text_col)
    palette.setColor(QPalette.ColorRole.Button, base.darker(105))
    palette.setColor(QPalette.ColorRole.ButtonText, text_col)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, text_col)
    app.setPalette(palette)
    for w in QApplication.allWidgets():
        w.update()

if __name__ == "__main__":
    # Load user settings and apply proxy flags before the Qt engine starts
    settings = load_settings()
    apply_proxy_settings(settings)

    url = sys.argv[1] if len(sys.argv) > 1 else None
    if url and send_url_to_running_instance(url):
        sys.exit(0)
    if os.name == "nt":
        import ctypes
        if sys.argv[0].endswith("py"):
            myappid = f'app.qwertz.blobben.{version}'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        # Set up the IPC server
    app = QApplication(sys.argv)
    # Apply dark theme if enabled
    default_palette = QPalette(app.palette())
    apply_theme(app, settings.get("themeColor"), default_palette)

    # ---------------------------
    #  Settings hot-reloader
    # ---------------------------
    current_settings = settings.copy()  # mutable dict we will update in place

    def on_settings_updated():
        try:
            new_settings = load_settings()
        except Exception:
            return  # malformed file, ignore

        # --- Dark mode toggle for internal pages ---
        old_dark = current_settings.get("darkMode")
        new_dark = new_settings.get("darkMode")
        if new_dark != old_dark:
            js_toggle = f'document.body.classList.toggle("dark", {str(bool(new_dark)).lower()});'
            for i in range(window.tabs.count()):
                widget = window.tabs.widget(i)
                if isinstance(widget, Toolbar):
                    widget.web_view.page().runJavaScript(js_toggle)

        # --- Theme color change ---
        old_color = current_settings.get("themeColor")
        new_color = new_settings.get("themeColor")
        if new_color != old_color:
            apply_theme(app, new_color, default_palette)

        # --- Proxy toggle / change ---
        if (new_settings.get("useProxy") != current_settings.get("useProxy") or
            any(new_settings.get(k) != current_settings.get(k) for k in ("proxyType","proxyIP","proxyPort"))):
            if new_settings.get("useProxy"):
                proxy_type = new_settings.get("proxyType", "socks5h")
                qtype = QNetworkProxy.ProxyType.Socks5Proxy if proxy_type.startswith("socks5") else QNetworkProxy.ProxyType.Socks5Proxy
                proxy = QNetworkProxy(qtype, new_settings.get("proxyIP", "127.0.0.1"), new_settings.get("proxyPort", 1080))
            else:
                proxy = QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)
            QNetworkProxy.setApplicationProxy(proxy)
            # Reload pages so new proxy takes effect
            for i in range(window.tabs.count()):
                widget = window.tabs.widget(i)
                if isinstance(widget, Toolbar):
                    widget.web_view.reload()

        # Re-add path in case the file was replaced (QFileSystemWatcher limitation)
        if SETTINGS_PATH not in watcher.files():
            watcher.addPath(SETTINGS_PATH)

        # update stored settings dict in place to avoid global/nonlocal rebinding
        current_settings.clear()
        current_settings.update(new_settings)

    watcher = QFileSystemWatcher([SETTINGS_PATH])
    watcher.fileChanged.connect(lambda _: on_settings_updated())

    window = Browser()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    server.setblocking(False)
    def startBackend():
        sites.backend(cwd)
        os.chdir(cwd)
    threading.Thread(target=startBackend, daemon=True).start()
    def check_for_new_urls():
            try:
                conn, _ = server.accept()
                data = conn.recv(1024).decode()
                if data:
                    window.add_new_tab(QUrl(data))
                conn.close()
            except BlockingIOError:
                pass  # No connection, just continue

    # Use QTimer to poll the socket every 100ms
    timer = QTimer()
    timer.timeout.connect(check_for_new_urls)
    timer.start(100)
    window.show()
    if url:
        window.add_new_tab(QUrl(url))
    sys.exit(app.exec())