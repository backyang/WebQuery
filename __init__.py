# -*- coding: utf-8 -*-
# Copyright: kuangkuang <upday7@163.com>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""
Project : ImageHunter
Created: 12/24/2017
"""
import json
from uuid import uuid4

from PyQt5.QtCore import QUrl, QRect, QSize, Qt, pyqtSignal
from PyQt5.QtGui import *
from PyQt5.QtGui import QImage
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtWidgets import *
from anki.cards import Card
from anki.hooks import addHook
# noinspection PyArgumentList
from anki.lang import _
from anki.notes import Note
from aqt import mw, os
# region Meta classes
from aqt.reviewer import Reviewer
from aqt.utils import tooltip


class _MetaEasyVar(type):
    def __new__(mcs, name, bases, attributes):
        assert isinstance(attributes, dict)
        c = super(_MetaEasyVar, mcs).__new__(mcs, name, bases, attributes)
        return c

    def __getattribute__(cls, item):
        value = super(_MetaEasyVar, cls).__getattribute__(item)
        if callable(value):
            return value
        _val = value
        if _val and (item.endswith("folder") or item.startswith("folder")) or \
                item.endswith("FOLDER") or item.startswith("FOLDER"):
            return cls.ensure_dir(_val)
        return _val

    def ensure_dir(cls, name):
        if not os.path.isdir(name):
            os.makedirs(name)
        return name

    @property
    def profile_folder(cls):
        try:
            return mw.pm.profileFolder()
        except:
            return ''

    @property
    def media_folder(cls):
        try:
            return os.path.join(cls.profile_folder, "collection.media")
        except:
            return ''


class _Vars(metaclass=_MetaEasyVar):
    addon_model_name = __name__.split(".")[0]
    addons_folder = mw.addonManager.addonsFolder()
    this_addon_folder = mw.addonManager.addonsFolder(addon_model_name)
    user_files_folder = os.path.join(this_addon_folder, "user_files")

    @staticmethod
    def addon_config_obj(profile_store):
        return mw.pm.profile if profile_store else mw.addonManager.getConfig(_Vars.addon_model_name)

    addon_config_file = os.path.join(this_addon_folder, "config.json")


class _MetaConfigObj(type):
    """
    Meta class for reading/saving config.json for anki addon
    """
    metas = {}

    # noinspection PyArgumentList
    def __new__(mcs, name, bases, attributes):

        config_dict = {k: attributes[k] for k in attributes.keys() if not k.startswith("_") and k != "Meta"}
        attributes['config_dict'] = config_dict

        for k in config_dict.keys():
            attributes.pop(k)
        c = super(_MetaConfigObj, mcs).__new__(mcs, name, bases, attributes)

        # region Meta properties
        # meta class
        meta = attributes.get('Meta', type("Meta", (), {}))
        # meta values
        setattr(meta, "config_dict", config_dict)
        setattr(meta, "__profile_store__", getattr(meta, "__profile_store__", False))

        _MetaConfigObj.metas[c.__name__] = meta
        # endregion

        if not config_dict:
            return c

        mcs.attributes = attributes  # attributes that is the configuration items

        # get default configuration keys and values from class properties
        if meta.__profile_store__:
            # load to profile data
            # noinspection PyUnresolvedReferences
            addHook('profileLoaded', lambda: c.load_default_profile_var())
        else:
            # create config.json file
            # noinspection PyUnresolvedReferences
            addHook('profileLoaded', lambda: c.load_default_json())
            # reload to profile database
            # addHook('profileLoaded', lambda: c.reload_config_values())

        return c

    def __getattr__(cls, item):
        if item == "meta":
            return _MetaConfigObj.metas[cls.__name__]
        else:
            config_obj = _Vars.addon_config_obj(cls.metas[cls.__name__].__profile_store__)
            return config_obj.get(item)

    def __setattr__(cls, key, value):
        """
        when user set values to addon config obj class, will be passed to anki's addon manager and be saved.
        :param key:
        :param value:
        :return:
        """
        try:
            config_obj = _Vars.addon_config_obj(cls.metas[cls.__name__].__profile_store__)
            config_obj[key] = value
            if not _MetaConfigObj.metas[cls.__name__].__profile_store__:
                mw.addonManager.writeConfig(_Vars.addon_model_name, config_obj)
        except:
            super(_MetaConfigObj, cls).__setattr__(key, value)

    def load_default_json(cls):
        with open(_Vars.addon_config_file, "w", encoding="utf-8") as f:
            json.dump(cls.config_dict, f)

    def load_default_profile_var(cls):
        for k, v in cls.config_dict.items():
            _Vars.addon_config_obj(_MetaConfigObj.metas[cls.__name__].__profile_store__).setdefault(k, v)


# endregion

# region Default Configuration Objects
class Config(metaclass=_MetaConfigObj):
    class Meta:
        __profile_store__ = True

    doc_size = (500, 300)

    image_field_map = {}


class UserConfig(metaclass=_MetaConfigObj):
    class Meta:
        __profile_store__ = False

    load_on_question = True
    provider_url = "https://www.bing.com/images/search?q=%s"


# endregion


class _Page(QWebEnginePage):
    def __init__(self, parent, keyword=None):
        super(_Page, self).__init__(parent)
        self.clicked_img_url = None
        self.keyword = keyword
        self.profile.setHttpUserAgent(
            self.agent)

    @property
    def agent(self):
        return 'Mozilla/5.0 (iPhone; U; CPU like Mac OS X) ' \
               'AppleWebKit/420.1 (KHTML, like Gecko) Version/3.0 Mobile/4A93 '

    @property
    def provider(self):
        return UserConfig.provider_url

    # noinspection PyArgumentList
    def get_url(self):
        return QUrl(self.provider % self.keyword)

    def load(self, keyword):
        self.keyword = keyword
        if not keyword:
            url = QUrl('about:blank')
        else:
            url = self.get_url()
        super(_Page, self).load(url)

    @property
    def profile(self):
        """

        :rtype: QWebEngineProfile
        """
        return super(_Page, self).profile()


class _WebView(QWebEngineView):

    def __init__(self, parent):
        super(_WebView, self).__init__(parent)
        self.qry_page = None

    def add_query_page(self, page):
        if not self.qry_page:
            self.qry_page = page
        self.setPage(self.qry_page)

    def load_page(self):
        if self.qry_page:
            self.qry_page.load()


class ImageLabel(QLabel):
    cropMode = True
    mouse_released = pyqtSignal()

    def __init__(self):
        super(ImageLabel, self).__init__()
        self._image = None

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, img):
        self._image = img
        self.setPixmap(QPixmap.fromImage(img))

    def mouseReleaseEvent(self, event):
        self.crop()
        self.mouse_released.emit()

    def mousePressEvent(self, event):
        print("ImageHolder: " + str(event.pos()))
        self.mousePressPoint = event.pos()
        if self.cropMode:
            if hasattr(self, "currentQRubberBand"):
                self.currentQRubberBand.hide()
            self.currentQRubberBand = QRubberBand(QRubberBand.Rectangle, self)
            self.currentQRubberBand.setGeometry(QRect(self.mousePressPoint, QSize()))
            self.currentQRubberBand.show()

    def mouseMoveEvent(self, event):
        # print("mouseMove: " + str(event.pos()))
        if self.cropMode:
            self.currentQRubberBand.setGeometry(QRect(self.mousePressPoint, event.pos()).normalized())

    def paintEvent(self, event):
        self.painter = QPainter(self)
        self.painter.setPen(QPen(QBrush(QColor(255, 241, 18, 100)), 15, Qt.SolidLine, Qt.RoundCap))
        self.painter.drawImage(0, 0, self.image)
        self.painter.end()

    def crop(self):
        rect = self.currentQRubberBand.geometry()
        self.image = self.image.copy(rect)
        self.setMinimumSize(self.image.size())
        self.resize(self.image.size())
        # QApplication.restoreOverrideCursor()
        self.currentQRubberBand.hide()
        self.repaint()


class WebQueryWidget(QWidget):
    img_saving = pyqtSignal(QImage)

    def add_query_page(self, page):
        self._view.add_query_page(page)
        self.show_view(True)

    def reload(self):
        self._view.reload()

    def __init__(self, parent):
        super(WebQueryWidget, self).__init__(parent)

        # all widgets
        self._view = _WebView(self)
        self.img_lb = ImageLabel()
        self.img_lb.mouse_released.connect(self.cropped)
        self.loading_lb = QLabel()
        self.capture_button = QPushButton('Capture', self)
        self.capture_button.setShortcut(QKeySequence("c"))
        self.view_button = QPushButton('View', self)
        self.view_button.setShortcut(QKeySequence("v"))

        self.capture_button.clicked.connect(self.on_capture)
        self.view_button.clicked.connect(self.on_view)

        # region Save Image Button and Combo Group
        self.img_btn_grp_ly = QHBoxLayout()
        self.save_img_button = QPushButton('Save Img', self)
        self.save_img_button.setShortcut(QKeySequence("s"))
        self.save_img_button.clicked.connect(self.save_img)

        self.combo_cur_fld_nm = QComboBox(self)
        self.combo_cur_fld_nm.clear()

        self.img_btn_grp_ly.addWidget(self.combo_cur_fld_nm)
        self.img_btn_grp_ly.addWidget(self.save_img_button)

        self.show_save_img_button(False)
        # endregion

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.loading_lb, alignment=Qt.AlignCenter)
        self.layout.addWidget(self._view)
        self.layout.addWidget(self.img_lb, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.capture_button)
        self.layout.addWidget(self.view_button)
        self.layout.addItem(self.img_btn_grp_ly)

        self.setLayout(self.layout)

        # Visibles
        self.loading_lb.setVisible(False)
        self.img_lb.setVisible(False)
        self._view.setVisible(False)

        # other slots
        self._view.loadStarted.connect(self.loading_started)
        self._view.loadFinished.connect(self.load_completed)

    def loading_started(self):
        self.img_lb.setVisible(False)
        self.show_view(False)
        self.show_capture(False)
        self.loading_lb.show()

        mv = QMovie(os.path.join(_Vars.this_addon_folder, "loading.gif"))
        mv.setScaledSize(QSize(self._view.size().width() / 2, self._view.size().height() / 4))
        self.loading_lb.setMovie(mv)

        mv.start()

    def load_completed(self, *args):
        self.loading_lb.setVisible(False)
        self.show_view(True)
        self.show_capture(False)

    def show_capture(self, show):
        self.img_lb.setVisible(show)
        self.view_button.setVisible(show)

    def show_view(self, show):
        self._view.setVisible(show)
        self.capture_button.setVisible(show)
        if not show:
            QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
        else:
            QApplication.restoreOverrideCursor()

    def show_save_img_button(self, show):
        self.save_img_button.setVisible(show)
        self.combo_cur_fld_nm.setVisible(self.save_img_button.isVisible())

    def on_capture(self, *args):
        self.img_lb.image = QImage(self.grab(self._view.rect()))
        self.img_lb.setVisible(True)
        self.show_view(False)
        self.show_capture(True)

    def on_view(self, *args):
        self.show_view(True)
        self.show_capture(False)
        self.show_save_img_button(False)
        self.img_lb.setVisible(False)

    def save_img(self, *args):
        self.img_saving.emit(self.img_lb.image)
        self.show_view(True)
        self.show_save_img_button(False)
        self.show_capture(False)

    def cropped(self):
        self.show_save_img_button(True)


class WebQryAddon:

    def __init__(self):
        self.shown = False

        self.pages = [
            _Page(mw),
        ]

        self.web = WebQueryWidget(mw, )
        self.web.setVisible(False)
        self.web.img_saving.connect(self.save_img)
        self.dock = None

        self.pre_loaded = False

        addHook("showQuestion", self.pre_load)
        addHook("showAnswer", self.show_web)
        addHook("deckClosing", self.hide)
        addHook("reviewCleanup", self.hide)

        self.init_menu()

    def init_menu(self):
        action = QAction(mw.form.menuTools)
        action.setText("Web Query")
        action.setShortcut(QKeySequence("ALT+W"))
        mw.form.menuTools.addAction(action)
        action.triggered.connect(self.toggle)

    @property
    def reviewer(self):
        """

        :rtype: Reviewer
        """
        return mw.reviewer

    @property
    def card(self):
        """

        :rtype: Card
        """
        return self.reviewer.card

    @property
    def note(self):
        """

        :rtype: Note
        """
        return self.reviewer.card.note()

    @property
    def word(self):
        if not mw.reviewer:
            return None
        word = self.note.fields[0]
        return word

    def load_pages(self, keyword):
        for page in self.pages:
            page.load(keyword)
            page.loadFinished.connect(lambda s: self.web.reload)

    def add_dock(self, title, w):
        class DockableWithClose(QDockWidget):
            closed = pyqtSignal()

            def closeEvent(self, evt):
                self.closed.emit()
                QDockWidget.closeEvent(self, evt)

            def resizeEvent(self, evt):
                assert isinstance(evt, QResizeEvent)
                Config.doc_size = (evt.size().width(),
                                   evt.size().height())
                super(DockableWithClose, self).resizeEvent(evt)
                evt.accept()

            def sizeHint(self):
                return QSize(Config.doc_size[0], Config.doc_size[1])

        dock = DockableWithClose(title, mw)
        dock.setObjectName(title)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetClosable)
        dock.setWidget(w)
        dock.setContentsMargins(10, 10, 10, 10)
        if mw.width() < 600:
            mw.resize(QSize(600, mw.height()))
        mw.addDockWidget(Qt.RightDockWidgetArea, dock)
        return dock

    def pre_load(self):
        self.show()
        if not self.word:
            return
        self.pre_loaded = False
        if not UserConfig.load_on_question:
            self.hide_web()
        else:
            self.show_web()
            self.pre_loaded = True

    def show_web(self):
        if not self.pre_loaded:
            QApplication.restoreOverrideCursor()
            self.load_pages(self.word)
            self.web.add_query_page(self.pages[0])
            self.web.combo_cur_fld_nm.clear()
            if self.reviewer:
                image_field = Config.image_field_map.get(str(self.note.mid), 1)
                self.web.combo_cur_fld_nm.addItems(self.note.keys())
                self.web.combo_cur_fld_nm.setCurrentIndex(image_field)
                self.web.capture_button.clicked.connect(self.capturing)
                self.web.view_button.clicked.connect(self.capture_complete)
            self.pre_loaded = False

    def capturing(self, *args):
        self.web.combo_cur_fld_nm.currentIndexChanged.connect(self.img_field_changed)

    def capture_complete(self, *args):
        try:
            self.web.combo_cur_fld_nm.currentIndexChanged.disconnect()
        except TypeError:
            pass
        self.web.combo_cur_fld_nm.currentIndexChanged.connect(self.img_field_changed)

    def hide_web(self):
        self.load_pages('')

    def hide(self):
        self.dock.setVisible(False)

    def show(self):
        if not self.dock:
            self.dock = self.add_dock(_('Web Query'), self.web)
            self.dock.closed.connect(self.on_closed)
        self.dock.setVisible(True)

    def toggle(self, on):
        if not self.dock:
            return
        if self.dock.isVisible():
            self.hide()
        else:
            self.show()

    def on_closed(self):
        mw.progress.timer(100, self.hide, False)

    def img_field_changed(self, index):
        if index == -1:
            return
        _mp = Config.image_field_map
        _mp[str(self.note.mid)] = index
        Config.image_field_map = _mp

    def save_img(self, img):
        """

        :type img: QImage
        :return:
        """
        print("Saving Image: {} {}".format(img, "PNG"))
        if not self.reviewer:
            return
        fld_index = self.web.combo_cur_fld_nm.currentIndex()
        anki_label = '<img src="{}">'
        fn = "web_qry_{}_{}.png".format(self.word, uuid4().hex.upper())
        self.note.fields[fld_index] = anki_label.format(fn)
        if img.save(fn):
            self.note.flush()
            self.card.flush()
            tooltip("Saved image to current card: {}".format(fn), 5000)
        # self.reviewer.show()


WebQryAddon()
