import os
import logging

from .config import Config
from .common import Common
from .audio import Audio
from .gpt_model.gpt import GPT_MODEL
from .logger import Configure_logger


class My_handle():
    def __init__(self, config_path):
        self.common = Common()
        self.config = Config(config_path)
        self.audio = Audio()

        # 日志文件路径
        file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        Configure_logger(file_path)

        self.proxy = None
        # self.proxy = {
        #     "http": "http://127.0.0.1:10809",
        #     "https": "http://127.0.0.1:10809"
        # }

        try:

            # 设置会话初始值
            self.session_config = {'msg': [{"role": "system", "content": self.config.get('chatgpt', 'preset')}]}
            self.sessions = {}
            self.current_key_index = 0

            # 直播间号
            self.room_id = self.config.get("room_display_id")

            self.before_prompt = self.config.get("before_prompt")
            self.after_prompt = self.config.get("after_prompt")

            # 过滤配置
            self.filter_config = self.config.get("filter")

            self.chat_type = self.config.get("chat_type")

            self.need_lang = self.config.get("need_lang")

            # 优先本地问答库匹配
            self.local_qa = self.config.get("local_qa")

            # openai
            self.openai_config = self.config.get("openai")
            # chatgpt
            self.chatgpt_config = self.config.get("chatgpt")
            # claude
            self.claude_config = self.config.get("claude")
            # chatterbot
            self.chatterbot_config = self.config.get("chatterbot")
            # chatglm
            self.chatglm_config = self.config.get("chatglm")
            # chat_with_file
            self.chat_with_file_config = self.config.get("chat_with_file")
            self.text_generation_webui_config = self.config.get("text_generation_webui")

            # 音频合成使用技术
            self.audio_synthesis_type = self.config.get("audio_synthesis_type")

            self.sd_config = self.config.get("sd")

            logging.info(f"配置数据加载成功。")
        except Exception as e:
            logging.info(e)

        # 设置GPT_Model全局模型列表
        GPT_MODEL.set_model_config("openai", self.openai_config)
        GPT_MODEL.set_model_config("chatgpt", self.chatgpt_config)
        GPT_MODEL.set_model_config("claude", self.claude_config)
        GPT_MODEL.set_model_config("chatglm", self.chatglm_config)
        GPT_MODEL.set_model_config("text_generation_webui", self.text_generation_webui_config)

        # 聊天相关类实例化
        if self.chat_type == "chatgpt":
            self.chatgpt = GPT_MODEL.get("chatgpt")

        elif self.chat_type == "claude":
            self.claude = GPT_MODEL.get(self.chat_type)

            # 初次运行 先重置下会话
            if not self.claude.reset_claude():
                logging.error("重置Claude会话失败喵~")

        elif self.chat_type == "chatterbot":
            from chatterbot import ChatBot  # 导入聊天机器人库
            try:
                self.bot = ChatBot(
                    self.chatterbot_config["name"],  # 聊天机器人名字
                    database_uri='sqlite:///' + self.chatterbot_config["db_path"]  # 数据库URI，数据库用于存储对话历史
                )
            except Exception as e:
                logging.info(e)
                exit(0)

        elif self.chat_type == "chatglm":
            self.chatglm = GPT_MODEL.get(self.chat_type)

        elif self.chat_type == "chat_with_file":
            from utils.chat_with_file.chat_with_file import Chat_with_file
            self.chat_with_file = Chat_with_file(self.chat_with_file_config)

        elif self.chat_type == "text_generation_webui":
            self.text_generation_webui = GPT_MODEL.get(self.chat_type)

        elif self.chat_type == "game":
            exit(0)

        if self.sd_config["enable"]:
            from utils.sd import SD

            self.sd = SD(self.sd_config)

        # 日志文件路径
        self.log_file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        if os.path.isfile(self.log_file_path):
            logging.info(f'{self.log_file_path} 日志文件已存在，跳过')
        else:
            with open(self.log_file_path, 'w') as f:
                f.write('')
                logging.info(f'{self.log_file_path} 日志文件已创建')

        self.commit_file_path = "./log/commit-" + self.common.get_bj_time(1) + ".txt"
        if os.path.isfile(self.commit_file_path):
            logging.info(f'{self.commit_file_path} 弹幕文件已存在，跳过')
        else:
            with open(self.commit_file_path, 'w') as f:
                f.write('')
                logging.info(f'{self.commit_file_path} 弹幕文件已创建')

    def get_room_id(self):
        return self.room_id

    def find_answer(self, question, qa_file_path):
        """从本地问答库中搜索问题的答案

        Args:
            question (_type_): 问题文本
            qa_file_path (_type_): 问答库的路径

        Returns:
            _type_: 答案文本 或 None
        """
        with open(qa_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        for i in range(0, len(lines), 2):
            if question.strip() == lines[i].strip():
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
                else:
                    return None

        return None

    def commit_handle(self, user_name, content):
        # 匹配本地问答库
        if self.local_qa == True:
            # 输出当前用户发送的弹幕消息
            logging.info(f"[{user_name}]: {content}")
            tmp = self.find_answer(content, "data/本地问答库.txt")
            if tmp != None:
                resp_content = tmp
                # 将 AI 回复记录到日志文件中
                with open(self.commit_file_path, "r+", encoding="utf-8") as f:
                    tmp_content = f.read()
                    # 将指针移到文件头部位置（此目的是为了让直播中读取日志文件时，可以一直让最新内容显示在顶部）
                    f.seek(0, 0)
                    # 不过这个实现方式，感觉有点低效
                    # 设置单行最大字符数，主要目的用于接入直播弹幕显示时，弹幕过长导致的显示溢出问题
                    max_length = 20
                    resp_content_substrings = [resp_content[i:i + max_length] for i in
                                               range(0, len(resp_content), max_length)]
                    resp_content_joined = '\n'.join(resp_content_substrings)

                    # 根据 弹幕日志类型进行各类日志写入
                    if self.config.get("commit_log_type") == "问答":
                        f.write(
                            f"[{user_name} 提问]:{content}\n[AI回复{user_name}]:{resp_content_joined}\n" + tmp_content)
                    elif self.config.get("commit_log_type") == "问题":
                        f.write(f"[{user_name} 提问]:{content}\n" + tmp_content)
                    elif self.config.get("commit_log_type") == "回答":
                        f.write(f"[AI回复{user_name}]:{resp_content_joined}\n" + tmp_content)

                message = {
                    "type": self.audio_synthesis_type,
                    "data": self.config.get(self.audio_synthesis_type),
                    "config": self.filter_config,
                    "user_name": user_name,
                    "content": resp_content
                }

                # 音频合成（edge-tts / vits）并播放
                self.audio.audio_synthesis(message)

                return

        # 画图模式
        if content.startswith(self.sd_config["trigger"]):
            # 含有违禁词/链接
            if self.common.profanity_content(content) or self.common.check_sensitive_words2(
                    self.filter_config["badwords_path"], content) or \
                    self.common.is_url_check(content):
                logging.warning(f"违禁词/链接：{content}")
                return
        
            if self.sd_config["enable"] == False:
                logging.info("您还未启用SD模式，无法使用画画功能")
                return None
            else:
                # 输出当前用户发送的弹幕消息
                logging.info(f"[{user_name}]: {content}")

                self.sd.process_input(content[3:])
                return None

        # 判断弹幕是否以xx起始，如果不是则返回
        if self.filter_config["before_must_str"] and not any(
                content.startswith(prefix) for prefix in self.filter_config["before_must_str"]):
            return
        else:
            for prefix in self.filter_config["before_must_str"]:
                if content.startswith(prefix):
                    content = content[len(prefix):]  # 删除匹配的开头
                    break

        # 判断弹幕是否以xx结尾，如果不是则返回
        if self.filter_config["after_must_str"] and not any(
                content.endswith(prefix) for prefix in self.filter_config["after_must_str"]):
            return
        else:
            for prefix in self.filter_config["after_must_str"]:
                if content.endswith(prefix):
                    content = content[:-len(prefix)]  # 删除匹配的结尾
                    break

        # 输出当前用户发送的弹幕消息
        logging.info(f"[{user_name}]: {content}")

        # 全为标点符号
        if self.common.is_punctuation_string(content):
            return

        # 换行转为,
        content = content.replace('\n', ',')

        # 含有违禁词/链接
        if self.common.profanity_content(content) or self.common.check_sensitive_words2(
                self.filter_config["badwords_path"], content) or \
                self.common.is_url_check(content):
            logging.warning(f"违禁词/链接：{content}")
            return

        # 语言检测
        if self.common.lang_check(content, self.need_lang) is None:
            logging.warning("语言检测不通过，已过滤")
            return

        # 根据聊天类型执行不同逻辑
        if self.chat_type == "chatgpt":
            content = self.before_prompt + content + self.after_prompt
            # 调用gpt接口，获取返回内容
            resp_content = self.chatgpt.get_gpt_resp(user_name, content)
            if resp_content is not None:
                # 输出 ChatGPT 返回的回复消息
                logging.info(f"[AI回复{user_name}]：{resp_content}")
            else:
                resp_content = ""
                logging.info("警告：chatgpt无返回")
        elif self.chat_type == "claude":
            content = self.before_prompt + content + self.after_prompt
            resp_content = self.claude.get_claude_resp(content)
            if resp_content is not None:
                # 输出 返回的回复消息
                logging.info(f"[AI回复{user_name}]：{resp_content}")
            else:
                resp_content = ""
                logging.info("警告：claude无返回")
        elif self.chat_type == "chatterbot":
            # 生成回复
            resp_content = self.bot.get_response(content).text
            logging.info(f"[AI回复{user_name}]：{resp_content}")

        elif self.chat_type == "chatglm":
            # 生成回复
            resp_content = self.chatglm.get_chatglm_resp(content)
            logging.info(f"[AI回复{user_name}]：{resp_content}")

        elif self.chat_type == "chat_with_file":
            resp_content = self.chat_with_file.get_model_resp(content)
            print(f"[AI回复{user_name}]：{resp_content}")

        elif self.chat_type == "text_generation_webui":
            # 生成回复
            resp_content = self.text_generation_webui.get_text_generation_webui_resp(content)
            logging.info(f"[AI回复{user_name}]：{resp_content}")

        elif self.chat_type == "game":
            return
            g1 = game1()
            g1.parse_keys_and_simulate_key_press(content.split(), 2)

            return
        else:
            # 复读机
            resp_content = content

        # logger.info("resp_content=" + resp_content)

        # 将 AI 回复记录到日志文件中
        with open(self.commit_file_path, "r+", encoding="utf-8") as f:
            tmp_content = f.read()
            # 将指针移到文件头部位置（此目的是为了让直播中读取日志文件时，可以一直让最新内容显示在顶部）
            f.seek(0, 0)
            # 不过这个实现方式，感觉有点低效
            # 设置单行最大字符数，主要目的用于接入直播弹幕显示时，弹幕过长导致的显示溢出问题
            max_length = 20
            resp_content_substrings = [resp_content[i:i + max_length] for i in range(0, len(resp_content), max_length)]
            resp_content_joined = '\n'.join(resp_content_substrings)

            # 根据 弹幕日志类型进行各类日志写入
            if self.config.get("commit_log_type") == "问答":
                f.write(f"[{user_name} 提问]:{content}\n[AI回复{user_name}]:{resp_content_joined}\n" + tmp_content)
            elif self.config.get("commit_log_type") == "问题":
                f.write(f"[{user_name} 提问]:{content}\n" + tmp_content)
            elif self.config.get("commit_log_type") == "回答":
                f.write(f"[AI回复{user_name}]:{resp_content_joined}\n" + tmp_content)

        message = {
            "type": self.audio_synthesis_type,
            "data": self.config.get(self.audio_synthesis_type),
            "config": self.filter_config,
            "user_name": user_name,
            "content": resp_content
        }

        # 音频合成（edge-tts / vits）并播放
        self.audio.audio_synthesis(message)
