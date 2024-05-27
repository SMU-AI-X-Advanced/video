import flet as ft
import asyncio
import subprocess
import json
import cv2
import pytesseract
import numpy as np
import difflib

# Tesseract OCR 설정
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class VideoOCR:
    def __init__(self, url):
        self.url = url
        self.detected_texts = [] # 인식 텍스트 저장

    #  url 동영상 프레임,fps 가져오는 비동기함수
    async def get_video_resolution(self,index):
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate',
            '-of', 'json',
            self.url[index]
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise Exception("Failed to get video resolution")
        info = json.loads(result.stdout)
        width = info['streams'][0]['width']
        height = info['streams'][0]['height']
        r_frame_rate = info['streams'][0]['r_frame_rate']
        numerator, denominator = map(int, r_frame_rate.split('/'))
        fps = numerator / denominator if denominator != 0 else 0
        return width, height, fps


    # ocr 하는 함수
    def enhanced_ocr(self,frame):
        config = ('-l eng --oem 3 --psm 3 -c preserve_interword_spaces=1')
        text = pytesseract.image_to_string(frame, config=config)
        print(text)
        return text
    # 비동기식 ocr 수행 함수
    async def process_video(self, index,frame_sampling_rate=10, similarity_threshold=0.23):
        width, height, fps = await self.get_video_resolution(int(index)) # 동영상 정보 가져오기
        ffmpeg_command = [
            'ffmpeg',
            '-i', self.url[index],
            '-loglevel', 'quiet',
            '-an',
            '-f', 'image2pipe',
            '-pix_fmt', 'bgr24',
            '-vcodec', 'rawvideo',
            '-'
        ]
        pipe = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, bufsize=10**8) ## ffmpeg 실행
        frame_size = width * height * 3

        prev_frame = None
        frame_count = 0
        current_text = ""
        start_time = None

        while True:
            raw_frame = pipe.stdout.read(frame_size)
            if not raw_frame:
                break
            frame = np.frombuffer(raw_frame, dtype='uint8').reshape((height, width, 3))

            if frame_count % frame_sampling_rate == 0 and prev_frame is not None:
                if self.detect_significant_change(frame, prev_frame,50000):
                    text = self.enhanced_ocr(frame)

                    if text.strip() and (not current_text or difflib.SequenceMatcher(None, text, current_text).ratio() < similarity_threshold):
                        if current_text:
                            self.detected_texts.append({
                                "start_timestamp": start_time,
                                "end_timestamp": frame_count / fps,
                                "text": current_text
                            })
                        current_text = text
                        start_time = frame_count / fps
                prev_frame = frame
            else:
                prev_frame = frame
            frame_count += 1

        if current_text:
            self.detected_texts.append({
                "start_timestamp": start_time,
                "end_timestamp": frame_count / fps,
                "text": current_text
            })
        print(self.detected_texts)

        pipe.terminate()
    # 프레임간 유의미 차이 감지함수
    def detect_significant_change(self, current_frame, prev_frame, threshold=50000):
        diff = cv2.absdiff(current_frame, prev_frame)
        return np.sum(diff) > threshold

class OCRVideoPlayer:
    def __init__(self, page: ft.Page, urls):
        self.page = page
        self.urls = urls
        self.current_video_index = 0
        self.video_players = []
        self.setup_ui()

    def setup_ui(self):
        self.playlist = [ft.VideoMedia(url) for url in self.urls]
        self.video_player = ft.Video(
            expand=True,
            autoplay=False,
            playlist=self.playlist,
            width=700,
            height=500,
            muted=True,


        )
        #수정
        self.video_container = ft.Container(content=self.video_player, width=700, height=500)
        # 재생목록 설정
        self.playlist_container = ft.Container(
            content=ft.Column([
                ft.TextField(value="재생목록", text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(text="반복문", width=250, on_click=lambda e, i=int(0): self.change_video(i)),
                ft.ElevatedButton(text="조건문", width=250, on_click=lambda e, i=int(1): self.change_video(i)),
                ft.ElevatedButton(text="재귀함수", width=250, on_click=lambda e, i=int(2): self.change_video(i)),
            ]),
            alignment=ft.Alignment(0, 1),
            width=250,
            height=500
        )
        # 버튼 컨트롤러
        self.button_container = ft.Container(
            content=ft.Row([
                ft.ElevatedButton(text="Previous", on_click=lambda e: self.video_player.previous()),
                ft.ElevatedButton(text="Play/Pause", on_click=lambda e: self.video_player.play_or_pause()),
                ft.ElevatedButton(text="Next", on_click=lambda e: self.video_player.next()),
            ], alignment=ft.MainAxisAlignment.CENTER),
            width=700,
            margin=5
        )
        # 비디오와 재생목록 레이아웃
        self.video_playlist = ft.Row([
            self.video_container,
            self.playlist_container
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # 전체 페이지 구성
        self.ocr_results = ft.ListView(expand=True)
        self.page.add(self.video_playlist)
        self.page.add(self.button_container)
        self.page.add(self.ocr_results)

    # 동영상 변경함수 , ocr동작 포함
    def change_video(self, video_index): # 동영상이 바뀔때 마다 OCR를 수핸한다. 근데 맨처음이면 시작을해야하는데 그거 구현해야함

        self.video_player.jump_to(video_index)
        self.current_video_index = int(video_index)
        self.ocr_results.controls.clear()
        #self.ocr_results.controls.clear() #이전 결과 지우기
        self.page.update()
        asyncio.run(self.process_ocr(self.current_video_index))  # 이부분이 비동기 ocr 수행


    async def process_ocr(self, index):
        ocr_processor = VideoOCR(self.urls)
        await ocr_processor.process_video(index)
        self.update_ui(ocr_processor.detected_texts)
    #  ocr 결과 업데이트
    def update_ui(self, ocr_data):
        self.ocr_results.controls.clear()
        for item in ocr_data:
            ocr_text_field = ft.TextField(
                value=item["text"],
                # value=str(n),
                multiline=True,
                width=650,
                height=80
            )

            go_button = ft.ElevatedButton(
                text="Go",
                on_click=lambda e, t=item["start_timestamp"]: self.jump_to_ocr_time(e, t),
                width=45,
                height=80
            )
            row = ft.Row([
                ocr_text_field,
                go_button
            ], )
            self.ocr_results.controls.append(row)
        self.page.update()
    # 텍스트에서 ocr 인식 시작지점으로 이동함수
    def jump_to_ocr_time(self, e, start_time):
        gotime = start_time * 1000
        self.video_player.seek(int(gotime))

        # 비디오 끝 이벤트 처리기

def main(page: ft.Page):
    urls = [
        "https://github.com/SMU-AI-X-Advanced/multi-channel-video-analyze/raw/main/only_code.mp4",
        "https://github.com/SMU-AI-X-Advanced/video/raw/master/ocr_audio.mp4",
        "https://user-images.githubusercontent.com/28951144/229373720-14d69157-1a56-4a78-a2f4-d7a134d7c3e9.mp4",

    ]
    OCRVideoPlayer(page, urls)

if __name__ == "__main__":
    ft.app(main)
