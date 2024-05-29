

import asyncio
import json
from flet import *
from quiz_generator import Quizgen
from analysis_Code import Analysis_Code
from V3_5_28 import OCRVideoPlayer, VideoOCR
import flet as ft

class uiMain:
    def __init__(self):
        self.quizGen = Quizgen()
        self.ac = Analysis_Code()
        self.urls = [
            "https://user-images.githubusercontent.com/28951144/229373720-14d69157-1a56-4a78-a2f4-d7a134d7c3e9.mp4",
            "https://github.com/SMU-AI-X-Advanced/multi-channel-video-analyze/raw/main/only_code.mp4",
            "https://github.com/SMU-AI-X-Advanced/video/raw/master/ocr_audio.mp4",

        ]
        self.ocr = VideoOCR(self.urls)

    async def main(self, page: Page):
        self.userCode = ''

        async def analCode(e):
            page.go("/analCode")
            self.userCode = user_code_input.value
            ac = await getac(user_code_input.value)
            page.update()
            return ac

        page.title = "다해 PYTHON 인강"
        page.window_width = 1500
        image = Image(src="/assets/image/main_page.png", width=400, height=400, fit=ImageFit.COVER)
        id_TF = TextField(label="아이디를 입력해주세요.")
        quiz = ''
        user_code_input = TextField(label="코드 입력 하세요", multiline=True,
                                    suffix=ElevatedButton("답안 제출 하기", on_click=analCode))

        async def login_btn(e):
            print("버튼눌림")
            page.go("/login")
            page.update()
            await self.run_ocr_background()

        page.add(
            Row([
                Image(src="./assets/image/main_page.png", width=400, height=400, fit=ImageFit.CONTAIN),
                Text("로그인 화면", size=20, color=colors.WHITE, bgcolor=colors.BLUE_400, weight=FontWeight.BOLD)
            ]),
            id_TF,
            ElevatedButton("로그인", on_click=login_btn)
        )

        async def getAnalCode():
            return self.ac.getAC()

        def check_item_clicked(e):
            e.control.checked = not e.control.checked
            page.update()

        pb = PopupMenuButton(
            items=[
                PopupMenuItem(ElevatedButton("퀵 정렬")),
                PopupMenuItem(),
                PopupMenuItem(ElevatedButton("삽입 정렬")),
                PopupMenuItem(),
                PopupMenuItem(ElevatedButton("버블 정렬")),
                PopupMenuItem(),
            ]
        )

        def sel_lecture(e, lecture_num):
            page.go(f"/lecture{lecture_num}")
            page.update()

        async def quizGen(e):
            quiz = await self.quizGen.getQuiz()
            page.go("/quizGen")
            page.update()
            return quiz

        def getQu():
            return self.quizGen.getQ()

        async def getac(user_code):
            quiz = getQu()
            return await self.ac.run(quiz=quiz, user_code=user_code)

        async def route_change(e):
            print("login은 눌리네")
            page.views.clear()
            if page.route == "/login":
                page.views.append(
                    View(
                        "/login",
                        [
                            AppBar(title=Text("파이썬 기초 강의"), bgcolor=colors.SURFACE_VARIANT),
                            Text("쉽고 간편하게 배우자 다해 코딩 과외", style="bodyMedium", size=20),
                            Text("\n\n기초 파이썬 프로그래밍 강의\n기초부터 심화 학습까지"),
                            Row([Text("1주차강의(변수)"), ElevatedButton("1강", on_click=lambda e: sel_lecture(e, 1))]),
                            Row([Text("2주차강의(상수)"), ElevatedButton("2강", on_click=lambda e: sel_lecture(e, 2))]),
                            Row([Text("3주차강의(정렬)"), ElevatedButton("3강", on_click=lambda e: sel_lecture(e, 3))]),
                            Row([Text("4주차강의(몰랑)"), ElevatedButton("4강", on_click=lambda e: sel_lecture(e, 4))]),
                            Row([Text("5주차강의(하기)"), ElevatedButton("5강", on_click=lambda e: sel_lecture(e, 5))]),
                            Row([Text("6주차강의(싫어)"), ElevatedButton("6강", on_click=lambda e: sel_lecture(e, 6))]),
                        ],
                    )
                )

            elif page.route == "/lecture1":
                self.player = OCRVideoPlayer(page, self.urls)
                self.player.setup_ui(inital_index=0)
                page.views.append(
                    View(
                        "/lecture1",
                        [
                            AppBar(
                                title=Text("1강 변수", size=30), bgcolor=colors.SURFACE_VARIANT
                            ),
                            self.player.video_playlist,
                            self.player.button_container,
                            self.player.ocr_results,
                            ElevatedButton("강의 복습 및 퀴즈 풀기", on_click=quizGen)
                        ],
                    )
                )
                page.update()

            elif page.route == "/quizGen":
                page.views.append(
                    View(
                        "/quizGen",
                        [
                            AppBar(title=Text("강의 복습 및 퀴즈 풀기 ", size=30), bgcolor=colors.SURFACE_VARIANT),
                            Text(getQu()),
                            user_code_input,
                        ],
                    )
                )
            elif page.route == "/analCode":
                page.views.append(
                    View(
                        "/analCode",
                        [
                            AppBar(title=Text("사용자 코드 분석 결과 ", size=30), bgcolor=colors.SURFACE_VARIANT),
                            Text("*사용자가 입력한 코드*", size=22),
                            Text(user_code_input.value),
                            Text("\n*분석 결과*", size=22),
                            Text(await getAnalCode()),
                        ],
                    )
                )
            page.update()

        def view_pop(e):
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)

        page.on_route_change = route_change
        page.on_view_pop = view_pop

        # 페이지 초기화 및 업데이트
        page.update()

    async def run_ocr_background(self):
        # OCR 작업을 비동기로 실행
        await self.ocr.process_ocr()

if __name__ == "__main__":
    ui = uiMain()
    ft.app(target=ui.main, view=AppView.WEB_BROWSER, assets_dir="assets")

