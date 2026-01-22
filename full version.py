from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock, mainthread
from kivy.properties import ListProperty, StringProperty, ObjectProperty
import requests
import os
import time
import base64
from bs4 import BeautifulSoup
import json
from kivy.logger import Logger
import threading
from playwright.sync_api import sync_playwright

# Configuration
SAVE_DIR = "downloaded_images"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

TEMP_IMAGE_DIR = os.path.join(SAVE_DIR, "temp_images")
if not os.path.exists(TEMP_IMAGE_DIR):
    os.makedirs(TEMP_IMAGE_DIR)

Window.size = (1000, 650)

# Site configurations and handlers
SITES = {
    "Danbooru": {
        "url": "https://danbooru.donmai.us/posts.json",
        "auth": False,
        "page_param": "page",
        "type": "json",
        "handler": lambda data: [{"url": post.get("file_url") or post.get("large_file_url"), "tags": post.get("tag_string", "").split()} for post in data],
        "query_param": "tags",
        "default_query": ""
    },
    "Furbooru": {
        "url": "https://furbooru.org/api/v1/json/search",
        "auth": False,
        "page_param": "page",
        "type": "json",
        "handler": lambda data: [{"url": image["representations"]["medium"], "tags": image.get("tags", [])} for image in data.get("images", [])],
        "user_agent": "FurbooruViewer/1.0",
        "per_page": 12,
        "query_param": "q",
        "default_query": "furry"
    },
    "e621": {
        "url": "https://e621.net/posts.json",
        "auth": False,
        "page_param": "page",
        "type": "json",
        "handler": lambda data: [{"url": post.get("sample", {}).get("url") or post.get("file", {}).get("url"), "tags": post.get("tags", {}).get("general", [])} for post in data.get("posts", [])],
        "user_agent": "E621Viewer/1.0 (by YourUsernameHere)",
        "query_param": "tags",
        "default_query": ""
    },
    "e926": {
        "url": "https://e926.net/posts.json",
        "auth": False,
        "page_param": "page",
        "type": "json",
        "handler": lambda data: [{"url": post.get("sample", {}).get("url") or post.get("file", {}).get("url"), "tags": post.get("tags", {}).get("general", [])} for post in data.get("posts", [])],
        "user_agent": "E926Viewer/1.0 (by YourUsernameHere)",
        "query_param": "tags",
        "default_query": ""
    },
    "Yande.re": {
        "url": "https://yande.re/post.json",
        "auth": False,
        "page_param": "page",
        "type": "json",
        "handler": lambda data: [{"url": post.get("file_url") or post.get("sample_url"), "tags": post.get("tags", "").split()} for post in data],
        "query_param": "tags",
        "default_query": ""
    },
    "Rule34": {
        "url": "https://rule34.xxx/index.php?page=dapi&s=post&q=index&json=1",
        "auth": False,
        "page_param": "pid",
        "type": "json",
        "handler": lambda data: [{"url": post.get("file_url") or post.get("sample_url"), "tags": post.get("tags", "").split()} for post in data],
        "query_param": "tags",
        "default_query": "",
        "limit_param": "limit",
        "limit_value": 20
    },
    "Safebooru": {
        "url": "https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1",
        "auth": False,
        "page_param": "pid",
        "type": "json",
        "handler": lambda data: [{"url": post.get("file_url") or post.get("sample_url"), "tags": post.get("tags", "").split()} for post in data],
        "query_param": "tags",
        "default_query": "",
        "limit_param": "limit",
        "limit_value": 20
    },
    "Zerochan": {
        "url": "https://www.zerochan.net/",
        "auth": False,
        "page_param": "p",
        "query_param": "",
        "type": "html",
        "handler": lambda soup: [
            {
                "url": (img.get('data-src') or img.get('src')).replace('240', 'full'),
                "tags": [img.get('alt', 'No tags')]
            }
            for img in soup.select('ul#thumbs2 img')
            if img.get('src') or img.get('data-src')
        ],
        "default_query": "Furry"
    },
    "Konachan": {
        "url": "https://konachan.com/post.json",
        "auth": False,
        "page_param": "page",
        "type": "json",
        "handler": lambda data: [{"url": post.get("file_url") or post.get("sample_url"), "tags": post.get("tags", "").split()} for post in data],
        "query_param": "tags",
        "default_query": "",
        "limit_param": "limit",
        "limit_value": 20
    },
    "Gelbooru": {
        "url": "https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1",
        "auth": True,
        "page_param": "pid",
        "type": "json",
        "handler": lambda data: [{"url": post.get("file_url") or post.get("sample_url"), "tags": post.get("tags", "").split()} for post in data.get("post", [])],
        "query_param": "tags",
        "default_query": "",
        "limit_param": "limit",
        "limit_value": 20
    },
    "XBooru": {
        "url": "https://xbooru.com/index.php?page=dapi&s=post&q=index&json=1",
        "auth": False,
        "page_param": "pid",
        "type": "json",
        "handler": lambda data: [{"url": post.get("file_url") or post.get("sample_url"), "tags": post.get("tags", "").split()} for post in data], # Corrected handler
        "query_param": "tags",
        "default_query": "",
        "limit_param": "limit",
        "limit_value": 20
    },
"Tbib": {
    "url": "https://tbib.org/index.php?page=dapi&s=post&q=index&json=1",
    "auth": False,
    "page_param": "pid",
    "type": "json",
    "query_param": "tags",
    "default_query": "",
    "limit_param": "limit",
    "limit_value": 20,
    "handler": lambda data: [
        {
            "url": f"https://tbib.org/images/{post['directory']}/{post['image']}",
            "tags": post.get("tags", "").split()
        }
        for post in data
        if post.get("directory") and post.get("image")
    ]
},
    "allthefallen": {
        "url": "https://booru.allthefallen.moe/posts.json",
        "auth": True,
        "page_param": "page",
        "type": "json",
        "handler": lambda data: [{"url": post.get("file_url") or post.get("large_file_url") or post.get("sample_url"), "tags": post.get("tag_string", "").split()} for post in data],
        "query_param": "tags",
        "default_query": "furry",
        "limit_param": "limit",
        "limit_value": 20
    }
}

class ImageItem(BoxLayout):
    def __init__(self, url, tags, app, **kwargs):
        super(ImageItem, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 220
        self.spacing = 5
        self.padding = 5
        self.url = url
        self.app = app
        self.temp_filepath = None

        self.placeholder_label = Label(text="Loading Image...", size_hint=(1, None), height=150,
                                       halign='center', valign='middle', color=(0.7, 0.7, 0.7, 1))
        self.add_widget(self.placeholder_label)

        self.image = AsyncImage(size_hint=(1, None), height=150, allow_stretch=True, keep_ratio=True, mipmap=True)
        self.image.bind(on_load=self.on_image_loaded)
        self.image.bind(on_error=self.on_image_error)

        if self.app.current_site == "allthefallen" and self.app.allthefallen_cookies:
            Logger.info(f"ImageItem: Attempting to load {self.url} with allthefallen cookies.")
            threading.Thread(target=self._load_image_with_cookies).start()
        else:
            Logger.info(f"ImageItem: Setting AsyncImage source directly to {self.url}.")
            self.image.source = self.url

        tag_text = ", ".join(tags[:3])[:50] if tags else "No tags"
        self.tags_label = Label(text=tag_text, size_hint_y=None, height=40, text_size=(self.width, None), halign='center')
        self.add_widget(self.tags_label)

        self.download_button = Button(text="Download", size_hint_y=None, height=30)
        self.download_button.bind(on_press=self.download_image)
        self.add_widget(self.download_button)

    def _load_image_with_cookies(self):
        """Manually fetches image data with cookies and sets AsyncImage source to a temp file."""
        try:
            Logger.debug(f"_load_image_with_cookies: Fetching {self.url} using requests with cookies.")
            
            current_cookies = {}
            if self.app.current_site == "allthefallen" and self.app.allthefallen_cookies:
                current_cookies = self.app.allthefallen_cookies

            response = requests.get(self.url, timeout=10, cookies=current_cookies)
            response.raise_for_status()

            ext = self.url.split('.')[-1].split('?')[0]
            if not ext or len(ext) > 5:
                ext = "jpg"
            self.temp_filepath = os.path.join(TEMP_IMAGE_DIR, f"temp_{int(time.time() * 1000)}_{os.getpid()}.{ext}")
            
            Logger.debug(f"_load_image_with_cookies: Saving to temp file: {self.temp_filepath}")
            with open(self.temp_filepath, 'wb') as f:
                f.write(response.content)
            
            Clock.schedule_once(lambda dt: self._set_image_source_from_temp(self.temp_filepath), 0)

        except requests.RequestException as e:
            Logger.error(f"Failed to load image with cookies from {self.url}: {e}")
            Clock.schedule_once(lambda dt: self.on_image_error(self.image, f"Network Error: {e}"), 0)
        except Exception as e:
            Logger.error(f"Unexpected error loading image with cookies from {self.url}: {e}")
            Clock.schedule_once(lambda dt: self.on_image_error(self.image, f"General Error: {e}"), 0)

    @mainthread
    def _set_image_source_from_temp(self, filepath):
        """Sets the AsyncImage source to the local temporary file."""
        Logger.debug(f"_set_image_source_from_temp: Setting image source to {filepath}")
        self.image.source = filepath
        self.image.reload()

    @mainthread
    def on_image_loaded(self, instance):
        """Called when AsyncImage successfully loads the image."""
        Logger.debug(f"Image loaded callback: {instance.source}")
        if self.placeholder_label in self.children:
            self.remove_widget(self.placeholder_label)
        if self.image not in self.children:
            self.add_widget(self.image, index=2)
        Logger.info(f"Image loaded: {self.url} (from {instance.source})")

    @mainthread
    def on_image_error(self, instance, error):
        """Called when AsyncImage fails to load the image."""
        Logger.error(f"Image load error for {self.url} (source: {instance.source}): {error}")
        if self.placeholder_label in self.children:
            self.placeholder_label.text = "Image Failed to Load"
        else:
            if self.image in self.children:
                self.remove_widget(self.image)
            self.add_widget(Label(text="Image Failed to Load", size_hint=(1, None), height=150,
                                  halign='center', valign='middle', color=(1, 0, 0, 1)), index=2)
        if self.temp_filepath and os.path.exists(self.temp_filepath):
            try:
                os.remove(self.temp_filepath)
                Logger.debug(f"Cleaned up temporary file: {self.temp_filepath}")
            except OSError as e:
                Logger.warning(f"Could not remove temporary file {self.temp_filepath}: {e}")

    def download_image(self, instance):
        threading.Thread(target=self._do_download).start()

    def _do_download(self):
        try:
            download_headers = {}
            download_cookies = {}
            if self.app.current_site == "allthefallen" and self.app.allthefallen_cookies:
                download_cookies = self.app.allthefallen_cookies

            Logger.info(f"Downloading image from {self.url} with cookies: {bool(download_cookies)}")
            response = requests.get(self.url, timeout=10, headers=download_headers, cookies=download_cookies)
            response.raise_for_status()

            filename = f"image_{int(time.time())}.{self.url.split('.')[-1].split('?')[0]}"
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            Clock.schedule_once(lambda dt: setattr(self.app, 'status_message', f"Downloaded to {filepath}"), 0)
            Logger.info(f"Image downloaded to {filepath}")
        except requests.RequestException as e:
            Clock.schedule_once(lambda dt: setattr(self.app, 'status_message', f"Download failed: {e}"), 0)
            Logger.error(f"Download failed: {e}")
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.app, 'status_message', f"An error occurred during download: {e}"), 0)
            Logger.error(f"An error occurred during download: {e}")

class LoginPopup(BoxLayout):
    def __init__(self, app, popup, site_name, **kwargs):
        super(LoginPopup, self).__init__(**kwargs)
        self.app = app
        self.popup = popup
        self.site_name = site_name
        self.orientation = 'vertical'
        self.spacing = 10
        self.padding = 10

        self.add_widget(Label(text=f"{site_name} Login"))
        self.username_input = TextInput(text='', hint_text='User ID/Username', multiline=False)
        self.add_widget(self.username_input)
        self.apikey_input = TextInput(text='', hint_text='API Key', password=True, multiline=False)
        self.add_widget(self.apikey_input)
        self.login_button = Button(text="Login", size_hint_y=None, height=40)
        self.login_button.bind(on_press=self.login)
        self.add_widget(self.login_button)
        self.error_label = Label(text='', size_hint_y=None, height=40, color=(1, 0, 0, 1))
        self.add_widget(self.error_label)

    def login(self, instance):
        username = self.username_input.text.strip()
        apikey = self.apikey_input.text.strip()

        if not username or not apikey:
            self.error_label.text = "Please enter both User ID/Username and API key."
            return

        if self.site_name == "Gelbooru" and not username.isdigit():
            self.error_label.text = "Gelbooru User ID must be numeric."
            return

        if self.site_name == "Gelbooru":
            self.app.gelbooru_username = username
            self.app.gelbooru_apikey = apikey
        elif self.site_name == "allthefallen":
            self.app.allthefallen_username = username
            self.app.allthefallen_apikey = apikey
            self.popup.dismiss()
            self.app.verify_allthefallen_antibot()
            return

        self.popup.dismiss()
        self.app.load_images()


class BooruApp(App):
    images = ListProperty([])
    search_text = StringProperty("")
    current_page = 1
    status_message = StringProperty("Ready")
    current_site = StringProperty("Danbooru")

    # Login credentials for Gelbooru
    gelbooru_username = StringProperty("")
    gelbooru_apikey = StringProperty("")

    # Login credentials for allthefallen
    allthefallen_username = StringProperty("")
    allthefallen_apikey = StringProperty("")
    allthefallen_cookies = ObjectProperty({})

    login_popup = ObjectProperty(None)
    current_login_site = StringProperty("")

    def build(self):
        self.layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        top_bar = BoxLayout(size_hint_y=None, height=40)
        self.site_button = Button(text="Site: Danbooru", size_hint=(0.2, 1))
        self.dropdown = DropDown()
        for site in SITES.keys():
            btn = Button(text=site, size_hint_y=None, height=40)
            btn.bind(on_release=lambda btn, site=site: self.select_site(btn, site))
            self.dropdown.add_widget(btn)
        self.site_button.bind(on_release=self.dropdown.open)
        top_bar.add_widget(self.site_button)

        self.search_input = TextInput(text=self.search_text, hint_text="Search...", multiline=False, size_hint=(0.5, 1))
        self.search_input.bind(text=self.on_search_text)
        self.search_button = Button(text="Search", size_hint=(0.2, 1))
        self.search_button.bind(on_press=self.start_search)
        top_bar.add_widget(self.search_input)
        top_bar.add_widget(self.search_button)
        self.layout.add_widget(top_bar)

        self.status_label = Label(text=self.status_message, size_hint_y=None, height=30, color=(0.2, 0.6, 1, 1))
        self.layout.add_widget(self.status_label)

        nav_box = BoxLayout(size_hint_y=None, height=40)
        self.prev_button = Button(text="Previous", size_hint_x=0.3)
        self.prev_button.bind(on_press=self.prev_page)
        nav_box.add_widget(self.prev_button)
        self.page_label = Label(text=f"Page {self.current_page}", size_hint_x=0.4, halign='center')
        nav_box.add_widget(self.page_label)
        self.next_button = Button(text="Next", size_hint_x=0.3)
        self.next_button.bind(on_press=self.next_page)
        nav_box.add_widget(self.next_button)
        self.layout.add_widget(nav_box)

        self.scroll = ScrollView(size_hint=(1, 0.8))
        self.grid = GridLayout(cols=3, spacing=10, size_hint_y=None, padding=10)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        return self.layout

    def select_site(self, btn, site):
        self.current_site = site
        self.dropdown.select(btn.text)
        self.site_button.text = f"Site: {site}"
        self.current_page = 1
        self.search_input.text = ""

        if SITES[site]["auth"]:
            if site == "Gelbooru" and not (self.gelbooru_username and self.gelbooru_apikey):
                self.show_login_popup("Gelbooru")
                return
            elif site == "allthefallen" and not (self.allthefallen_username and self.allthefallen_apikey):
                self.show_login_popup("allthefallen")
                return

        self.load_images()

    def show_login_popup(self, site_name):
        self.current_login_site = site_name
        content = LoginPopup(self, Popup(title=f"{site_name} Login", content=BoxLayout(), size_hint=(0.5, 0.5)), site_name)
        self.login_popup = Popup(title=f"{site_name} Login", content=content, size_hint=(0.5, 0.5))
        self.login_popup.content = content
        
        if site_name == "Gelbooru" and self.gelbooru_username:
            content.username_input.text = self.gelbooru_username
            content.apikey_input.text = self.gelbooru_apikey
        elif site_name == "allthefallen" and self.allthefallen_username:
            content.username_input.text = self.allthefallen_username
            content.apikey_input.text = self.allthefallen_apikey

        self.login_popup.open()

    def start_search(self, instance):
        self.search_text = self.search_input.text.strip()
        site_config = SITES[self.current_site]
        if not self.search_text and not site_config["default_query"]:
            self.status_message = "Please enter search terms"
            return

        if site_config["auth"]:
            if self.current_site == "Gelbooru" and not (self.gelbooru_username and self.gelbooru_apikey):
                self.status_message = "Gelbooru requires login. Please log in first."
                self.show_login_popup("Gelbooru")
                return
            elif self.current_site == "allthefallen":
                if not (self.allthefallen_username and self.allthefallen_apikey):
                    self.status_message = "allthefallen requires login. Please log in first."
                    self.show_login_popup("allthefallen")
                    return
                elif not self.allthefallen_cookies:
                    self.status_message = "allthefallen requires anti-bot verification. Starting verification..."
                    self.verify_allthefallen_antibot()
                    return

        self.current_page = 1
        self.load_images()

    def load_images(self):
        self.status_message = "Loading..."
        self.search_button.disabled = True
        self.prev_button.disabled = True
        self.next_button.disabled = True
        self.grid.clear_widgets()
        threading.Thread(target=self._fetch_images_async).start()

    def _fetch_images_async(self, retries=3):
        images_data = [] # Initialize images_data here
        site_config = SITES[self.current_site]
        url = site_config["url"]
        headers = {"User-Agent": site_config.get("user_agent", "KivyBooruViewer/1.0")}
        page_param = site_config["page_param"]
        per_page = site_config.get("per_page", 20)
        query_param = site_config["query_param"]
        default_query = site_config["default_query"]
        query = self.search_text or default_query

        params = {page_param: self.current_page}
        if site_config.get("limit_param"):
            params[site_config["limit_param"]] = site_config.get("limit_value", per_page)
        if query:
            params[query_param] = query

        session_cookies = {} 
        
        if self.current_site == "Gelbooru" and self.gelbooru_username and self.gelbooru_apikey:
            params.update({"user_id": self.gelbooru_username, "api_key": self.gelbooru_apikey})
        elif self.current_site == "allthefallen" and self.allthefallen_username and self.allthefallen_apikey:
            params.update({"login": self.allthefallen_username, "api_key": self.allthefallen_apikey})
            if self.allthefallen_cookies:
                session_cookies = self.allthefallen_cookies
            else:
                Clock.schedule_once(lambda dt: setattr(self, 'status_message', "allthefallen requires anti-bot verification. Please log in first and verify."), 0)
                Clock.schedule_once(lambda dt: self._enable_controls(), 0)
                return

        try:
            response = None # Initialize response to None
            for attempt in range(retries):
                try:
                    Logger.info(f"Sending request to {url} with params: {params} and cookies: {bool(session_cookies)}")
                    response = requests.get(url, params=params, headers=headers, timeout=15, cookies=session_cookies)
                    response.raise_for_status()
                    if response.status_code == 429:
                        Clock.schedule_once(lambda dt: setattr(self, 'status_message', "Rate limit exceeded. Please try again later."), 0)
                        Logger.error("HTTP 429: Rate limit exceeded")
                        time.sleep(2 ** attempt)
                        continue
                    break # Break loop if successful
                except requests.exceptions.RequestException as e:
                    error_msg = f"Request failed: {e} - Response: {response.text[:500] if response else 'No response'}"
                    Logger.error(error_msg)
                    if attempt == retries - 1:
                        Clock.schedule_once(lambda dt: setattr(self, 'status_message', f"Request failed after multiple retries: {e}"), 0)
                        return # Exit function if max retries reached
                    Clock.schedule_once(lambda dt: setattr(self, 'status_message', f"Request failed. Retrying... (Attempt {attempt+1})"), 0)
                    time.sleep(2 ** attempt)
            else: # This else block runs if the for loop completes without a 'break'
                Clock.schedule_once(lambda dt: setattr(self, 'status_message', "Failed to connect after multiple retries."), 0)
                return

            if not response: # If response is still None, something went very wrong
                Clock.schedule_once(lambda dt: setattr(self, 'status_message', "No response received from API."), 0)
                return

            Logger.info(f"API Response ({self.current_site}): {response.text[:500]}...")
            if not response.text.strip():
                Clock.schedule_once(lambda dt: setattr(self, 'status_message', f"Empty response from {self.current_site}"), 0)
                return

            if site_config["type"] == "json":
                try:
                    data = response.json()
                    if self.current_site == "Gelbooru" and isinstance(data, dict) and "error" in data:
                        Clock.schedule_once(lambda dt: setattr(self, 'status_message', f"Gelbooru Error: {data.get('error', 'Unknown error')}"), 0)
                        Logger.error(f"Gelbooru API Error: {data}")
                        return
                    if self.current_site == "allthefallen" and isinstance(data, dict) and data.get("success") == False:
                        Clock.schedule_once(lambda dt: setattr(self, 'status_message', f"allthefallen Error: {data.get('message', 'Bad credentials or other API error')}"), 0)
                        Logger.error(f"allthefallen API Error: {data}")
                        return

                    images_data = site_config["handler"](data)
                except json.JSONDecodeError as e:
                    Clock.schedule_once(lambda dt: setattr(self, 'status_message', f"JSON Parse Error: {e} - Response: {response.text[:200]}"), 0)
                    Logger.error(f"JSON Parse Error: {e} - Response: {response.text}")
                    return
            elif site_config["type"] == "html":
                soup = BeautifulSoup(response.text, 'html.parser')
                images_data = site_config["handler"](soup)

            Clock.schedule_once(lambda dt: self._update_image_grid(images_data, per_page, site_config.get("limit_value")), 0)

        except Exception as e: # Catch any other unexpected errors
            Clock.schedule_once(lambda dt: setattr(self, 'status_message', f"Error: {str(e)}"), 0)
            Logger.error(f"Unexpected error in _fetch_images_async: {e}")
        finally:
            # This will always execute, regardless of whether an error occurred
            # _enable_controls needs to be passed the context needed for next/prev buttons
            Clock.schedule_once(lambda dt: self._enable_controls(images_data, per_page, site_config.get("limit_value")), 0)


    @mainthread
    def _update_image_grid(self, images_data, per_page, limit_value):
        self.grid.clear_widgets()
        for data in images_data:
            if data.get("url"):
                self.grid.add_widget(ImageItem(data["url"], data["tags"], self))
        self.status_message = f"Found {len(images_data)} results"
        Logger.info(f"Loaded {len(images_data)} images")

    @mainthread
    def _enable_controls(self, images_data=None, per_page=None, limit_value=None):
        self.search_button.disabled = False
        self.prev_button.disabled = self.current_page <= 1

        if images_data is not None and (limit_value is not None or per_page is not None):
            expected_count = limit_value if limit_value is not None else per_page
            self.next_button.disabled = len(images_data) < expected_count
        else:
            # If images_data or expected_count isn't available, default to enabled
            self.next_button.disabled = False

        self.page_label.text = f"Page {self.current_page}"

    def verify_allthefallen_antibot(self):
        self.status_message = "Opening browser for anti-bot verification. Please solve the captcha."
        threading.Thread(target=self._run_playwright_verification).start()

    def _run_playwright_verification(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False, channel="msedge")
                context = browser.new_context()
                page = context.new_page()

                test_url = "https://booru.allthefallen.moe/posts/1"
                Logger.info(f"Navigating to {test_url} for anti-bot verification...")
                page.goto(test_url, wait_until="load", timeout=60000)

                Clock.schedule_once(lambda dt: setattr(self, 'status_message', "Please solve the captcha in the opened browser. Closing in 10 seconds..."), 0)
                time.sleep(10)

                current_cookies = context.cookies()
                allthefallen_cookies_dict = {cookie['name']: cookie['value'] for cookie in current_cookies if "allthefallen.moe" in cookie['domain']}

                if allthefallen_cookies_dict:
                    self.allthefallen_cookies = allthefallen_cookies_dict
                    Logger.info(f"allthefallen anti-bot verification successful. Cookies obtained.")
                    Clock.schedule_once(lambda dt: setattr(self, 'status_message', "allthefallen verification successful. Loading images..."), 0)
                    Clock.schedule_once(lambda dt: self.load_images(), 0)
                else:
                    Logger.warning("allthefallen anti-bot verification failed: No relevant cookies found.")
                    Clock.schedule_once(lambda dt: setattr(self, 'status_message', "allthefallen verification failed. Please try again."), 0)

                browser.close()

        except Exception as e:
            Logger.error(f"Playwright error during anti-bot verification: {e}")
            Clock.schedule_once(lambda dt: setattr(self.app, 'status_message', f"Anti-bot verification failed: {e}. Please try again."), 0)
        finally:
            # This should be self, not self.app
            Clock.schedule_once(lambda dt: self._enable_controls(), 0)

    def prev_page(self, instance):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_images()

    def next_page(self, instance):
        self.current_page += 1
        self.load_images()

    def on_search_text(self, instance, value):
        self.search_text = value

if __name__ == "__main__":
    from kivy.logger import LOG_LEVELS, Logger
    Logger.setLevel(LOG_LEVELS["debug"])
    BooruApp().run()