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
        self.videoOCRIndex=int(0)

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
        #print(text)
        return text


    def save_results(self,detected_texts, output_file):
        with open('vidoe'+str(output_file)+'.json', 'w', encoding='UTF-8') as file:
            json.dump(detected_texts, file, indent=4, ensure_ascii=False)
    # 비동기식 ocr 수행 함수
    async def process_video(self, index,frame_sampling_rate=10, similarity_threshold=0.23):
        # 여기 오디오와 같이할려면
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
                                "code_start_timestamp": start_time,
                                "code_end_timestamp": frame_count / fps,
                                "code_text": current_text
                            })
                        current_text = text
                        start_time = frame_count / fps
                prev_frame = frame
            else:
                prev_frame = frame
            frame_count += 1

        if current_text:
            self.detected_texts.append({
                "code_start_timestamp": start_time,
                "code_end_timestamp": frame_count / fps,
                "code_text": current_text
            })
        #json 저장
        self.save_results(self.detected_texts,index)
        self.detected_texts=[]


        pipe.terminate()
    # 프레임간 유의미 차이 감지함수
    def detect_significant_change(self, current_frame, prev_frame, threshold=50000):
        diff = cv2.absdiff(current_frame, prev_frame)
        return np.sum(diff) > threshold

    async def process_ocr(self):
        await self.process_video(0)
        await self.process_video(1)
        await self.process_video(2)
        print("OCR끝")
    

    

   

class OCRVideoPlayer:
    def __init__(self, page: ft.Page, urls):
        self.page = page
        self.urls = urls
        self.current_video_index = 0
        self.video_player = None
        self.video_playlist = None
        self.button_container = None
        self.ocr_results = None


    def setup_ui(self, inital_index ):
        self.current_video_index = inital_index
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
        
        
        # 재생목록 설정
        self.playlist_container = ft.Container(
            content=ft.Column([
                ft.TextField(value="재생목록", text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(text="반복문", width=250, on_click=lambda e, i=int(0): self.change_video(i)),
                ft.ElevatedButton(text="조건문", width=250, on_click=lambda e, i=int(1): self.change_video(i)),
                ft.ElevatedButton(text="재귀함수", width=250, on_click=lambda e, i=int(2): self.change_video(i)),
                ft.ElevatedButton(text="반복문", width=250, on_click=lambda e, i=int(3): self.change_video(i)),
                ft.ElevatedButton(text="조건문", width=250, on_click=lambda e, i=int(4): self.change_video(i)),
                ft.ElevatedButton(text="재귀함수", width=250, on_click=lambda e, i=int(5): self.change_video(i)),
            ]),
            alignment=ft.alignment.center,
            width=300,
            bgcolor=ft.colors.GREY_100,
            # height=500,
            expand=3
        )
        # 버튼 컨트롤러
        self.button_container = ft.Container(
            content=ft.Row([
                #ft.ElevatedButton(text="Previous", on_click=lambda e: self.video_player.previous()),
                ft.ElevatedButton(text="스크립트", on_click=lambda e: self.update_ui(self.current_video_index)),
                #ft.ElevatedButton(text="Next", on_click=lambda e: self.video_player.next()),
            ],alignment=ft.MainAxisAlignment.CENTER),
            # width=700,
            # margin=5,
            expand=1
        )


        
        self.video_button_container = ft.Container(
            content=ft.Row([
                ft.ElevatedButton(text="Previous", on_click=self.previous_video),
                ft.ElevatedButton(text="Next", on_click=self.next_video),
            ],alignment=ft.MainAxisAlignment.CENTER),
            width=700,
        )
        self.side_bar_container = ft.Container(
            content=ft.Column([
                ft.ElevatedButton(text="재생목록",on_click=self.show_playlist,width=150,),
                ft.ElevatedButton(text="스크립트",on_click=self.show_script,width=150),
                ft.ElevatedButton(text="메모장",width=150),
                ft.ElevatedButton(text="Q&A",width=150),
                
            ])
        )
        
        self.ocr_results = ft.ListView(expand=9)

        # OCR 스크립트
        self.script_Container = ft.Container(
            content=self.ocr_results,
            expand=9,
            border_radius=ft.border_radius.all(10)
        )
        

        # 스크립트와 버튼을 포함한 컨테이너
        self.script_playlist = ft.Container(
            content=ft.Column([
                self.button_container,
                self.script_Container
            ]),
            bgcolor=ft.colors.GREY_100,
            expand=3,
            width=300,
        )
        # 비디오 + 이전 이후 버튼
        self.video_container = ft.Container(
            content=ft.Column([
                self.video_player, # 비디오 + 버튼
                self.video_button_container # 
        ], alignment=ft.MainAxisAlignment.CENTER),
        expand=5
    )


        # 전체 
        self.video_playlist = ft.Row([
            self.video_container,
            self.script_playlist,
            self.side_bar_container        
            
        ], alignment=ft.MainAxisAlignment.START,expand=True)

       
        
    def previous_video(self, e):
        if self.current_video_index > 0:
            self.current_video_index -= 1
            self.change_video(self.current_video_index)
  
    def next_video(self, e):
        if self.current_video_index < len(self.urls) - 1:
            self.current_video_index += 1
            self.change_video(self.current_video_index)

    def show_playlist(self, e):
        self.video_playlist.controls[1] = self.playlist_container
        self.page.update()

    def show_script(self, e):
        self.video_playlist.controls[1] = self.script_playlist
        self.page.update()

    # 동영상 변경함수 , ocr동작 포함
    def change_video(self, video_index):
        self.video_player.jump_to(video_index)

        self.current_video_index = int(video_index)
        self.ocr_results.controls.clear()
        self.page.update()
        #asyncio.create_task(self.process_ocr(self.current_video_index))  # 이부분이 비동기 ocr 수행 a
        #asyncio.run으로하면 runtime에러로 ocr은 안돌아가는데 동영상을 빨리바뀌고 asyncio.create_task로하면 OCR이 다돌때까지 첫번째 동영상화면이다가 다돌아가면 비디오가 바뀜
    def set_video_index(self, index):
        self.current_video_index = index
        self.change_video(index)

    # async def process_ocr(self, index):
    #     ocr_processor = VideoOCR(self.urls)
    #     await ocr_processor.process_video(index)
    #     self.update_ui(ocr_processor.detected_texts)
    #     # 여기에 stt 스크립트 추가가된다면 어떻게될까
    #  ocr 결과 업데이트
    def update_ui(self,index):
        path ='./script_data/extracted_data.json'
        print(path)
        with open(path,'r', encoding='UTF-8') as file:
            data=json.load(file)
        self.ocr_results.controls.clear()
        for item in data:
            ocr_text_field = ft.TextField(
                value=item["topic"],
                # value=str(n),
                multiline=True,
                width=400,
                height=70,
                bgcolor=ft.colors.BLUE_200
            )

            go_button = ft.ElevatedButton(
                '　',
                icon=ft.icons.SEND_ROUNDED,
                icon_color=ft.colors.PINK_400,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=1)),
                on_click=lambda e, t=item["code_start_timestamp"]: self.jump_to_ocr_time(e, t),
                width=50,
                height=70,
                bgcolor=ft.colors.WHITE
            )
            row = ft.Row([
                ocr_text_field,
                go_button],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
                
                )
            self.ocr_results.controls.append(row)
        self.page.update()
    # 텍스트에서 ocr 인식 시작지점으로 이동함수
    def jump_to_ocr_time(self, e, start_time):
        gotime = start_time * 1000
        self.video_player.seek(int(gotime))

        # 비디오 끝 이벤트 처리기

def main(page: ft.Page):
    urls = [
            "https://github.com/SMU-AI-X-Advanced/video/raw/master/assets/dongbinna_sorting_algo.mp4",
            "https://github.com/SMU-AI-X-Advanced/multi-channel-video-analyze/raw/main/only_code.mp4",
            "https://github.com/SMU-AI-X-Advanced/video/raw/master/ocr_audio.mp4",
    ]
    ocr=OCRVideoPlayer(page, urls) ####

if __name__ == "__main__":
    ft.app(main)