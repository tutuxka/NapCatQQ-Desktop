# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from qfluentwidgets import Action, SystemTrayMenu
from qfluentwidgets import FluentIcon as FIF

if TYPE_CHECKING:
    from src.Ui.MainWindow.Window import MainWindow


class SystemTrayIcon(QSystemTrayIcon):
    """
    ## 系统托盘功能
    """

    def __init__(self, parent: "MainWindow" = None):
        super().__init__(parent=parent)

        # 创建控件
        self.menu = SystemTrayMenu(parent=parent)
        self.menu.addAction(Action(FIF.CLOSE, self.tr("Close NapCat Desktop"), triggered=QApplication.quit))

        # 设置控件
        self.setIcon(parent.windowIcon())
        self.setToolTip("NapCat Desktop")
        self.setContextMenu(self.menu)

