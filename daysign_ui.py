import os
import random
import re
import time
from xml.etree import ElementTree as ET

import httpx
from bs4 import BeautifulSoup
from DrissionPage import Chromium, ChromiumOptions

HOST = os.getenv("SEHUATANG_HOST", "sehuatang.org")
FID = os.getenv("SEHUATANG_FID", 103)
NUM = os.getenv("SEHUATANG_ACCOUNTS_NUM", 1)
REPLY_TIMES = os.getenv("SEHUATANG_REPLY_TIMES", 1)
CHROME_PATH = os.getenv("SEHUATANG_CHROME_PATH", "/usr/bin/google-chrome")

AUTO_REPLIES = (
    "感谢楼主分享好片",
    "感谢分享！！",
    "谢谢分享！",
    "感谢分享感谢分享",
    "必需支持",
    "简直太爽了",
    "感谢分享啊",
    "封面还不错",
    "有点意思啊",
    "封面还不错，支持一波",
    "真不错啊",
    "不错不错",
    "这身材可以呀",
    "终于等到你",
    "不错。。！",
    "謝謝辛苦分享",
    "赏心悦目",
    "快乐无限~~",
    "這怎麼受的了啊",
    "谁也挡不住！",
    "感謝分享",
    "分享支持。",
    "这谁顶得住啊",
    "这是要精J人亡啊！",
    "饰演很赞",
    "這系列真有戲",
    "感谢大佬分享",
    "看着不错",
    "感谢老板分享",
    "可以看看",
    "谢谢分享！！！",
    "真是骚气十足",
    "给我看硬了！",
    "这个眼神谁顶得住。",
    "妙不可言",
    "看硬了，确实不错。",
    "等这一部等了好久了！",
    "终于来了，等了好久了。",
    "这一部确实不错",
    "感谢分享这一部资源",
    "剧情还是挺OK的。",
)


def retrieve_cookies_from_fetch(s: str) -> dict:
    def parse_fetch(s: str) -> dict:
        ans = {}
        exec(s, {"fetch": lambda _, o: ans.update(o), "null": None})
        return ans

    cookie_str = parse_fetch(s)["headers"]["cookie"]  # type: ignore
    return dict(s.strip().split("=", maxsplit=1) for s in cookie_str.split(";"))


def preprocess_text(text) -> str:
    if "xml" not in text:
        return text

    try:
        root = ET.fromstring(text)
        cdata = root.text
        soup = BeautifulSoup(cdata, "html.parser")
        for script in soup.find_all("script"):
            script.decompose()
        return soup.get_text()
    except:  # noqa: E722
        return text


def push_notification(title: str, content: str) -> None:
    r = httpx.post(
        url=os.getenv("BARK"),
        json={
            "title": title,
            "body": content,
            "icon": os.getenv("BARK_ICON"),
        },
    )
    r.raise_for_status()


def main(index):
    sign_result = None
    try:
        # 1️⃣ 获取cookies
        cookies = {}
        cookies_key = f"SEHUATANG_FETCH_COOKIES_{index}"

        cookies = retrieve_cookies_from_fetch(os.getenv(cookies_key))
        cookies.pop("cf_clearance")
        cookies["domain"] = HOST

        print(cookies)

        # 2️⃣ 启动浏览器
        co = ChromiumOptions().set_browser_path(CHROME_PATH)
        co.headless()
        co.set_argument("--no-sandbox")
        # co.set_argument("--ozone-platform=wayland")

        tab = Chromium(co).latest_tab
        ua = tab.user_agent.replace("Headless", "")
        tab.set.user_agent(ua)

        # 3️⃣ 设置cookies
        tab.get(f"https://{HOST}")
        print(tab.title)
        tab.set.cookies(cookies)

        # 4️⃣ 获取帖子ID
        tab.get(f"https://{HOST}/forum.php?mod=forumdisplay&fid={FID}")
        thread_eles = tab.eles("@id^normalthread_")
        tids = [ele.attr("id").split("_")[-1] for ele in thread_eles]
        tid = random.choice(tids)
        print(f"choose tid = {tid} to comment")

        # 5️⃣ 发表回复
        tab.get(f"https://{HOST}/forum.php?mod=viewthread&tid={tid}&extra=page%3D1")
        message = random.choice(AUTO_REPLIES)
        reply_ele = tab.ele("@id=fastpostmessage")
        while reply_ele.value != message:
            tab.ele("@id=fastpostmessage").input(message)
            tab.wait(1)
        tab.ele("@id=fastpostsubmit").click()

        # 5️⃣ 签到
        tab.get(f"https://{HOST}/plugin.php?id=dd_sign")
        tab.ele("@class=ddpc_sign_btn_red").click()
        id_hash = tab.ele("@id:seqaajs_").attr("id").split("_")[-1]
        question = tab.ele(f"css:#secqaa_{id_hash} td").texts()[-1]
        # print(question)
        expr = re.search(r"([\d\s+\-*/]+)", question).group(1)
        answer = eval(expr)
        # print(answer)
        tab.ele(f"@id=secqaaverify_{id_hash}").input(answer)
        tab.listen.start("signsubmit=yes")
        tab.ele("@@tag()=button@@text()=签到").click()

        # 6️⃣ 签到结果
        packet = tab.listen.wait()
        sign_result = packet.response.body
        print(sign_result)
        tab.listen.stop()
    except Exception as e:
        if sign_result:
            # 7️⃣ 推送消息
            if "签到成功" in sign_result:
                title, message = (
                    "每日签到",
                    re.findall(r"'(签到成功.+?)'", sign_result, re.MULTILINE)[0],
                )
            else:
                title, message = "签到失败", sign_result
        else:
            title, message = "签到异常", str(e)
    finally:
        prefix_message = f"酒保{index} "
        push_notification(f"{prefix_message}{title}", message)


if __name__ == "__main__":
    for i in range(int(NUM)):
        index = i + 1
        main(index)
        sleep_time = random.uniform(60 * 2, 60 * 5)
        if i != NUM - 1:
            time.sleep(sleep_time)
