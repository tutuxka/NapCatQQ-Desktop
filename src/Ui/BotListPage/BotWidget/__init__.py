# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, List

from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
from creart import it
from qfluentwidgets import (
    SegmentedWidget, TransparentToolButton, FluentIcon, ToolTipFilter, PrimaryPushButton, InfoBar, InfoBarPosition,
    PushButton, StateToolTip
)

from src.Core.Config.ConfigModel import Config
from src.Core.PathFunc import PathFunc
from src.Ui.BotListPage.BotWidget.BotSetupPage import BotSetupPage
from src.Ui.StyleSheet import StyleSheet
from src.Ui.common import CodeEditor, LogHighlighter

from src.Core.Config import cfg


class BotWidget(QWidget):
    """
    ## 机器人卡片对应的 Widget
    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.isRun = False  # 用于标记机器人是否在运行
        # 创建所需控件
        self._createView()
        self._createPivot()
        self._createButton()

        self.vBoxLayout = QVBoxLayout()
        self.hBoxLayout = QHBoxLayout()
        self.buttonLayout = QHBoxLayout()

        # 调用方法
        self._setLayout()
        self._addTooltips()

        StyleSheet.BOT_WIDGET.apply(self)

    def _createPivot(self) -> None:
        """
        ## 创建机器人 Widget 顶部导航栏
            - routeKey 使用 QQ号 作为前缀保证该 pivot 的 objectName 全局唯一
        """
        self.pivot = SegmentedWidget(self)
        self.pivot.addItem(
            routeKey=self.botInfoPage.objectName(),
            text=self.tr("Bot info"),
            onClick=lambda: self.view.setCurrentWidget(self.botInfoPage)
        )
        self.pivot.addItem(
            routeKey=self.botSetupPage.objectName(),
            text=self.tr("Bot Setup"),
            onClick=lambda: self.view.setCurrentWidget(self.botSetupPage)
        )
        self.pivot.addItem(
            routeKey=self.botLogPage.objectName(),
            text=self.tr("Bot Log"),
            onClick=lambda: self.view.setCurrentWidget(self.botLogPage)
        )
        self.pivot.setCurrentItem(self.botInfoPage.objectName())
        self.pivot.setMaximumWidth(300)

    def _createView(self) -> None:
        """
        ## 创建用于切换页面的 view
        """
        # 创建 view 和 页面
        self.view = QStackedWidget()
        self.botInfoPage = QWidget(self)
        self.botInfoPage.setObjectName(f"{self.config.bot.QQID}_BotWidgetPivot_BotInfo")

        self.botSetupPage = BotSetupPage(self.config, self)

        self.botLogPage = CodeEditor(self)
        self.botLogPage.setObjectName(f"{self.config.bot.QQID}_BotWidgetPivot_BotLog")

        # 将页面添加到 view
        self.view.addWidget(self.botInfoPage)
        self.view.addWidget(self.botSetupPage)
        self.view.addWidget(self.botLogPage)
        self.view.setObjectName("BotView")
        self.view.setCurrentWidget(self.botInfoPage)
        self.view.currentChanged.connect(self._pivotSolt)

    def _createButton(self) -> None:
        """
        ## 创建按钮并设置
        """
        # 创建按钮
        self.runButton = PrimaryPushButton(FluentIcon.POWER_BUTTON, self.tr("Startup"))
        self.stopButton = PushButton(FluentIcon.POWER_BUTTON, self.tr("Stop"))
        self.rebootButton = PrimaryPushButton(FluentIcon.UPDATE, self.tr("Reboot"))
        self.updateConfigButton = PrimaryPushButton(FluentIcon.UPDATE, self.tr("Update config"))  # 更新配置按钮
        self.returnListButton = TransparentToolButton(FluentIcon.RETURN)  # 返回到列表按钮
        self.botSetupSubPageReturnButton = TransparentToolButton(FluentIcon.RETURN)  # 返回到 BotSetup 按钮

        # 连接槽函数
        self.runButton.clicked.connect(self._runButtonSolt)
        self.stopButton.clicked.connect(self._stopButtonSolt)
        self.rebootButton.clicked.connect(self._rebootButtonSolt)
        self.updateConfigButton.clicked.connect(self._updateButtonSolt)
        self.botSetupSubPageReturnButton.clicked.connect(self._botSetupSubPageReturnButtonSolt)
        self.returnListButton.clicked.connect(self._returnListButtonSolt)

        # 隐藏按钮
        self.stopButton.hide()
        self.rebootButton.hide()
        self.updateConfigButton.hide()
        self.botSetupSubPageReturnButton.hide()

    def _addTooltips(self) -> None:
        """
        ## 为按钮添加悬停提示
        """
        self.returnListButton.setToolTip(self.tr("Click Back to list"))
        self.returnListButton.installEventFilter(ToolTipFilter(self.returnListButton))

        self.botSetupSubPageReturnButton.setToolTip(self.tr("Click Back to BotSetup"))
        self.botSetupSubPageReturnButton.installEventFilter(ToolTipFilter(self.botSetupSubPageReturnButton))

    def _runButtonSolt(self):
        """
        ## 启动按钮槽函数

        # 清除已有(如果有)的log
        # 配置环境变量
            - 使用 QProcess.systemEnvironment() 复制一份系统环境变量列表
            - 使用 append 添加 NapCat 所需的 ELECTRON_RUN_AS_NODE=1
        # 创建 QProcess
            - 设置先前配置好的 环境变量
            - 设置启动的程序(QQ)路径
            - 将 NapCat 以参数新式启动
        # 配置 QProcess
            - 设置输出合并
            - 连接日志输出管道
            - 连接结束函数
            - 设置日志高亮
        # 启动 QProcess
            - 进度条设置完成
            - 切换到 botLogPage
        """
        self.botLogPage.clear()

        self.env = QProcess.systemEnvironment()
        self.env.append("ELECTRON_RUN_AS_NODE=1")

        self.process = QProcess(self)
        self.process.setEnvironment(self.env)
        self.process.setProgram(str(Path(self.config.advanced.QQPath) / "QQ.exe"))
        self.process.setArguments(
            [str(Path(cfg.NapCatPath.value) / "napcat.mjs"), "-q", self.config.bot.QQID]
        )
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.finished.connect(self._process_finished)
        self.highlighter = LogHighlighter(self.botLogPage.document())
        # self.stateTooltip = StateToolTip(
        #     self.tr("starting"),
        #     self.tr("I can't eat hot tofu in a hurry"),
        #     self.parent().parent()
        # )
        # self.show()
        self.process.start()
        # self.process.waitForStarted()
        # self.stateTooltip.setContent(self.tr("Successful start!"))
        # self.stateTooltip.setState(True)

        self.isRun = True
        self.view.setCurrentWidget(self.botLogPage)

    def _stopButtonSolt(self):
        """
        ## 停止按钮槽函数
        """
        self.stateTooltip = StateToolTip(
            self.tr("Suspended"),
            self.tr("I can't eat hot tofu in a hurry"),
            self.parent().parent()
        )
        self.process.kill()
        self.process.waitForFinished()
        self.stateTooltip.setContent(self.tr("Stop Successful!"))
        self.stateTooltip.setState(True)

        self.isRun = False
        self.view.setCurrentWidget(self.botInfoPage)

    def _rebootButtonSolt(self):
        """
        ## 重启机器人, 直接调用函数吧
        """
        self._stopButtonSolt()
        self._runButtonSolt()

    def _handle_stdout(self):
        """
        ## 日志管道
        """
        # 获取所有输出
        data = self.process.readAllStandardOutput().data().decode()
        # 匹配并移除 ANSI 转义码
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        data = ansi_escape.sub('', data)
        # 获取 CodeEditor 的 cursor 并移动插入输出内容
        cursor = self.botLogPage.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(data)
        self.botLogPage.setTextCursor(cursor)

    def _process_finished(self, exit_code, exit_status):
        cursor = self.botLogPage.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"进程结束，退出码为 {exit_code}，状态为 {exit_status}")
        self.botLogPage.setTextCursor(cursor)

    def _updateButtonSolt(self) -> None:
        """
        ## 更新按钮的槽函数
        """
        self.newConfig = Config(**self.botSetupPage.getValue())

        # 读取配置列表
        with open(str(it(PathFunc).bot_config_path), "r", encoding="utf-8") as f:
            bot_configs = json.load(f)
            bot_configs = [Config(**config) for config in bot_configs]
        if bot_configs:
            # 如果从文件加载的 bot_config 不为空则进行更新(为空怎么办呢,我能怎么办,崩了呗bushi
            for index, config in enumerate(bot_configs):
                # 遍历配置列表,找到一样则替换
                if config.bot.QQID == self.newConfig.bot.QQID:
                    bot_configs[index] = self.newConfig
                    break
            # 不可以直接使用 dict方法 转为 dict对象, 内部 WebsocketUrl 和 HttpUrl 不会自动转为 str
            bot_configs = [json.loads(config.json()) for config in bot_configs]
            with open(str(it(PathFunc).bot_config_path), "w", encoding="utf-8") as f:
                json.dump(bot_configs, f, indent=4)
            # 更新成功提示
            InfoBar.success(
                title=self.tr("Update success"),
                content=self.tr("The updated configuration is successful"),
                orient=Qt.Orientation.Vertical,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=2000,
                parent=self.parent().parent()
            )
        else:
            # 为空报错
            InfoBar.error(
                title=self.tr("Update error"),
                content=self.tr("Data loss within the profile"),
                orient=Qt.Orientation.Vertical,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=50000,
                isClosable=True,
                parent=self.parent().parent()
            )

    @staticmethod
    def _returnListButtonSolt() -> None:
        """
        ## 返回列表按钮的槽函数
        """
        from src.Ui.BotListPage.BotListWidget import BotListWidget
        it(BotListWidget).view.setCurrentIndex(0)
        it(BotListWidget).topCard.breadcrumbBar.setCurrentIndex(0)
        it(BotListWidget).topCard.updateListButton.show()

    def _botSetupSubPageReturnButtonSolt(self) -> None:
        """
        ## BotSetup 页面中子页面返回按钮的槽函数
        """
        self.botSetupSubPageReturnButton.hide()
        self.returnListButton.show()
        self.view.setCurrentWidget(self.botSetupPage)

    def _pivotSolt(self, index: int) -> None:
        """
        ## pivot 切换槽函数
        """
        widget = self.view.widget(index)
        self.pivot.setCurrentItem(widget.objectName())

        # 定义页面对应的操作字典
        page_actions = {
            self.botInfoPage.objectName(): {
                'returnListButton': 'show',
                'updateConfigButton': 'hide',
                'botSetupSubPageReturnButton': 'hide',
                'runButton': 'hide' if self.isRun else 'show',
                'stopButton': 'show' if self.isRun else 'hide',
                'rebootButton': 'show' if self.isRun else 'hide'
            },
            self.botSetupPage.objectName(): {
                'updateConfigButton': 'show',
                'botSetupSubPageReturnButton': 'show',
                'returnListButton': 'hide',
                'runButton': 'hide',
                'stopButton': 'hide',
                'rebootButton': 'hide'
            },
            self.botLogPage.objectName(): {
                'returnListButton': 'show',
                'updateConfigButton': 'hide',
                'botSetupSubPageReturnButton': 'hide',
                'runButton': 'hide' if self.isRun else 'show',
                'stopButton': 'show' if self.isRun else 'hide',
                'rebootButton': 'show' if self.isRun else 'hide'
            }
        }

        # 根据 widget.objectName() 执行相应操作
        if widget.objectName() in page_actions:
            actions = page_actions[widget.objectName()]
            for button, action in actions.items():
                getattr(self, button).setVisible(action == 'show')

    def _setLayout(self) -> None:
        """
        ## 对内部进行布局
        """
        self.buttonLayout.setSpacing(8)
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonLayout.addWidget(self.runButton)
        self.buttonLayout.addWidget(self.stopButton)
        self.buttonLayout.addWidget(self.rebootButton)
        self.buttonLayout.addWidget(self.updateConfigButton)
        self.buttonLayout.addWidget(self.returnListButton)
        self.buttonLayout.addWidget(self.botSetupSubPageReturnButton)
        self.buttonLayout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.pivot)
        self.hBoxLayout.addLayout(self.buttonLayout)

        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.addLayout(self.hBoxLayout)
        self.vBoxLayout.addSpacing(10)
        self.vBoxLayout.addWidget(self.view)

        self.setLayout(self.vBoxLayout)
