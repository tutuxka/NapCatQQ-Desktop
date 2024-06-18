# -*- coding: utf-8 -*-
import json
from typing import List, Tuple, TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from creart import it
from qfluentwidgets import ScrollArea, InfoBar, InfoBarPosition, FlowLayout, PushButton

from src.Core.Config.ConfigModel import Config
from src.Core.PathFunc import PathFunc
from src.Ui.BotListPage.BotCard import BotCard

if TYPE_CHECKING:
    from src.Ui.BotListPage import BotListWidget


class BotList(ScrollArea):
    """
    ## BotListWidget 内部的机器人列表

    自动读取配置文件中已有的的机器人配置
    """

    def __init__(self, parent):
        """
        ## 初始化
        """
        super().__init__(parent=parent)
        # 创建属性
        self.botList: List[Config] = []
        self.botCardList: List[BotCard] = []

        # 调用方法
        self._createView()
        self._initWidget()

    def _initWidget(self):
        """
        ## 设置 ScrollArea
        """
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _createView(self):
        """
        ## 构建并设置 ScrollArea 所需的 widget
        """
        self.view = QWidget(self)
        self.cardLayout = FlowLayout(self.view, True)
        self.cardLayout.setContentsMargins(0, 0, 0, 0)
        self.cardLayout.setSpacing(4)
        self.view.setObjectName("BotListView")
        self.view.setLayout(self.cardLayout)

    def updateList(self):
        """
        ## 更新机器人列表
        """
        self._parseList()

        if not self.botCardList:
            # 如果是首次运行, 则直接添加到布局和 botCardList
            for bot in self.botList:
                card = BotCard(bot, self)
                self.cardLayout.addWidget(card)
                self.botCardList.append(card)
            return

        QQList = [card.config.bot.QQID for card in self.botCardList]
        for bot_config in self.botList:
            # 遍历并判断是否有新增的 bot
            if bot_config.bot.QQID in QQList:
                # 如果属于则直接跳过
                continue

            # 不属于则就属于新增, 创建 card 并 添加到布局
            card = BotCard(bot_config)
            self.cardLayout.addWidget(card)
            self.botCardList.append(card)

        for card in self.botCardList:
            # 遍历并判断是否有减少的 bot
            if card.config in self.botList:
                # 属于则就是没有被删除, 跳过
                continue

            # 移除出布局并删除
            self.botCardList.remove(card)
            self.cardLayout.removeWidget(card)
            card.deleteLater()

        # 刷新一次布局
        self.cardLayout.update()

    def _parseList(self):
        """
        ## 解析机器人配置(如果有)
        """
        try:
            # 读取配置列表
            with open(str(it(PathFunc).bot_config_path), "r", encoding="utf-8") as f:
                bot_configs = json.load(f)
            if bot_configs:
                # 如果从文件加载的 bot_config 不为空则执行使用Config和列表表达式解析
                self.botList: List[Config] = [Config(**config) for config in bot_configs]
                self.parent().parent().showSuccess(
                    title=self.tr("Load the list of bots"),
                    content=self.tr("The list of bots was successfully loaded"),
                )
            else:
                # 创建信息条
                self.parent().parent().showInfo(
                    title=self.tr("There are no bot configuration items"),
                    content=self.tr("You'll need to add it in the Add bot page"),
                )
                self.botList = []

        except FileNotFoundError:
            # 如果文件不存在则创建一个
            with open(str(it(PathFunc).bot_config_path), "w", encoding="utf-8") as f:
                json.dump([], f, indent=4)
            self.botList = []

        except ValueError as e:
            # 如果配置文件解析失败则提示错误信息并覆盖原有文件
            self.parent().parent().showError(self.tr("Unable to load bot list"), str(e))
            with open(str(it(PathFunc).bot_config_path), "w", encoding="utf-8") as f:
                json.dump([], f, indent=4)
            self.botList = []
